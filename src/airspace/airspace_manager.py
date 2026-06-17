"""
Airspace Manager — Master Orchestrator
=======================================
Central integration point for all airspace intelligence.
Coordinates geofencing, TFRs, corridors, altitude, database, and
provides unified interfaces for the rest of the drone brain.

This is the primary module every other component (Perception, Mapping,
Memory, Attention, Prediction, Decision, Planner, Controller)
communicates with for airspace information.
"""

from __future__ import annotations

import time
import math
from typing import List, Optional, Tuple, Dict, Any, Callable
from collections import defaultdict

from .restricted_zone import (
    RestrictedZone, ZoneType, ZoneShape, ZonePriority,
    RiskLevel, ZoneStatus, ZoneAction, AltitudeEnvelope,
    CircleZone, Point2D, PolygonZone,
)
from .geofence import GeofenceEngine
from .temporary_restrictions import TemporaryRestrictionManager, TFRDefinition
from .corridor_manager import CorridorManager, FlightCorridor
from .altitude_manager import AltitudeManager, AltitudeLayer
from .airspace_database import AirspaceDatabase


class AirspaceManager:
    """
    Master orchestrator for the Airspace Intelligence System.

    Integrates:
      - GeofenceEngine: real-time zone enforcement
      - TemporaryRestrictionManager: dynamic TFRs
      - CorridorManager: flight corridors
      - AltitudeManager: altitude layers and optimization
      - AirspaceDatabase: import/export/persistence

    Every module in the drone brain accesses airspace through this class.
    """

    def __init__(self, world_width: float = 100.0, world_height: float = 100.0,
                 max_altitude: float = 200.0):
        self.world_width = world_width
        self.world_height = world_height
        self.max_altitude = max_altitude

        # Sub-managers
        self.geofence = GeofenceEngine(world_width, world_height)
        self.tfr_manager = TemporaryRestrictionManager()
        self.corridor_manager = CorridorManager()
        self.altitude_manager = AltitudeManager(max_altitude)
        self.database = AirspaceDatabase()

        # Mission planning state
        self._mission_plan: Dict[str, Any] = {}
        self._mission_reports: List[Dict[str, Any]] = []
        self._total_distance_saved: float = 0.0
        self._total_distance_extra: float = 0.0
        self._replan_count: int = 0

        # Action tracking
        self._decision_history: List[Dict[str, Any]] = []
        self._current_decisions: List[Dict[str, Any]] = []

        # Event bus integration (optional - set externally)
        self._event_bus = None

        # Initialize with example zones if world bounds are standard
        if world_width >= 100 and world_height >= 100:
            self._load_default_zones()

    # ══════════════════════════════════════════════════════════════
    # INITIALIZATION
    # ══════════════════════════════════════════════════════════════

    def _load_default_zones(self):
        """Load default restricted zones from database into geofence engine."""
        zone_ids = self.database.generate_example_zones(
            self.world_width, self.world_height
        )
        for zid in zone_ids:
            zone = self.database.get_zone(zid)
            if zone:
                self.geofence.add_zone(zone)

    def initialize_from_database(self):
        """Load all database zones into the geofence engine."""
        for zone in self.database.get_all_zones():
            self.geofence.add_zone(zone)

    def reload_zones(self):
        """Reload all zones from database to geofence."""
        self.geofence.clear_zones()
        for zone in self.database.get_all_zones():
            self.geofence.add_zone(zone)

    # ══════════════════════════════════════════════════════════════
    # CONFIGURATION
    # ══════════════════════════════════════════════════════════════

    def set_event_bus(self, event_bus):
        """Connect to the drone's event bus for integration."""
        self._event_bus = event_bus
        # Subscribe to mission events
        if event_bus:
            try:
                event_bus.subscribe("mission.planning", self._on_mission_planning)
                event_bus.subscribe("position.updated", self._on_position_update)
                event_bus.subscribe("emergency.triggered", self._on_emergency)
            except Exception:
                pass

    def _on_mission_planning(self, event):
        """Handle mission planning event."""
        pass

    def _on_position_update(self, event):
        """Handle position update event."""
        pass

    def _on_emergency(self, event):
        """Handle emergency event."""
        pass

    # ══════════════════════════════════════════════════════════════
    # MAIN UPDATE LOOP
    # ══════════════════════════════════════════════════════════════

    def update(self, drone_position: Tuple[float, float],
               drone_altitude: float = 50.0,
               drone_speed: float = 0.0,
               mission_priority: int = 5,
               battery_level: float = 50.0) -> Dict[str, Any]:
        """
        Main update method. Called every simulation step.
        Returns a complete airspace intelligence report.

        Coordinates:
          1. Geofence monitoring (violations, proximity)
          2. TFR updates (expiry, new restrictions)
          3. Altitude advisories
        """
        # 1. Update geofence monitoring
        geofence_report = self.geofence.update(
            drone_position, drone_altitude, drone_speed
        )

        # 2. Update TFR manager
        tfr_report = self.tfr_manager.update(drone_position)

        # 3. Handle TFRs from geofence
        self._sync_tfrs_to_geofence()

        # 4. Compile decision recommendations
        decisions = self._compile_decisions(
            drone_position, drone_altitude,
            drone_speed, mission_priority,
            battery_level, geofence_report,
        )

        # 5. Compute risk analysis
        risk = self._compute_risk_analysis(
            drone_position, drone_altitude,
            drone_speed, geofence_report
        )

        # Build comprehensive report
        report = {
            'timestamp': time.time(),
            'position': drone_position,
            'altitude': drone_altitude,
            'speed': drone_speed,
            'has_violations': geofence_report.get('has_violations', False),
            'violation_count': geofence_report.get('violation_count', 0),
            'violations': geofence_report.get('violations', []),
            'proximity_warnings': geofence_report.get('proximity_warnings', []),
            'recommended_actions': geofence_report.get('recommended_actions', []),
            'active_tfrs': tfr_report.get('active_tfrs', 0),
            'nearby_tfrs': tfr_report.get('nearby_tfrs', 0),
            'tfr_predictions': tfr_report.get('predictions', []),
            'decisions': decisions,
            'risk_analysis': risk,
            'geofence_active_zones': self.geofence.get_zone_count(),
            'airspace_risk_score': risk.get('airspace_risk_score', 0.0),
        }

        # Store decisions for audit
        self._current_decisions = decisions

        # Publish to event bus if connected
        if self._event_bus:
            try:
                self._event_bus.publish("airspace.update", report, "airspace_manager")
            except Exception:
                pass

        return report

    def _sync_tfrs_to_geofence(self):
        """Ensure all active TFRs are registered as geofence zones."""
        for tfr in self.tfr_manager.get_active_tfrs():
            zone = tfr.to_restricted_zone()
            if not self.geofence.get_zone(tfr.tfr_id):
                self.geofence.add_zone(zone)
            elif self.geofence.get_zone(tfr.tfr_id):
                # Update existing zone properties
                existing = self.geofence.get_zone(tfr.tfr_id)
                if existing:
                    existing.expiration_time = zone.expiration_time
                    existing.status = zone.status

    # ══════════════════════════════════════════════════════════════
    # PRE-FLIGHT MISSION VALIDATION
    # ══════════════════════════════════════════════════════════════

    def validate_mission(self, start: Tuple[float, float],
                          target: Tuple[float, float],
                          altitude: float = 50.0,
                          waypoints: Optional[List[Tuple[float, float]]] = None,
                          mission_type: str = "standard",
                          battery_capacity: float = 100.0) -> Dict[str, Any]:
        """
        Comprehensive pre-flight mission validation.
        Returns detailed pre-flight report.
        """
        # Build full path
        path = [start]
        if waypoints:
            path.extend(waypoints)
        path.append(target)

        # 1. Check takeoff location
        takeoff_valid = not self.geofence.check_point(start, altitude)
        takeoff_zones = self.geofence.get_zones_at(start, altitude)

        # 2. Check landing location
        landing_valid = not self.geofence.check_point(target, altitude)
        landing_zones = self.geofence.get_zones_at(target, altitude)

        # 3. Validate entire route
        route_validation = self.geofence.validate_path(path, altitude)

        # 4. Check return route
        return_path = [target] + list(reversed(path[:-1]))
        return_validation = self.geofence.validate_path(return_path, altitude)

        # 5. Estimate distance and battery
        total_distance = 0.0
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            total_distance += math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)

        estimated_battery_use = total_distance * 1.2  # rough estimate
        battery_sufficient = estimated_battery_use <= battery_capacity * 0.8

        # 6. Find alternative landing sites
        alternative_landings = self._find_alternative_landing_sites(
            path, altitude
        )

        # 7. Altitude optimization
        altitude_advice = self.altitude_manager.suggest_optimal_altitude(
            total_distance, battery_capacity
        )

        # Determine overall validity
        is_valid = (
            takeoff_valid
            and landing_valid
            and route_validation['is_valid']
            and return_validation['is_valid']
            and battery_sufficient
        )

        # Calculate violation probability
        violation_prob = self._compute_violation_probability(path, altitude)

        report = {
            'is_valid': is_valid,
            'mission_type': mission_type,
            'start_position': start,
            'target_position': target,
            'planned_altitude': altitude,
            'total_distance': total_distance,
            'estimated_battery_use': estimated_battery_use,
            'battery_capacity': battery_capacity,
            'battery_sufficient': battery_sufficient,
            'takeoff_legal': takeoff_valid,
            'takeoff_issues': [z.name for z in takeoff_zones],
            'landing_legal': landing_valid,
            'landing_issues': [z.name for z in landing_zones],
            'route_valid': route_validation['is_valid'],
            'route_violations': route_validation['total_violations'],
            'return_route_valid': return_validation['is_valid'],
            'return_violations': return_validation['total_violations'],
            'violation_probability': violation_prob,
            'alternative_landing_sites': alternative_landings,
            'altitude_recommendation': altitude_advice,
            'recommended_actions': [],
            'risk_level': 'HIGH' if not is_valid else 'LOW',
        }

        # Generate recommended actions
        if not takeoff_valid:
            report['recommended_actions'].append(
                "Takeoff location is in restricted airspace. Choose different start point."
            )
        if not landing_valid:
            report['recommended_actions'].append(
                "Target location is in restricted airspace. Choose different landing point."
            )
        if not route_validation['is_valid']:
            report['recommended_actions'].append(
                f"Route passes through {route_validation['total_violations']} restricted zone(s). "
                f"Reroute required."
            )
        if not battery_sufficient:
            report['recommended_actions'].append(
                f"Insufficient battery for mission. Need {estimated_battery_use:.0f}%, have {battery_capacity}%."
            )

        # Store for post-mission report
        self._mission_plan = report

        if self._event_bus:
            try:
                self._event_bus.publish("mission.validation", report, "airspace_manager")
            except Exception:
                pass

        return report

    # ══════════════════════════════════════════════════════════════
    # INTELLIGENT ROUTE PLANNING
    # ══════════════════════════════════════════════════════════════

    def plan_route(self, start: Tuple[float, float],
                   target: Tuple[float, float],
                   altitude: float = 50.0,
                   mission_priority: int = 5,
                   battery_level: float = 100.0,
                   payload: Dict[str, Any] = None,
                   wind_speed: float = 0.0) -> Dict[str, Any]:
        """
        Plan shortest legal route considering all airspace constraints.

        Factors considered:
          - All active restricted zones
          - Altitude restrictions
          - Temporary restrictions
          - Weather (wind)
          - Mission priority
          - Battery level
          - Payload
          - Terrain
        """
        payload = payload or {}
        payload_weight = payload.get('weight', 0.0)

        # 1. Optimize altitude based on mission parameters
        altitude_opt = self.altitude_manager.suggest_optimal_altitude(
            math.sqrt((target[0] - start[0]) ** 2 + (target[1] - start[1]) ** 2),
            battery_level, wind_speed, payload_weight
        )
        optimal_altitude = altitude_opt['optimal_altitude']

        # Use the higher of requested and optimal altitude for safety
        planning_altitude = max(altitude, optimal_altitude)

        # 2. Check if direct path is clear
        direct_path = [start, target]
        path_validation = self.geofence.validate_path(direct_path, planning_altitude)

        if path_validation['is_valid']:
            # Direct path is clear
            return {
                'waypoints': direct_path,
                'altitude': planning_altitude,
                'original_distance': path_validation['total_path_distance'],
                'total_distance': path_validation['total_path_distance'],
                'extra_distance': 0.0,
                'requires_replan': False,
                'zones_avoided': [],
                'explanation': 'Direct path is clear. No airspace restrictions detected.',
                'altitude_recommendation': altitude_opt,
            }

        # 3. Find alternative path around zones
        alt_path = self.geofence.find_alternative_path(
            start, target, planning_altitude
        )

        # 4. Update corridor manager if available
        nearby_corridor = self.corridor_manager.find_nearest_corridor(start)
        if nearby_corridor and nearby_corridor[1] < 20:
            corridor = nearby_corridor[0]
            waypoints = [wp.position for wp in corridor.waypoints]
            alt_path['waypoints'] = waypoints
            alt_path['explanation'] = f'Using approved corridor: {corridor.name}'

        # Calculate distances
        original_dist = math.sqrt((target[0] - start[0]) ** 2 + (target[1] - start[1]) ** 2)
        alt_waypoints = alt_path.get('waypoints', [start, target])
        alt_dist = 0.0
        for i in range(len(alt_waypoints) - 1):
            a, b = alt_waypoints[i], alt_waypoints[i + 1]
            alt_dist += math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)

        extra_dist = alt_dist - original_dist
        self._total_distance_extra += max(0, extra_dist)
        self._replan_count += 1

        return {
            'waypoints': alt_path.get('waypoints', [start, target]),
            'altitude': planning_altitude,
            'original_distance': original_dist,
            'total_distance': alt_dist,
            'extra_distance': max(0, extra_dist),
            'requires_replan': True,
            'zones_avoided': alt_path.get('zones_avoided', []),
            'explanation': alt_path.get('explanation', 'Rerouted around restricted zones.'),
            'altitude_recommendation': altitude_opt,
        }

    # ══════════════════════════════════════════════════════════════
    # DECISION MAKING
    # ══════════════════════════════════════════════════════════════

    def _compile_decisions(self, drone_position: Tuple[float, float],
                            drone_altitude: float,
                            drone_speed: float,
                            mission_priority: int,
                            battery_level: float,
                            geofence_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compile recommended decisions based on airspace situation."""
        decisions = []

        # Process each recommended action from geofence
        for action_rec in geofence_report.get('recommended_actions', []):
            decision = {
                'zone_id': action_rec['zone_id'],
                'zone_name': action_rec['zone_name'],
                'action': action_rec['action'],
                'distance': action_rec['distance'],
                'priority': action_rec['priority'],
                'explanation': action_rec['explanation'],
                'timestamp': time.time(),
                'selected': False,
                'alternatives': [],
            }

            # Generate alternative actions
            decision['alternatives'] = self._generate_alternatives(
                action_rec['action'],
                drone_altitude,
                battery_level,
            )

            # Auto-select the best action based on context
            decision['selected'] = self._select_best_action(
                action_rec['action'],
                action_rec['priority'],
                mission_priority,
                battery_level,
            )

            decisions.append(decision)

        # If no specific actions, add general advisory
        if not decisions:
            decisions.append({
                'action': 'proceed_normal',
                'explanation': 'No airspace restrictions detected. Proceeding normally.',
                'selected': True,
                'timestamp': time.time(),
            })

        self._decision_history.extend(decisions)
        return decisions

    def _generate_alternatives(self, primary_action: str,
                                altitude: float,
                                battery: float) -> List[Dict[str, str]]:
        """Generate alternative actions for a given situation."""
        alternatives = []

        if primary_action == ZoneAction.AVOID.value:
            alternatives.append({'action': 'fly_around', 'explanation': 'Navigate around the zone laterally.'})
            if altitude < 100:
                alternatives.append({'action': 'increase_altitude', 'explanation': 'Climb above the restricted altitude.'})
        elif primary_action == ZoneAction.FLY_AROUND.value:
            alternatives.append({'action': 'avoid', 'explanation': 'Take a wider detour.'})
            if battery > 30:
                alternatives.append({'action': 'wait', 'explanation': 'Hover and wait for zone to clear.'})
        elif primary_action == ZoneAction.INCREASE_ALTITUDE.value:
            alternatives.append({'action': 'fly_around', 'explanation': 'Navigate around instead of climbing.'})
            if battery < 20:
                alternatives.append({'action': 'return_home', 'explanation': 'Low battery - return to base.'})
        elif primary_action == ZoneAction.RETURN_HOME.value:
            alternatives.append({'action': 'land', 'explanation': 'Land at nearest safe location.'})
            if battery > 50:
                alternatives.append({'action': 'wait', 'explanation': 'Wait for conditions to improve.'})

        return alternatives

    def _select_best_action(self, primary_action: ZoneAction,
                             zone_priority: int,
                             mission_priority: int,
                             battery: float) -> bool:
        """Determine if the primary action should be auto-selected."""
        # Critical zone priorities always auto-select
        if zone_priority >= ZonePriority.HIGH.value:
            return True

        # Mission priority override
        if mission_priority <= 2 and zone_priority <= ZonePriority.MEDIUM.value:
            # High-priority mission with moderate zone - still select avoidance
            return True

        # Battery safety
        if battery < 20 and primary_action in (ZoneAction.RETURN_HOME, ZoneAction.LAND):
            return True

        # Default: select if it's the safe option
        return primary_action in (
            ZoneAction.AVOID, ZoneAction.FLY_AROUND,
            ZoneAction.INCREASE_ALTITUDE, ZoneAction.DECREASE_ALTITUDE,
        )

    def get_active_decision(self) -> Optional[str]:
        """Get the currently selected action."""
        for d in self._current_decisions:
            if d.get('selected'):
                return d.get('action', 'unknown')
        return None

    def get_decision_explanations(self) -> List[str]:
        """Get explanations for all current decisions."""
        return [d.get('explanation', '') for d in self._current_decisions]

    # ══════════════════════════════════════════════════════════════
    # RISK ANALYSIS
    # ══════════════════════════════════════════════════════════════

    def _compute_risk_analysis(self, position: Tuple[float, float],
                                altitude: float, speed: float,
                                geofence_report: Dict[str, Any]) -> Dict[str, Any]:
        """Compute comprehensive airspace risk analysis."""
        violations = geofence_report.get('violations', [])
        proximity = geofence_report.get('proximity_warnings', [])

        # Airspace Risk Score (0.0 - 1.0)
        if violations:
            airspace_risk = min(1.0, len(violations) * 0.3 +
                                max(v.get('risk_score', 0.0) for v in violations))
        elif proximity:
            airspace_risk = 0.3 + min(0.4, len(proximity) * 0.1)
        else:
            airspace_risk = 0.0

        # Violation probability
        violation_prob = 0.0
        if violations:
            violation_prob = 1.0
        elif proximity:
            # Probability based on distance
            min_dist = min(w.get('distance', 15) for w in proximity)
            violation_prob = max(0.0, 1.0 - (min_dist / self.geofence.proximity_warning_distance))
        else:
            violation_prob = 0.0

        # Penalty score
        penalty = sum(v.get('risk_score', 0.5) * 100 for v in violations)

        # Mission delay estimate
        delay = len(violations) * 10.0 + len(proximity) * 3.0

        # Confidence (inverse of uncertainty)
        confidence = 1.0 - airspace_risk

        # Safety margin
        nearest = self.geofence.get_nearest_zone(position)
        if nearest:
            safety_margin = nearest[1]  # distance to nearest zone
        else:
            safety_margin = float('inf')

        return {
            'airspace_risk_score': round(airspace_risk, 3),
            'violation_probability': round(violation_prob, 3),
            'penalty_score': round(penalty, 1),
            'mission_delay_estimate': round(delay, 1),
            'confidence': round(confidence, 3),
            'safety_margin': round(safety_margin, 1) if safety_margin != float('inf') else 'clear',
            'nearest_zone_distance': nearest[1] if nearest else None,
            'nearest_zone_name': nearest[0].name if nearest else None,
        }

    def _compute_violation_probability(self, path: List[Tuple[float, float]],
                                        altitude: float) -> float:
        """Compute probability of route violation."""
        violations = self.geofence.check_path(path, altitude)
        if not violations:
            return 0.0
        return min(1.0, len(violations) * 0.2)

    def _find_alternative_landing_sites(self, path: List[Tuple[float, float]],
                                         altitude: float,
                                         max_sites: int = 3) -> List[Dict[str, Any]]:
        """Find safe alternative landing sites along the route."""
        sites = []
        # Sample points along the path
        for i in range(len(path) - 1):
            for t in [0.25, 0.5, 0.75]:
                a = path[i]
                b = path[i + 1]
                px = a[0] + (b[0] - a[0]) * t
                py = a[1] + (b[1] - a[1]) * t

                # Check if this point is in a restricted zone
                if not self.geofence.check_point((px, py), altitude):
                    # Check if safe
                    zones_nearby = self.geofence.get_zones_in_radius((px, py), 10)
                    if not zones_nearby:
                        sites.append({
                            'position': (px, py),
                            'distance_from_path': 0.0,
                            'is_safe': True,
                        })

        return sites[:max_sites]

    # ══════════════════════════════════════════════════════════════
    # PREDICTION
    # ══════════════════════════════════════════════════════════════

    def predict_restrictions(self, position: Tuple[float, float],
                              lookahead_seconds: float = 60.0) -> Dict[str, Any]:
        """
        Predict future restrictions and dangers.

        Returns:
          - Future restricted zones
          - Moving restricted areas
          - Expanding danger areas
          - Weather movement
          - Predicted TFRs
        """
        # 1. TFR predictions from historical data
        tfr_predictions = self.tfr_manager.predict_tfrs(position)

        # 2. Predict zone expirations (zones that will clear soon)
        soon_expiring = []
        for zone in self.geofence.get_active_zones():
            if zone.is_temporal:
                time_left = zone.expiration_time - time.time()
                if 0 < time_left <= lookahead_seconds:
                    soon_expiring.append({
                        'zone_id': zone.zone_id,
                        'name': zone.name,
                        'expires_in': time_left,
                    })

        # 3. Predict expanding danger areas (dynamic zones)
        expanding = []
        for zone in self.geofence.get_active_zones():
            if zone.is_dynamic:
                dist = zone.distance_to(position)
                if dist < 0:  # Inside zone
                    expanding.append({
                        'zone_id': zone.zone_id,
                        'name': zone.name,
                        'type': zone.zone_type.value,
                        'distance_inside': -dist,
                    })

        return {
            'tfr_predictions': tfr_predictions,
            'soon_expiring': soon_expiring,
            'expanding_danger': expanding,
            'lookahead_seconds': lookahead_seconds,
        }

    # ══════════════════════════════════════════════════════════════
    # POST-MISSION REPORT
    # ══════════════════════════════════════════════════════════════

    def generate_mission_report(self, mission_id: str = "unknown") -> Dict[str, Any]:
        """
        Generate a comprehensive post-mission airspace report.
        """
        violations = self.geofence.get_violation_history(limit=100)

        # Categorize violations
        by_type = defaultdict(list)
        for v in violations:
            by_type[v.get('zone_type', 'unknown')].append(v)

        # Calculate distances
        total_extra = self._total_distance_extra

        # Time lost estimate
        time_lost = len(violations) * 5.0  # seconds per violation

        report = {
            'mission_id': mission_id,
            'generated_at': time.time(),
            'summary': {
                'restricted_zones_encountered': len(by_type),
                'zones_by_type': {k: len(v) for k, v in by_type.items()},
                'total_violations': len(violations),
                'extra_distance_flown': round(total_extra, 1),
                'estimated_time_lost': round(time_lost, 1),
                'replanning_count': self._replan_count,
            },
            'violations': violations[:20],  # Last 20 violations
            'decisions_made': self._decision_history[-50:],  # Last 50 decisions
            'risk_analysis': self._compute_risk_summary(violations),
            'recommendations': self._generate_recommendations(violations),
        }

        self._mission_reports.append(report)
        return report

    def _compute_risk_summary(self, violations: List[Dict]) -> Dict[str, Any]:
        """Compute summary risk metrics."""
        if not violations:
            return {'overall_risk': 0.0, 'max_risk': 0.0, 'avg_risk': 0.0}

        risk_scores = [v.get('risk_score', 0.5) for v in violations]
        return {
            'overall_risk': min(1.0, sum(risk_scores) / len(risk_scores) + len(violations) * 0.05),
            'max_risk': max(risk_scores),
            'avg_risk': sum(risk_scores) / len(risk_scores),
            'total_incidents': len(violations),
        }

    def _generate_recommendations(self, violations: List[Dict]) -> List[str]:
        """Generate improvement recommendations."""
        recs = []
        if violations:
            recs.append("Review frequent violation zones for permanent avoidance routes.")
            recs.append("Consider establishing approved corridors through high-traffic areas.")

        zone_types = set(v.get('zone_type', '') for v in violations)
        if ZoneType.SCHOOL_ZONE.value in zone_types:
            recs.append("Schedule missions outside school hours to avoid school zone restrictions.")
        if ZoneType.AIRPORT.value in zone_types:
            recs.append("Maintain required distance from airport approach paths.")

        if self._replan_count > 10:
            recs.append("High replan count suggests pre-flight route optimization is needed.")
        if self._total_distance_extra > 100:
            recs.append("Significant extra distance flown - consider alternative base locations.")

        return recs if recs else ["No issues detected. Airspace compliance maintained."]

    # ══════════════════════════════════════════════════════════════
    # COGNITIVE INTEGRATION (Memory Interface)
    # ══════════════════════════════════════════════════════════════

    def get_memory_data(self) -> Dict[str, Any]:
        """
        Get airspace data for cognitive memory integration.

        Returns data the Drone Brain's memory system can use to
        learn from past airspace interactions.
        """
        violations = self.geofence.get_violation_history(limit=200)
        zone_frequencies = defaultdict(int)
        for v in violations:
            zone_frequencies[v.get('zone_name', 'unknown')] += 1

        return {
            'frequently_restricted_locations': dict(zone_frequencies.most_common(10) if hasattr(zone_frequencies, 'most_common') else
                                                     sorted(zone_frequencies.items(), key=lambda x: x[1], reverse=True)[:10]),
            'historical_violations': len(violations),
            'common_safe_routes': [c.name for c in self.corridor_manager.get_active_corridors()],
            'seasonal_restrictions': self._get_seasonal_restrictions(),
            'mission_success_rate': self._compute_success_rate(),
            'preferred_corridors': [c.corridor_id for c in self.corridor_manager.get_active_corridors()],
        }

    def _get_seasonal_restrictions(self) -> List[Dict[str, Any]]:
        """Get seasonal restriction patterns."""
        month = time.localtime().tm_mon
        seasonal = []
        for zone in self.geofence.get_active_zones():
            if zone.zone_type == ZoneType.WILDLIFE_SANCTUARY:
                seasonal.append({
                    'zone_name': zone.name,
                    'season': 'nesting' if 3 <= month <= 8 else 'normal',
                    'restriction_level': 'high' if 3 <= month <= 8 else 'normal',
                })
        return seasonal

    def _compute_success_rate(self) -> float:
        """Compute mission success rate from history."""
        total = len(self._mission_reports)
        if total == 0:
            return 1.0
        successful = sum(
            1 for r in self._mission_reports
            if r.get('summary', {}).get('total_violations', 0) == 0
        )
        return successful / total

    # ══════════════════════════════════════════════════════════════
    # Airspace Enforcement Grid (for CostMap integration)
    # ══════════════════════════════════════════════════════════════

    def get_airspace_cost_grid(self, resolution: int = 100) -> List[List[float]]:
        """
        Generate a 2D cost grid from airspace restrictions.

        This grid can be combined with the existing CostMap so the
        planner naturally avoids restricted airspace.

        Returns a 2D list where:
          0.0 = free airspace
          0.5 = caution (proximity zone)
          1.0 = restricted (no-fly zone)
        """
        grid = [[0.0 for _ in range(resolution)] for _ in range(resolution)]

        for y in range(resolution):
            for x in range(resolution):
                wx = (x / resolution) * self.world_width
                wy = (y / resolution) * self.world_height

                # Check if point is in any restricted zone
                zones = self.geofence.get_zones_at((wx, wy))
                if zones:
                    # Find highest restriction level
                    max_risk = max(z.risk_level.value for z in zones)
                    grid[y][x] = min(1.0, max_risk + 0.2)
                else:
                    # Check proximity
                    nearest = self.geofence.get_nearest_zone((wx, wy))
                    if nearest:
                        dist = nearest[1]
                        if dist < self.geofence.proximity_warning_distance:
                            # Gradual cost increase as drone approaches zone
                            factor = 1.0 - (dist / self.geofence.proximity_warning_distance)
                            grid[y][x] = 0.3 * factor

        return grid

    # ══════════════════════════════════════════════════════════════
    # UTILITY
    # ══════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive airspace system statistics."""
        return {
            'geofence': self.geofence.get_stats(),
            'tfr': self.tfr_manager.get_stats(),
            'corridors': self.corridor_manager.get_stats(),
            'altitude': self.altitude_manager.get_stats(),
            'database': self.database.get_stats(),
            'total_decisions': len(self._decision_history),
            'replan_count': self._replan_count,
            'extra_distance': round(self._total_distance_extra, 1),
        }

    def reset_stats(self):
        """Reset all statistics counters."""
        self._total_distance_saved = 0.0
        self._total_distance_extra = 0.0
        self._replan_count = 0
        self._decision_history.clear()
        self._mission_reports.clear()