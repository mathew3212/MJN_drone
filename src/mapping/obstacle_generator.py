"""
ObstacleGenerator
=================
Factory for generating circular, rectangular, and polygon obstacles
for the obstacle field.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from src.core.environment import Environment, Obstacle
from src.core.grid_map import CellState


@dataclass
class CircularObstacle:
    """A circular obstacle with center and radius."""
    cx: float
    cy: float
    radius: float


@dataclass
class RectangularObstacle:
    """A rectangular obstacle defined by corners."""
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass
class PolygonObstacle:
    """A polygon obstacle defined by vertex list."""
    vertices: np.ndarray  # (N, 2) array of vertices


class ObstacleGenerator:
    """
    Generates obstacles of various shapes and adds them to the environment.

    Supports circular, rectangular, and polygon obstacle types
    with configurable placement.
    """

    def __init__(self, rng: Optional[np.random.RandomState] = None) -> None:
        self._rng = rng or np.random.RandomState(42)

    def add_circular(
        self,
        env: Environment,
        cx: float,
        cy: float,
        radius: float,
    ) -> CircularObstacle:
        """Add a circular obstacle cluster to the environment."""
        obs = CircularObstacle(cx, cy, radius)
        for dy in range(-int(radius), int(radius) + 1):
            for dx in range(-int(radius), int(radius) + 1):
                if dx * dx + dy * dy <= radius * radius:
                    x, y = int(cx + dx), int(cy + dy)
                    if env.grid_map.in_bounds(x, y):
                        env.grid_map.set_occupied(x, y)
                        env.add_static_obstacle(float(x), float(y))
        return obs

    def add_rectangular(
        self,
        env: Environment,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> RectangularObstacle:
        """Add a rectangular obstacle to the environment."""
        obs = RectangularObstacle(x1, y1, x2, y2)
        x_min, x_max = int(min(x1, x2)), int(max(x1, x2))
        y_min, y_max = int(min(y1, y2)), int(max(y1, y2))

        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if env.grid_map.in_bounds(x, y):
                    env.grid_map.set_occupied(x, y)
                    env.add_static_obstacle(float(x), float(y))
        return obs

    def add_polygon(
        self,
        env: Environment,
        vertices: List[Tuple[float, float]],
    ) -> PolygonObstacle:
        """Add a polygon obstacle to the environment."""
        vert_arr = np.array(vertices)
        obs = PolygonObstacle(vert_arr)

        # Rasterize polygon using bounding box + point-in-polygon test
        x_min = int(max(0, np.min(vert_arr[:, 0])))
        x_max = int(min(env.width - 1, np.max(vert_arr[:, 0])))
        y_min = int(max(0, np.min(vert_arr[:, 1])))
        y_max = int(min(env.height - 1, np.max(vert_arr[:, 1])))

        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if self._point_in_polygon(x, y, vert_arr):
                    env.grid_map.set_occupied(x, y)
                    env.add_static_obstacle(float(x), float(y))
        return obs

    def generate_random_circular(
        self,
        env: Environment,
        count: int = 5,
        min_radius: int = 2,
        max_radius: int = 6,
    ) -> List[CircularObstacle]:
        """Generate random circular obstacle clusters."""
        obstacles = []
        for _ in range(count):
            cx = self._rng.randint(5, env.width - 5)
            cy = self._rng.randint(5, env.height - 5)
            radius = self._rng.randint(min_radius, max_radius)
            obs = self.add_circular(env, float(cx), float(cy), float(radius))
            obstacles.append(obs)
        return obstacles

    def generate_random_rectangular(
        self,
        env: Environment,
        count: int = 5,
        min_size: int = 3,
        max_size: int = 10,
    ) -> List[RectangularObstacle]:
        """Generate random rectangular obstacles."""
        obstacles = []
        for _ in range(count):
            x1 = self._rng.randint(2, env.width - 2)
            y1 = self._rng.randint(2, env.height - 2)
            w = self._rng.randint(min_size, max_size)
            h = self._rng.randint(min_size, max_size)
            x2 = min(x1 + w, env.width - 1)
            y2 = min(y1 + h, env.height - 1)
            obs = self.add_rectangular(env, float(x1), float(y1), float(x2), float(y2))
            obstacles.append(obs)
        return obstacles

    def _point_in_polygon(
        self,
        px: float,
        py: float,
        vertices: np.ndarray,
    ) -> bool:
        """Ray casting point-in-polygon test."""
        n = len(vertices)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = vertices[i]
            xj, yj = vertices[j]
            if ((yi > py) != (yj > py)) and (
                px < (xj - xi) * (py - yi) / (yj - yi) + xi
            ):
                inside = not inside
            j = i
        return inside

    def seed(self, seed: int) -> None:
        """Reset random generator."""
        self._rng = np.random.RandomState(seed)