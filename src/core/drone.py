"""
High-Performance Drone Model
=============================
Extended drone with velocity, acceleration, jerk, yaw rate, and flight mode support.
Designed for high-speed autonomous flight.
"""

from __future__ import annotations
import math
from enum import Enum
from typing import Optional, Tuple


class FlightMode(Enum):
    """Flight modes with increasing performance profiles."""
    ECO = "ECO"
    NORMAL = "NORMAL"
    CRUISE = "CRUISE"
    SPORT = "SPORT"
    TURBO = "TURBO"
    EMERGENCY = "EMERGENCY"
    PRECISION = "PRECISION"
    LANDING = "LANDING"


@staticmethod
def default_mode_params(mode: FlightMode) -> dict:
    """Return default performance parameters for each flight mode."""
    params = {
        FlightMode.ECO: {
            "max_speed": 3.0,
            "max_acceleration": 1.0,
            "max_yaw_rate": 1.0,
            "max_jerk": 0.5,
            "min_obstacle_clearance": 5.0,
            "planning_frequency": 5.0,
            "energy_usage": 0.3,
        },
        FlightMode.NORMAL: {
            "max_speed": 5.0,
            "max_acceleration": 2.0,
            "max_yaw_rate": 1.5,
            "max_jerk": 1.0,
            "min_obstacle_clearance": 4.0,
            "planning_frequency": 5.0,
            "energy_usage": 0.5,
        },
        FlightMode.CRUISE: {
            "max_speed": 8.0,
            "max_acceleration": 3.0,
            "max_yaw_rate": 2.0,
            "max_jerk": 1.5,
            "min_obstacle_clearance": 3.0,
            "planning_frequency": 10.0,
            "energy_usage": 0.6,
        },
        FlightMode.SPORT: {
            "max_speed": 12.0,
            "max_acceleration": 5.0,
            "max_yaw_rate": 3.0,
            "max_jerk": 2.5,
            "min_obstacle_clearance": 2.5,
            "planning_frequency": 15.0,
            "energy_usage": 0.75,
        },
        FlightMode.TURBO: {
            "max_speed": 20.0,
            "max_acceleration": 8.0,
            "max_yaw_rate": 4.0,
            "max_jerk": 4.0,
            "min_obstacle_clearance": 2.0,
            "planning_frequency": 20.0,
            "energy_usage": 0.95,
        },
        FlightMode.EMERGENCY: {
            "max_speed": 15.0,
            "max_acceleration": 10.0,
            "max_yaw_rate": 5.0,
            "max_jerk": 6.0,
            "min_obstacle_clearance": 1.5,
            "planning_frequency": 25.0,
            "energy_usage": 1.0,
        },
        FlightMode.PRECISION: {
            "max_speed": 3.0,
            "max_acceleration": 1.5,
            "max_yaw_rate": 0.8,
            "max_jerk": 0.5,
            "min_obstacle_clearance": 5.0,
            "planning_frequency": 5.0,
            "energy_usage": 0.4,
        },
        FlightMode.LANDING: {
            "max_speed": 1.0,
            "max_acceleration": 0.5,
            "max_yaw_rate": 0.5,
            "max_jerk": 0.3,
            "min_obstacle_clearance": 8.0,
            "planning_frequency": 5.0,
            "energy_usage": 0.2,
        },
    }
    return params.get(mode, params[FlightMode.NORMAL]).copy()


