class PIDController:

    def __init__(

        self,

        kp=1.5,

        ki=0.01,

        kd=0.3

    ):

        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.integral = 0.0
        self.previous_error = 0.0

    def reset(self):

        self.integral = 0.0
        self.previous_error = 0.0

    def update(

        self,

        error,

        dt=1.0

    ):

        self.integral += (
            error * dt
        )

        self.integral = max(
            -100,
            min(
                100,
                self.integral
            )
        )

        derivative = (

            error
            -
            self.previous_error

        ) / dt

        output = (

            self.kp * error

            +

            self.ki * self.integral

            +

            self.kd * derivative

        )

        self.previous_error = (
            error
        )

        return output