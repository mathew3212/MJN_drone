"""
WorldVisualization
==================
Rendering functions for the 2D world grid, obstacles, drone, and targets.
Uses matplotlib for all display.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle

from src.core.environment import Environment, Obstacle
from src.core.grid_map import GridMap, CellState


class WorldRenderer:
    """Renders the world state to a matplotlib axis."""

    def __init__(self) -> None:
        self._static_scatter: Optional[PathCollection] = None
        self._dynamic_scatter: Optional[PathCollection] = None
        self._drone_marker: Optional[PathCollection] = None
        self._target_marker: Optional[PathCollection] = None
        self._trail_line: Optional[Line2D] = None
        self._sensor_circle: Optional[Circle] = None
        self.trail: List[Tuple[float, float]] = []

    def render(
        self,
        ax: plt.Axes,
        env: Environment,
        drone_pos: Tuple[float, float],
        drone_heading: float,
        target: Optional[Tuple[float, float]] = None,
        path: Optional[List[Tuple[float, float]]] = None,
        scan_radius: float = 0,
    ) -> None:
        """Render the full world state on the given axis."""
        if self._static_scatter is None:
            self._init_artists(ax)

        ax.set_xlim(-0.5, env.width - 0.5)
        ax.set_ylim(-0.5, env.height - 0.5)

        # Static obstacles
        static_pos = [(o.x, o.y) for o in env.static_obstacles]
        if static_pos:
            self._static_scatter.set_offsets(np.array(static_pos))

        # Dynamic obstacles
        dynamic_pos = [(o.x, o.y) for o in env.dynamic_obstacles]
        if dynamic_pos:
            self._dynamic_scatter.set_offsets(np.array(dynamic_pos))

        # Drone
        self._drone_marker.set_offsets(np.array([[drone_pos[0], drone_pos[1]]]))

        # Trail
        self.trail.append(drone_pos)
        self.trail = self.trail[-300:]
        if len(self.trail) > 1:
            trail_arr = np.array(self.trail)
            self._trail_line.set_data(trail_arr[:, 0], trail_arr[:, 1])

        # Target
        if target:
            self._target_marker.set_offsets(np.array([[target[0], target[1]]]))

        # Sensor range
        if scan_radius > 0:
            self._sensor_circle.center = (drone_pos[0], drone_pos[1])
            self._sensor_circle.set_radius(scan_radius)

    def _init_artists(self, ax: plt.Axes) -> None:
        """Initialize matplotlib artists."""
        self._static_scatter = ax.scatter(
            [], [], s=18, c="#334155", alpha=0.85, linewidths=0,
        )
        self._dynamic_scatter = ax.scatter(
            [], [], marker="D", s=80, c="#FF3B30",
            edgecolors="#7f1d1d", linewidths=0.6,
        )
        self._drone_marker = ax.scatter(
            [], [], marker="^", s=240, c="#FF9800",
            edgecolors="#9A3412", linewidths=1.0, zorder=5,
        )
        self._target_marker = ax.scatter(
            [], [], marker="*", s=360, c="#00FF66",
            edgecolors="#14532D", linewidths=1.0, zorder=4,
        )
        self._trail_line = ax.plot(
            [], [], linewidth=2.0, color="#FF9800",
            alpha=0.6,
        )[0]
        self._sensor_circle = Circle(
            (0, 0), 1, fill=False, linestyle=":",
            linewidth=1.5, color="#14B8A6", alpha=0.7,
        )
        ax.add_patch(self._sensor_circle)

    def render_grid(
        self,
        ax: plt.Axes,
        grid_map: GridMap,
    ) -> None:
        """Render the occupancy grid as a colored image."""
        grid_data = grid_map.to_numpy()
        display = np.zeros((*grid_data.shape, 3), dtype=np.float32)

        # Unknown: dark gray
        display[grid_data == CellState.UNKNOWN.value] = [0.15, 0.15, 0.2]
        # Free: dark teal
        display[grid_data == CellState.FREE.value] = [0.08, 0.12, 0.16]
        # Occupied: red/brown
        display[grid_data == CellState.OCCUPIED.value] = [0.4, 0.12, 0.08]

        ax.imshow(display, origin="lower", interpolation="nearest")


def render_world_grid(
    env: Environment,
    drone_pos: Tuple[float, float],
    drone_heading: float,
    target: Optional[Tuple[float, float]] = None,
    path: Optional[List[Tuple[float, float]]] = None,
    scan_radius: float = 0,
    title: str = "World",
) -> None:
    """Convenience function to create a standalone world plot."""
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_title(title, fontsize=12, fontweight="bold")
    renderer = WorldRenderer()
    renderer.render(ax, env, drone_pos, drone_heading, target, path, scan_radius)
    plt.show()