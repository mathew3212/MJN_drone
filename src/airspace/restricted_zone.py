"""
Restricted Zone Models
=======================
Comprehensive zone definitions for airspace intelligence.

Supports:
  - 18+ zone types (military, airports, schools, hospitals, TFRs, etc.)
  - 8 zone shapes (circle, rectangle, polygon, 3D volume, etc.)
  - Priority levels and risk scoring
  - Altitude envelopes and safety buffers
  - Temporal activation windows
  - Dynamic/static classification
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum, auto


# ═══════════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════════

class ZoneType(Enum):
    """Comprehensive airspace restriction categories."""
    RESTRICTED = "restricted"
    MILITARY_BASE = "military_base"
    AIRPORT = "airport"
    HELIPAD = "helipad"
    GOVERNMENT_BUILDING = "government_building"
    POWER_PLANT = "power_plant"
    NUCLEAR_FACILITY = "nuclear_facility"
    PRISON = "prison"
    WILDLIFE_SANCTUARY = "wildlife_sanctuary"
    NATIONAL_PARK = "national_park"
    SCHOOL_ZONE = "school_zone"
    HOSPITAL = "hospital"
    EMERGENCY_ZONE = "emergency_zone"
    TFR = "temporary_flight_restriction"
    VIP_MOVEMENT = "vip_movement"
    DISASTER_AREA = "disaster_area"
    CONSTRUCTION_ZONE = "construction_zone"
    EVENT_ZONE = "event_zone"
    PRIVATE_PROPERTY = "private_property"
    CUSTOM = "custom"
    FUTURE_DYNAMIC = "future_dynamic"


class ZoneShape(Enum):
    """Supported geofence shapes."""
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    POLYGON = "polygon"
    MULTI_POLYGON = "multi_polygon"
    CORRIDOR = "corridor"
    ALTITUDE_CYLINDER = "altitude_cylinder"
    VOLUME_3D = "3d_volume"
    COMPLEX_GEOFENCE = "complex_geofence"


class ZonePriority(Enum):
    """Priority levels for zone conflict resolution."""
    LOWEST = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    HIGHEST = 4
    CRITICAL = 5


class RiskLevel(Enum):
    """Risk classification for airspace zones."""
    NONE = 0.0
    MINIMAL = 0.2
    LOW = 0.4
    MODERATE = 0.6
    HIGH = 0.8
    SEVERE = 1.0


class ZoneStatus(Enum):
    """Operational status of a restricted zone."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SCHEDULED = "scheduled"
    EXPIRED = "expired"
    PENDING_REVIEW = "pending_review"
    CANCELLED = "cancelled"


class ZoneAction(Enum):
    """Possible actions when a restricted zone is encountered."""
    AVOID = "avoid"
    FLY_AROUND = "fly_around"
    INCREASE_ALTITUDE = "increase_altitude"
    DECREASE_ALTITUDE = "decrease_altitude"
    WAIT = "wait"
    RETURN_HOME = "return_home"
    LAND = "land"
    REQUEST_PERMISSION = "request_permission"
    ABORT_MISSION = "abort_mission"
    FOLLOW_CORRIDOR = "follow_corridor"
    PROCEED_CAUTIOUSLY = "proceed_cautiously"


class AirspaceClass(Enum):
    """Standard aviation airspace classes (ICAO/FAA)."""
    CLASS_A = "Class A"
    CLASS_B = "Class B"
    CLASS_C = "Class C"
    CLASS_D = "Class D"
    CLASS_E = "Class E"
    CLASS_G = "Class G"
    UNCLASSIFIED = "Unclassified"
    RESTRICTED = "Restricted"
    PROHIBITED = "Prohibited"
    WARNING = "Warning Area"
    MOA = "Military Operations Area"
    TFR = "Temporary Flight Restriction"


