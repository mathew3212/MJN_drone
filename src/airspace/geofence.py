"""
Geofence Engine
================
Enforces airspace boundaries with real-time detection and response.

Features:
  - Real-time position monitoring against all active zones
  - Proximity warnings with configurable thresholds
  - Automatic action recommendation based on zone priority
  - Violation detection and logging
  - Multi-zone conflict resolution
  - Path segment validation
  - Configurable safety buffers
"""

from __future__ import annotations

import time
import math
from typing import List, Optional, Tuple, Dict, Any, Set, Callable
from collections import defaultdict

from .restricted_zone import (
    RestrictedZone, ZoneType, ZonePriority, RiskLevel,
    ZoneStatus, ZoneAction, ZoneShape, Point2D,
)


class GeofenceEngine:
    """
    Core geofence enforcement engine.
    Monitors drone position against all active restricted zones.
    """

    def __init__(self, world_width: float = 100.0, world_height: float = 100.0):
        self.world_width = world_width
        self.world_height = world_height

        # Zone storage
        self._zones: Dict[str, RestrictedZone] = {}
        self._zone_grid: Dict[str, List[str]] = defaultdict(list)  # grid cell -> zone IDs

        # Monitoring
        self._violation_history: List[Dict[str, Any]] = []
        self._proximity_warnings: List[Dict[str, Any]] = []

        # Configuration
        self.proximity_warning_distance: float = 15.0
        self.critical_warning_distance: float = 5.0
        self.grid_cell_size: float = 20.0
        self.enabled: bool = True

        # Callbacks
        self._violation_callbacks: List[Callable] = []
        self._proximity_callbacks: List[Callable] = []
        self._entry_callbacks: List[Callable] = []

        # Active violations tracking
        self._active_violations: Set[str] = set()
        self._zones_in_proximity: Set[str] = set()

        # Build initial spatial index
        self._rebuild_spatial_index()

    # ── Zone Management ──────────────────────────────────────────

    def add_zone(self, zone: RestrictedZone) -> bool:
        """Add a restricted zone to the engine."""
        if zone.zone_id in self._zones:
            return False
        self._zones[zone.zone_id] = zone
        self._index_zone(zone)
        return True

    def remove_zone(self, zone_id: str) -> bool:
        """Remove a restricted zone."""
        if zone_id not in self._zones:
            return False
        zone = self._zones.pop(zone_id)
        self._remove_from_index(zone_id)
        self._active_violations.discard(zone_id)
        self._zones_in_proximity.discard(zone_id)
        return True

    def get_zone(self, zone_id: str) -> Optional[RestrictedZone]:
        """Get a zone by ID."""
        return self._zones.get(zone_id)

    def get_all_zones(self) -> List[RestrictedZone]:
        """Get all registered zones."""
        return list(self._zones.values())

    def get_active_zones(self) -> List[RestrictedZone]:
        """Get all currently active zones."""
        now = time.time()
        return [
            z for z in self._zones.values()
            if z.status == ZoneStatus.ACTIVE
            and not z.is_expired
            and not z.is_future
        ]

    def get_zones_by_type(self, zone_type: ZoneType) -> List[RestrictedZone]:
        """Get zones of a specific type."""
        return [z for z in self._zones.values() if z.zone_type == zone_type]

    def clear_zones(self):
        """Remove all zones."""
        self._zones.clear()
        self._zone_grid.clear()
        self._active_violations.clear()
        self._zones_in_proximity.clear()

    def get_zone_count(self) -> int:
        return len(self._zones)

    # ── Spatial Queries ──────────────────────────────────────────

    def get_zones_at(self, position: Tuple[float, float],
                     altitude: Optional[float] = None) -> List[RestrictedZone]:
        """Get all zones that contain the given position."""
        result = []
        cell_id = self._position_to_cell(position)
        candidate_ids = self._zone_grid.get(cell_id, [])

        for zone_id in candidate_ids:
            zone = self._zones.get(zone_id)
            if zone and zone.contains_point(position, altitude):
                result.append(zone)

        return result

    def get_zones_in_radius(self, position: Tuple[float, float],
                             radius: float) -> List[RestrictedZone]:
        """Get all zones within a radius of the position."""
        result = []
        cells = self._get_cells_in_radius(position, radius)

        seen = set()
        for cell_id in cells:
            for zone_id in self._zone_grid.get(cell_id, []):
                if zone_id in seen:
                    continue
                seen.add(zone_id)
                zone = self._zones.get(zone_id)
                if zone and zone.distance_to(position) <= radius:
                    result.append(zone)

        return result

    def check_point(self, position: Tuple[float, float],
                    altitude: Optional[float] = None) -> bool:
        """Check if a point is inside ANY restricted zone."""
        return len(self.get_zones_at(position, altitude)) > 0

    def check_path(self, path: List[Tuple[float, float]],
                   altitude: Optional[float] = None) -> List[Tuple[int, str]]:
        """
        Check an entire path for zone violations.
        Returns list of (waypoint_index, zone_id) for violations.
        """
        violations = []
        for i, point in enumerate(path):
            zones = self.get_zones_at(point, altitude)
            for zone in zones:
                violations.append((i, zone.zone_id))
        return violations

    def get_nearest_zone(self, position: Tuple[float, float]) -> Optional[Tuple[RestrictedZone, float]]:
        """Get the nearest active zone and its distance."""
        nearest = None
        nearest_dist = float('inf')
        for zone in self.get_active_zones():
            dist = zone.distance_to(position)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = zone
        if nearest:
            return (nearest, nearest_dist)
        return None

    # ── Monitoring ───────────────────────────────────────────────

    def update(self, drone_position: Tuple[float, float],
               drone_altitude: float = 50.0,
               drone_speed: float = 0.0) -> Dict[str, Any]:
        """
        Update geofence monitoring. Returns status report.
        Called every simulation step.
        """
        if not self.enabled:
            return {'status': 'disabled'}

        now = time.time()
        current_violations: Set[str] = set()
        current_proximity: Set[str] = set()
        report = {
            'violations': [],
            'proximity_warnings': [],
            'entry_warnings': [],
            'recommended_actions': [],
            'risk_score': 0.0,
        }

        # Check all relevant cells
        cells = self._get_cells_in_radius(drone_position, self.critical_warning_distance * 2)

        for cell_id in cells:
            for zone_id in self._zone_grid.get(cell_id, []):
                zone = self._zones.get(zone_id)
                if not zone or zone.status != ZoneStatus.ACTIVE:
                    continue
                if zone.is_expired or zone.is_future:
                    continue

                dist = zone.distance_to(drone_position)
                contained = dist <= 0

                # Violation detection
                if contained and zone.altitude_limits.contains(drone_altitude):
                    current_violations.add(zone_id)
                    violation = {
                        'zone_id': zone_id,
                        'zone_name': zone.name,
                        'zone_type': zone.zone_type.value,
                        'position': drone_position,
                        'altitude': drone_altitude,
                        'distance': dist,
                        'timestamp': now,
                        'risk_score': zone.compute_risk_score(drone_speed, drone_altitude),
                    }
                    report['violations'].append(violation)
                    self._violation_history.append(violation)

                    # Check for new violation
                    if zone_id not in self._active_violations:
                        self._trigger_violation_callbacks(zone, drone_position, drone_altitude)

                # Proximity warnings
                elif 0 < dist <= self.proximity_warning_distance:
                    current_proximity.add(zone_id)
                    warning = {
                        'zone_id': zone_id,
                        'zone_name': zone.name,
                        'zone_type': zone.zone_type.value,
                        'distance': dist,
                        'position': drone_position,
                        'timestamp': now,
                    }
                    report['proximity_warnings'].append(warning)

                    if zone_id not in self._zones_in_proximity:
                        self._trigger_proximity_callbacks(zone, dist)
                        report['entry_warnings'].append(warning)

                # Determine recommended actions
                if contained or dist <= self.proximity_warning_distance:
                    action = zone.get_avoidance_action(drone_position, drone_altitude)
                    report['recommended_actions'].append({
                        'zone_id': zone_id,
                        'zone_name': zone.name,
                        'distance': dist,
                        'action': action.value,
                        'priority': zone.priority.value,
                        'explanation': self._generate_action_explanation(zone, action, dist),
                    })

        # Update tracking sets
        newly_cleared = self._active_violations - current_violations
        for zid in newly_cleared:
            self._trigger_exit_callbacks(self._zones.get(zid))

        self._active_violations = current_violations
        self._zones_in_proximity = current_proximity

        # Compute aggregate risk score
        if report['violations']:
            report['risk_score'] = max(v['risk_score'] for v in report['violations'])
        elif report['proximity_warnings']:
            report['risk_score'] = 0.3
        else:
            report['risk_score'] = 0.0

        report['has_violations'] = len(current_violations) > 0
        report['violation_count'] = len(current_violations)

        return report

    # ── Path Validation ─────────────────────────────────────────

    def validate_path(self, path: List[Tuple[float, float]],
                      altitude: float = 50.0) -> Dict[str, Any]:
        """
        Validate an entire path against all active zones.
        Returns detailed validation report.
        """
        violations = self.check_path(path, altitude)
        risky_segments = []
        safe_segments = []
        total_distance = 0.0

        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            seg_dist = math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)
            total_distance += seg_dist

            # Sample points along segment
            samples = max(3, int(seg_dist / 2))
            segment_violations = []
            for s in range(samples + 1):
                t = s / samples
                px = a[0] + (b[0] - a[0]) * t
                py = a[1] + (b[1] - a[1]) * t
                zones = self.get_zones_at((px, py), altitude)
                if zones:
                    segment_violations.extend([z.zone_id for z in zones])

            if segment_violations:
                risky_segments.append({
                    'start_index': i,
                    'end_index': i + 1,
                    'zones': list(set(segment_violations)),
                })
            else:
                safe_segments.append(i)

        return {
            'is_valid': len(violations) == 0,
            'total_violations': len(violations),
            'violation_count_by_zone': len(set(v for _, v in violations)),
            'total_path_distance': total_distance,
            'violation_details': violations,
            'risky_segments': risky_segments,
            'safe_segments': safe_segments,
        }

    # ── Route Replanning Assistance ──────────────────────────────

    def find_alternative_path(self, start: Tuple[float, float],
                               goal: Tuple[float, float],
                               altitude: float = 50.0) -> Dict[str, Any]:
        """
        Find a path around restricted zones.
        Returns waypoints that avoid all active zones.
        """
        # Get zones that intersect the direct path
        zones_to_avoid = self.get_zones_in_radius(
            ((start[0] + goal[0]) / 2, (start[1] + goal[1]) / 2),
            max(abs(goal[0] - start[0]), abs(goal[1] - start[1])) / 2 + 20
        )

        if not zones_to_avoid:
            return {
                'requires_replan': False,
                'waypoints': [start, goal],
                'explanation': 'Direct path is clear.',
            }

        # Generate waypoints to circumvent zones
        waypoints = [start]
        current_pos = start

        for zone in sorted(zones_to_avoid, key=lambda z: z.priority.value, reverse=True):
            dist = zone.distance_to(current_pos)
            if dist > 0:
                # Before zone - create bypass waypoints
                center = Point2D(zone.center_lon, zone.center_lat)
                bb = zone.get_bounding_box()

                # Generate bypass points on either side
                bypass_x = bb[2] + zone.safety_buffer + 5
                bypass_y = current_pos[1]

                # Clamp to world boundaries
                bypass_x = min(max(bypass_x, 2), self.world_width - 2)
                bypass_y = min(max(bypass_y, 2), self.world_height - 2)

                waypoints.append((bypass_x, bypass_y))
                # Rejoin toward goal
                waypoints.append((bypass_x + 5, goal[1]))

        waypoints.append(goal)

        return {
            'requires_replan': True,
            'waypoints': waypoints,
            'zones_avoided': [z.name for z in zones_to_avoid],
            'explanation': f'Re-routed around {len(zones_to_avoid)} restricted zone(s).',
        }

    def suggest_altitude_change(self, position: Tuple[float, float],
                                 current_altitude: float) -> Dict[str, Any]:
        """Suggest altitude changes to avoid zone conflicts."""
        zones = self.get_zones_at(position)
        if not zones:
            return {'altitude_change': 0, 'reason': 'No zone conflict.'}

        suggestions = []
        for zone in zones:
            if current_altitude < zone.altitude_limits.minimum_altitude:
                suggestions.append({
                    'direction': 'increase',
                    'amount': zone.altitude_limits.minimum_altitude - current_altitude + 5,
                    'target': zone.altitude_limits.minimum_altitude + 5,
                })
            elif current_altitude > zone.altitude_limits.maximum_altitude:
                suggestions.append({
                    'direction': 'decrease',
                    'amount': current_altitude - zone.altitude_limits.maximum_altitude + 5,
                    'target': zone.altitude_limits.maximum_altitude - 5,
                })

        if suggestions:
            # Pick the minimal safe change
            best = min(suggestions, key=lambda s: s['amount'])
            return {
                'altitude_change': best['amount'],
                'direction': best['direction'],
                'target_altitude': best['target'],
                'reason': f'Adjust to avoid {zone.name} altitude restriction.',
            }

        return {'altitude_change': 0, 'reason': 'Altitude is safe.'}

    # ── Callbacks ────────────────────────────────────────────────

    def on_violation(self, callback: Callable):
        """Register callback for zone violations."""
        self._violation_callbacks.append(callback)

    def on_proximity(self, callback: Callable):
        """Register callback for proximity warnings."""
        self._proximity_callbacks.append(callback)

    def on_entry(self, callback: Callable):
        """Register callback for zone entry."""
        self._entry_callbacks.append(callback)

    def _trigger_violation_callbacks(self, zone: RestrictedZone,
                                      position: Tuple[float, float],
                                      altitude: float):
        for cb in self._violation_callbacks:
            try:
                cb(zone, position, altitude)
            except Exception:
                pass

    def _trigger_proximity_callbacks(self, zone: RestrictedZone, distance: float):
        for cb in self._proximity_callbacks:
            try:
                cb(zone, distance)
            except Exception:
                pass

    def _trigger_entry_callbacks(self, zone: RestrictedZone,
                                  position: Tuple[float, float]):
        for cb in self._entry_callbacks:
            try:
                cb(zone, position)
            except Exception:
                pass

    def _trigger_exit_callbacks(self, zone: Optional[RestrictedZone]):
        if zone is None:
            return

    # ── Spatial Indexing ─────────────────────────────────────────

    def _rebuild_spatial_index(self):
        """Rebuild the spatial grid index."""
        self._zone_grid.clear()
        for zone in self._zones.values():
            self._index_zone(zone)

    def _index_zone(self, zone: RestrictedZone):
        """Add zone to spatial index cells."""
        bb = zone.get_bounding_box()
        min_cell_x = int(bb[0] / self.grid_cell_size)
        min_cell_y = int(bb[1] / self.grid_cell_size)
        max_cell_x = int(bb[2] / self.grid_cell_size)
        max_cell_y = int(bb[3] / self.grid_cell_size)

        for cx in range(min_cell_x, max_cell_x + 1):
            for cy in range(min_cell_y, max_cell_y + 1):
                cell_id = f"{cx}:{cy}"
                if zone.zone_id not in self._zone_grid[cell_id]:
                    self._zone_grid[cell_id].append(zone.zone_id)

    def _remove_from_index(self, zone_id: str):
        """Remove zone from all index cells."""
        for cell_id in list(self._zone_grid.keys()):
            if zone_id in self._zone_grid[cell_id]:
                self._zone_grid[cell_id].remove(zone_id)
            if not self._zone_grid[cell_id]:
                del self._zone_grid[cell_id]

    def _position_to_cell(self, position: Tuple[float, float]) -> str:
        """Convert position to grid cell ID."""
        cx = int(position[0] / self.grid_cell_size)
        cy = int(position[1] / self.grid_cell_size)
        return f"{cx}:{cy}"

    def _get_cells_in_radius(self, position: Tuple[float, float],
                              radius: float) -> List[str]:
        """Get all grid cells within a radius of position."""
        cells = []
        cell_size = self.grid_cell_size
        cx = int(position[0] / cell_size)
        cy = int(position[1] / cell_size)
        cell_radius = int(radius / cell_size) + 1

        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                cells.append(f"{cx + dx}:{cy + dy}")

        return cells

    # ── Reporting ────────────────────────────────────────────────

    def get_violation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get history of zone violations."""
        return self._violation_history[-limit:]

    def get_violation_count(self) -> int:
        return len(self._violation_history)

    def get_stats(self) -> Dict[str, Any]:
        """Get geofence engine statistics."""
        return {
            'total_zones': len(self._zones),
            'active_zones': len(self.get_active_zones()),
            'active_violations': len(self._active_violations),
            'zones_in_proximity': len(self._zones_in_proximity),
            'total_violations': len(self._violation_history),
            'grid_cells': len(self._zone_grid),
        }

    @staticmethod
    def _generate_action_explanation(zone: RestrictedZone,
                                      action: ZoneAction,
                                      distance: float) -> str:
        """Generate human-readable explanation for recommended action."""
        if action == ZoneAction.AVOID:
            return f"Avoiding {zone.name} ({zone.zone_type.value}). Zone is {distance:.1f} units away."
        elif action == ZoneAction.FLY_AROUND:
            return f"Flying around {zone.name}. Safe passage available at {distance:.1f} units."
        elif action == ZoneAction.INCREASE_ALTITUDE:
            return f"Increasing altitude to clear {zone.name}'s minimum ceiling."
        elif action == ZoneAction.DECREASE_ALTITUDE:
            return f"Decreasing altitude to stay below {zone.name}'s maximum ceiling."
        elif action == ZoneAction.WAIT:
            return f"Waiting for {zone.name} to become inactive or clearance to be granted."
        elif action == ZoneAction.RETURN_HOME:
            return f"Returning home. {zone.name} cannot be safely circumvented."
        elif action == ZoneAction.LAND:
            return f"Landing immediately. {zone.name} poses imminent safety risk."
        elif action == ZoneAction.REQUEST_PERMISSION:
            return f"Requesting permission to enter {zone.name}. Contact: {zone.permission_contact}."
        elif action == ZoneAction.ABORT_MISSION:
            return f"Aborting mission. {zone.name} is a critical restricted zone."
        else:
            return f"Proceeding with caution near {zone.name}."