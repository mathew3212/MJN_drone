import numpy as np


class MemoryMap:

    def __init__(
        self,
        width,
        height
    ):

        self.width = width
        self.height = height

        self.grid = np.zeros(
            (
                height,
                width
            ),
            dtype=float
        )

        self.decay_rate = 0.995
        # Penalty added when a cell is visited to discourage revisits
        self.revisit_penalty = 0.5

    def update(
        self,
        visible_obstacles,
        visited_positions=None
    ):

        # Slowly forget old information

        self.grid *= self.decay_rate

        # Strengthen memory where obstacles are seen

        for ox, oy in visible_obstacles:

            if (
                0 <= ox < self.width
                and
                0 <= oy < self.height
            ):

                self.grid[
                    oy,
                    ox
                ] = 1.0

        # Apply revisit penalty for visited positions (increase memory value)
        if visited_positions:
            for vx, vy in visited_positions:
                if (
                    0 <= vx < self.width
                    and
                    0 <= vy < self.height
                ):
                    self.grid[vy, vx] += self.revisit_penalty
                    # Keep memory values bounded
                    self.grid[vy, vx] = min(1.0, self.grid[vy, vx])

        return self

    def get_value(
        self,
        x,
        y
    ):

        return self.grid[
            y,
            x
        ]