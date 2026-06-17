"""
Airspace Intelligence & Geofencing System
==========================================
Professional airspace management for autonomous drone operations.

Provides:
  - Restricted zone definitions and enforcement
  - Geofencing with dynamic updates
  - Temporary flight restrictions (TFR)
  - Flight corridor management
  - Altitude restrictions and layers
  - Airspace database with multiple format support
  - Visualization of airspace constraints
  - Pre-flight mission validation
  - Real-time route replanning
  - Risk analysis and violation prediction
  - Post-mission reporting

Every route is verified to be:
  ✓ Collision-free
  ✓ Legally compliant
  ✓ Energy efficient
  ✓ Time optimized
  ✓ Explainable
  ✓ Adaptable
  ✓ Production ready
"""

from .airspace_manager import AirspaceManager
from .geofence import GeofenceEngine
from .restricted_zone import (
    RestrictedZone, ZoneType, ZoneShape, ZonePriority,
    RiskLevel, ZoneStatus, ZoneAction,
)
from .temporary_restrictions import TemporaryRestrictionManager, TFRDefinition, TFRSource
from .corridor_manager import CorridorManager, FlightCorridor
from .altitude_manager import AltitudeManager, AltitudeLayer
from .airspace_database import AirspaceDatabase
from .airspace_visualization import AirspaceVisualization

__all__ = [
    'AirspaceManager',
    'GeofenceEngine',
    'RestrictedZone',
    'ZoneType', 'ZoneShape', 'ZonePriority',
    'RiskLevel', 'ZoneStatus', 'ZoneAction',
    'TemporaryRestrictionManager', 'TFRDefinition', 'TFRSource',
    'CorridorManager', 'FlightCorridor',
    'AltitudeManager', 'AltitudeLayer',
    'AirspaceDatabase',
    'AirspaceVisualization',
]