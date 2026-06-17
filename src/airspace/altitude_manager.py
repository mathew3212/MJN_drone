"""
Altitude Manager
=================
Manages altitude-based restrictions and flight level assignments.

Features:
  - Altitude layers with configurable heights
  - Altitude-specific restrictions
  - Optimal altitude calculation for efficiency
  - Terrain awareness and minimum safe altitudes
  - Airspace class altitude boundaries
  - Vertical conflict detection
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto

from .restricted_zone import (
    RestrictedZone, AltitudeEnvelope, ZoneType, RiskLevel,
)


@dataclass
class AltitudeLayer:
    """A defined altitude band with rules."""
    layer_id: str = ""
    name: str = ""
    min_altitude: float = 0.0
    max_altitude: float = 50.0
    max_speed: float = 10.0
    direction: str = "any"  # "any", "northbound", "southbound", etc.
    is_restricted: bool = False
    requires_clearance: bool = False
    description: str = ""
    priority: int = 5  # for conflict resolution

    def contains(self, altitude: float) -> bool:
        return self.min_altitude <= altitude <= self.max_altitude

    @property
    def midpoint(self) -> float:
        return (self.min_altitude + self.max_altitude) / 2

    @property
    def thickness(self) -> float:
        return self.max_altitude - self.min_altitude


class AltitudeManager:
    """
    Manages altitude-based navigation constraints.
    """

    def __init__(self, max_altitude: float = 200.0):
        self.max_altitude = max_altitude
        self._layers: List[AltitudeLayer] = []
        self._default_layers_initialized: bool = False
        self._altitude_restrictions: Dict[str, AltitudeEnvelope] = {}

        self._init_default_layers()

    def _init_default_layers(self):
        """Initialize standard altitude layers."""
        self._layers = [
            AltitudeLayer(
                layer_id="ground",
                name="Ground Level",
                min_altitude=0.0, max_altitude=5.0,
                max_speed=2.0, direction="any",
                description="Takeoff and landing zone",
            ),
            AltitudeLayer(
                layer_id="low",
                name="Low Altitude",
                min_altitude=5.0, max_altitude=30.0,
                max_speed=5.0, direction="any",
                description="Low altitude operations",
            ),
            AltitudeLayer(
                layer_id="cruise_low",
                name="Cruise Low",
                min_altitude=30.0, max_altitude=60.0,
                max_speed=10.0, direction="any",
                description="Standard cruising altitude",
            ),
            AltitudeLayer(
                layer_id="cruise_high",
                name="Cruise High",
                min_altitude=60.0, max_altitude=100.0,
                max_speed=15.0, direction="any",
                description="High speed cruising altitude",
            ),
            AltitudeLayer(
                layer_id="high",
                name="High Altitude",
                min_altitude=100.0, max_altitude=150.0,
                max_speed=20.0, direction="any",
                description="High altitude operations",
            ),
            AltitudeLayer(
                layer_id="max",
                name="Maximum Altitude",
                min_altitude=150.0, max_altitude=self.max_altitude,
                max_speed=8.0, direction="any",
                description="Maximum operational ceiling",
            ),
        ]
        self._default_layers_initialized = True

    # ── Layer Management ────────────────────────────────────────

    def add_layer(self, layer: AltitudeLayer) -> bool:
        if any(l.layer_id == layer.layer_id for l in self._layers):
            return False
        self._layers.append(layer)
        self._layers.sort(key=lambda l: l.min_altitude)
        return True

    def remove_layer(self, layer_id: str) -> bool:
        for i, layer in enumerate(self._layers):
            if layer.layer_id == layer_id:
                self._layers.pop(i)
                return True
        return False

    def get_layer(self, layer_id: str) -> Optional[AltitudeLayer]:
        for layer in self._layers:
            if layer.layer_id == layer_id:
                return layer
        return None

    def get_layers(self) -> List[AltitudeLayer]:
        return list(self._layers)

    def get_active_layers(self) -> List[AltitudeLayer]:
        return [l for l in self._layers if not l.is_restricted]

    def get_layer_at(self, altitude: float) -> Optional[AltitudeLayer]:
        for layer in self._layers:
            if layer.contains(altitude):
                return layer
        return None

    # ── Altitude Restrictions ───────────────────────────────────

    def add_restriction(self, zone_id: str, envelope: AltitudeEnvelope):
        """Add an altitude restriction for a zone."""
        self._altitude_restrictions[zone_id] = envelope

    def remove_restriction(self, zone_id: str):
        self._altitude_restrictions.pop(zone_id, None)

    def get_restrictions_for(self, altitude: float) -> List[Tuple[str, AltitudeEnvelope]]:
        """Get all restrictions that apply at a given altitude."""
        return [
            (zid, env) for zid, env in self._altitude_restrictions.items()
            if env.contains(altitude)
        ]

    # ── Altitude Optimization ───────────────────────────────────

    def suggest_optimal_altitude(self, distance_to_go: float,
                                  battery_level: float = 50.0,
                                  wind_speed: float = 0.0,
                                  payload_weight: float = 0.0) -> Dict[str, Any]:
        """
        Suggest the optimal altitude for current mission parameters.

        Considers:
          - Distance remaining
          - Battery efficiency at different altitudes
          - Wind conditions
          - Payload weight
        """
        # Base altitude selection on distance
        if distance_to_go > 80:
            optimal = 80.0  # high cruise for long distances
            reason = "Long distance - high altitude for efficiency"
        elif distance_to_go > 50:
            optimal = 60.0
            reason = "Medium distance - standard cruise altitude"
        elif distance_to_go > 20:
            optimal = 40.0
            reason = "Short distance - low altitude"
        else:
            optimal = 20.0
            reason = "Very short distance - minimal climb"

        # Adjust for battery
        if battery_level < 20:
            optimal = 15.0
            reason = "Low battery - minimum altitude"
        elif battery_level < 40:
            optimal = min(optimal, 40.0)
            reason = "Moderate battery - reduced altitude"

        # Adjust for wind (climb above wind if possible)
        if wind_speed > 10:
            desired = min(optimal + 20, 100.0)
            if desired > 60:
                optimal = desired
                reason = "High wind - increased altitude for stability"

        # Adjust for payload
        if payload_weight > 0.5:
            optimal = max(optimal - 10, 10.0)
            reason = "Heavy payload - reduced optimal altitude"

        # Find the layer this altitude falls in
        layer = self.get_layer_at(optimal)
        max_speed = layer.max_speed if layer else 10.0

        return {
            'optimal_altitude': optimal,
            'max_speed': max_speed,
            'layer_id': layer.layer_id if layer else 'unknown',
            'layer_name': layer.name if layer else 'Unknown',
            'reason': reason,
        }

    def find_safe_altitude(self, position: Tuple[float, float],
                            zones: List[RestrictedZone],
                            current_altitude: float = 50.0) -> Dict[str, Any]:
        """
        Find a safe altitude that avoids all zone restrictions.
        Returns the best altitude and explanation.
        """
        # Collect forbidden altitude ranges
        forbidden_ranges = []
        for zone in zones:
            if zone.contains_point(position):
                forbidden_ranges.append(
                    (zone.altitude_limits.minimum_altitude,
                     zone.altitude_limits.maximum_altitude)
                )

        if not forbidden_ranges:
            return {
                'safe_altitude': current_altitude,
                'change_required': False,
                'reason': 'No altitude conflicts.',
            }

        # Find gaps in the forbidden ranges
        safe_altitudes = []
        test_alts = [5, 15, 30, 50, 70, 90, 120, 150]

        for alt in test_alts:
            is_safe = not any(
                lo <= alt <= hi for lo, hi in forbidden_ranges
            )
            if is_safe and alt <= self.max_altitude:
                safe_altitudes.append(alt)

        if not safe_altitudes:
            return {
                'safe_altitude': current_altitude,
                'change_required': True,
                'reason': 'No safe altitude found - all altitudes restricted.',
                'action': 'return_home',
            }

        # Pick closest safe altitude to current
        best_alt = min(safe_altitudes, key=lambda a: abs(a - current_altitude))

        return {
            'safe_altitude': best_alt,
            'change_required': abs(best_alt - current_altitude) > 2.0,
            'change_amount': best_alt - current_altitude,
            'direction': 'Climb' if best_alt > current_altitude else 'Descend',
            'reason': f'Adjusting from {current_altitude:.0f}m to {best_alt:.0f}m to avoid restricted altitudes.',
        }

    def validate_altitude(self, altitude: float) -> Dict[str, Any]:
        """
        Validate whether an altitude is safe and legal.
        """
        if altitude < 0:
            return {'valid': False, 'reason': 'Below ground level.'}
        if altitude > self.max_altitude:
            return {'valid': False, 'reason': f'Exceeds maximum altitude of {self.max_altitude}m.'}

        layer = self.get_layer_at(altitude)
        if layer and layer.is_restricted:
            return {'valid': False, 'reason': f'Altitude {altitude}m is in restricted layer: {layer.name}.'}

        return {
            'valid': True,
            'layer': layer.name if layer else 'Unknown',
            'max_speed': layer.max_speed if layer else 10.0,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            'max_altitude': self.max_altitude,
            'layers': len(self._layers),
            'restrictions': len(self._altitude_restrictions),
        }