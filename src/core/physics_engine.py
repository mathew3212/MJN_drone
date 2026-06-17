"""
Advanced Physics Engine for Realistic Drone Flight
====================================================
Simulates physically believable flight with:

  - Aerodynamic drag and lift
  - Turbulence and wind disturbance
  - Propeller thrust modeling
  - Inertia and momentum
  - Ground effect (near surface)
  - Payload influence
  - Battery weight degradation
  - Motor efficiency

All forces are computed in 2D with altitude approximation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass
class DronePhysicsState:
    """Complete physical state of the drone."""
    # Position
    x: float = 0.0
    y: float = 0.0
    altitude: float = 0.0

    # Velocity
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0  # vertical speed

    # Acceleration
    ax: float = 0.0
    ay: float = 0.0
    az: float = 0.0

    # Orientation
    pitch: float = 0.0  # radians (forward tilt)
    roll: float = 0.0   # radians (bank angle)
    yaw: float = 0.0    # radians (heading)

    # Angular velocities
    pitch_rate: float = 0.0
    roll_rate: float = 0.0
    yaw_rate: float = 0.0

    # Forces
    thrust: float = 0.0
    drag_force: float = 0.0
    lift_force: float = 0.0
    gravity_force: float = 0.0
    wind_force_x: float = 0.0
    wind_force_y: float = 0.0

    # Physical properties
    total_mass: float = 1.5  # kg (drone + battery + payload)
    battery_mass: float = 0.4  # kg
    propeller_rpm: float = 0.0
    motor_efficiency: float = 0.85


class PhysicsEngine:
    """
    Realistic physics engine for drone flight simulation.

    Computes aerodynamic forces, motor thrust, drag, turbulence,
    and ground effects to produce physically believable motion.
    """

    def __init__(self):
        # Drone physical constants
        self.gravity = 9.81  # m/s^2
        self.air_density = 1.225  # kg/m^3 at sea level
        self.drag_coefficient = 0.3
        self.lift_coefficient = 0.8
        self.cross_section_area = 0.05  # m^2
        self.propeller_area = 0.02  # m^2 per propeller
        self.num_propellers = 4
        self.max_thrust = 20.0  # N (total)
        self.max_rpm = 12000.0

        # Ground effect parameters
        self.ground_effect_height = 3.0  # altitude where ground effect kicks in
        self.ground_effect_factor = 0.3  # 30% thrust reduction near ground

        # Payload
        self.payload_mass = 0.0  # kg

        # Wind
        self.wind_x = 0.0
        self.wind_y = 0.0
        self.turbulence_intensity = 0.0

        # State
        self.state = DronePhysicsState()
        self.dt = 1.0 / 60.0  # 60 Hz physics

    def update(
        self,
        command_x: float,  # commanded X position
        command_y: float,  # commanded Y position
        command_alt: float = 5.0,  # commanded altitude
        wind_x: float = 0.0,
        wind_y: float = 0.0,
        turbulence: float = 0.0,
        battery_pct: float = 100.0,
    ) -> DronePhysicsState:
        """
        Update physics one timestep.

        Returns the new physical state.
        """
        s = self.state
        dt = self.dt

        # ── 1. Compute thrust needed ──
        # Position error
        err_x = command_x - s.x
        err_y = command_y - s.y
        err_alt = command_alt - s.altitude

        # PID-like thrust command
        kp = 2.0
        kd = 0.5
        cmd_thrust_x = kp * err_x - kd * s.vx
        cmd_thrust_y = kp * err_y - kd * s.vy
        cmd_thrust_alt = kp * err_alt - kd * s.vz

        # Convert to total thrust
        total_thrust_cmd = math.sqrt(
            cmd_thrust_x**2 + cmd_thrust_y**2 + (cmd_thrust_alt + self.gravity)**2
        )
        total_thrust_cmd = max(0, min(self.max_thrust, total_thrust_cmd))

        # ── 2. Motor physics ──
        # Battery affects motor efficiency
        battery_factor = 0.5 + 0.5 * (battery_pct / 100.0)
        effective_thrust = total_thrust_cmd * battery_factor * s.motor_efficiency

        # Propeller RPM based on thrust
        s.propeller_rpm = (effective_thrust / self.max_thrust) * self.max_rpm
        s.thrust = effective_thrust

        # ── 3. Aerodynamic drag ──
        # Drag = 0.5 * rho * Cd * A * v^2
        speed = math.sqrt(s.vx**2 + s.vy**2)
        drag_magnitude = 0.5 * self.air_density * self.drag_coefficient * self.cross_section_area * speed**2
        if speed > 0.001:
            drag_x = -drag_magnitude * (s.vx / speed)
            drag_y = -drag_magnitude * (s.vy / speed)
        else:
            drag_x = 0
            drag_y = 0
        s.drag_force = drag_magnitude

        # ── 4. Wind forces ──
        relative_wind_x = wind_x - s.vx
        relative_wind_y = wind_y - s.vy
        wind_drag = 0.5 * self.air_density * 0.8 * self.cross_section_area * 2.0
        s.wind_force_x = wind_drag * relative_wind_x * 0.1
        s.wind_force_y = wind_drag * relative_wind_y * 0.1

        # Add turbulence
        if turbulence > 0:
            turb_x = np.random.normal(0, turbulence * 0.3)
            turb_y = np.random.normal(0, turbulence * 0.3)
            s.wind_force_x += turb_x
            s.wind_force_y += turb_y

        # ── 5. Gravity ──
        total_mass = s.total_mass + self.payload_mass + s.battery_mass * (battery_pct / 100.0)
        s.gravity_force = total_mass * self.gravity

        # ── 6. Lift (depends on thrust and ground effect) ──
        lift = s.thrust
        # Ground effect: more lift near ground
        if s.altitude < self.ground_effect_height and s.altitude > 0.01:
            ground_factor = 1.0 + self.ground_effect_factor * (1.0 - s.altitude / self.ground_effect_height)
            lift *= ground_factor
        s.lift_force = lift

        # ── 7. Compute net acceleration ──
        # Horizontal
        s.ax = (cmd_thrust_x * 0.5 + drag_x + s.wind_force_x) / total_mass
        s.ay = (cmd_thrust_y * 0.5 + drag_y + s.wind_force_y) / total_mass

        # Vertical
        s.az = (cmd_thrust_alt * 0.5 + (s.lift_force - s.gravity_force)) / total_mass

        # ── 8. Integrate velocity ──
        # Smooth acceleration (clamp to prevent jitter)
        max_accel = 5.0
        s.ax = max(-max_accel, min(max_accel, s.ax))
        s.ay = max(-max_accel, min(max_accel, s.ay))
        s.az = max(-max_accel, min(max_accel, s.az))

        s.vx += s.ax * dt
        s.vy += s.ay * dt
        s.vz += s.az * dt

        # Damping
        damping = 0.95
        s.vx *= damping
        s.vy *= damping
        s.vz *= damping

        # ── 9. Integrate position ──
        s.x += s.vx * dt
        s.y += s.vy * dt
        s.altitude += s.vz * dt

        # Ground collision
        if s.altitude < 0:
            s.altitude = 0
            s.vz = max(0, s.vz)  # bounce
            s.vx *= 0.8  # friction
            s.vy *= 0.8

        # ── 10. Compute heading and bank ──
        if speed > 0.1:
            target_yaw = math.atan2(s.vy, s.vx)
            # Smooth yaw transition
            yaw_diff = target_yaw - s.yaw
            while yaw_diff > math.pi:
                yaw_diff -= 2 * math.pi
            while yaw_diff < -math.pi:
                yaw_diff += 2 * math.pi
            s.yaw += yaw_diff * min(1.0, 3.0 * dt)

        # Bank angle from lateral acceleration
        target_roll = math.atan2(s.ay, max(0.1, self.gravity))
        s.roll += (target_roll - s.roll) * min(1.0, 5.0 * dt)

        # Pitch from forward acceleration
        target_pitch = math.atan2(s.ax, max(0.1, self.gravity))
        s.pitch += (target_pitch - s.pitch) * min(1.0, 5.0 * dt)

        # Speed
        s.speed = math.sqrt(s.vx**2 + s.vy**2 + s.vz**2)

        return s

    def get_heading(self) -> float:
        """Get current heading angle."""
        return self.state.yaw

    def get_speed(self) -> float:
        """Get current speed."""
        return self.state.speed

    def get_altitude(self) -> float:
        """Get current altitude."""
        return self.state.altitude

    def get_position(self) -> Tuple[float, float]:
        """Get current (x, y) position."""
        return (self.state.x, self.state.y)

    def set_position(self, x: float, y: float, altitude: float = 5.0):
        """Set position directly."""
        self.state.x = x
        self.state.y = y
        self.state.altitude = altitude

    def set_payload(self, mass: float):
        """Set payload mass in kg."""
        self.payload_mass = mass

    def get_energy_usage(self) -> float:
        """Estimate energy usage rate."""
        # Power ~ thrust * velocity + drag losses
        speed = self.state.speed
        return (self.state.thrust * speed * 0.1 + 
                self.state.thrust * self.state.thrust * 0.02 +
                self.state.motor_efficiency * 0.1)