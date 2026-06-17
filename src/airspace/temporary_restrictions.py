"""
Temporary Flight Restrictions (TFR) Manager
=============================================
Manages dynamically appearing and expiring airspace restrictions.

Supports:
  - TFRs from events (VIP, disaster, construction, sports, etc.)
  - Time-based activation and expiration
  - Dynamic zone creation during flight
  - Emergency zone generation (fire, flood, police activity)
  - TFR prediction based on historical patterns
  - Calendar/schedule integration
"""

from __future__ import annotations

import time
import random
import math
from typing import List, Optional, Tuple, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from .restricted_zone import (
    RestrictedZone, ZoneType, ZoneShape, ZonePriority,
    RiskLevel, ZoneStatus, ZoneAction, AltitudeEnvelope,
    CircleZone, Point2D,
)


class TFRSource(Enum):
    """Sources of temporary flight restrictions."""
    NOTAM = "notam"
    VIP_MOVEMENT = "vip_movement"
    DISASTER = "disaster"
    CONSTRUCTION = "construction"
    EVENT = "event"
    POLICE_ACTIVITY = "police_activity"
    EMERGENCY_HELICOPTER = "emergency_helicopter"
    FIRE = "fire"
    FLOOD = "flood"
    AIRPORT_ISSUE = "airport_issue"
    CRANE_OPERATION = "crane_operation"
    LARGE_GATHERING = "large_gathering"
    WEATHER = "weather"
    SECURITY = "security"
    USER_DEFINED = "user_defined"


@dataclass
class TFRDefinition:
    """Definition of a temporary flight restriction."""
    tfr_id: str = ""
    source: TFRSource = TFRSource.USER_DEFINED
    name: str = ""
    description: str = ""
    zone_type: ZoneType = ZoneType.TFR
    center: Tuple[float, float] = (50, 50)
    radius: float = 15.0
    altitude_min: float = 0.0
    altitude_max: float = 120.0
    duration_seconds: float = 300.0
    creation_time: float = field(default_factory=time.time)
    uncertainty_radius: float = 2.0  # for moving/predictive TFRs
    is_active: bool = True
    priority: ZonePriority = ZonePriority.HIGH
    risk_level: RiskLevel = RiskLevel.HIGH

    def to_restricted_zone(self) -> RestrictedZone:
        """Convert TFR definition to full RestrictedZone."""
        return RestrictedZone(
            zone_id=self.tfr_id,
            name=self.name,
            description=self.description,
            zone_type=self.zone_type,
            zone_shape=ZoneShape.CIRCLE,
            priority=self.priority,
            center_lat=self.center[1],
            center_lon=self.center[0],
            shape_data=CircleZone(
                center=Point2D(self.center[0], self.center[1]),
                radius=self.radius,
            ),
            altitude_limits=AltitudeEnvelope(
                minimum_altitude=self.altitude_min,
                maximum_altitude=self.altitude_max,
            ),
            safety_buffer=5.0,
            activation_time=self.creation_time,
            expiration_time=self.creation_time + self.duration_seconds,
            is_dynamic=True,
            risk_level=self.risk_level,
            source=f"tfr_{self.source.value}",
        )


