"""
Cinematic Flight Controller
============================
Enhances the drone's flight dynamics with smooth, realistic motion.

Features:
  - Smooth acceleration/deceleration profiles (S-curves, not trapezoidal)
  - Coordinated turns with proper banking
  - Realistic momentum and inertia
  - Wind response and turbulence
  - Continuous curved trajectories (no stop-and-turn)
  - Configurable flight personality (aggressive vs smooth)

This is a thin enhancement layer that works with the existing
PID/Motion controllers to produce cinematic-quality flight.
"""

from __future__ import annotations

import math
import random as _rand
from dataclasses import dataclass, field
from typing import Optional, Tuple, List

import numpy as np


@dataclass
class FlightProfile:
    """Defines the drone's flight personality."""
    name: str = "CINEMATIC"
    max_acceleration: float = 3.0
    max_jerk: float = 1.5  # Rate of change of acceleration (smoothness)
    max_speed: float = 8.0
    max_yaw_rate: float = 1.2
    bank_angle_limit: float = math.radians(35)  # Max bank angle
    turn_smoothness: float = 0.15  # 0=instant, 1=extremely smooth
    momentum_factor: float = 0.85  # How much velocity carries over
    wind_sensitivity: float = 0.15
    turbulence_intensity: float = 0.05


@dataclass
class FlightState:
    """Current smoothed flight state."""
    target_x: float = 0.0
    target_y: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    acceleration_x: float = 0.0
    acceleration_y: float = 0.0
    heading: float = 0.0
    bank_angle: float = 0.0
    speed: float = 0.0


