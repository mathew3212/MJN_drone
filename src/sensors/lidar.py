"""
Lidar
=====
Simulated 2D lidar with configurable number of rays, range, and noise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from src.core.environment import Environment


@dataclass
class LidarConfig:
    """Configuration for the lidar sensor."""
    num_rays: int = 64
    max_range: float = 15.0
    noise_std: float = 0.2
    angle_min: float = 0.0
    angle_max: float = 2 * np.pi


class Lidar:
    """
    Simulated 2D lidar scanner. Returns range readings for each ray.
    """

    def __init__(self, config: Optional[LidarConfig] = None) -> None:
        self.config = config or LidarConfig()
        self._rng = np.random.RandomState()

    def scan(
        self,
        env: Environment,
        drone_x: float,
        drone_y: float,
        drone_heading: float,
    ) -> List[Tuple[float, float, float]]:
        """
        Perform a full 360-degree lidar scan.

        Returns:
            List of (angle, range, x, y) for each detected point.
        """
        angles = np.linspace(
            self.config.angle_min + drone_heading,
            self.config.angle_max + drone_heading,
            self.config.num_rays,
            endpoint=False,
        )
        readings = []

        for angle in angles:
            range_found = self.config.max_range

            # Check static obstacles
            for obs in env.static_obstacles:
                dx = obs.x - drone_x
                dy = obs.y - drone_y
                dist = np.sqrt(dx * dx + dy * dy)

                # Check if obstacle is along this ray
                angle_diff = abs(np.arctan2(np.sin(np.arctan2(dy, dx) - angle),
                                            np.cos(np.arctan2(dy, dx) - angle)))
                if angle_diff < 0.1:  # Within beam width
                    if dist < range_found:
                        range_found = dist

            # Add noise
            range_found += self._rng.randn() * self.config.noise_std
            range_found = max(0.0, range_found)

            x = drone_x + range_found * np.cos(angle)
            y = drone_y + range_found * np.sin(angle)
            readings.append((float(angle), float(range_found), float(x), float(y)))

        return readings

    def get_obstacle_points(
        self,
        env: Environment,
        drone_x: float,
        drone_y: float,
        drone_heading: float,
    ) -> List[Tuple[float, float]]:
        """Get just the (x, y) obstacle points from a scan."""
        readings = self.scan(env, drone_x, drone_y, drone_heading)
        points = []
        for _, r, x, y in readings:
            if r < self.config.max_range - 0.1:  # Detected something
                points.append((x, y))
        return points

    def seed(self, seed: int) -> None:
        """Set random seed for noise."""
        self._rng = np.random.RandomState(seed)