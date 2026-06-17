"""
WorldGenerator
==============
Random world generation with seeded RNG, configurable obstacle placement.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from src.core.configuration import SimulationConfig
from src.core.environment import Environment, EnvironmentConfig, Obstacle


class WorldGenerator:
    """
    Factory for generating random simulation worlds.

    Uses a seeded random state for reproducible generation.
    Supports multiple obstacle shapes and density levels.
    """

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self._rng = np.random.RandomState(config.random_seed)

    def generate(self) -> Environment:
        """Generate a complete environment with obstacles from config."""
        env_config = EnvironmentConfig(
            width=self.config.world_width,
            height=self.config.world_height,
            num_static_obstacles=self.config.num_static_obstacles,
            num_dynamic_obstacles=self.config.num_dynamic_obstacles,
            resolution=self.config.world_resolution,
            seed=self.config.random_seed,
        )
        env = Environment(env_config)

        # Generate random obstacles
        env.generate_random_obstacles()
        env.generate_random_dynamic_obstacles()

        return env

    def generate_empty(self) -> Environment:
        """Generate an environment with no obstacles."""
        env_config = EnvironmentConfig(
            width=self.config.world_width,
            height=self.config.world_height,
            num_static_obstacles=0,
            num_dynamic_obstacles=0,
            resolution=self.config.world_resolution,
            seed=self.config.random_seed,
        )
        return Environment(env_config)

    def generate_with_density(
        self,
        obstacle_density: float = 0.1,
    ) -> Environment:
        """
        Generate an environment with obstacles at a given density.

        Args:
            obstacle_density: Fraction of grid cells to fill (0.0 to 1.0).
        """
        total_cells = self.config.world_width * self.config.world_height
        num_obs = int(total_cells * obstacle_density)
        self.config.num_static_obstacles = num_obs
        return self.generate()

    def generate_clustered(
        self,
        num_clusters: int = 5,
        cluster_size: int = 10,
    ) -> Environment:
        """Generate clustered obstacle fields."""
        env = self.generate_empty()

        for _ in range(num_clusters):
            cx = self._rng.randint(10, self.config.world_width - 10)
            cy = self._rng.randint(10, self.config.world_height - 10)

            for _ in range(cluster_size):
                x = cx + int(self._rng.randint(-3, 3))
                y = cy + int(self._rng.randint(-3, 3))
                if 0 <= x < self.config.world_width and 0 <= y < self.config.world_height:
                    env.add_static_obstacle(float(x), float(y))

        return env

    def generate_maze(self) -> Environment:
        """
        Generate a simple maze-like obstacle structure.
        Uses recursive division algorithm.
        """
        env = self.generate_empty()
        w, h = self.config.world_width, self.config.world_height

        def divide(x1: int, y1: int, x2: int, y2: int) -> None:
            if x2 - x1 < 4 or y2 - y1 < 4:
                return

            # Draw horizontal or vertical wall
            if (x2 - x1) > (y2 - y1):
                # Vertical wall
                wx = self._rng.randint(x1 + 1, x2)
                # Leave a gap
                gap = self._rng.randint(y1, y2)
                for y in range(y1, y2 + 1):
                    if y != gap:
                        env.add_static_obstacle(float(wx), float(y))
                divide(x1, y1, wx - 1, y2)
                divide(wx + 1, y1, x2, y2)
            else:
                # Horizontal wall
                wy = self._rng.randint(y1 + 1, y2)
                gap = self._rng.randint(x1, x2)
                for x in range(x1, x2 + 1):
                    if x != gap:
                        env.add_static_obstacle(float(x), float(wy))
                divide(x1, y1, x2, wy - 1)
                divide(x1, wy + 1, x2, y2)

        divide(1, 1, w - 2, h - 2)
        return env

    def seed(self, seed: int) -> None:
        """Reset the random generator with a specific seed."""
        self._rng = np.random.RandomState(seed)