class Drone:
    """
    High-performance drone model with continuous dynamics.
    Tracks position, velocity, acceleration, jerk, yaw, and yaw rate.
    Supports dynamic flight mode switching for optimal mission performance.
    """

    def __init__(
        self,
        start_position: Tuple[float, float],
        flight_mode: FlightMode = FlightMode.NORMAL
    ):
        # Position (continuous)
        self.x = float(start_position[0])
        self.y = float(start_position[1])

        # Velocity (m/s)
        self.vx = 0.0
        self.vy = 0.0

        # Acceleration (m/s^2)
        self.ax = 0.0
        self.ay = 0.0

        # Jerk (m/s^3)
        self.jx = 0.0
        self.jy = 0.0

        # Heading (radians) - continuous
        self.heading = 0.0

        # Yaw rate (rad/s)
        self.yaw_rate = 0.0

        # Speed magnitude
        self.speed = 0.0

        # Flight mode
        self._flight_mode = flight_mode
        self._mode_params = default_mode_params(flight_mode)

        # Previous values for smooth transitions
        self._prev_speed = 0.0

    @property
    def flight_mode(self) -> FlightMode:
        return self._flight_mode

    @flight_mode.setter
    def flight_mode(self, mode: FlightMode) -> None:
        """Switch flight mode and update performance parameters."""
        self._flight_mode = mode
        self._mode_params = default_mode_params(mode)

    @property
    def mode_params(self) -> dict:
        return self._mode_params

    @property
    def position(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @position.setter
    def position(self, pos: Tuple[float, float]) -> None:
        self.x = float(pos[0])
        self.y = float(pos[1])

    @property
    def velocity(self) -> Tuple[float, float]:
        return (self.vx, self.vy)

    @property
    def velocity_magnitude(self) -> float:
        return math.sqrt(self.vx * self.vx + self.vy * self.vy)

    @property
    def acceleration_magnitude(self) -> float:
        return math.sqrt(self.ax * self.ax + self.ay * self.ay)

    @property
    def jerk_magnitude(self) -> float:
        return math.sqrt(self.jx * self.jx + self.jy * self.jy)

    @property
    def max_speed(self) -> float:
        return self._mode_params["max_speed"]

    @property
    def max_acceleration(self) -> float:
        return self._mode_params["max_acceleration"]

    @property
    def max_yaw_rate(self) -> float:
        return self._mode_params["max_yaw_rate"]

    @property
    def max_jerk(self) -> float:
        return self._mode_params["max_jerk"]

    @property
    def min_obstacle_clearance(self) -> float:
        return self._mode_params["min_obstacle_clearance"]

    def set_max_speed(self, speed: float) -> None:
        """Dynamically override max speed (clamped to mode maximum)."""
        self._mode_params["max_speed"] = min(speed, self._mode_params["max_speed"])

    def reset_max_speed(self) -> None:
        """Reset max speed to mode default."""
        self._mode_params["max_speed"] = default_mode_params(self._flight_mode)["max_speed"]

    def update_dynamics(self, dt: float = 1.0) -> None:
        """
        Advance drone dynamics by dt seconds.
        Applies velocity, acceleration limits smoothly.
        """
        # Clamp acceleration
        accel = math.sqrt(self.ax * self.ax + self.ay * self.ay)
        max_accel = self.max_acceleration
        if accel > max_accel and max_accel > 0:
            scale = max_accel / accel
            self.ax *= scale
            self.ay *= scale

        # Update velocity
        self.vx += self.ax * dt
        self.vy += self.ay * dt

        # Clamp speed
        speed = math.sqrt(self.vx * self.vx + self.vy * self.vy)
        max_spd = self.max_speed
        if speed > max_spd and max_spd > 0:
            scale = max_spd / speed
            self.vx *= scale
            self.vy *= scale
            speed = max_spd

        self.speed = speed

        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Update heading from velocity direction
        if speed > 0.01:
            target_heading = math.atan2(self.vy, self.vx)
            # Smooth heading change
            heading_diff = target_heading - self.heading
            while heading_diff > math.pi:
                heading_diff -= 2 * math.pi
            while heading_diff < -math.pi:
                heading_diff += 2 * math.pi

            max_yaw_step = self.max_yaw_rate * dt
            heading_diff = max(-max_yaw_step, min(max_yaw_step, heading_diff))
            self.heading += heading_diff
            self.yaw_rate = heading_diff / dt if dt > 0 else 0.0
        else:
            self.yaw_rate = 0.0

        # Wrap heading
        while self.heading > math.pi:
            self.heading -= 2 * math.pi
        while self.heading < -math.pi:
            self.heading += 2 * math.pi

        self._prev_speed = speed

    def set_velocity_target(self, target_vx: float, target_vy: float, dt: float = 1.0) -> None:
        """
        Set velocity target with acceleration-limited ramping.
        dt should match the loop update rate (e.g., 0.01 for 100Hz).
        """
        max_accel = self.max_acceleration  # max acceleration per second

        # Compute desired acceleration (per second)
        desired_ax = (target_vx - self.vx) / max(dt, 0.001)
        desired_ay = (target_vy - self.vy) / max(dt, 0.001)

        # Clamp acceleration to mode limit
        desired_accel = math.sqrt(desired_ax * desired_ax + desired_ay * desired_ay)
        if desired_accel > max_accel and max_accel > 0:
            scale = max_accel / desired_accel
            desired_ax *= scale
            desired_ay *= scale

        self.ax = desired_ax
        self.ay = desired_ay

    def apply_brakes(self, dt: float = 1.0) -> None:
        """Apply maximum deceleration to stop."""
        speed = self.velocity_magnitude
        if speed < 0.01:
            self.vx = 0.0
            self.vy = 0.0
            self.ax = 0.0
            self.ay = 0.0
            return

        decel = min(self.max_acceleration, speed / dt)
        scale = decel / speed if speed > 0 else 0.0
        self.ax = -self.vx * scale
        self.ay = -self.vy * scale

    def reset(self) -> None:
        """Reset all dynamics."""
        self.vx = 0.0
        self.vy = 0.0
        self.ax = 0.0
        self.ay = 0.0
        self.jx = 0.0
        self.jy = 0.0
        self.heading = 0.0
        self.yaw_rate = 0.0
        self.speed = 0.0
        self._prev_speed = 0.0

    def distance_to(self, target: Tuple[float, float]) -> float:
        """Euclidean distance to target."""
        dx = target[0] - self.x
        dy = target[1] - self.y
        return math.sqrt(dx * dx + dy * dy)

    def heading_to(self, target: Tuple[float, float]) -> float:
        """Heading towards target."""
        return math.atan2(target[1] - self.y, target[0] - self.x)

    def is_at_position(self, target: Tuple[float, float], tolerance: float = 0.5) -> bool:
        """Check if drone is within tolerance of target."""
        return self.distance_to(target) <= tolerance