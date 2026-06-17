import numpy as np


class PathSmoother:

    def __init__(
        self,
        interpolation_points=10
    ):

        self.interpolation_points = (
            interpolation_points
        )

    def smooth(
        self,
        path
    ):

        if path is None:

            return None

        if len(path) < 3:

            return path

        smoothed = []

        for i in range(
            len(path) - 1
        ):

            x1, y1 = path[i]
            x2, y2 = path[i + 1]

            for t in np.linspace(
                0,
                1,
                self.interpolation_points,
                endpoint=False
            ):

                x = (
                    x1
                    +
                    (x2 - x1) * t
                )

                y = (
                    y1
                    +
                    (y2 - y1) * t
                )

                smoothed.append(
                    (
                        float(x),
                        float(y)
                    )
                )

        smoothed.append(
            path[-1]
        )

        return smoothed