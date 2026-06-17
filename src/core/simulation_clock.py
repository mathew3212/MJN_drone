"""
SimulationClock
===============
Fixed-timestep clock for deterministic simulation execution.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class SimulationClock:
    """
    Provides fixed-timestep simulation timing with real-time synchronization.

    Attributes:
        dt: Fixed time step in seconds (default 0.1).
        time: Current simulation time.
        step: Current simulation step count.
        realtime_factor: How fast simulation runs vs real time (1.0 = realtime).
    """
    dt: float = 0.1
    time: float = 0.0
    step: int = 0
    realtime_factor: float = 1.0
    _last_wall_time: float = 0.0
    _running: bool = False

    def start(self) -> None:
        """Start the clock."""
        self._running = True
        self._last_wall_time = time.perf_counter()

    def tick(self) -> float:
        """
        Advance one simulation step. Sleeps to maintain realtime factor.

        Returns:
            The simulation dt for this step.
        """
        if not self._running:
            self.start()

        # Sleep to maintain realtime factor
        if self.realtime_factor > 0:
            expected_wall_dt = self.dt / self.realtime_factor
            elapsed = time.perf_counter() - self._last_wall_time
            sleep_time = expected_wall_dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.time += self.dt
        self.step += 1
        self._last_wall_time = time.perf_counter()
        return self.dt

    def reset(self) -> None:
        """Reset the clock to initial state."""
        self.time = 0.0
        self.step = 0
        self._running = False

    def get_fps(self) -> float:
        """Calculate current simulation steps per second."""
        return 1.0 / self.dt if self.dt > 0 else 0.0

    def get_wall_time(self) -> float:
        """Get wall clock time since start."""
        if self._running:
            return time.perf_counter() - self._last_wall_time
        return 0.0