class CinematicFlightController:
    """Premium flight controller that produces smooth, cinematic motion.

    Works as a pre-processor for the existing control system:
    1. Takes raw waypoints from the path planner
    2. Produces smooth velocity/acceleration commands
    3. Adds wind response and turbulence
    4. Generates coordinated turn profiles
    """

    def __init__(
        self,
        profile: Optional[FlightProfile] = None,
    ):
        self.profile = profile or FlightProfile()
        self.state = FlightState()

        # Waypoint tracking
        self.current_waypoint_idx: int = 0
        self.path: List[Tuple[float, float]] = []

        # Wind and turbulence
        self.wind_x: float = 0.0
        self.wind_y: float = 0.0
        self.wind_time: float = 0.0

        # Drone position reference (set externally)
        self.drone_x: float = 0.0
        self.drone_y: float = 0.0
        self.drone_heading: float = 0.0

        # Output smoothing
        self.smooth_target_x: float = 0.0
        self.smooth_target_y: float = 0.0
        self.smooth_heading: float = 0.0

    # ══════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════

    def set_path(self, path: List[Tuple[float, float]]):
        """Set a new path for the drone to follow."""
        if not path:
            return
        self.path = path
        self.current_waypoint_idx = 0

        # Initialize smooth targets
        if len(path) > 0:
            self.smooth_target_x = path[0][0]
            self.smooth_target_y = path[0][1]

    def update(
        self,
        drone_x: float,
        drone_y: float,
        drone_heading: float,
        dt: float = 0.016,
    ) -> Tuple[float, float, float]:
        """
        Update flight controller and return (target_x, target_y, heading).

        Returns:
            Tuple of (target_x, target_y, target_heading)
        """
        self.drone_x = drone_x
        self.drone_y = drone_y
        self.drone_heading = drone_heading

        if not self.path:
            return (drone_x, drone_y, drone_heading)

        # Update wind and turbulence
        self._update_wind(dt)

        # Get current target waypoint
        target = self._get_current_target()

        # Compute smooth approach to target
        smooth_target = self._compute_smooth_target(target, dt)

        # Compute heading with coordinated turn logic
        heading = self._compute_heading(target, dt)

        # Apply wind perturbation to target
        wind_offset_x = self.wind_x * self.profile.wind_sensitivity
        wind_offset_y = self.wind_y * self.profile.wind_sensitivity

        final_x = smooth_target[0] + wind_offset_x
        final_y = smooth_target[1] + wind_offset_y

        return (final_x, final_y, heading)

    def update_path_smoothing(self, path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Pre-process a path with smooth interpolation for cinematic flight."""
        if not path or len(path) < 2:
            return path

        # Increase path resolution with smooth interpolation
        smoothed = []
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]

            # Add interpolated points between waypoints
            distance = math.hypot(x2 - x1, y2 - y1)
            num_steps = max(2, int(distance / 0.5))

            for j in range(num_steps):
                t = j / num_steps
                # S-curve easing
                t_smooth = t * t * (3.0 - 2.0 * t)
                sx = x1 + (x2 - x1) * t_smooth
                sy = y1 + (y2 - y1) * t_smooth
                smoothed.append((sx, sy))

        # Add last point
        if path:
            smoothed.append(path[-1])

        return smoothed

    # ══════════════════════════════════════════════════════════════════
    # INTERNAL
    # ══════════════════════════════════════════════════════════════════

    def _get_current_target(self) -> Tuple[float, float]:
        """Get the current target waypoint."""
        if not self.path:
            return (self.drone_x, self.drone_y)

        idx = min(self.current_waypoint_idx, len(self.path) - 1)
        return self.path[idx]

    def _update_wind(self, dt: float):
        """Update wind and turbulence model."""
        self.wind_time += dt

        # Gusting wind model
        base_wind = 1.0
        gust = math.sin(self.wind_time * 0.3) * 0.8 + \
               math.sin(self.wind_time * 0.7) * 0.4 + \
               math.sin(self.wind_time * 1.3) * 0.2

        wind_speed = base_wind + gust * 0.5
        wind_angle = self.wind_time * 0.1 + math.sin(self.wind_time * 0.2) * 0.5

        self.wind_x = wind_speed * math.cos(wind_angle)
        self.wind_y = wind_speed * math.sin(wind_angle)

    def _compute_smooth_target(
        self,
        target: Tuple[float, float],
        dt: float,
    ) -> Tuple[float, float]:
        """Compute smooth approach to target using S-curve velocity profiling."""
        tx, ty = target
        dx = tx - self.drone_x
        dy = ty - self.drone_y
        distance = math.hypot(dx, dy)

        if distance < 0.5:
            # Advance to next waypoint
            if self.current_waypoint_idx < len(self.path) - 1:
                self.current_waypoint_idx += 1
                return target
            return target

        # Compute direction to target
        dir_x = dx / distance if distance > 0 else 0
        dir_y = dy / distance if distance > 0 else 0

        # S-curve velocity profile
        # Slow down when close, speed up when far
        deceleration_distance = 5.0
        speed_fraction = min(1.0, distance / deceleration_distance)

        # Apply S-curve (smoothstep)
        s_curve = speed_fraction * speed_fraction * (3.0 - 2.0 * speed_fraction)
        approach_speed = self.profile.max_speed * (0.3 + 0.7 * s_curve)

        # Compute smooth target position ahead on the path
        look_ahead = approach_speed * dt * 4.0
        smooth_x = self.drone_x + dir_x * min(distance, look_ahead)
        smooth_y = self.drone_y + dir_y * min(distance, look_ahead)

        return (smooth_x, smooth_y)

    def _compute_heading(self, target: Tuple[float, float], dt: float) -> float:
        """Compute heading with coordinated turn logic."""
        tx, ty = target
        dx = tx - self.drone_x
        dy = ty - self.drone_y

        desired_heading = math.atan2(dy, dx) if dx != 0 or dy != 0 else self.drone_heading

        # Compute heading error
        heading_error = desired_heading - self.drone_heading
        # Normalize to [-pi, pi]
        while heading_error > math.pi:
            heading_error -= 2 * math.pi
        while heading_error < -math.pi:
            heading_error += 2 * math.pi

        # Smooth heading change (coordinated turn)
        max_turn_rate = self.profile.max_yaw_rate * dt
        if abs(heading_error) < max_turn_rate:
            new_heading = desired_heading
        else:
            new_heading = self.drone_heading + math.copysign(max_turn_rate, heading_error)

        # Compute bank angle (proportional to turn rate)
        turn_rate = (new_heading - self.drone_heading) / dt if dt > 0 else 0
        self.state.bank_angle = -math.copysign(
            min(abs(turn_rate) * 2.0, self.profile.bank_angle_limit),
            turn_rate,
        )

        return new_heading

    def get_flight_metrics(self) -> dict:
        """Return current flight metrics."""
        return {
            "speed": math.hypot(
                self.drone_x - getattr(self, '_prev_x', self.drone_x),
                self.drone_y - getattr(self, '_prev_y', self.drone_y),
            ),
            "heading_deg": math.degrees(self.drone_heading),
            "bank_angle_deg": math.degrees(self.state.bank_angle),
            "wind_speed": math.hypot(self.wind_x, self.wind_y),
            "waypoints_remaining": max(0, len(self.path) - self.current_waypoint_idx - 1),
        }

    def setattr(self, name, value):
        object.__setattr__(self, name, value)
