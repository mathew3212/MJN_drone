"""
Compass
=======
Simulated digital compass with configurable drift and noise.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class CompassConfig:
    """Configuration for the compass sensor."""
    noise_std: float = 0.05  # radians
    drift_rate: float = 0.001  # radians per reading


class Compass:
    """
    Simulated compass that measures heading with noise and drift.
    """

    def __init__(self, config: Optional[CompassConfig] = None) -> None:
        self.config = config or CompassConfig()
        self._drift: float = 0.0
        self._rng = np.random.RandomState()

    def read(self, true_heading: float) -> float:
        """
        Read the current heading with noise and drift.

        Args:
            true_heading: Actual heading in radians.

        Returns:
            Measured heading in radians.
        """
        self._drift += self._rng.randn() * self.config.drift_rate
        noise = self._rng.randn() * self.config.noise_std
        measured = true_heading + self._drift + noise
        return float(np.arctan2(np.sin(measured), np.cos(measured)))

    def reset(self) -> None:
        """Reset drift."""
        self._drift = 0.0

    def seed(self, seed: int) -> None:
        """Set random seed."""
        self._rng = np.random.RandomState(seed)