# ═══════════════════════════════════════════════════════════════════
# Zone Geometry
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Point2D:
    """A 2D geographic point."""
    x: float  # meters or grid units
    y: float

    def distance_to(self, other: Point2D) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class AltitudeEnvelope:
    """Altitude constraints for a zone."""
    minimum_altitude: float = 0.0  # meters AGL
    maximum_altitude: float = 150.0  # meters AGL
    ceiling_type: str = "AGL"  # AGL or MSL

    def contains(self, altitude: float) -> bool:
        return self.minimum_altitude <= altitude <= self.maximum_altitude

    def altitude_range(self) -> float:
        return self.maximum_altitude - self.minimum_altitude


# ═══════════════════════════════════════════════════════════════════
# Shape Implementations
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CircleZone:
    """Circular restricted zone."""
    center: Point2D
    radius: float  # meters or grid units

    def contains_point(self, point: Point2D, buffer: float = 0.0) -> bool:
        return point.distance_to(self.center) <= (self.radius + buffer)

    def distance_from_edge(self, point: Point2D) -> float:
        return point.distance_to(self.center) - self.radius

    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        return (
            self.center.x - self.radius,
            self.center.y - self.radius,
            self.center.x + self.radius,
            self.center.y + self.radius,
        )


@dataclass
class RectangleZone:
    """Rectangular restricted zone (axis-aligned or rotated)."""
    center: Point2D
    width: float
    height: float
    rotation: float = 0.0  # radians

    def contains_point(self, point: Point2D, buffer: float = 0.0) -> bool:
        # Rotate point to local coordinate system
        dx = point.x - self.center.x
        dy = point.y - self.center.y
        cos_r = math.cos(-self.rotation)
        sin_r = math.sin(-self.rotation)
        local_x = dx * cos_r - dy * sin_r
        local_y = dx * sin_r + dy * cos_r
        half_w = self.width / 2 + buffer
        half_h = self.height / 2 + buffer
        return -half_w <= local_x <= half_w and -half_h <= local_y <= half_h

    def distance_from_edge(self, point: Point2D) -> float:
        """Approximate distance from point to rectangle edge."""
        dx = point.x - self.center.x
        dy = point.y - self.center.y
        cos_r = math.cos(-self.rotation)
        sin_r = math.sin(-self.rotation)
        local_x = dx * cos_r - dy * sin_r
        local_y = dx * sin_r + dy * cos_r
        half_w = self.width / 2
        half_h = self.height / 2
        dx_edge = abs(local_x) - half_w
        dy_edge = abs(local_y) - half_h
        if dx_edge > 0 and dy_edge > 0:
            return math.sqrt(dx_edge ** 2 + dy_edge ** 2)
        elif dx_edge > 0:
            return dx_edge
        elif dy_edge > 0:
            return dy_edge
        return min(abs(local_x) - half_w, abs(local_y) - half_h)

    def get_vertices(self) -> List[Point2D]:
        """Get the 4 corner vertices."""
        half_w = self.width / 2
        half_h = self.height / 2
        cos_r = math.cos(self.rotation)
        sin_r = math.sin(self.rotation)
        corners = [
            (-half_w, -half_h),
            (half_w, -half_h),
            (half_w, half_h),
            (-half_w, half_h),
        ]
        return [
            Point2D(
                self.center.x + x * cos_r - y * sin_r,
                self.center.y + x * sin_r + y * cos_r,
            )
            for x, y in corners
        ]

    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        verts = self.get_vertices()
        xs = [v.x for v in verts]
        ys = [v.y for v in verts]
        return (min(xs), min(ys), max(xs), max(ys))


