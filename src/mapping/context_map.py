import math
import numpy as np


class ContextMap:

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
        target
    ):

        tx, ty = target

        max_distance = math.sqrt(

            self.width ** 2
            +
            self.height ** 2

        )

        for y in range(self.height):

            for x in range(self.width):

                distance = math.sqrt(

                    (x - tx) ** 2
                    +
                    (y - ty) ** 2

                )

                value = (

                    1.0
                    -
                    (
                        distance
                        /
                        max_distance
                    )

                )

                self.grid[y][x] = value

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