"""
Environment
===========
Container that holds the complete world state including grid map,
dynamic obstacles, bounds, and simulation settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from src.core.grid_map import GridMap, GridMapConfig, CellState


@dataclass
class Obstacle:
    """A static or dynamic obstacle in the environment."""
    x: float
    y: float
    radius: float = 0.5
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    is_dynamic: bool = False
    obstacle_type: str = "circular"  # circular, rectangular, polygon


@dataclass
class EnvironmentConfig:
    """Configuration for the simulation environment."""
    width: int = 100
    height: int = 100
    num_static_obstacles: int = 100
    num_dynamic_obstacles: int = 10
    resolution: float = 1.0
    seed: int = 42


class Environment:
    """
    Complete simulation environment container.

    Owns the GridMap, static and dynamic obstacles, and provides
    methods for updating the world state each simulation step.
    """

    def __init__(self, config: EnvironmentConfig) -> None:
        self.config = config
        self.width = config.width
        self.height = config.height

        self.grid_map = GridMap(GridMapConfig(
            width=config.width,
            height=config.height,
            resolution=config.resolution,
        ))

        self.static_obstacles: List[Obstacle] = []
        self.dynamic_obstacles: List[Obstacle] = []
        self._rng = np.random.RandomState(config.seed)
        self.time: float = 0.0
        self.step_count: int = 0

    def add_static_obstacle(
        self,
        x: float,
        y: float,
        radius: float = 0.5,
        obstacle_type: str = "circular",
    ) -> Obstacle:
        """Add a static obstacle to the environment."""
        obs = Obstacle(
            x=x, y=y, radius=radius,
            is_dynamic=False, obstacle_type=obstacle_type,
        )
        self.static_obstacles.append(obs)
        self.grid_map.set_occupied(int(x), int(y))
        return obs

    def add_dynamic_obstacle(
        self,
        x: float,
        y: float,
        vx: float = 0.0,
        vy: float = 0.0,
        radius: float = 0.5,
    ) -> Obstacle:
        """Add a dynamic (moving) obstacle to the environment."""
        obs = Obstacle(
            x=x, y=y, radius=radius,
            velocity_x=vx, velocity_y=vy,
            is_dynamic=True, obstacle_type="circular",
        )
        self.dynamic_obstacles.append(obs)
        return obs

    def generate_random_obstacles(
        self,
        count: Optional[int] = None,
    ) -> None:
        """Generate random static obstacles within bounds."""
        n = count if count is not None else self.config.num_static_obstacles
        for _ in range(n):
            x = self._rng.randint(0, self.width)
            y = self._rng.randint(0, self.height)
            self.add_static_obstacle(float(x), float(y))

    def generate_random_dynamic_obstacles(
        self,
        count: Optional[int] = None,
    ) -> None:
        """Generate random dynamic obstacles with random velocities."""
        n = count if count is not None else self.config.num_dynamic_obstacles
        for _ in range(n):
            x = float(self._rng.randint(0, self.width))
            y = float(self._rng.randint(0, self.height))
            vx = float(self._rng.choice([-1, 1]) * self._rng.uniform(0.1, 0.5))
            vy = float(self._rng.choice([-1, 1]) * self._rng.uniform(0.1, 0.5))
            self.add_dynamic_obstacle(x, y, vx, vy)

    def update(self, dt: float = 1.0) -> None:
        """Advance the simulation by one time step."""
        self.time += dt
        self.step_count += 1

        # Update dynamic obstacle positions
        for obs in self.dynamic_obstacles:
            obs.x += obs.velocity_x * dt
            obs.y += obs.velocity_y * dt

            # Bounce off walls
            if obs.x < 0 or obs.x >= self.width:
                obs.velocity_x *= -1
                obs.x = max(0.0, min(self.width - 1, obs.x))
            if obs.y < 0 or obs.y >= self.height:
                obs.velocity_y *= -1
                obs.y = max(0.0, min(self.height - 1, obs.y))

    def is_collision(
        self,
        x: float,
        y: float,
        margin: float = 0.0,
    ) -> bool:
        """Check if a point collides with any obstacle."""
        # Check grid map occupancy
        gx, gy = int(x), int(y)
        if self.grid_map.is_occupied(gx, gy):
            return True

        # Check dynamic obstacles
        m = int(np.ceil(margin))
        for obs in self.dynamic_obstacles:
            dx = x - obs.x
            dy = y - obs.y
            dist = np.sqrt(dx * dx + dy * dy)
            if dist < (obs.radius + margin + 0.5):
                return True

        return False

    def get_obstacle_positions(self) -> List[Tuple[float, float]]:
        """Get all static and dynamic obstacle positions."""
        positions = [(o.x, o.y) for o in self.static_obstacles]
        positions.extend((o.x, o.y) for o in self.dynamic_obstacles)
        return positions

    def reset(self) -> None:
        """Reset the environment to initial state."""
        self.grid_map.reset()
        self.static_obstacles.clear()
        self.dynamic_obstacles.clear()
        self.time = 0.0
        self.step_count = 0
        self._rng = np.random.RandomState(self.config.seed)