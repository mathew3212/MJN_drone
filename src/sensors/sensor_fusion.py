class SensorFusion:

    def __init__(self):

        self.x = 0

        self.y = 0

    def update(

        self,

        gps_x,
        gps_y,

        imu_dx,
        imu_dy

    ):

        imu_x = (
            self.x
            +
            imu_dx
        )

        imu_y = (
            self.y
            +
            imu_dy
        )

        self.x = (

            0.7 * gps_x

            +

            0.3 * imu_x

        )

        self.y = (

            0.7 * gps_y

            +

            0.3 * imu_y

        )

        return (
            self.x,
            self.y
        )