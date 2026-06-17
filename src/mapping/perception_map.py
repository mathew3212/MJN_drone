import math
import numpy as np


class PerceptionMap:

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

    def update(
        self,
        visible_obstacles
    ):

        self.grid.fill(0)

        influence_radius = 10

        for ox, oy in visible_obstacles:

            for y in range(self.height):

                for x in range(self.width):

                    distance = math.sqrt(
                        (x - ox) ** 2
                        +
                        (y - oy) ** 2
                    )

                    risk = max(
                        0,
                        1 - distance / influence_radius
                    )

                    self.grid[y][x] += risk

        max_value = np.max(self.grid)

        if max_value > 0:

            self.grid /= max_value

        return self

    def get_value(
        self,
        x,
        y
    ):

        return self.grid[y][x]