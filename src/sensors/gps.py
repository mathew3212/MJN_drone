import random


class GPSSensor:

    def __init__(
        self,
        noise_std=1.5
    ):

        self.noise_std = noise_std

    def read(
        self,
        true_x,
        true_y
    ):

        gps_x = (

            true_x

            +

            random.gauss(
                0,
                self.noise_std
            )

        )

        gps_y = (

            true_y

            +

            random.gauss(
                0,
                self.noise_std
            )

        )

        return (
            gps_x,
            gps_y
        )