class TemporaryRestrictionManager:
    """
    Manages temporary flight restrictions that appear during flight.
    Supports dynamic creation, prediction, and automatic cleanup.
    """

    def __init__(self):
        self._tfrs: Dict[str, TFRDefinition] = {}
        self._active_zone_ids: List[str] = []
        self._tfr_history: List[TFRDefinition] = []

        # Configuration
        self.auto_cleanup: bool = True
        self.cleanup_interval: float = 10.0  # seconds
        self._last_cleanup: float = time.time()

        # Generation settings
        self.max_concurrent_tfrs: int = 5
        self.generation_enabled: bool = True
        self.prediction_enabled: bool = True

        # Callbacks
        self._on_new_tfr: List[Callable] = []
        self._on_tfr_expired: List[Callable] = []
        self._on_tfr_predicted: List[Callable] = []

        # Historical prediction data
        self._prediction_model: Dict[str, Any] = {
            'hourly_distribution': {},  # hour -> frequency
            'type_distribution': {},  # TFRSource -> frequency
            'location_hotspots': [],  # high-frequency locations
        }

    # ── TFR Management ──────────────────────────────────────────

    def add_tfr(self, tfr: TFRDefinition) -> str:
        """Add a new temporary restriction."""
        if not tfr.tfr_id:
            tfr.tfr_id = f"tfr_{int(time.time())}_{random.randint(1000, 9999)}"

        self._tfrs[tfr.tfr_id] = tfr
        self._active_zone_ids.append(tfr.tfr_id)

        # Trigger callback
        zone = tfr.to_restricted_zone()
        for cb in self._on_new_tfr:
            try:
                cb(zone)
            except Exception:
                pass

        return tfr.tfr_id

    def remove_tfr(self, tfr_id: str) -> bool:
        """Remove a temporary restriction."""
        if tfr_id not in self._tfrs:
            return False
        tfr = self._tfrs.pop(tfr_id)
        if tfr_id in self._active_zone_ids:
            self._active_zone_ids.remove(tfr_id)
        for cb in self._on_tfr_expired:
            try:
                cb(tfr)
            except Exception:
                pass
        return True

    def get_active_tfrs(self) -> List[TFRDefinition]:
        """Get all currently active TFRs."""
        now = time.time()
        return [
            tfr for tfr in self._tfrs.values()
            if tfr.is_active
            and now < tfr.creation_time + tfr.duration_seconds
        ]

    def get_expired_tfrs(self) -> List[TFRDefinition]:
        """Get all expired TFRs."""
        now = time.time()
        return [
            tfr for tfr in self._tfrs.values()
            if not tfr.is_active or now >= tfr.creation_time + tfr.duration_seconds
        ]

    def get_tfr_count(self) -> int:
        return len(self._tfrs)

    def get_tfrs_near(self, position: Tuple[float, float],
                       radius: float) -> List[TFRDefinition]:
        """Get TFRs near a position."""
        result = []
        for tfr in self.get_active_tfrs():
            dist = math.sqrt(
                (tfr.center[0] - position[0]) ** 2 +
                (tfr.center[1] - position[1]) ** 2
            )
            if dist <= radius + tfr.radius:
                result.append(tfr)
        return result

    # ── Dynamic Generation ──────────────────────────────────────

    def generate_emergency_tfr(self, position: Tuple[float, float],
                                emergency_type: str = "police") -> TFRDefinition:
        """Generate an emergency TFR (police, fire, medical, etc.)."""
        source_map = {
            'police': TFRSource.POLICE_ACTIVITY,
            'fire': TFRSource.FIRE,
            'flood': TFRSource.FLOOD,
            'medical': TFRSource.EMERGENCY_HELICOPTER,
            'disaster': TFRSource.DISASTER,
        }
        source = source_map.get(emergency_type, TFRSource.EMERGENCY_HELICOPTER)

        tfr = TFRDefinition(
            source=source,
            name=f"Emergency: {emergency_type.title()}",
            description=f"Dynamic TFR due to {emergency_type} activity.",
            zone_type=ZoneType.EMERGENCY_ZONE,
            center=position,
            radius=random.uniform(10, 25),
            altitude_min=0.0,
            altitude_max=150.0,
            duration_seconds=random.uniform(120, 600),
            priority=ZonePriority.HIGHEST,
            risk_level=RiskLevel.SEVERE,
        )
        self.add_tfr(tfr)
        return tfr

    def generate_vip_tfr(self, position: Tuple[float, float]) -> TFRDefinition:
        """Generate a VIP movement TFR."""
        tfr = TFRDefinition(
            source=TFRSource.VIP_MOVEMENT,
            name="VIP Movement Restriction",
            description="Temporary restriction for VIP movement and security.",
            zone_type=ZoneType.VIP_MOVEMENT,
            center=position,
            radius=random.uniform(15, 30),
            altitude_min=0.0,
            altitude_max=200.0,
            duration_seconds=random.uniform(180, 900),
            priority=ZonePriority.CRITICAL,
            risk_level=RiskLevel.SEVERE,
        )
        self.add_tfr(tfr)
        return tfr

    def generate_event_tfr(self, position: Tuple[float, float],
                            event_name: str = "Large Event") -> TFRDefinition:
        """Generate an event-based TFR."""
        tfr = TFRDefinition(
            source=TFRSource.EVENT,
            name=f"Event: {event_name}",
            description=f"Temporary restriction for {event_name}.",
            zone_type=ZoneType.EVENT_ZONE,
            center=position,
            radius=random.uniform(10, 20),
            altitude_min=0.0,
            altitude_max=120.0,
            duration_seconds=random.uniform(300, 3600),
            priority=ZonePriority.HIGH,
            risk_level=RiskLevel.HIGH,
        )
        self.add_tfr(tfr)
        return tfr

    def generate_construction_tfr(self, position: Tuple[float, float]) -> TFRDefinition:
        """Generate a construction zone TFR."""
        tfr = TFRDefinition(
            source=TFRSource.CONSTRUCTION,
            name="Construction Zone",
            description="Temporary restriction due to crane/construction activity.",
            zone_type=ZoneType.CONSTRUCTION_ZONE,
            center=position,
            radius=random.uniform(5, 15),
            altitude_min=5.0,
            altitude_max=80.0,
            duration_seconds=random.uniform(600, 7200),
            priority=ZonePriority.MEDIUM,
            risk_level=RiskLevel.MODERATE,
        )
        self.add_tfr(tfr)
        return tfr

    def generate_weather_tfr(self, position: Tuple[float, float],
                              weather_type: str = "storm") -> TFRDefinition:
        """Generate a weather-related TFR."""
        tfr = TFRDefinition(
            source=TFRSource.WEATHER,
            name=f"Weather: {weather_type.title()}",
            description=f"Temporary restriction due to {weather_type} conditions.",
            zone_type=ZoneType.TFR,
            center=position,
            radius=random.uniform(20, 50),
            altitude_min=0.0,
            altitude_max=200.0,
            duration_seconds=random.uniform(300, 1800),
            priority=ZonePriority.HIGH,
            risk_level=RiskLevel.HIGH,
        )
        self.add_tfr(tfr)
        return tfr

    # ── Prediction ──────────────────────────────────────────────

    def predict_tfrs(self, position: Tuple[float, float],
                      lookahead_minutes: float = 30.0) -> List[Dict[str, Any]]:
        """
        Predict future TFRs based on historical patterns.
        Returns list of predicted TFRs with confidence scores.
        """
        if not self.prediction_enabled:
            return []

        predictions = []
        current_hour = time.localtime().tm_hour

        # Hourly distribution prediction
        hour_freq = self._prediction_model['hourly_distribution'].get(current_hour, 0)
        if hour_freq > 0:
            # High-traffic hour - predict likely TFRs
            for zone_type, freq in self._prediction_model['type_distribution'].items():
                if freq > 2:  # Only predict if historically common
                    predictions.append({
                        'type': zone_type,
                        'probability': min(freq / 10, 0.9),
                        'timeframe': f"{current_hour}:00 - {current_hour + 1}:00",
                        'confidence': min(freq / 20, 0.95),
                    })

        # Location hotspot prediction
        for hotspot in self._prediction_model['location_hotspots']:
            hx, hy = hotspot['position']
            dist = math.sqrt((hx - position[0]) ** 2 + (hy - position[1]) ** 2)
            if dist < 30 and hotspot['frequency'] > 3:
                predictions.append({
                    'type': hotspot.get('type', 'unknown'),
                    'position': (hx, hy),
                    'radius': hotspot.get('radius', 15),
                    'probability': min(hotspot['frequency'] / 15, 0.85),
                    'confidence': min(hotspot['frequency'] / 25, 0.9),
                    'timeframe': 'likely within next hour',
                })

        return predictions

    def record_tfr_occurrence(self, tfr: TFRDefinition):
        """Record a TFR occurrence for prediction model improvement."""
        hour = time.localtime().tm_hour
        self._prediction_model['hourly_distribution'][hour] = \
            self._prediction_model['hourly_distribution'].get(hour, 0) + 1

        source_str = tfr.source.value
        self._prediction_model['type_distribution'][source_str] = \
            self._prediction_model['type_distribution'].get(source_str, 0) + 1

    def record_location_hotspot(self, position: Tuple[float, float],
                                 zone_type: str, radius: float):
        """Record a location as a TFR hotspot."""
        for hotspot in self._prediction_model['location_hotspots']:
            hx, hy = hotspot['position']
            if math.sqrt((hx - position[0]) ** 2 + (hy - position[1]) ** 2) < 10:
                hotspot['frequency'] += 1
                hotspot['radius'] = max(hotspot['radius'], radius)
                return

        self._prediction_model['location_hotspots'].append({
            'position': position,
            'type': zone_type,
            'radius': radius,
            'frequency': 1,
        })

    # ── Update Cycle ────────────────────────────────────────────

    def update(self, drone_position: Tuple[float, float],
               current_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Update TFR manager. Cleans up expired TFRs and generates reports.
        Called every simulation step.
        """
        now = current_time or time.time()
        report = {
            'active_tfrs': len(self.get_active_tfrs()),
            'expired_this_cycle': 0,
            'new_this_cycle': 0,
            'nearby_tfrs': len(self.get_tfrs_near(drone_position, 30)),
            'predictions': [],
        }

        # Auto-cleanup expired TFRs
        if self.auto_cleanup and (now - self._last_cleanup) >= self.cleanup_interval:
            expired = self.get_expired_tfrs()
            for tfr in expired:
                self.remove_tfr(tfr.tfr_id)
                self._tfr_history.append(tfr)
                report['expired_this_cycle'] += 1
            self._last_cleanup = now

        # Generate predictions if enabled and nearby
        if self.prediction_enabled:
            report['predictions'] = self.predict_tfrs(drone_position)

        return report

    # ── Configuration ───────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get TFR manager statistics."""
        return {
            'total_tfrs': len(self._tfrs),
            'active_tfrs': len(self.get_active_tfrs()),
            'historical_tfrs': len(self._tfr_history),
            'max_concurrent': self.max_concurrent_tfrs,
            'prediction_enabled': self.prediction_enabled,
            'prediction_hotspots': len(self._prediction_model['location_hotspots']),
        }

    def clear_all(self):
        """Clear all TFRs."""
        self._tfrs.clear()
        self._active_zone_ids.clear()