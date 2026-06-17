"""
Military-Grade Terrain Generation System
==========================================
Procedural terrain with height maps, vegetation, water, roads,
buildings, bridges, and military infrastructure.

Generates realistic terrain using layered Perlin-like noise
and places structural elements based on terrain characteristics.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import numpy as np


# ── Terrain Types ────────────────────────────────────────────────────────────


class TerrainType(Enum):
    """Classification of terrain cell types."""
    FLAT_GROUND = auto()
    GRASS = auto()
    DIRT = auto()
    SAND = auto()
    ROCK = auto()
    WATER = auto()
    ROAD = auto()
    BRIDGE = auto()
    BUILDING = auto()
    TREE = auto()
    GRASS_TALL = auto()
    PAVEMENT = auto()
    FENCE = auto()


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class Structure:
    """A placed structure in the world."""
    x: int
    y: int
    width: int
    height: int
    structure_type: str  # "building", "tower", "bridge", "fence"
    metadata: dict = field(default_factory=dict)


@dataclass
class WaterBody:
    """A body of water."""
    cells: list[tuple[int, int]] = field(default_factory=list)
    depth: float = 1.0


@dataclass
class Road:
    """A road segment."""
    cells: list[tuple[int, int]] = field(default_factory=list)
    road_type: str = "dirt"  # dirt, paved, highway


# ── Noise Generator ──────────────────────────────────────────────────────────


class PerlinNoise2D:
    """Simple 2D Perlin-like noise for terrain generation."""

    def __init__(self, seed: int = 42, scale: float = 0.05):
        self.seed = seed
        self.scale = scale
        self._perm = list(range(256))
        rng = random.Random(seed)
        rng.shuffle(self._perm)
        self._perm = self._perm + self._perm

    def _fade(self, t: float) -> float:
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + t * (b - a)

    def _grad(self, h: int, x: float, y: float) -> float:
        h = h & 3
        if h == 0:
            return x + y
        if h == 1:
            return -x + y
        if h == 2:
            return x - y
        return -x - y

    def noise(self, x: float, y: float) -> float:
        """Return noise value in [-1, 1] range."""
        xi = math.floor(x / self.scale) if self.scale != 0 else 0
        yi = math.floor(y / self.scale) if self.scale != 0 else 0

        xf = (x / self.scale) - xi if self.scale != 0 else 0
        yf = (y / self.scale) - yi if self.scale != 0 else 0

        u = self._fade(xf)
        v = self._fade(yf)

        xi &= 255
        yi &= 255

        aa = self._perm[self._perm[xi] + yi]
        ab = self._perm[self._perm[xi] + yi + 1]
        ba = self._perm[self._perm[xi + 1] + yi]
        bb = self._perm[self._perm[xi + 1] + yi + 1]

        x1 = self._lerp(self._grad(aa, xf, yf), self._grad(ba, xf - 1, yf), u)
        x2 = self._lerp(self._grad(ab, xf, yf - 1), self._grad(bb, xf - 1, yf - 1), u)
        return self._lerp(x1, x2, v)

    def octave_noise(self, x: float, y: float, octaves: int = 4,
                     persistence: float = 0.5) -> float:
        """Multi-octave noise for richer terrain variation."""
        total = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_val = 0.0
        for _ in range(octaves):
            total += self.noise(x * frequency, y * frequency) * amplitude
            max_val += amplitude
            amplitude *= persistence
            frequency *= 2.0
        return total / max_val if max_val > 0 else 0.0


# ── Terrain Generator ────────────────────────────────────────────────────────


class TerrainGenerator:
    """Procedural terrain generator for military drone simulation.

    Generates:
      - Height map using layered Perlin noise
      - Terrain type classification (grass, dirt, sand, rock, water)
      - Road networks
      - Building clusters
      - Tree placement
      - Water bodies
      - Bridges across water
    """

    def __init__(self, width: int = 100, height: int = 100,
                 seed: int = 42, difficulty: str = "normal"):
        self.width = width
        self.height = height
        self.seed = seed
        self.difficulty = difficulty

        # Noise generators with different seeds for variety
        self._height_noise = PerlinNoise2D(seed=seed, scale=0.08)
        self._moisture_noise = PerlinNoise2D(seed=seed + 1, scale=0.12)
        self._detail_noise = PerlinNoise2D(seed=seed + 2, scale=0.25)

        # Output arrays
        self.height_map = np.zeros((height, width), dtype=np.float32)
        self.terrain_types = np.zeros((height, width), dtype=np.int32)
        self.moisture_map = np.zeros((height, width), dtype=np.float32)

        # Placed features
        self.structures: list[Structure] = []
        self.water_bodies: list[WaterBody] = []
        self.roads: list[Road] = []
        self.tree_positions: list[tuple[int, int]] = []

        # Obstacle compatibility: set of (x, y) positions that are obstacles
        self.obstacle_positions: set[tuple[int, int]] = set()

    def generate(self) -> dict:
        """Generate complete terrain. Returns dict of terrain data."""
        self._generate_height_map()
        self._classify_terrain()
        self._generate_water_bodies()
        self._generate_roads()
        self._generate_buildings()
        self._generate_trees()
        self._collect_obstacles()

        return {
            "height_map": self.height_map,
            "terrain_types": self.terrain_types,
            "moisture_map": self.moisture_map,
            "structures": self.structures,
            "water_bodies": self.water_bodies,
            "roads": self.roads,
            "tree_positions": self.tree_positions,
            "obstacle_positions": self.obstacle_positions,
        }

    def _generate_height_map(self) -> None:
        """Generate height map using multi-octave Perlin noise."""
        cx, cy = self.width / 2, self.height / 2
        max_r = math.sqrt(cx * cx + cy * cy)

        for y in range(self.height):
            for x in range(self.width):
                # Base terrain height
                h = self._height_noise.octave_noise(x, y, octaves=4, persistence=0.5)
                # Add detail
                detail = self._detail_noise.octave_noise(x, y, octaves=2, persistence=0.4) * 0.3
                # Edge falloff for natural boundaries
                dx = (x - cx) / cx
                dy = (y - cy) / cy
                dist = math.sqrt(dx * dx + dy * dy)
                falloff = max(0, 1.0 - dist * 0.6)

                self.height_map[y, x] = (h + detail) * falloff

        # Normalize to [0, 1]
        hmin, hmax = self.height_map.min(), self.height_map.max()
        if hmax - hmin > 0:
            self.height_map = (self.height_map - hmin) / (hmax - hmin)

    def _classify_terrain(self) -> None:
        """Classify each cell into terrain type based on height and moisture."""
        for y in range(self.height):
            for x in range(self.width):
                h = self.height_map[y, x]
                m = self._moisture_noise.octave_noise(x, y, octaves=2)
                self.moisture_map[y, x] = (m + 1) / 2.0

                if h < 0.2:
                    self.terrain_types[y, x] = TerrainType.WATER.value
                elif h < 0.3:
                    self.terrain_types[y, x] = TerrainType.SAND.value
                elif h < 0.6:
                    if m > 0.3:
                        self.terrain_types[y, x] = TerrainType.GRASS.value
                    else:
                        self.terrain_types[y, x] = TerrainType.DIRT.value
                elif h < 0.8:
                    self.terrain_types[y, x] = TerrainType.ROCK.value
                else:
                    self.terrain_types[y, x] = TerrainType.FLAT_GROUND.value

    def _generate_water_bodies(self) -> None:
        """Identify connected water regions."""
        visited = set()
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in visited:
                    continue
                if self.terrain_types[y, x] != TerrainType.WATER.value:
                    continue
                # Flood fill to find water body
                water_cells = []
                queue = [(x, y)]
                while queue:
                    cx, cy = queue.pop()
                    if (cx, cy) in visited:
                        continue
                    if not (0 <= cx < self.width and 0 <= cy < self.height):
                        continue
                    if self.terrain_types[cy, cx] != TerrainType.WATER.value:
                        continue
                    visited.add((cx, cy))
                    water_cells.append((cx, cy))
                    queue.extend([
                        (cx + 1, cy), (cx - 1, cy),
                        (cx, cy + 1), (cx, cy - 1),
                    ])
                if water_cells:
                    self.water_bodies.append(WaterBody(cells=water_cells))

    def _generate_roads(self) -> None:
        """Generate road network connecting key points."""
        rng = random.Random(self.seed + 100)

        # Create 2-3 major roads
        num_roads = rng.randint(2, 3)
        for _ in range(num_roads):
            road = Road()
            # Pick random start and end
            sx = rng.randint(5, self.width - 5)
            sy = rng.randint(0, 1) * (self.height - 1)  # Top or bottom
            ex = rng.randint(5, self.width - 5)
            ey = rng.randint(0, 1) * (self.height - 1)

            # Simple A to B path with slight randomization
            steps = max(abs(ex - sx), abs(ey - sy))
            if steps == 0:
                continue
            for i in range(steps + 1):
                t = i / steps
                rx = int(sx + (ex - sx) * t + rng.uniform(-1, 1))
                ry = int(sy + (ey - sy) * t)
                rx = max(0, min(self.width - 1, rx))
                ry = max(0, min(self.height - 1, ry))

                # Road width of 2 cells
                for dx in range(-1, 2):
                    nx = max(0, min(self.width - 1, rx + dx))
                    if 0 <= ry < self.height:
                        self.terrain_types[ry, nx] = TerrainType.ROAD.value
                        road.cells.append((nx, ry))

            self.roads.append(road)

        # Create 1-2 cross roads
        for _ in range(rng.randint(1, 2)):
            road = Road(road_type="paved")
            sx = 0 if rng.random() > 0.5 else self.width - 1
            sy = rng.randint(10, self.height - 10)
            ex = self.width - 1 if sx == 0 else 0
            ey = rng.randint(10, self.height - 10)

            steps = max(abs(ex - sx), abs(ey - sy))
            if steps == 0:
                continue
            for i in range(steps + 1):
                t = i / steps
                rx = int(sx + (ex - sx) * t)
                ry = int(sy + (ey - sy) * t + rng.uniform(-0.5, 0.5))
                rx = max(0, min(self.width - 1, rx))
                ry = max(0, min(self.height - 1, ry))

                for dy in range(-1, 2):
                    ny = max(0, min(self.height - 1, ry + dy))
                    if 0 <= rx < self.width:
                        self.terrain_types[ny, rx] = TerrainType.ROAD.value
                        road.cells.append((rx, ny))

            self.roads.append(road)

    def _generate_buildings(self) -> None:
        """Place building clusters at strategic locations."""
        rng = random.Random(self.seed + 200)

        # Building zones: strategic locations
        zones = [
            (self.width // 4, self.height // 4),
            (3 * self.width // 4, self.height // 4),
            (self.width // 2, self.height // 2),
            (self.width // 4, 3 * self.height // 4),
            (3 * self.width // 4, 3 * self.height // 4),
        ]

        for zx, zy in zones:
            num_buildings = rng.randint(2, 5)
            for _ in range(num_buildings):
                bw = rng.randint(2, 4)
                bh = rng.randint(2, 4)
                bx = max(0, min(self.width - bw - 1, zx + rng.randint(-8, 8)))
                by = max(0, min(self.height - bh - 1, zy + rng.randint(-8, 8)))

                # Check terrain suitability
                suitable = True
                for dy in range(bh):
                    for dx in range(bw):
                        tx, ty = bx + dx, by + dy
                        if self.terrain_types[ty, tx] in (
                            TerrainType.WATER.value,
                            TerrainType.ROAD.value,
                        ):
                            suitable = False
                            break
                    if not suitable:
                        break

                if suitable:
                    structure = Structure(
                        x=bx, y=by, width=bw, height=bh,
                        structure_type="building",
                        metadata={
                            "floors": rng.randint(1, 4),
                            "name": f"BLD-{len(self.structures):03d}",
                        },
                    )
                    self.structures.append(structure)
                    for dy in range(bh):
                        for dx in range(bw):
                            self.terrain_types[by + dy, bx + dx] = (
                                TerrainType.BUILDING.value
                            )

    def _generate_trees(self) -> None:
        """Scatter trees across grass and dirt terrain."""
        rng = random.Random(self.seed + 300)
        tree_density = 0.08 if self.difficulty == "easy" else 0.05

        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.terrain_types[y, x] in (
                    TerrainType.GRASS.value,
                    TerrainType.DIRT.value,
                ):
                    if rng.random() < tree_density:
                        # Don't place on roads or too close to buildings
                        near_structure = False
                        for s in self.structures:
                            if (s.x - 2 <= x <= s.x + s.width + 1 and
                                    s.y - 2 <= y <= s.y + s.height + 1):
                                near_structure = True
                                break
                        if not near_structure:
                            self.terrain_types[y, x] = TerrainType.TREE.value
                            self.tree_positions.append((x, y))

    def _collect_obstacles(self) -> None:
        """Collect all obstacle positions for compatibility with existing World."""
        self.obstacle_positions.clear()
        for y in range(self.height):
            for x in range(self.width):
                tt = self.terrain_types[y, x]
                if tt in (
                    TerrainType.BUILDING.value,
                    TerrainType.TREE.value,
                    TerrainType.WATER.value,
                    TerrainType.ROCK.value,
                    TerrainType.FENCE.value,
                ):
                    self.obstacle_positions.add((x, y))
        # Add structure footprints
        for s in self.structures:
            for dy in range(s.height):
                for dx in range(s.width):
                    self.obstacle_positions.add((s.x + dx, s.y + dy))

    def get_height(self, x: int, y: int) -> float:
        """Get height at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return float(self.height_map[y, x])
        return 0.0

    def get_terrain_type(self, x: int, y: int) -> TerrainType:
        """Get terrain type at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            val = self.terrain_types[y, x]
            for tt in TerrainType:
                if tt.value == val:
                    return tt
        return TerrainType.FLAT_GROUND

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if position is walkable (not water, building, rock)."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        tt = self.terrain_types[y, x]
        return tt not in (
            TerrainType.WATER.value,
            TerrainType.BUILDING.value,
            TerrainType.ROCK.value,
            TerrainType.FENCE.value,
        )

    def get_terrain_color(self, x: int, y: int) -> tuple[float, float, float]:
        """Get display color for terrain type (RGB 0-1)."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return (0.1, 0.1, 0.1)

        tt = self.terrain_types[y, x]
        color_map = {
            TerrainType.FLAT_GROUND.value: (0.15, 0.18, 0.12),
            TerrainType.GRASS.value: (0.12, 0.35, 0.10),
            TerrainType.DIRT.value: (0.35, 0.25, 0.15),
            TerrainType.SAND.value: (0.76, 0.70, 0.50),
            TerrainType.ROCK.value: (0.35, 0.35, 0.35),
            TerrainType.WATER.value: (0.05, 0.20, 0.55),
            TerrainType.ROAD.value: (0.22, 0.22, 0.25),
            TerrainType.BRIDGE.value: (0.45, 0.35, 0.25),
            TerrainType.BUILDING.value: (0.25, 0.28, 0.32),
            TerrainType.TREE.value: (0.08, 0.28, 0.06),
            TerrainType.GRASS_TALL.value: (0.15, 0.40, 0.12),
            TerrainType.PAVEMENT.value: (0.30, 0.30, 0.32),
            TerrainType.FENCE.value: (0.50, 0.40, 0.30),
        }
        return color_map.get(tt, (0.2, 0.2, 0.2))

    def get_terrain_color_array(self) -> np.ndarray:
        """Get full terrain color array as (H, W, 3) float array."""
        colors = np.zeros((self.height, self.width, 3), dtype=np.float32)
        for y in range(self.height):
            for x in range(self.width):
                colors[y, x] = self.get_terrain_color(x, y)
        return colors