"""
Airspace Visualization
=======================
Visualization components for the airspace intelligence system.

Supports:
  - Restricted zone rendering with color coding
  - Proximity warning visualization
  - Altitude layer display
  - Flight corridor rendering
  - Emergency landing sites
  - Airspace class labels
  - Mission path validation overlay

Color Coding:
  - Green: Safe airspace
  - Yellow: Caution (near zones)
  - Orange: Restricted zones
  - Red: Prohibited zones
  - Purple: Temporary restrictions
  - Blue: Approved flight corridors
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple, Dict, Any

from .restricted_zone import (
    RestrictedZone, ZoneType, ZonePriority, ZoneShape,
    RiskLevel, ZoneStatus, Point2D, AltitudeEnvelope,
    CircleZone, RectangleZone, PolygonZone, MultiPolygonZone,
)
from .altitude_manager import AltitudeLayer


class AirspaceVisualization:
    """
    Generates visualization data for airspace overlays.
    Outputs data structures that can be rendered by the dashboard.
    """

    def __init__(self, world_width: float = 100.0, world_height: float = 100.0):
        self.world_width = world_width
        self.world_height = world_height
        self.resolution: int = 100  # default grid resolution

    # ══════════════════════════════════════════════════════════════
    # COLOR SCHEME
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def get_zone_color(zone: RestrictedZone) -> str:
        """Get the display color for a zone based on its type and risk."""
        color_map = {
            ZoneType.RESTRICTED: '#FF6600',  # Orange
            ZoneType.MILITARY_BASE: '#FF0000',  # Red
            ZoneType.AIRPORT: '#DC143C',  # Crimson
            ZoneType.HELIPAD: '#FF4500',  # OrangeRed
            ZoneType.GOVERNMENT_BUILDING: '#8B0000',  # DarkRed
            ZoneType.POWER_PLANT: '#FF6347',  # Tomato
            ZoneType.NUCLEAR_FACILITY: '#FF0000',  # Red
            ZoneType.PRISON: '#B22222',  # FireBrick
            ZoneType.WILDLIFE_SANCTUARY: '#228B22',  # ForestGreen
            ZoneType.NATIONAL_PARK: '#006400',  # DarkGreen
            ZoneType.SCHOOL_ZONE: '#FFD700',  # Gold
            ZoneType.HOSPITAL: '#FF69B4',  # HotPink
            ZoneType.EMERGENCY_ZONE: '#FF0000',  # Red
            ZoneType.TFR: '#800080',  # Purple
            ZoneType.VIP_MOVEMENT: '#9400D3',  # DarkViolet
            ZoneType.DISASTER_AREA: '#FF0000',  # Red
            ZoneType.CONSTRUCTION_ZONE: '#FFA500',  # Orange
            ZoneType.EVENT_ZONE: '#9932CC',  # DarkOrchid
            ZoneType.PRIVATE_PROPERTY: '#DAA520',  # Goldenrod
            ZoneType.CUSTOM: '#FF6600',  # Orange
            ZoneType.FUTURE_DYNAMIC: '#808080',  # Gray
        }
        return color_map.get(zone.zone_type, '#FF6600')

    @staticmethod
    def get_zone_opacity(zone: RestrictedZone) -> float:
        """Get display opacity based on zone status and risk."""
        if zone.status != ZoneStatus.ACTIVE:
            return 0.1
        if zone.risk_level == RiskLevel.SEVERE:
            return 0.4
        if zone.risk_level == RiskLevel.HIGH:
            return 0.3
        return 0.2

    @staticmethod
    def get_status_color(zone_status: str) -> str:
        """Get color for zone status indicators."""
        colors = {
            'active': '#00FF00',  # Green
            'inactive': '#808080',  # Gray
            'scheduled': '#FFFF00',  # Yellow
            'expired': '#A9A9A9',  # DarkGray
            'pending_review': '#FFA500',  # Orange
            'cancelled': '#808080',  # Gray
        }
        return colors.get(zone_status, '#808080')

    # ══════════════════════════════════════════════════════════════
    # ZONE RENDERING
    # ══════════════════════════════════════════════════════════════

    def render_zone(self, zone: RestrictedZone) -> Dict[str, Any]:
        """
        Render a single zone as display data.
        Returns dict with vertices, color, label, etc.
        """
        shape_data = {
            'zone_id': zone.zone_id,
            'name': zone.name,
            'type': zone.zone_type.value,
            'color': self.get_zone_color(zone),
            'opacity': self.get_zone_opacity(zone),
            'status': zone.status.value,
            'status_color': self.get_status_color(zone.status.value),
            'priority': zone.priority.value,
            'risk_level': zone.risk_level.value,
            'center': (zone.center_lon, zone.center_lat),
            'altitude_min': zone.altitude_limits.minimum_altitude,
            'altitude_max': zone.altitude_limits.maximum_altitude,
            'is_dynamic': zone.is_dynamic,
            'activation': zone.activation_time,
            'expiration': zone.expiration_time,
            'border_color': '#FFFFFF',
            'border_width': 2,
        }

        # Generate vertices based on shape
        if isinstance(zone.shape_data, CircleZone):
            shape_data['shape'] = 'circle'
            shape_data['radius'] = zone.shape_data.radius
            shape_data['vertices'] = self._circle_to_polygon(
                zone.shape_data.center, zone.shape_data.radius, 24
            )
            # Also render safety buffer
            shape_data['buffer_vertices'] = self._circle_to_polygon(
                zone.shape_data.center,
                zone.shape_data.radius + zone.safety_buffer,
                24
            )
            shape_data['buffer_opacity'] = 0.08

        elif isinstance(zone.shape_data, RectangleZone):
            shape_data['shape'] = 'rectangle'
            verts = zone.shape_data.get_vertices()
            shape_data['vertices'] = [(v.x, v.y) for v in verts]
            shape_data['width'] = zone.shape_data.width
            shape_data['height'] = zone.shape_data.height
            shape_data['rotation'] = zone.shape_data.rotation

        elif isinstance(zone.shape_data, PolygonZone):
            shape_data['shape'] = 'polygon'
            shape_data['vertices'] = [(v.x, v.y) for v in zone.shape_data.vertices]

        elif isinstance(zone.shape_data, MultiPolygonZone):
            shape_data['shape'] = 'multi_polygon'
            shape_data['polygons'] = [
                [(v.x, v.y) for v in poly.vertices]
                for poly in zone.shape_data.polygons
            ]
        else:
            # Default circle from center
            shape_data['shape'] = 'circle'
            shape_data['radius'] = 10.0
            shape_data['vertices'] = self._circle_to_polygon(
                Point2D(zone.center_lon, zone.center_lat), 10.0, 24
            )

        return shape_data

    def render_all_zones(self, zones: List[RestrictedZone]) -> List[Dict[str, Any]]:
        """Render all zones as display data."""
        return [self.render_zone(z) for z in zones]

    @staticmethod
    def _circle_to_polygon(center: Point2D, radius: float,
                            segments: int = 24) -> List[Tuple[float, float]]:
        """Convert circle to polygon vertices for rendering."""
        verts = []
        for i in range(segments):
            angle = (2 * math.pi * i) / segments
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            verts.append((x, y))
        return verts

    # ══════════════════════════════════════════════════════════════
    # LAYER VISUALIZATION
    # ══════════════════════════════════════════════════════════════

    def render_altitude_layers(self, layers: List[AltitudeLayer]) -> List[Dict[str, Any]]:
        """Render altitude layers for display."""
        return [
            {
                'layer_id': l.layer_id,
                'name': l.name,
                'min_altitude': l.min_altitude,
                'max_altitude': l.max_altitude,
                'max_speed': l.max_speed,
                'is_restricted': l.is_restricted,
                'color': '#FF0000' if l.is_restricted else '#00AA00',
                'opacity': 0.15 if not l.is_restricted else 0.3,
                'label': f"{l.name}: {l.min_altitude:.0f}-{l.max_altitude:.0f}m",
            }
            for l in layers
        ]

    # ══════════════════════════════════════════════════════════════
    # CORRIDOR VISUALIZATION
    # ══════════════════════════════════════════════════════════════

    def render_corridor(self, waypoints: List[Tuple[float, float]],
                          width: float = 8.0,
                          color: str = '#0066FF',
                          label: str = '') -> Dict[str, Any]:
        """
        Render a flight corridor as visualization data.
        Returns corridor path and boundary lines.
        """
        if len(waypoints) < 2:
            return {}

        # Generate corridor boundary
        left_boundary = []
        right_boundary = []

        for i, wp in enumerate(waypoints):
            # Calculate perpendicular direction
            if i < len(waypoints) - 1:
                dx = waypoints[i + 1][0] - wp[0]
                dy = waypoints[i + 1][1] - wp[1]
            elif i > 0:
                dx = wp[0] - waypoints[i - 1][0]
                dy = wp[1] - waypoints[i - 1][1]
            else:
                dx, dy = 1, 0

            seg_len = math.sqrt(dx ** 2 + dy ** 2)
            if seg_len > 0:
                perp_x = -dy / seg_len * width
                perp_y = dx / seg_len * width
            else:
                perp_x, perp_y = width, 0

            left_boundary.append((wp[0] + perp_x, wp[1] + perp_y))
            right_boundary.append((wp[0] - perp_x, wp[1] - perp_y))

        return {
            'type': 'corridor',
            'label': label,
            'color': color,
            'opacity': 0.25,
            'border_color': '#0066FF',
            'border_width': 1,
            'center_line': waypoints,
            'left_boundary': left_boundary,
            'right_boundary': right_boundary,
            'width': width,
        }

    # ══════════════════════════════════════════════════════════════
    # OVERLAY GRID
    # ══════════════════════════════════════════════════════════════

    def generate_overlay_grid(self, zones: List[RestrictedZone],
                                resolution: Optional[int] = None) -> List[List[float]]:
        """
        Generate a 2D risk overlay grid.
        0.0 = safe, 1.0 = restricted, 0.5 = caution zone.

        Can be overlaid on the dashboard map.
        """
        if resolution is None:
            resolution = self.resolution

        grid = [[0.0 for _ in range(resolution)] for _ in range(resolution)]

        for y in range(resolution):
            for x in range(resolution):
                wx = (x / resolution) * self.world_width
                wy = (y / resolution) * self.world_height
                pt = Point2D(wx, wy)

                for zone in zones:
                    if zone.status != ZoneStatus.ACTIVE:
                        continue

                    # Check inside zone
                    if zone.contains_point((wx, wy)):
                        risk = zone.risk_level.value
                        grid[y][x] = max(grid[y][x], risk + 0.2)
                    else:
                        # Check proximity (buffer zone)
                        dist = zone.distance_to((wx, wy))
                        buffer_zone = zone.safety_buffer * 2
                        if 0 < dist <= buffer_zone:
                            factor = 1.0 - (dist / buffer_zone)
                            grid[y][x] = max(grid[y][x], 0.3 * factor)

        # Clamp values
        for y in range(resolution):
            for x in range(resolution):
                grid[y][x] = min(1.0, max(0.0, grid[y][x]))

        return grid

    # ══════════════════════════════════════════════════════════════
    # LEGEND
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def get_legend() -> List[Dict[str, str]]:
        """Get color legend for the visualization."""
        return [
            {'color': '#00FF00', 'label': 'Safe Airspace', 'type': 'safe'},
            {'color': '#FFFF00', 'label': 'Caution (Warning)', 'type': 'caution'},
            {'color': '#FF6600', 'label': 'Restricted Zone', 'type': 'restricted'},
            {'color': '#FF0000', 'label': 'Prohibited Zone', 'type': 'prohibited'},
            {'color': '#800080', 'label': 'Temporary Restriction (TFR)', 'type': 'temporary'},
            {'color': '#0066FF', 'label': 'Approved Flight Corridor', 'type': 'corridor'},
            {'color': '#FF4500', 'label': 'Emergency Zone', 'type': 'emergency'},
            {'color': '#FFD700', 'label': 'School/Hospital Zone', 'type': 'sensitive'},
            {'color': '#228B22', 'label': 'Wildlife/Park Zone', 'type': 'environmental'},
        ]

    # ══════════════════════════════════════════════════════════════
    # COMPLETE OVERLAY
    # ══════════════════════════════════════════════════════════════

    def generate_complete_overlay(self, zones: List[RestrictedZone],
                                    corridors: List = None,
                                    emergency_sites: List = None) -> Dict[str, Any]:
        """
        Generate complete visualization overlay with all elements.
        This is the main method called by the dashboard.
        """
        overlay = {
            'zones': self.render_all_zones(zones),
            'overlay_grid': self.generate_overlay_grid(zones),
            'legend': self.get_legend(),
            'emergency_sites': emergency_sites or [],
            'corridors': [],
            'resolution': self.resolution,
            'world_width': self.world_width,
            'world_height': self.world_height,
        }

        # Add corridors if provided
        if corridors:
            for corridor in corridors:
                if hasattr(corridor, 'waypoints'):
                    corr_data = self.render_corridor(
                        [wp.position for wp in corridor.waypoints],
                        getattr(corridor, 'width', 8.0),
                        label=getattr(corridor, 'name', ''),
                    )
                    if corr_data:
                        overlay['corridors'].append(corr_data)

        return overlay