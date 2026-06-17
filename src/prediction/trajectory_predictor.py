import numpy as np


class TrajectoryPredictor:

    def __init__(
        self,
        width,
        height,
        prediction_horizon=15
    ):

        self.width = width
        self.height = height

        self.prediction_horizon = (
            prediction_horizon
        )

        self.grid = np.zeros(
            (
                height,
                width
            ),
            dtype=float
        )

        self.history = {}

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

            if idx not in self.history:

                self.history[idx] = []

            self.history[idx].append(
                current
            )

            if len(
                self.history[idx]
            ) > 5:

                self.history[idx].pop(0)

            self.predict(
                idx
            )

        return self

    def predict(
        self,
        obstacle_id
    ):

        history = (
            self.history[
                obstacle_id
            ]
        )

        if len(history) < 2:
            return

        x1, y1 = history[-2]
        x2, y2 = history[-1]

        vx = x2 - x1
        vy = y2 - y1

        px = x2
        py = y2

        for step in range(
            1,
            self.prediction_horizon + 1
        ):

            px += vx
            py += vy

            if not (
                0 <= px < self.width
                and
                0 <= py < self.height
            ):
                break

            risk = (
                self.prediction_horizon
                - step + 1
            ) / self.prediction_horizon

            self.grid[
                int(py)
            ][
                int(px)
            ] += risk

    def get_risk(
        self,
        x,
        y
    ):

        return self.grid[
            y
        ][
            x
        ]