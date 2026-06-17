import random


class IMUSensor:

    def __init__(self):

        self.drift_x = 0

        self.drift_y = 0

    def read(
        self,
        dx,
        dy
    ):

        self.drift_x += random.gauss(
            0,
            0.01
        )

        self.drift_y += random.gauss(
            0,
            0.01
        )

        measured_dx = (

            dx
            +
            self.drift_x

        )

        measured_dy = (

            dy
            +
            self.drift_y

        )

        return (
            measured_dx,
            measured_dy
        )