import numpy as np


class CostMap:

    def __init__(
        self,
        width,
        height
    ):

        self.width = width
        self.height = height

        self.grid = np.ones(
            (
                height,
                width
            ),
            dtype=float
        )
        # Anti-oscillation: last position penalty
        self.last_position = None
        self.last_position_penalty = 20.0

        # Learned predictor component weight
        self.learned_weight = 6.0

    def update(
        self,
        perception_map,
        memory_map,
        context_map,
        risk_map,
        trajectory_map,
        last_position=None,
        learned_predictor=None,
    ):

        self.grid = (

            1.0

            +

            5.0 * perception_map.grid

            +

            3.0 * memory_map.grid

            +

            8.0 * risk_map.grid

            +

            10.0 * trajectory_map.grid

            -

            2.0 * context_map.grid

        )

        # Incorporate learned attention-based risk predictions
        if learned_predictor is not None and hasattr(learned_predictor, 'grid'):
            self.grid += self.learned_weight * learned_predictor.grid

        self.grid = np.clip(
            self.grid,
            0.1,
            100
        )

        # Apply anti-oscillation penalty to last position to avoid immediate returns
        self.last_position = last_position
        if last_position is not None:
            lx, ly = int(round(last_position[0])), int(round(last_position[1]))
            if (
                0 <= lx < self.width
                and
                0 <= ly < self.height
            ):
                self.grid[ly, lx] += self.last_position_penalty
                self.grid = np.clip(
                    self.grid,
                    0.1,
                    100
                )

        return self

    def get_cost(
        self,
        x,
        y
    ):

        ix = int(round(x))
        iy = int(round(y))
        return self.grid[
            iy,
            ix
        ]
