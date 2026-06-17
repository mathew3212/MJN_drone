"""
SpatialIndex
============
KDTree-based spatial index for fast distance queries and nearest-neighbor
lookups against the obstacle field.
"""

from __future__ import annotations

from typing import Iterator, List, Optional, Tuple

import numpy as np
from scipy.spatial import KDTree

from src.core.environment import Environment, Obstacle


class SpatialIndex:
    """
    KDTree wrapper for efficient spatial queries on obstacles.

    Provides fast nearest-neighbor, radius, and distance queries
    against both static and dynamic obstacles.
    """

    def __init__(self, leaf_size: int = 16) -> None:
        self.leaf_size = leaf_size
        self._tree: Optional[KDTree] = None
        self._points: np.ndarray = np.empty((0, 2), dtype=float)
        self._obstacle_ids: List[int] = []

    def build(self, env: Environment) -> None:
        """Build the KDTree from all obstacles in the environment."""
        points = []
        ids = []

        for idx, obs in enumerate(env.static_obstacles):
            points.append([obs.x, obs.y])
            ids.append(idx)  # Positive = static

        for idx, obs in enumerate(env.dynamic_obstacles):
            points.append([obs.x, obs.y])
            ids.append(-(idx + 1))  # Negative = dynamic

        if points:
            self._points = np.array(points, dtype=float)
            self._tree = KDTree(self._points, leafsize=self.leaf_size)
            self._obstacle_ids = ids
        else:
            self._tree = None
            self._points = np.empty((0, 2), dtype=float)
            self._obstacle_ids = []

    def nearest(
        self,
        x: float,
        y: float,
        k: int = 1,
    ) -> List[Tuple[float, float, float]]:
        """
        Find k nearest obstacles to (x, y).

        Returns:
            List of (distance, obstacle_x, obstacle_y) tuples.
        """
        if self._tree is None or len(self._points) == 0:
            return []

        distances, indices = self._tree.query([x, y], k=min(k, len(self._points)))
        if k == 1:
            distances = [distances]
            indices = [indices]

        results = []
        for d, idx in zip(distances[0], indices[0]):
            pt = self._points[idx]
            results.append((float(d), float(pt[0]), float(pt[1])))
        return results

    def radius_search(
        self,
        x: float,
        y: float,
        radius: float,
    ) -> List[Tuple[float, float, float]]:
        """
        Find all obstacles within a given radius.

        Returns:
            List of (distance, obstacle_x, obstacle_y) tuples.
        """
        if self._tree is None or len(self._points) == 0:
            return []

        indices = self._tree.query_ball_point([x, y], radius)
        results = []
        for idx in indices:
            pt = self._points[idx]
            d = float(np.sqrt((pt[0] - x) ** 2 + (pt[1] - y) ** 2))
            results.append((d, float(pt[0]), float(pt[1])))
        return results

    def distance_to_nearest(self, x: float, y: float) -> float:
        """Get distance to the nearest obstacle. Returns inf if none exist."""
        nearest = self.nearest(x, y, k=1)
        if not nearest:
            return float("inf")
        return nearest[0][0]

    def update_dynamic(self, env: Environment) -> None:
        """Rebuild the tree to reflect moved dynamic obstacles."""
        self.build(env)

    def all_points(self) -> np.ndarray:
        """Get all obstacle points as (N, 2) array."""
        return self._points.copy()

    def clear(self) -> None:
        """Clear the spatial index."""
        self._tree = None
        self._points = np.empty((0, 2), dtype=float)
        self._obstacle_ids = []