@dataclass
class PolygonZone:
    """Arbitrary polygon restricted zone."""
    vertices: List[Point2D]  # clockwise or counter-clockwise

    def contains_point(self, point: Point2D, buffer: float = 0.0) -> bool:
        """Ray casting algorithm for point-in-polygon."""
        if len(self.vertices) < 3:
            return False
        inside = False
        j = len(self.vertices) - 1
        for i in range(len(self.vertices)):
            xi, yi = self.vertices[i].x, self.vertices[i].y
            xj, yj = self.vertices[j].x, self.vertices[j].y
            if ((yi > point.y) != (yj > point.y)) and \
               (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        xs = [v.x for v in self.vertices]
        ys = [v.y for v in self.vertices]
        return (min(xs), min(ys), max(xs), max(ys))


@dataclass
class MultiPolygonZone:
    """Zone consisting of multiple polygons (e.g., complex airspace)."""
    polygons: List[PolygonZone]

    def contains_point(self, point: Point2D, buffer: float = 0.0) -> bool:
        return any(p.contains_point(point, buffer) for p in self.polygons)

    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        boxes = [p.get_bounding_box() for p in self.polygons]
        return (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )


@dataclass
class Volume3D:
    """3D volume zone with full spatial constraints."""
    shape: Any  # One of the shape classes above
    altitude_envelope: AltitudeEnvelope = field(default_factory=AltitudeEnvelope)

    def contains_point_3d(self, point: Point2D, altitude: float) -> bool:
        if not self.altitude_envelope.contains(altitude):
            return False
        return self.shape.contains_point(point)


# ═══════════════════════════════════════════════════════════════════
# Restricted Zone (Master Class)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class RestrictedZone:
    """
    Complete restricted zone definition with all properties.
    """
    # Identity
    zone_id: str = ""
    name: str = ""
    description: str = ""

    # Classification
    zone_type: ZoneType = ZoneType.RESTRICTED
    zone_shape: ZoneShape = ZoneShape.CIRCLE
    priority: ZonePriority = ZonePriority.MEDIUM
    airspace_class: AirspaceClass = AirspaceClass.UNCLASSIFIED

    # Geometry
    center_lat: float = 0.0  # latitude or y-coordinate
    center_lon: float = 0.0  # longitude or x-coordinate
    shape_data: Any = None  # CircleZone, RectangleZone, etc.
    altitude_limits: AltitudeEnvelope = field(default_factory=AltitudeEnvelope)

    # Safety
    safety_buffer: float = 5.0  # safety margin in grid units/meters
    max_speed: float = 0.0  # 0 = no speed limit
    allowed_directions: List[float] = field(default_factory=list)

    # Temporal
    activation_time: float = 0.0  # timestamp, 0 = always active
    expiration_time: float = float('inf')  # timestamp, inf = permanent
    is_dynamic: bool = False

    # Permissions
    permission_required: bool = False
    permission_contact: str = ""

    # Risk
    risk_level: RiskLevel = RiskLevel.MODERATE
    base_penalty: float = 100.0  # penalty score for violation
    violation_probability: float = 0.0  # computed dynamically

    # Operational
    suggested_action: ZoneAction = ZoneAction.AVOID
    is_active: bool = True
    status: ZoneStatus = ZoneStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    source: str = "manual"  # manual, import, api, etc.

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.zone_id:
            self.zone_id = str(uuid.uuid4())[:12]

    # ── Properties ────────────────────────────────────────────────

    @property
    def center(self) -> Tuple[float, float]:
        return (self.center_lon, self.center_lat)

    @center.setter
    def center(self, value: Tuple[float, float]):
        self.center_lon, self.center_lat = value

    @property
    def is_permanent(self) -> bool:
        return self.expiration_time == float('inf')

    @property
    def is_temporal(self) -> bool:
        return not self.is_permanent and self.expiration_time > 0

    @property
    def is_expired(self) -> bool:
        if self.is_permanent:
            return False
        return time.time() > self.expiration_time

    @property
    def is_future(self) -> bool:
        return self.activation_time > time.time()

    # ── Spatial Queries ──────────────────────────────────────────

    def contains_point(self, point: Tuple[float, float],
                       altitude: Optional[float] = None,
                       include_buffer: bool = True) -> bool:
        """Check if a point (x, y) lies within this restricted zone."""
        if self.status != ZoneStatus.ACTIVE:
            return False
        if self.is_expired:
            return False
        if self.is_future:
            return False

        pt = Point2D(point[0], point[1])
        buffer = self.safety_buffer if include_buffer else 0.0

        if self.shape_data is None:
            # Default: use circle from center
            return CircleZone(center=Point2D(self.center_lon, self.center_lat),
                              radius=10.0).contains_point(pt, buffer)

        # Use the shape's containment test
        if isinstance(self.shape_data, (CircleZone, RectangleZone)):
            result = self.shape_data.contains_point(pt, buffer)
        elif isinstance(self.shape_data, PolygonZone):
            result = self.shape_data.contains_point(pt, buffer)
        elif isinstance(self.shape_data, MultiPolygonZone):
            result = self.shape_data.contains_point(pt, buffer)
        elif isinstance(self.shape_data, Volume3D):
            if altitude is not None:
                result = self.shape_data.contains_point_3d(pt, altitude)
            else:
                result = self.shape_data.shape.contains_point(pt, buffer)
        else:
            result = CircleZone(
                center=Point2D(self.center_lon, self.center_lat),
                radius=10.0
            ).contains_point(pt, buffer)

        # Also check altitude if provided
        if altitude is not None:
            result = result and self.altitude_limits.contains(altitude)

        return result

    def distance_to(self, point: Tuple[float, float]) -> float:
        """Distance from a point to the edge of this zone (negative if inside)."""
        pt = Point2D(point[0], point[1])
        if self.shape_data is None:
            center = Point2D(self.center_lon, self.center_lat)
            return pt.distance_to(center) - 10.0

        if hasattr(self.shape_data, 'distance_from_edge'):
            return self.shape_data.distance_from_edge(pt)

        # Fallback: distance to center minus approximate radius
        if isinstance(self.shape_data, CircleZone):
            return self.shape_data.distance_from_edge(pt)

        # For polygons, compute minimum distance to any edge
        if isinstance(self.shape_data, PolygonZone):
            verts = self.shape_data.vertices
            if self.contains_point(point):
                return -self._min_distance_to_polygon_edge(pt, verts)
            return self._min_distance_to_polygon_edge(pt, verts)

        return self._approx_distance(pt)

    def _min_distance_to_polygon_edge(self, pt: Point2D,
                                       verts: List[Point2D]) -> float:
        """Minimum distance from point to polygon edges."""
        min_dist = float('inf')
        n = len(verts)
        for i in range(n):
            a = verts[i]
            b = verts[(i + 1) % n]
            dist = self._point_to_segment_distance(pt, a, b)
            min_dist = min(min_dist, dist)
        return min_dist

    @staticmethod
    def _point_to_segment_distance(p: Point2D, a: Point2D,
                                    b: Point2D) -> float:
        """Distance from point to line segment."""
        dx = b.x - a.x
        dy = b.y - a.y
        if dx == 0 and dy == 0:
            return p.distance_to(a)
        t = max(0, min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx ** 2 + dy ** 2)))
        proj_x = a.x + t * dx
        proj_y = a.y + t * dy
        return math.sqrt((p.x - proj_x) ** 2 + (p.y - proj_y) ** 2)

    def _approx_distance(self, pt: Point2D) -> float:
        """Approximate distance using bounding box."""
        bb = self.get_bounding_box()
        center_x = (bb[0] + bb[2]) / 2
        center_y = (bb[1] + bb[3]) / 2
        approx_radius = max((bb[2] - bb[0]) / 2, (bb[3] - bb[1]) / 2)
        return pt.distance_to(Point2D(center_x, center_y)) - approx_radius

    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Get bounding box as (min_x, min_y, max_x, max_y)."""
        if self.shape_data is None:
            clat = self.center_lat
            clon = self.center_lon
            r = 10.0 + self.safety_buffer
            return (clon - r, clat - r, clon + r, clat + r)

        if hasattr(self.shape_data, 'get_bounding_box'):
            return self.shape_data.get_bounding_box()

        return (self.center_lon - 10, self.center_lat - 10,
                self.center_lon + 10, self.center_lat + 10)

    # ── Risk Computation ─────────────────────────────────────────

    def compute_risk_score(self, drone_speed: float = 0.0,
                            drone_altitude: float = 50.0) -> float:
        """Compute current risk score for approaching this zone."""
        base = self.risk_level.value
        speed_factor = min(drone_speed / 20.0, 1.0) * 0.2
        alt_factor = 0.0
        if drone_altitude < self.altitude_limits.minimum_altitude:
            alt_factor = 0.1
        elif drone_altitude > self.altitude_limits.maximum_altitude:
            alt_factor = 0.05
        priority_factor = self.priority.value / 5.0 * 0.3
        dynamic_factor = 0.2 if self.is_dynamic else 0.0
        return min(base + speed_factor + alt_factor + priority_factor + dynamic_factor, 1.0)

    def get_avoidance_action(self, drone_position: Tuple[float, float],
                              drone_altitude: float) -> ZoneAction:
        """Determine the best action based on geometry and context."""
        pt = Point2D(drone_position[0], drone_position[1])

        # Check altitude options first
        if drone_altitude < self.altitude_limits.minimum_altitude:
            return ZoneAction.INCREASE_ALTITUDE
        if drone_altitude > self.altitude_limits.maximum_altitude:
            return ZoneAction.DECREASE_ALTITUDE

        # Check if we can fly around
        dist = self.distance_to(drone_position)
        if dist > 0 and dist < 50:
            return ZoneAction.FLY_AROUND

        # Check if we can avoid
        if dist > 50:
            return ZoneAction.AVOID

        # Permission-based
        if self.permission_required:
            return ZoneAction.REQUEST_PERMISSION

        # Default actions based on priority
        if self.priority in (ZonePriority.CRITICAL, ZonePriority.HIGHEST):
            return ZoneAction.ABORT_MISSION
        if self.priority == ZonePriority.HIGH:
            return ZoneAction.RETURN_HOME
        if self.priority == ZonePriority.MEDIUM:
            return ZoneAction.LAND

        return ZoneAction.WAIT

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'zone_id': self.zone_id,
            'name': self.name,
            'description': self.description,
            'zone_type': self.zone_type.value,
            'zone_shape': self.zone_shape.value,
            'priority': self.priority.value,
            'center_lat': self.center_lat,
            'center_lon': self.center_lon,
            'altitude_limits': {
                'min': self.altitude_limits.minimum_altitude,
                'max': self.altitude_limits.maximum_altitude,
            },
            'safety_buffer': self.safety_buffer,
            'max_speed': self.max_speed,
            'activation_time': self.activation_time,
            'expiration_time': self.expiration_time,
            'permission_required': self.permission_required,
            'risk_level': self.risk_level.value,
            'is_dynamic': self.is_dynamic,
            'is_active': self.is_active,
            'status': self.status.value,
            'source': self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RestrictedZone:
        """Deserialize from dictionary."""
        alt_limits = data.get('altitude_limits', {})
        return cls(
            zone_id=data.get('zone_id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            zone_type=ZoneType(data.get('zone_type', 'restricted')),
            zone_shape=ZoneShape(data.get('zone_shape', 'circle')),
            priority=ZonePriority(data.get('priority', 2)),
            center_lat=data.get('center_lat', 0.0),
            center_lon=data.get('center_lon', 0.0),
            altitude_limits=AltitudeEnvelope(
                minimum_altitude=alt_limits.get('min', 0.0),
                maximum_altitude=alt_limits.get('max', 150.0),
            ),
            safety_buffer=data.get('safety_buffer', 5.0),
            max_speed=data.get('max_speed', 0.0),
            activation_time=data.get('activation_time', 0.0),
            expiration_time=data.get('expiration_time', float('inf')),
            permission_required=data.get('permission_required', False),
            risk_level=RiskLevel(data.get('risk_level', 0.6)),
            is_dynamic=data.get('is_dynamic', False),
            is_active=data.get('is_active', True),
            status=ZoneStatus(data.get('status', 'active')),
            source=data.get('source', 'manual'),
        )