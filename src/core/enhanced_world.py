"""
Enhanced Military World
========================
Wraps the existing World class, adding terrain, weather, and
military infrastructure without breaking existing interfaces.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from src.core.world import World, DynamicObstacle
from src.core.terrain import TerrainGenerator, TerrainType
from src.core.weather import WeatherSystem, WeatherType


# ── Military Zone Types ──────────────────────────────────────────────────────


@dataclass
class MilitaryZone:
    """A specialized military zone (landing zone, restricted, etc.)."""
    x: int
    y: int
    radius: int
    zone_type: str  # "landing", "restricted", "mission", "danger", "radar"
    metadata: dict = field(default_factory=dict)


@dataclass
class Convoy:
    """A moving convoy (group of dynamic obstacles)."""
    positions: list[tuple[int, int]]
    direction: tuple[int, int]
    speed: int = 1
    convoy_type: str = "vehicle"


class EnhancedWorld(World):
    """Enhanced world with terrain, weather, and military infrastructure.

    Inherits from World to maintain full backward compatibility.
    """

    def __init__(self, width: int = 100, height: int = 100,
                 num_obstacles: int = 100, seed: int = 42):
        # Initialize parent World (generates static + dynamic obstacles)
        super().__init__(width, height, num_obstacles)

        self.seed = seed

        # Terrain system
        self.terrain = TerrainGenerator(width, height, seed=seed)
        self.terrain_data = self.terrain.generate()

        # Weather system
        self.weather = WeatherSystem(width, height, seed=seed)

        # Military zones
        self.military_zones: list[MilitaryZone] = []
        self._generate_military_zones()

        # Convoy obstacle groups
        self.convoys: list[Convoy] = []
        self._generate_convoys()

        # Enemy drones (dynamic)
        self.enemy_drones: list[DynamicObstacle] = []
        self._generate_enemy_drones()

        # Add terrain obstacles to static obstacles
        self._merge_terrain_obstacles()

        # Additional obstacle metadata
        self.obstacle_categories: dict[tuple[int, int], str] = {}
        self._categorize_obstacles()

        # Frame counter for animations
        self.frame_count: int = 0

    def _generate_military_zones(self) -> None:
        """Generate military zones at strategic locations."""
        rng = random.Random(self.seed + 700)

        # Landing zones
        for _ in range(rng.randint(2, 4)):
            x = rng.randint(10, self.width - 10)
            y = rng.randint(10, self.height - 10)
            self.military_zones.append(MilitaryZone(
                x=x, y=y, radius=rng.randint(3, 5),
                zone_type="landing",
                metadata={"name": f"LZ-{chr(65 + len(self.military_zones))}"},
            ))

        # Restricted zones
        for _ in range(rng.randint(1, 3)):
            x = rng.randint(15, self.width - 15)
            y = rng.randint(15, self.height - 15)
            self.military_zones.append(MilitaryZone(
                x=x, y=y, radius=rng.randint(5, 10),
                zone_type="restricted",
                metadata={"name": f"RZ-{len(self.military_zones)}"},
            ))

        # Mission zones
        self.military_zones.append(MilitaryZone(
            x=self.width // 2, y=self.height // 2,
            radius=8,
            zone_type="mission",
            metadata={"name": "OP AREA"},
        ))

        # Radar towers
        for _ in range(rng.randint(1, 3)):
            x = rng.randint(10, self.width - 10)
            y = rng.randint(10, self.height - 10)
            self.military_zones.append(MilitaryZone(
                x=x, y=y, radius=15,
                zone_type="radar",
                metadata={"name": f"RADAR-{len(self.military_zones)}"},
            ))

    def _generate_convoys(self) -> None:
        """Generate moving convoy obstacle groups."""
        rng = random.Random(self.seed + 800)
        for _ in range(rng.randint(1, 3)):
            start_x = rng.randint(10, self.width - 30)
            start_y = rng.randint(10, self.height - 10)
            direction = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            length = rng.randint(3, 5)
            positions = [
                (start_x + direction[0] * i, start_y + direction[1] * i)
                for i in range(length)
            ]
            self.convoys.append(Convoy(
                positions=positions,
                direction=direction,
                speed=1,
                convoy_type="vehicle",
            ))

    def _generate_enemy_drones(self) -> None:
        """Generate enemy drone obstacles."""
        rng = random.Random(self.seed + 900)
        for _ in range(rng.randint(2, 5)):
            ex = rng.randint(15, self.width - 15)
            ey = rng.randint(15, self.height - 15)
            drone = DynamicObstacle(ex, ey)
            drone.direction = rng.choice([
                (1, 0), (-1, 0), (0, 1), (0, -1),
                (1, 1), (-1, -1), (1, -1), (-1, 1),
            ])
            self.enemy_drones.append(drone)

    def _merge_terrain_obstacles(self) -> None:
        """Merge terrain obstacles into the World's obstacle set."""
        for pos in self.terrain_data["obstacle_positions"]:
            self.obstacles.add(pos)

    def _categorize_obstacles(self) -> None:
        """Assign categories to all obstacles for metadata lookups."""
        for x, y in self.obstacles:
            tt = self.terrain.get_terrain_type(x, y)
            if tt == TerrainType.BUILDING:
                self.obstacle_categories[(x, y)] = "building"
            elif tt == TerrainType.TREE:
                self.obstacle_categories[(x, y)] = "tree"
            elif tt == TerrainType.WATER:
                self.obstacle_categories[(x, y)] = "water"
            elif tt == TerrainType.ROCK:
                self.obstacle_categories[(x, y)] = "rock"
            else:
                self.obstacle_categories[(x, y)] = "terrain"

    def update(self) -> None:
        """Update all dynamic systems (parent + weather + convoys + enemies)."""
        super().update()
        self.weather.update(dt=1.0)

        # Update convoys
        for convoy in self.convoys:
            # Remove old positions from obstacles
            for px, py in convoy.positions:
                self.obstacles.discard((px, py))

            # Move positions
            new_positions = []
            for px, py in convoy.positions:
                nx = px + convoy.direction[0] * convoy.speed
                ny = py + convoy.direction[1] * convoy.speed
                # Bounce off walls
                if not (0 <= nx < self.width):
                    convoy.direction = (-convoy.direction[0], convoy.direction[1])
                    nx = px
                if not (0 <= ny < self.height):
                    convoy.direction = (convoy.direction[0], -convoy.direction[1])
                    ny = py
                new_positions.append((nx, ny))
            convoy.positions = new_positions

            # Add new positions to obstacles
            for px, py in convoy.positions:
                self.obstacles.add((px, py))
                self.obstacle_categories[(px, py)] = "convoy"

        # Update enemy drones
        for drone in self.enemy_drones:
            drone.update(self.width, self.height)

        self.frame_count += 1

    def get_wind_at(self, x: float, y: float):
        """Get wind at position."""
        return self.weather.wind.get_wind_at(x, y)

    def get_terrain_type_at(self, x: int, y: int) -> TerrainType:
        """Get terrain type at position."""
        return self.terrain.get_terrain_type(x, y)

    def get_weather_state(self) -> dict:
        """Get current weather state as dictionary."""
        return {
            "type": self.weather.weather_type,
            "wind_speed": self.weather.wind.base_wind.speed,
            "wind_direction": self.weather.wind.base_wind.direction,
            "visibility": self.weather.atmosphere.visibility,
            "fog_density": self.weather.atmosphere.fog_density,
            "ambient_light": self.weather.atmosphere.ambient_light,
            "temperature": self.weather.atmosphere.temperature,
            "time_of_day": self.weather.atmosphere.time_of_day.name,
            "day_progress": self.weather.atmosphere.day_progress,
        }

    def get_military_zone_at(self, x: int, y: int) -> Optional[MilitaryZone]:
        """Check if position is within any military zone."""
        for zone in self.military_zones:
            dist = math.sqrt((x - zone.x) ** 2 + (y - zone.y) ** 2)
            if dist <= zone.radius:
                return zone
        return None

    def get_all_dynamic_positions(self) -> list[tuple[float, float, str]]:
        """Get all dynamic obstacle positions with types."""
        positions = []
        for obs in self.dynamic_obstacles:
            positions.append((obs.x, obs.y, "dynamic"))
        for drone in self.enemy_drones:
            positions.append((drone.x, drone.y, "enemy_drone"))
        for convoy in self.convoys:
            for px, py in convoy.positions:
                positions.append((px, py, "convoy"))
        return positions