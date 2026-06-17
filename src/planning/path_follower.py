import math

from src.control.pid_controller import (
    PIDController
)


class PathFollower:

    def __init__(
        self,
        waypoint_tolerance=6.0,
        max_speed=6.0,
        max_turn_rate=3.0,
        heading_pid=None
    ):

        self.waypoint_tolerance = (
            waypoint_tolerance
        )

        self.max_speed = max_speed

        self.max_turn_rate = (
            max_turn_rate
        )

        self.heading_pid = (
            heading_pid
            if heading_pid is not None
            else PIDController(
                kp=1.5,
                ki=0.01,
                kd=0.3
            )
        )

    def normalize_angle(
        self,
        angle
    ):

        while angle > math.pi:
            angle -= (
                2 * math.pi
            )

        while angle < -math.pi:
            angle += (
                2 * math.pi
            )

        return angle

    def follow(

        self,

        drone,

        target_waypoint

    ):

        tx, ty = target_waypoint

        dx = tx - drone.x

        dy = ty - drone.y

        distance = math.sqrt(
            dx * dx +
            dy * dy
        )

        print(
            "Distance:",
            round(distance, 2)
        )

        if (
            distance
            <=
            self.waypoint_tolerance
        ):

            drone.x = tx
            drone.y = ty

            return True

        desired_heading = (
            math.atan2(
                dy,
                dx
            )
        )

        heading_error = (
            self.normalize_angle(
                desired_heading
                -
                drone.heading
            )
        )

        heading_step = (

            self.heading_pid.update(
                heading_error
            )

        )

        heading_step = max(

            -self.max_turn_rate,

            min(
                self.max_turn_rate,
                heading_step
            )

        )

        drone.heading += (
            heading_step
        )

        speed = min(
            self.max_speed,
            distance * 0.8
        )

        drone.x += (
            math.cos(
                drone.heading
            )
            *
            speed
        )

        drone.y += (
            math.sin(
                drone.heading
            )
            *
            speed
        )

        return False