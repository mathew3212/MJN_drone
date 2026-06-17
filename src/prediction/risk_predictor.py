import numpy as np


class RiskPredictor:

    def __init__(
        self,
        width,
        height,
        prediction_steps=10
    ):

        self.width = width
        self.height = height

        self.prediction_steps = prediction_steps

        self.grid = np.zeros(
            (
                height,
                width
            ),
            dtype=float
        )

        self.previous_positions = {}

    def update(
        self,
        dynamic_obstacles
    ):

        self.grid.fill(0)

        for idx, obstacle in enumerate(
            dynamic_obstacles
        ):

            current = (
                obstacle.x,
                obstacle.y
            )

            if idx in self.previous_positions:

                prev_x, prev_y = (
                    self.previous_positions[idx]
                )

                vx = (
                    current[0]
                    - prev_x
                )

                vy = (
                    current[1]
                    - prev_y
                )

            else:

                vx = 0
                vy = 0

            self.previous_positions[
                idx
            ] = current

            self._predict_future(
                current,
                vx,
                vy
            )

        return self

    def _predict_future(
        self,
        current,
        vx,
        vy
    ):

        x, y = current

        for step in range(
            1,
            self.prediction_steps + 1
        ):

            px = int(
                x + vx * step
            )

            py = int(
                y + vy * step
            )

            if (
                0 <= px < self.width
                and
                0 <= py < self.height
            ):

                risk = (
                    self.prediction_steps
                    - step
                    + 1
                ) / self.prediction_steps

                self.grid[
                    py,
                    px
                ] += risk

    def get_risk(
        self,
        x,
        y
    ):

        return self.grid[
            y,
            x
        ]