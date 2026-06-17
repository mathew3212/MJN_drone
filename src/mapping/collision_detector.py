"""
CollisionDetector
=================
Fast collision detection for point, circle, rectangle, and polygon
shapes against the obstacle field.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from src.core.environment import Environment
from src.core.grid_map import CellState
from src.mapping.spatial_index import SpatialIndex


class CollisionDetector:
    """
    Provides collision detection methods for various geometric shapes
    against the environment's obstacle field.
    """

    def __init__(self, env: Environment) -> None:
        self.env = env
        self.spatial_index = SpatialIndex()

    def rebuild_index(self) -> None:
        """Rebuild the spatial index from the current environment state."""
        self.spatial_index.build(self.env)

    def point_collision(self, x: float, y: float) -> bool:
        """Check if a single point collides with any obstacle."""
        gx, gy = int(x), int(y)
        if self.env.grid_map.in_bounds(gx, gy):
            return self.env.grid_map.is_occupied(gx, gy)
        return True  # Out of bounds = collision

    def circle_collision(
        self,
        cx: float,
        cy: float,
        radius: float,
    ) -> bool:
        """Check if a circle overlaps any obstacle."""
        # Grid check for all cells within bounding box
        x_min = max(0, int(cx - radius))
        x_max = min(self.env.width - 1, int(cx + radius))
        y_min = max(0, int(cy - radius))
        y_max = min(self.env.height - 1, int(cy + radius))

        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                if self.env.grid_map.is_occupied(x, y):
                    dx = x - cx
                    dy = y - cy
                    if dx * dx + dy * dy <= radius * radius:
                        return True

        # Check dynamic obstacles
        for obs in self.env.dynamic_obstacles:
            dx = obs.x - cx
            dy = obs.y - cy
            dist = np.sqrt(dx * dx + dy * dy)
            if dist < (radius + obs.radius):
                return True

        return False

    def line_collision(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> bool:
        """Check if a line segment intersects any obstacle using Bresenham."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        px, py = int(x0), int(y0)

        while True:
            if self.env.grid_map.is_occupied(px, py):
                return True
            if px == int(x1) and py == int(y1):
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                px += sx
            if e2 <= dx:
                err += dx
                py += sy

        return False

    def rect_collision(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> bool:
        """Check if a rectangle overlaps any obstacle."""
        x_min, x_max = int(min(x1, x2)), int(max(x1, x2))
        y_min, y_max = int(min(y1, y2)), int(max(y1, y2))

        for x in range(max(0, x_min), min(self.env.width, x_max + 1)):
            for y in range(max(0, y_min), min(self.env.height, y_max + 1)):
                if self.env.grid_map.is_occupied(x, y):
                    return True
        return False

    def nearest_free_point(
        self,
        x: float,
        y: float,
        max_radius: int = 50,
    ) -> Optional[Tuple[float, float]]:
        """Find the nearest free cell to (x, y)."""
        cell = self.env.grid_map.nearest_free_cell(int(x), int(y), max_radius)
        if cell is not None:
            return (float(cell[0]), float(cell[1]))
        return None

    def clear_path(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        steps: int = 10,
    ) -> bool:
        """Check if there is a clear path between two points by sampling."""
        for i in range(steps + 1):
            t = i / steps
            x = x0 + t * (x1 - x0)
            y = y0 + t * (y1 - y0)
            if self.point_collision(x, y):
                return False
        return True

    def distance_to_obstacle(
        self,
        x: float,
        y: float,
    ) -> float:
        """Get the minimum distance to any obstacle."""
        return self.spatial_index.distance_to_nearest(x, y)