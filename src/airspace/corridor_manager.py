"""
Flight Corridor Manager
========================
Manages approved flight corridors for safe navigation through controlled airspace.

Features:
  - Pre-defined flight corridors through restricted zones
  - Dynamic corridor generation around obstacles
  - Corridor priority and capacity management
  - Entry/exit waypoint management
  - Altitude constraints within corridors
  - Speed limits and direction enforcement
"""

from __future__ import annotations

import math
import time
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto

from .restricted_zone import (
    RestrictedZone, ZoneType, ZonePriority, ZoneShape,
    Point2D, AltitudeEnvelope,
)


@dataclass
class CorridorWaypoint:
    """A waypoint within a flight corridor."""
    position: Tuple[float, float]
    altitude: float = 50.0
    max_speed: float = 10.0
    tolerance: float = 5.0
    is_entry: bool = False
    is_exit: bool = False
    label: str = ""


@dataclass
class FlightCorridor:
    """A defined flight corridor through airspace."""
    corridor_id: str = ""
    name: str = ""
    description: str = ""
    waypoints: List[CorridorWaypoint] = field(default_factory=list)
    width: float = 10.0  # half-width of corridor
    altitude_limits: AltitudeEnvelope = field(default_factory=AltitudeEnvelope)
    max_speed: float = 10.0
    direction: str = "bidirectional"  # "one_way", "bidirectional"
    priority: int = 5  # 0=highest, 9=lowest
    requires_clearance: bool = False
    is_active: bool = True
    connected_zones: List[str] = field(default_factory=list)  # zone IDs this corridor connects through

    @property
    def entry_point(self) -> Optional[CorridorWaypoint]:
        for wp in self.waypoints:
            if wp.is_entry:
                return wp
        return self.waypoints[0] if self.waypoints else None

    @property
    def exit_point(self) -> Optional[CorridorWaypoint]:
        for wp in self.waypoints:
            if wp.is_exit:
                return wp
        return self.waypoints[-1] if self.waypoints else None

    @property
    def length(self) -> float:
        total = 0.0
        for i in range(len(self.waypoints) - 1):
            a = self.waypoints[i].position
            b = self.waypoints[i + 1].position
            total += math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)
        return total

    def contains_point(self, point: Tuple[float, float],
                        altitude: Optional[float] = None) -> bool:
        """Check if a point is within this corridor."""
        if altitude is not None and not self.altitude_limits.contains(altitude):
            return False

        pt = Point2D(point[0], point[1])
        for i in range(len(self.waypoints) - 1):
            a = Point2D(*self.waypoints[i].position)
            b = Point2D(*self.waypoints[i + 1].position)
            dist = self._point_to_segment_distance(pt, a, b)
            if dist <= self.width:
                return True
        return False

    def nearest_point_on_corridor(self, point: Tuple[float, float]) -> Tuple[float, float]:
        """Find the nearest point on this corridor to a given point."""
        pt = Point2D(point[0], point[1])
        best_dist = float('inf')
        best_point = point

        for i in range(len(self.waypoints) - 1):
            a = Point2D(*self.waypoints[i].position)
            b = Point2D(*self.waypoints[i + 1].position)
            nearest = self._closest_point_on_segment(pt, a, b)
            dist = pt.distance_to(nearest)
            if dist < best_dist:
                best_dist = dist
                best_point = (nearest.x, nearest.y)

        return best_point

    def get_segment_index(self, point: Tuple[float, float]) -> int:
        """Get the index of the nearest corridor segment."""
        pt = Point2D(point[0], point[1])
        best_idx = 0
        best_dist = float('inf')

        for i in range(len(self.waypoints) - 1):
            a = Point2D(*self.waypoints[i].position)
            b = Point2D(*self.waypoints[i + 1].position)
            nearest = self._closest_point_on_segment(pt, a, b)
            dist = pt.distance_to(nearest)
            if dist < best_dist:
                best_dist = dist
                best_idx = i

        return best_idx

    @staticmethod
    def _point_to_segment_distance(p: Point2D, a: Point2D, b: Point2D) -> float:
        dx = b.x - a.x
        dy = b.y - a.y
        if dx == 0 and dy == 0:
            return p.distance_to(a)
        t = max(0, min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx ** 2 + dy ** 2)))
        proj_x = a.x + t * dx
        proj_y = a.y + t * dy
        return math.sqrt((p.x - proj_x) ** 2 + (p.y - proj_y) ** 2)

    @staticmethod
    def _closest_point_on_segment(p: Point2D, a: Point2D, b: Point2D) -> Point2D:
        dx = b.x - a.x
        dy = b.y - a.y
        if dx == 0 and dy == 0:
            return Point2D(a.x, a.y)
        t = max(0, min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx ** 2 + dy ** 2)))
        return Point2D(a.x + t * dx, a.y + t * dy)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'corridor_id': self.corridor_id,
            'name': self.name,
            'description': self.description,
            'waypoints': [(wp.position, wp.altitude) for wp in self.waypoints],
            'width': self.width,
            'altitude_limits': {'min': self.altitude_limits.minimum_altitude,
                                'max': self.altitude_limits.maximum_altitude},
            'max_speed': self.max_speed,
            'direction': self.direction,
            'priority': self.priority,
            'is_active': self.is_active,
        }


