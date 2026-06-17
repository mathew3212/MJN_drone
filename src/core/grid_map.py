"""
GridMap
=======
2D occupancy grid with configurable size, cell states, and collision lookup.
Core spatial data structure for the autonomous drone navigation system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Generator, List, Optional, Tuple

import numpy as np


class CellState(IntEnum):
    """Occupancy states for each cell in the grid."""
    FREE = 0
    OCCUPIED = 1
    UNKNOWN = -1


@dataclass
class GridMapConfig:
    """Configuration for grid map dimensions and behavior."""
    width: int = 100
    height: int = 100
    resolution: float = 1.0  # meters per cell
    initial_state: CellState = CellState.UNKNOWN


class GridMap:
    """
    2D occupancy grid map with collision detection and spatial queries.

    Provides O(1) cell lookup, obstacle collision checks,
    and utility methods for converting between world and grid coordinates.
    """

    def __init__(self, config: GridMapConfig) -> None:
        self.config = config
        self.width = config.width
        self.height = config.height
        self.resolution = config.resolution

        self._grid: np.ndarray = np.full(
            (config.height, config.width),
            config.initial_state.value,
            dtype=np.int8,
        )

    # ── Cell Access ──────────────────────────────────────────────────

    def __getitem__(self, key: Tuple[int, int]) -> int:
        x, y = key
        return int(self._grid[y, x])

    def __setitem__(self, key: Tuple[int, int], value: int) -> None:
        x, y = key
        self._grid[y, x] = np.int8(value)

    # ── State Queries ────────────────────────────────────────────────

    def is_occupied(self, x: int, y: int) -> bool:
        """Returns True if the cell at (x, y) is occupied."""
        if not self.in_bounds(x, y):
            return True  # Out-of-bounds treated as obstacle
        return self._grid[y, x] == CellState.OCCUPIED.value

    def is_free(self, x: int, y: int) -> bool:
        """Returns True if the cell at (x, y) is free."""
        if not self.in_bounds(x, y):
            return False
        return self._grid[y, x] == CellState.FREE.value

    def is_unknown(self, x: int, y: int) -> bool:
        """Returns True if the cell at (x, y) is unexplored."""
        if not self.in_bounds(x, y):
            return False
        return self._grid[y, x] == CellState.UNKNOWN.value

    def in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are within grid bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    # ── Cell Manipulation ────────────────────────────────────────────

    def set_occupied(self, x: int, y: int) -> None:
        """Mark cell as occupied."""
        if self.in_bounds(x, y):
            self._grid[y, x] = CellState.OCCUPIED.value

    def set_free(self, x: int, y: int) -> None:
        """Mark cell as free."""
        if self.in_bounds(x, y):
            self._grid[y, x] = CellState.FREE.value

    def set_unknown(self, x: int, y: int) -> None:
        """Reset cell to unknown."""
        if self.in_bounds(x, y):
            self._grid[y, x] = CellState.UNKNOWN.value

    # ── Batch Operations ─────────────────────────────────────────────

    def mark_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        state: CellState = CellState.FREE,
    ) -> None:
        """Mark all cells within a circular region with the given state."""
        cx, cy = int(center_x), int(center_y)
        r = int(np.ceil(radius / self.resolution))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    x, y = cx + dx, cy + dy
                    if self.in_bounds(x, y):
                        self._grid[y, x] = state.value

    def mark_line(
        self,
        x0: int, y0: int,
        x1: int, y1: int,
        state: CellState = CellState.OCCUPIED,
    ) -> None:
        """Bresenham line algorithm to mark cells along a line."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        while True:
            if self.in_bounds(x0, y0):
                self._grid[y0, x0] = state.value
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    # ── Queries ──────────────────────────────────────────────────────

    def occupied_cells(self) -> Generator[Tuple[int, int], None, None]:
        """Iterate over all occupied cells."""
        ys, xs = np.where(self._grid == CellState.OCCUPIED.value)
        for y, x in zip(ys, xs):
            yield (int(x), int(y))

    def free_cells(self) -> Generator[Tuple[int, int], None, None]:
        """Iterate over all free cells."""
        ys, xs = np.where(self._grid == CellState.FREE.value)
        for y, x in zip(ys, xs):
            yield (int(x), int(y))

    def unknown_cells(self) -> Generator[Tuple[int, int], None, None]:
        """Iterate over all unknown cells."""
        ys, xs = np.where(self._grid == CellState.UNKNOWN.value)
        for y, x in zip(ys, xs):
            yield (int(x), int(y))

    def explored_count(self) -> int:
        """Number of cells that are not UNKNOWN."""
        return int(np.count_nonzero(self._grid != CellState.UNKNOWN.value))

    def explored_percentage(self) -> float:
        """Percentage of grid that has been explored."""
        total = self.width * self.height
        return (self.explored_count() / total) * 100.0 if total else 0.0

    def obstacle_count(self) -> int:
        """Number of occupied cells."""
        return int(np.count_nonzero(self._grid == CellState.OCCUPIED.value))

    def collision_check(
        self,
        x: float,
        y: float,
        margin: int = 0,
    ) -> bool:
        """
        Check if a point collides with any occupied cell.

        Args:
            x, y: World coordinates.
            margin: Additional cells to check around the point.

        Returns:
            True if collision detected.
        """
        gx, gy = int(x), int(y)
        for dy in range(-margin, margin + 1):
            for dx in range(-margin, margin + 1):
                if self.is_occupied(gx + dx, gy + dy):
                    return True
        return False

    def nearest_free_cell(
        self,
        x: int,
        y: int,
        max_radius: int = 50,
    ) -> Optional[Tuple[int, int]]:
        """Find nearest free cell to (x, y) within max_radius."""
        for r in range(1, max_radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if abs(dx) == r or abs(dy) == r:
                        nx, ny = x + dx, y + dy
                        if self.in_bounds(nx, ny) and self.is_free(nx, ny):
                            return (nx, ny)
        return None

    # ── I/O ──────────────────────────────────────────────────────────

    def to_numpy(self) -> np.ndarray:
        """Return a copy of the underlying grid as a numpy array."""
        return self._grid.copy()

    def from_numpy(self, grid: np.ndarray) -> None:
        """Load grid data from a numpy array."""
        if grid.shape == (self.height, self.width):
            self._grid = grid.astype(np.int8)

    def reset(self) -> None:
        """Reset all cells to UNKNOWN."""
        self._grid.fill(CellState.UNKNOWN.value)

    def copy(self) -> GridMap:
        """Create an independent copy."""
        new = GridMap(self.config)
        new._grid = self._grid.copy()
        return new