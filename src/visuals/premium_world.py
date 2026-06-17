"""
Premium World Generator
=======================
Procedurally generates a rich, cinematic simulation environment with:
  - Urban areas (buildings, skyscrapers, industrial zones, warehouses)
  - Natural environments (forests, parks, rivers, lakes, mountains)
  - Infrastructure (roads, bridges, landing pads, power lines, rooftop pads)
  - Moving entities (vehicles, pedestrians, birds, dynamic obstacles)
  - Landing zones and delivery locations
  - Dynamic construction zones

All obstacles are registered in the world's obstacle set so the
navigation and planning systems interact with them naturally.
"""

from __future__ import annotations

import math
import random as _rand
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable

import numpy as np

from src.core.terrain import TerrainType
from src.core.weather import WeatherType

# ── Color palette for the premium world ─────────────────────────────────────
class WorldColors:
    URBAN_GROUND = "#3D3D3D"
    URBAN_ROOF = "#4A4A4A"
    GRASS_LIGHT = "#5A8C3C"
    GRASS_DARK = "#3D6B2E"
    FOREST_DARK = "#2D5A1E"
    FOREST_LIGHT = "#4A7C34"
    DIRT_PATH = "#8B7355"
    SAND = "#D4B978"
    WATER_DEEP = "#1A3A5C"
    WATER_SHALLOW = "#2A6A9C"
    RIVER = "#3A7AB5"
    ROAD_ASPHALT = "#4A4A4A"
    ROAD_LINE = "#F5E642"
    SIDEWALK = "#7A7A7A"
    BUILDING_1 = "#6B6B6B"
    BUILDING_2 = "#7A7A7A"
    BUILDING_3 = "#5A5A5A"
    BUILDING_4 = "#8A7A6A"
    SKYSCRAPER = "#3A4A6A"
    WAREHOUSE = "#8A7A6A"
    ROOFTOP = "#5A5A6A"
    BRIDGE = "#6A7A8A"
    BRIDGE_ROAD = "#5A6A7A"
    MOUNTAIN = "#6A5A4A"
    MOUNTAIN_SNOW = "#D4D4E8"
    MOUNTAIN_SHADOW = "#4A3A2A"
    TREE_GREEN = "#3A7A2A"
    TREE_DARK = "#2A5A1A"
    TREE_BROWN = "#5A3A1A"
    LANDING_PAD = "#1A7A3A"
    LANDING_PAD_RING = "#00CC44"
    POWER_LINE = "#4A4A4A"
    CONSTRUCTION = "#C47A1A"
    VEHICLE_RED = "#CC2222"
    VEHICLE_BLUE = "#2266CC"
    VEHICLE_WHITE = "#CCCCCC"
    PEDESTRIAN = "#D4A46A"
    BIRD = "#4A4A4A"


# ── Data classes for world features ─────────────────────────────────────────

@dataclass
class Building:
    """A building in the city."""
    x: float
    y: float
    width: float
    height: float
    floors: int
    color: str
    has_rooftop_pad: bool = False
    is_skyscraper: bool = False
    windows: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class Road:
    """A road segment."""
    x1: float
    y1: float
    x2: float
    y2: float
    width: float
    is_bridge: bool = False
    lanes: int = 2


@dataclass
class River:
    """A river segment."""
    points: List[Tuple[float, float]] = field(default_factory=list)
    width: float = 3.0


@dataclass
class ForestCluster:
    """A cluster of trees."""
    center_x: float
    center_y: float
    radius: float
    tree_count: int
    tree_positions: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class Vehicle:
    """A moving vehicle on a road."""
    x: float
    y: float
    speed: float
    direction: Tuple[float, float]
    road_idx: int
    color: str
    width: float = 1.2
    height: float = 0.6


@dataclass
class Pedestrian:
    """A walking pedestrian."""
    x: float
    y: float
    speed: float
    angle: float
    color: str


@dataclass
class Bird:
    """A flying bird."""
    x: float
    y: float
    speed: float
    angle: float
    flap_phase: float = 0.0


@dataclass
class LandingPad:
    """A designated landing zone."""
    x: float
    y: float
    radius: float
    label: str
    is_rooftop: bool = False
    building_idx: int = -1