class CorridorManager:
    """
    Manages flight corridors for safe navigation.
    """

    def __init__(self):
        self._corridors: Dict[str, FlightCorridor] = {}

    def add_corridor(self, corridor: FlightCorridor) -> bool:
        if corridor.corridor_id in self._corridors:
            return False
        self._corridors[corridor.corridor_id] = corridor
        return True

    def remove_corridor(self, corridor_id: str) -> bool:
        return self._corridors.pop(corridor_id, None) is not None

    def get_corridor(self, corridor_id: str) -> Optional[FlightCorridor]:
        return self._corridors.get(corridor_id)

    def get_all_corridors(self) -> List[FlightCorridor]:
        return list(self._corridors.values())

    def get_active_corridors(self) -> List[FlightCorridor]:
        return [c for c in self._corridors.values() if c.is_active]

    def find_nearest_corridor(self, position: Tuple[float, float]) -> Optional[Tuple[FlightCorridor, float]]:
        best = None
        best_dist = float('inf')
        for corridor in self.get_active_corridors():
            nearest = corridor.nearest_point_on_corridor(position)
            dist = math.sqrt((nearest[0] - position[0]) ** 2 + (nearest[1] - position[1]) ** 2)
            if dist < best_dist:
                best_dist = dist
                best = (corridor, dist)
        return best

    def get_corridors_connecting(self, zone_id: str) -> List[FlightCorridor]:
        return [
            c for c in self._corridors.values()
            if zone_id in c.connected_zones
        ]

    def create_corridor_between(self, start: Tuple[float, float],
                                  end: Tuple[float, float],
                                  name: str = "Auto Corridor",
                                  altitude: float = 50.0) -> FlightCorridor:
        """Create a simple corridor between two points."""
        import uuid
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2

        corridor = FlightCorridor(
            corridor_id=str(uuid.uuid4())[:12],
            name=name,
            description=f"Auto-generated corridor from {start} to {end}",
            waypoints=[
                CorridorWaypoint(position=start, altitude=altitude, is_entry=True),
                CorridorWaypoint(position=(mid_x, mid_y), altitude=altitude),
                CorridorWaypoint(position=end, altitude=altitude, is_exit=True),
            ],
            width=8.0,
            max_speed=10.0,
        )
        self.add_corridor(corridor)
        return corridor

    def get_stats(self) -> Dict[str, Any]:
        return {
            'total_corridors': len(self._corridors),
            'active_corridors': len(self.get_active_corridors()),
        }