"""
VirtualCamera
=============
Simulated RGB/depth camera with configurable FOV, resolution, and noise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from src.core.environment import Environment


@dataclass
class CameraConfig:
    """Configuration for the virtual camera sensor."""
    fov_degrees: float = 90.0
    resolution: Tuple[int, int] = (64, 64)
    max_range: float = 20.0
    noise_std: float = 0.1


class VirtualCamera:
    """
    Simulated camera that detects obstacles within its field of view.

    Returns obstacle positions in the camera's local coordinate frame.
    """

    def __init__(self, config: Optional[CameraConfig] = None) -> None:
        self.config = config or CameraConfig()
        self._rng = np.random.RandomState()

    def detect(
        self,
        env: Environment,
        drone_x: float,
        drone_y: float,
        drone_heading: float,
    ) -> List[Tuple[float, float]]:
        """
        Detect obstacles visible in the camera's FOV.

        Returns:
            List of (x, y) obstacle positions in world coordinates.
        """
        half_fov = np.radians(self.config.fov_degrees / 2)
        detected = []

        for obs in env.static_obstacles:
            dx = obs.x - drone_x
            dy = obs.y - drone_y
            dist = np.sqrt(dx * dx + dy * dy)

            if dist > self.config.max_range:
                continue

            # Check if within FOV
            angle_to_obs = np.arctan2(dy, dx) - drone_heading
            angle_to_obs = np.arctan2(np.sin(angle_to_obs), np.cos(angle_to_obs))

            if abs(angle_to_obs) <= half_fov:
                # Add noise
                nx = obs.x + self._rng.randn() * self.config.noise_std
                ny = obs.y + self._rng.randn() * self.config.noise_std
                detected.append((float(nx), float(ny)))

        return detected

    def seed(self, seed: int) -> None:
        """Set random seed for noise generation."""
        self._rng = np.random.RandomState(seed)