@dataclass
class PowerLine:
    """A power line segment."""
    x1: float
    y1: float
    x2: float
    y2: float
    pole_positions: List[Tuple[float, float]] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════

class PremiumWorld:
    """Rich procedurally-generated simulation environment.

    Generates a detailed world with urban centres, road networks,
    rivers, forests, mountains, vehicles, pedestrians, birds,
    landing pads, power infrastructure, and construction zones.

    Designed to be a drop-in layer over the existing World/EnhancedWorld
    systems, providing enhanced obstacle sets and rendering data.
    """

    def __init__(
        self,
        width: int = 100,
        height: int = 100,
        seed: Optional[int] = None,
    ):
        self.width = width
        self.height = height
        self.seed = seed or _rand.randint(0, 99999)
        _rand.seed(self.seed)
        np.random.seed(self.seed % 2**32)

        # ── Feature containers ──
        self.buildings: List[Building] = []
        self.roads: List[Road] = []
        self.rivers: List[River] = []
        self.forests: List[ForestCluster] = []
        self.vehicles: List[Vehicle] = []
        self.pedestrians: List[Pedestrian] = []
        self.birds: List[Bird] = []
        self.landing_pads: List[LandingPad] = []
        self.power_lines: List[PowerLine] = []

        # ── Obstacle grid (for planners) ──
        self.obstacle_set: set = set()

        # ── Terrain type grid (for rendering) ──
        self.terrain_grid: np.ndarray = np.zeros((height, width), dtype=np.int32)
        self.terrain_colors: np.ndarray = np.zeros((height, width, 3), dtype=np.float32)

        # ── Height / elevation map ──
        self.elevation: np.ndarray = np.zeros((height, width), dtype=np.float32)

        # ── Generate ──
        self._generate()

    # ══════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════

    def get_obstacle_set(self) -> set:
        """Return all obstacle positions for the planner systems."""
        return self.obstacle_set

    def get_terrain_array(self) -> np.ndarray:
        """Return RGB terrain colour array for rendering."""
        return self.terrain_colors

    def get_elevation_array(self) -> np.ndarray:
        """Return elevation map for shading/shadows."""
        return self.elevation

    def update_moving_entities(self):
        """Advance all moving entities one simulation step."""
        self._update_vehicles()
        self._update_pedestrians()
        self._update_birds()

    def get_vehicle_positions(self) -> List[Tuple[float, float, float]]:
        """Return list of (x, y, heading) for all vehicles."""
        result = []
        for v in self.vehicles:
            h = math.atan2(v.direction[1], v.direction[0])
            result.append((v.x, v.y, h))
        return result

    def get_pedestrian_positions(self) -> List[Tuple[float, float, float]]:
        """Return list of (x, y, heading) for all pedestrians."""
        result = []
        for p in self.pedestrians:
            result.append((p.x, p.y, p.angle))
        return result

    def get_bird_positions(self) -> List[Tuple[float, float]]:
        """Return list of (x, y) for all birds."""
        return [(b.x, b.y) for b in self.birds]

    def get_landing_pads(self) -> List[LandingPad]:
        """Return list of all landing pads."""
        return self.landing_pads

    def get_delivery_locations(self) -> List[Tuple[float, float]]:
        """Return list of delivery locations (rooftop pads + ground pads)."""
        return [(p.x, p.y) for p in self.landing_pads]

    # ══════════════════════════════════════════════════════════════════
    # WORLD GENERATION
    # ══════════════════════════════════════════════════════════════════

    def _generate(self):
        """Run all procedural generation steps in order."""
        self._generate_terrain_base()
        self._generate_elevation()
        self._generate_rivers_and_lakes()
        self._generate_forests()
        self._generate_mountains()
        self._generate_road_network()
        self._generate_city_center()
        self._generate_industrial_zone()
        self._generate_power_lines()
        self._generate_landing_pads()
        self._generate_vehicles()
        self._generate_pedestrians()
        self._generate_birds()
        self._clear_safe_zones()
        self._finalize_terrain_colors()

    def _clear_safe_zones(self):
        """Clear obstacles around start (5,5) and target (90,90) zones."""
        h, w = self.height, self.width
        safe_radius = 7
        safe_positions = [(5, 5), (90, 90)]

        for sx, sy in safe_positions:
            for dy in range(-safe_radius, safe_radius + 1):
                for dx in range(-safe_radius, safe_radius + 1):
                    px, py = sx + dx, sy + dy
                    if 0 <= px < w and 0 <= py < h:
                        self.obstacle_set.discard((px, py))
                        if self.terrain_grid[py, px] in (
                            TerrainType.BUILDING.value, TerrainType.TREE.value,
                            TerrainType.ROCK.value,
                        ):
                            self.terrain_grid[py, px] = TerrainType.GRASS.value
                        self.elevation[py, px] = max(0, self.elevation[py, px])

    # ── Terrain Base ─────────────────────────────────────────────────

    def _generate_terrain_base(self):
        """Generate base terrain type grid."""
        h, w = self.height, self.width
        grid = self.terrain_grid

        # Fill with grass by default
        grid[:, :] = TerrainType.GRASS.value

        # Add patches of different terrain
        for _ in range(30):
            cx = _rand.randint(0, w - 1)
            cy = _rand.randint(0, h - 1)
            radius = _rand.randint(3, 15)
            tt = _rand.choice([
                TerrainType.GRASS.value,
                TerrainType.DIRT.value,
                TerrainType.SAND.value,
                TerrainType.GRASS.value,
                TerrainType.GRASS.value,
            ])
            for y in range(max(0, cy - radius), min(h, cy + radius)):
                for x in range(max(0, cx - radius), min(w, cx + radius)):
                    dx = x - cx
                    dy = y - cy
                    if dx * dx + dy * dy < radius * radius:
                        grid[y, x] = tt

    def _generate_elevation(self):
        """Generate elevation map using simple noise."""
        h, w = self.height, self.width
        elev = self.elevation

        # Generate a few hill/mountain seeds
        seeds = []
        for _ in range(8):
            sx = _rand.uniform(0, w - 1)
            sy = _rand.uniform(0, h - 1)
            sr = _rand.uniform(10, 25)
            sh = _rand.uniform(2, 8)
            seeds.append((sx, sy, sr, sh))

        for y in range(h):
            for x in range(w):
                val = 0.0
                for sx, sy, sr, sh in seeds:
                    d = math.hypot(x - sx, y - sy)
                    if d < sr:
                        val += sh * (1.0 - d / sr)
                elev[y, x] = val

    # ── Rivers ───────────────────────────────────────────────────────

    def _generate_rivers_and_lakes(self):
        """Generate rivers meandering across the map."""
        h, w = self.height, self.width
        num_rivers = _rand.randint(1, 3)

        for _ in range(num_rivers):
            river = River()
            start_x = _rand.uniform(0, w - 1)
            start_y = 0
            x, y = start_x, start_y
            points = [(x, y)]
            steps = _rand.randint(30, 60)
            dx = _rand.uniform(-0.3, 0.3)
            dy = _rand.uniform(0.5, 1.0)

            for _ in range(steps):
                dx += _rand.uniform(-0.2, 0.2)
                dy += _rand.uniform(-0.1, 0.1)
                # Keep within bounds
                x = max(2, min(w - 3, x + dx))
                y = max(2, min(h - 3, y + dy))
                dx *= 0.9
                dy *= 0.9
                points.append((x, y))

                # Mark terrain as water along the river
                rw = int(river.width)
                for py in range(int(y) - rw, int(y) + rw + 1):
                    for px in range(int(x) - rw, int(x) + rw + 1):
                        if 0 <= py < h and 0 <= px < w:
                            if math.hypot(px - x, py - y) < river.width:
                                self.terrain_grid[py, px] = TerrainType.WATER.value
                                self.elevation[py, px] = -1.0

            river.points = points
            self.rivers.append(river)

        # Add a small lake
        lx = _rand.randint(10, w - 10)
        ly = _rand.randint(10, h - 10)
        lr = _rand.randint(3, 6)
        for y in range(max(0, ly - lr), min(h, ly + lr)):
            for x in range(max(0, lx - lr), min(w, lx + lr)):
                if math.hypot(x - lx, y - ly) < lr:
                    self.terrain_grid[y, x] = TerrainType.WATER.value
                    self.elevation[y, x] = -1.0

    # ── Forests ──────────────────────────────────────────────────────

    def _generate_forests(self):
        """Generate forest clusters."""
        h, w = self.height, self.width
        num_forests = _rand.randint(3, 7)

        for _ in range(num_forests):
            cx = _rand.randint(5, w - 5)
            cy = _rand.randint(5, h - 5)
            radius = _rand.uniform(3, 12)
            count = _rand.randint(10, 40)

            forest = ForestCluster(
                center_x=float(cx), center_y=float(cy),
                radius=radius, tree_count=count,
            )

            for _ in range(count):
                angle = _rand.uniform(0, 2 * math.pi)
                r = _rand.uniform(0, radius)
                tx = cx + r * math.cos(angle)
                ty = cy + r * math.sin(angle)
                tx_i, ty_i = int(tx), int(ty)

                if 0 <= tx_i < w and 0 <= ty_i < h:
                    # Don't place on water
                    if self.terrain_grid[ty_i, tx_i] != TerrainType.WATER.value:
                        forest.tree_positions.append((tx, ty))
                        self.terrain_grid[ty_i, tx_i] = TerrainType.TREE.value
                        self.obstacle_set.add((tx_i, ty_i))

            self.forests.append(forest)

    # ── Mountains ────────────────────────────────────────────────────

    def _generate_mountains(self):
        """Generate mountainous regions."""
        h, w = self.height, self.width
        num_mountains = _rand.randint(0, 2)

        for _ in range(num_mountains):
            cx = _rand.randint(10, w - 10)
            cy = _rand.randint(10, h - 10)
            radius = _rand.uniform(8, 20)
            height_peak = _rand.uniform(4, 12)

            for y in range(max(1, cy - int(radius)), min(h - 1, cy + int(radius))):
                for x in range(max(1, cx - int(radius)), min(w - 1, cx + int(radius))):
                    d = math.hypot(x - cx, y - cy)
                    if d < radius:
                        # Mountain height
                        local_h = height_peak * (1.0 - d / radius) ** 2
                        self.elevation[y, x] = max(self.elevation[y, x], local_h)

                        # Mark as rock if steep enough
                        if local_h > 2.0:
                            self.terrain_grid[y, x] = TerrainType.ROCK.value
                            self.obstacle_set.add((x, y))

    # ── Road Network ─────────────────────────────────────────────────

    def _generate_road_network(self):
        """Generate a grid-like road network."""
        h, w = self.height, self.width

        # Horizontal roads
        for y_pos in range(15, h - 5, _rand.randint(12, 20)):
            road_width = _rand.uniform(2.0, 4.0)
            road = Road(
                x1=0, y1=float(y_pos),
                x2=float(w - 1), y2=float(y_pos),
                width=road_width,
                lanes=_rand.choice([2, 4]),
            )
            self.roads.append(road)
            # Mark road cells
            rw_int = int(road_width / 2) + 1
            for py in range(y_pos - rw_int, y_pos + rw_int + 1):
                for px in range(w):
                    if 0 <= py < h and 0 <= px < w:
                        if self.terrain_grid[py, px] != TerrainType.WATER.value:
                            self.terrain_grid[py, px] = TerrainType.DIRT.value

        # Vertical roads
        for x_pos in range(15, w - 5, _rand.randint(12, 20)):
            road_width = _rand.uniform(2.0, 4.0)
            road = Road(
                x1=float(x_pos), y1=0,
                x2=float(x_pos), y2=float(h - 1),
                width=road_width,
                lanes=_rand.choice([2, 4]),
            )
            self.roads.append(road)
            # Mark road cells
            rw_int = int(road_width / 2) + 1
            for px in range(x_pos - rw_int, x_pos + rw_int + 1):
                for py in range(h):
                    if 0 <= py < h and 0 <= px < w:
                        if self.terrain_grid[py, px] != TerrainType.WATER.value:
                            self.terrain_grid[py, px] = TerrainType.DIRT.value

    # ── City Center ──────────────────────────────────────────────────

    def _generate_city_center(self):
        """Generate a dense city center with buildings."""
        h, w = self.height, self.width
        cx, cy = w // 3, h // 3  # City center offset

        # Generate blocks of buildings (reduced density)
        for bx_offset in range(0, 30, 6):
            for by_offset in range(0, 30, 6):
                bx = cx + bx_offset
                by = cy + by_offset

                if bx + 3 >= w or by + 3 >= h:
                    continue

                # Check not on water
                if self.terrain_grid[by, bx] == TerrainType.WATER.value:
                    continue

                b_w = _rand.uniform(1.5, 3.5)
                b_h = _rand.uniform(1.5, 3.5)
                floors = _rand.randint(2, 8)
                is_skyscraper = floors >= 6 and _rand.random() < 0.3
                color = _rand.choice([
                    WorldColors.BUILDING_1, WorldColors.BUILDING_2,
                    WorldColors.BUILDING_3, WorldColors.BUILDING_4,
                ])

                building = Building(
                    x=float(bx), y=float(by),
                    width=b_w, height=b_h,
                    floors=floors,
                    color=color,
                    is_skyscraper=is_skyscraper,
                )

                # Add windows
                for wy in range(1, floors, 2):
                    for wx in range(0, int(b_w * 2), 2):
                        building.windows.append((float(wx), float(wy)))

                self.buildings.append(building)

                # Mark as obstacle
                bwi, bhi = int(b_w + 1), int(b_h + 1)
                for by_i in range(by, min(by + bhi, h)):
                    for bx_i in range(bx, min(bx + bwi, w)):
                        self.terrain_grid[by_i, bx_i] = TerrainType.BUILDING.value
                        self.obstacle_set.add((bx_i, by_i))

                # Rooftop pads on tall buildings
                if floors >= 5 and _rand.random() < 0.4:
                    building.has_rooftop_pad = True
                    pad = LandingPad(
                        x=float(bx) + b_w / 2,
                        y=float(by) + b_h / 2,
                        radius=1.5,
                        label=f"ROOFTOP-{len(self.landing_pads) + 1}",
                        is_rooftop=True,
                        building_idx=len(self.buildings) - 1,
                    )
                    self.landing_pads.append(pad)

    # ── Industrial Zone ──────────────────────────────────────────────

    def _generate_industrial_zone(self):
        """Generate an industrial zone with warehouses."""
        h, w = self.height, self.width
        iz_x = _rand.randint(w * 2 // 3, w - 15)
        iz_y = _rand.randint(h * 2 // 3, h - 15)

        for ix in range(iz_x, min(iz_x + 12, w - 2), 4):
            for iy in range(iz_y, min(iz_y + 12, h - 2), 3):
                if self.terrain_grid[iy, ix] == TerrainType.WATER.value:
                    continue

                color = WorldColors.WAREHOUSE
                b_w = _rand.uniform(2.5, 4.5)
                b_h = _rand.uniform(2.0, 3.5)
                floors = 1

                building = Building(
                    x=float(ix), y=float(iy),
                    width=b_w, height=b_h,
                    floors=floors,
                    color=color,
                )
                self.buildings.append(building)

                bwi, bhi = int(b_w + 1), int(b_h + 1)
                for by_i in range(iy, min(iy + bhi, h)):
                    for bx_i in range(ix, min(ix + bwi, w)):
                        self.terrain_grid[by_i, bx_i] = TerrainType.BUILDING.value
                        self.obstacle_set.add((bx_i, by_i))

        # Add ground landing pads in industrial zone
        for _ in range(2):
            px = iz_x + _rand.randint(0, 10)
            py = iz_y + _rand.randint(0, 10)
            if (px, py) not in self.obstacle_set:
                pad = LandingPad(
                    x=float(px), y=float(py),
                    radius=2.0,
                    label=f"LZ-{len(self.landing_pads) + 1}",
                )
                self.landing_pads.append(pad)

    # ── Power Lines ──────────────────────────────────────────────────

    def _generate_power_lines(self):
        """Generate power line infrastructure."""
        h, w = self.height, self.width
        for _ in range(_rand.randint(2, 4)):
            x1 = _rand.randint(10, w - 10)
            x2 = x1 + _rand.randint(-20, 20)
            y1 = _rand.randint(10, h - 10)
            y2 = y1 + _rand.randint(-10, 10)

            # Keep in bounds
            x2 = max(5, min(w - 5, x2))
            y2 = max(5, min(h - 5, y2))

            # Place poles along the line
            poles = []
            steps = _rand.randint(3, 6)
            for i in range(steps + 1):
                t = i / steps
                px = x1 + (x2 - x1) * t
                py = y1 + (y2 - y1) * t
                poles.append((px, py))

            pl = PowerLine(
                x1=float(x1), y1=float(y1),
                x2=float(x2), y2=float(y2),
                pole_positions=poles,
            )
            self.power_lines.append(pl)

            # Mark poles as obstacles
            for px, py in poles:
                ipx, ipy = int(px), int(py)
                if 0 <= ipx < w and 0 <= ipy < h:
                    self.obstacle_set.add((ipx, ipy))

    # ── Landing Pads (ground) ────────────────────────────────────────

    def _generate_landing_pads(self):
        """Generate additional ground-level landing pads / delivery zones."""
        h, w = self.height, self.width
        used_positions = {(int(p.x), int(p.y)) for p in self.landing_pads}

        for _ in range(_rand.randint(3, 6)):
            for attempt in range(20):
                px = _rand.randint(5, w - 5)
                py = _rand.randint(5, h - 5)
                if (px, py) not in self.obstacle_set and (px, py) not in used_positions:
                    tt = self.terrain_grid[py, px]
                    if tt not in (TerrainType.WATER.value, TerrainType.BUILDING.value):
                        pad = LandingPad(
                            x=float(px), y=float(py),
                            radius=2.0,
                            label=f"LZ-{len(self.landing_pads) + 1}",
                        )
                        self.landing_pads.append(pad)
                        used_positions.add((px, py))
                        break

    # ── Vehicles ─────────────────────────────────────────────────────

    def _generate_vehicles(self):
        """Generate moving vehicles on roads."""
        if not self.roads:
            return

        for road_idx, road in enumerate(self.roads[:12]):  # At most 12 roads
            num_vehicles = _rand.randint(0, 3)
            for _ in range(num_vehicles):
                t = _rand.uniform(0.05, 0.95)
                vx = road.x1 + (road.x2 - road.x1) * t
                vy = road.y1 + (road.y2 - road.y1) * t

                # Direction along road
                dx = road.x2 - road.x1
                dy = road.y2 - road.y1
                length = math.hypot(dx, dy)
                if length > 0:
                    dx /= length
                    dy /= length

                # Random direction (sometimes reverse)
                if _rand.random() < 0.4:
                    dx, dy = -dx, -dy

                color = _rand.choice([
                    WorldColors.VEHICLE_RED,
                    WorldColors.VEHICLE_BLUE,
                    WorldColors.VEHICLE_WHITE,
                ])
                speed = _rand.uniform(0.3, 0.8)

                vehicle = Vehicle(
                    x=vx, y=vy, speed=speed,
                    direction=(dx, dy),
                    road_idx=road_idx,
                    color=color,
                )
                self.vehicles.append(vehicle)

    # ── Pedestrians ──────────────────────────────────────────────────

    def _generate_pedestrians(self):
        """Generate pedestrians on sidewalks / roads."""
        h, w = self.height, self.width
        for _ in range(_rand.randint(8, 18)):
            for attempt in range(20):
                px = _rand.uniform(5, w - 5)
                py = _rand.uniform(5, h - 5)
                ipx, ipy = int(px), int(py)
                if 0 <= ipx < w and 0 <= ipy < h:
                    if (ipx, ipy) not in self.obstacle_set:
                        angle = _rand.uniform(0, 2 * math.pi)
                        speed = _rand.uniform(0.1, 0.3)
                        color = _rand.choice([
                            WorldColors.PEDESTRIAN, "#6A8AD4", "#D46A8A", "#8AD46A",
                        ])
                        pedestrian = Pedestrian(
                            x=px, y=py, speed=speed,
                            angle=angle, color=color,
                        )
                        self.pedestrians.append(pedestrian)
                        break

    # ── Birds ────────────────────────────────────────────────────────

    def _generate_birds(self):
        """Generate flying birds."""
        h, w = self.height, self.width
        for _ in range(_rand.randint(3, 8)):
            bird = Bird(
                x=_rand.uniform(10, w - 10),
                y=_rand.uniform(10, h - 10),
                speed=_rand.uniform(0.5, 1.5),
                angle=_rand.uniform(0, 2 * math.pi),
                flap_phase=_rand.uniform(0, 2 * math.pi),
            )
            self.birds.append(bird)

    # ── Finalize Terrain Colors ──────────────────────────────────────

    def _finalize_terrain_colors(self):
        """Convert terrain grid to RGB color array."""
        h, w = self.height, self.width
        colors = self.terrain_colors

        color_map = {
            TerrainType.GRASS.value: np.array([91/255, 140/255, 60/255]),
            TerrainType.DIRT.value: np.array([139/255, 115/255, 85/255]),
            TerrainType.SAND.value: np.array([212/255, 185/255, 120/255]),
            TerrainType.ROCK.value: np.array([106/255, 90/255, 74/255]),
            TerrainType.WATER.value: np.array([58/255, 122/255, 181/255]),
            TerrainType.TREE.value: np.array([58/255, 122/255, 42/255]),
            TerrainType.BUILDING.value: np.array([107/255, 107/255, 107/255]),
            TerrainType.GRASS_TALL.value: np.array([58/255, 100/255, 42/255]),
            TerrainType.PAVEMENT.value: np.array([120/255, 120/255, 120/255]),
            TerrainType.FENCE.value: np.array([90/255, 80/255, 70/255]),
            TerrainType.FLAT_GROUND.value: np.array([100/255, 130/255, 70/255]),
            TerrainType.ROAD.value: np.array([74/255, 74/255, 74/255]),
            TerrainType.BRIDGE.value: np.array([106/255, 122/255, 138/255]),
        }

        for y in range(h):
            for x in range(w):
                tt = self.terrain_grid[y, x]
                col = color_map.get(tt, np.array([91/255, 140/255, 60/255]))

                # Add elevation-based shading
                elev = self.elevation[y, x]
                shade = 0.7 + 0.3 * min(1.0, elev / 8.0)
                colors[y, x] = col * shade

                # Add slight random variation
                variation = _rand.uniform(0.92, 1.08)
                colors[y, x] = np.clip(colors[y, x] * variation, 0, 1)

    # ══════════════════════════════════════════════════════════════════
    # UPDATE MOVING ENTITIES
    # ══════════════════════════════════════════════════════════════════

    def _update_vehicles(self):
        """Move vehicles along their roads."""
        for v in self.vehicles:
            v.x += v.direction[0] * v.speed
            v.y += v.direction[1] * v.speed

            # Get road for bounds checking
            if v.road_idx < len(self.roads):
                road = self.roads[v.road_idx]
                # Check if off road range
                road_len = math.hypot(road.x2 - road.x1, road.y2 - road.y1)
                if road_len > 0:
                    t = ((v.x - road.x1) * (road.x2 - road.x1) +
                         (v.y - road.y1) * (road.y2 - road.y1)) / road_len ** 2
                    if t < -0.1 or t > 1.1:
                        # Reverse direction
                        v.direction = (-v.direction[0], -v.direction[1])

    def _update_pedestrians(self):
        """Move pedestrians with slight random wandering."""
        h, w = self.height, self.width
        for p in self.pedestrians:
            p.angle += _rand.uniform(-0.15, 0.15)
            p.x += math.cos(p.angle) * p.speed
            p.y += math.sin(p.angle) * p.speed

            # Boundary reflection
            if p.x < 1 or p.x > w - 2:
                p.angle = math.pi - p.angle
                p.angle += _rand.uniform(-0.3, 0.3)
            if p.y < 1 or p.y > h - 2:
                p.angle = -p.angle
                p.angle += _rand.uniform(-0.3, 0.3)

            p.x = max(0.5, min(w - 1.5, p.x))
            p.y = max(0.5, min(h - 1.5, p.y))

    def _update_birds(self):
        """Move birds with circular flocking patterns."""
        h, w = self.height, self.width
        for b in self.birds:
            b.flap_phase += 0.1
            b.angle += _rand.uniform(-0.08, 0.08)
            b.x += math.cos(b.angle) * b.speed
            b.y += math.sin(b.angle) * b.speed

            # Keep in bounds with gentle steering
            margin = 15
            if b.x < margin:
                b.angle = _rand.uniform(-0.5, 0.5)
            elif b.x > w - margin:
                b.angle = math.pi + _rand.uniform(-0.5, 0.5)
            if b.y < margin:
                b.angle = _rand.uniform(0, math.pi)
            elif b.y > h - margin:
                b.angle = _rand.uniform(-math.pi, 0)

            b.x = max(1, min(w - 1, b.x))
            b.y = max(1, min(h - 1, b.y))
