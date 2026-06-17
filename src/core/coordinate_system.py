"""
CoordinateSystem
================
2D coordinate transforms between world, grid, and local coordinate frames.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass
class CoordinateSystem:
    """
    Handles conversions between world coordinates (continuous),
    grid coordinates (discrete cells), and local body-fixed frames.
    """
    resolution: float = 1.0
    origin_x: float = 0.0
    origin_y: float = 0.0

    def world_to_grid(self, wx: float, wy: float) -> Tuple[int, int]:
        """Convert world coordinates to grid cell indices."""
        gx = int((wx - self.origin_x) / self.resolution)
        gy = int((wy - self.origin_y) / self.resolution)
        return (gx, gy)

    def grid_to_world(self, gx: int, gy: int) -> Tuple[float, float]:
        """Convert grid cell indices to world coordinates (cell center)."""
        wx = gx * self.resolution + self.resolution / 2 + self.origin_x
        wy = gy * self.resolution + self.resolution / 2 + self.origin_y
        return (wx, wy)

    def world_to_local(
        self,
        wx: float,
        wy: float,
        drone_x: float,
        drone_y: float,
        drone_heading: float,
    ) -> Tuple[float, float]:
        """Transform world point to drone body-fixed coordinates."""
        dx = wx - drone_x
        dy = wy - drone_y
        cos_h = np.cos(-drone_heading)
        sin_h = np.sin(-drone_heading)
        lx = dx * cos_h - dy * sin_h
        ly = dx * sin_h + dy * cos_h
        return (float(lx), float(ly))

    def local_to_world(
        self,
        lx: float,
        ly: float,
        drone_x: float,
        drone_y: float,
        drone_heading: float,
    ) -> Tuple[float, float]:
        """Transform body-fixed point to world coordinates."""
        cos_h = np.cos(drone_heading)
        sin_h = np.sin(drone_heading)
        wx = lx * cos_h - ly * sin_h + drone_x
        wy = lx * sin_h + ly * cos_h + drone_y
        return (float(wx), float(wy))

    def distance(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        """Euclidean distance between two world points."""
        return float(np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2))