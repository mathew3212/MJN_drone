"""
AirSim Physics Model
====================
Realistic physics simulation for drones, delegating to AirSim's
physics engine when available, and providing a fallback physics model
when AirSim is not connected (e.g., for testing).
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any

from src.airsim.airsim_config import AirSimPhysicsConfig

logger = logging.getLogger(__name__)


@dataclass
class ThrustVector:
    """Thrust components for multirotor rotors."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0  # vertical thrust (positive = up, NED negative)

    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)


@dataclass
class RotorState:
    """State of a single rotor."""

    index: int = 0
    speed: float = 0.0  # RPM
    thrust: float = 0.0  # Newtons
    torque: float = 0.0  # Nm
    is_active: bool = True


@dataclass
class PhysicsState:
    """Full physics state of the drone."""

    # Position (NED frame)
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Velocity (m/s, NED)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Acceleration (m/s^2, NED)
    acceleration: Tuple[float, float, float] = (0.0, 0.0, 9.81)
    # Euler angles (radians): roll, pitch, yaw
    orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Angular velocity (rad/s)
    angular_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def speed(self) -> float:
        """Total velocity magnitude."""
        vx, vy, vz = self.velocity
        return math.sqrt(vx ** 2 + vy ** 2 + vz ** 2)

    def heading(self) -> float:
        """Yaw angle in radians."""
        return self.orientation[2]


class AirSimPhysicsModel:
    """
    Physics model for drone simulation.

    When connected to AirSim, delegates to AirSim's physics.
    When disconnected, provides an independent physics simulation
    (Gravito-aerodynamic model for multirotor drones).
    """

    def __init__(self, config: AirSimPhysicsConfig) -> None:
        self.config = config
        self.state = PhysicsState()

        # Internal state for fallback physics
        self._position = [0.0, 0.0, 0.0]
        self._velocity = [0.0, 0.0, 0.0]
        self._orientation = [0.0, 0.0, 0.0]
        self._angular_velocity = [0.0, 0.0, 0.0]
        self._rotors = [
            RotorState(index=i) for i in range(config.rotor_count)
        ]

        # Force and torque accumulators
        self._force_total = [0.0, 0.0, 0.0]
        self._torque_total = [0.0, 0.0, 0.0]

        # Constants
        self._gravity = config.gravity
        self._air_density = config.air_density
        self._drag_coeff = config.drag_coefficient
        self._max_thrust = config.max_thrust
        self._max_torque = config.max_torque
        self._dt = config.sim_time_step

        # Drone mass (typical multirotor ~1.5 kg)
        self._mass = 1.5

        # Moment of inertia (simplified, kg*m^2)
        self._Ixx = 0.0192
        self._Iyy = 0.0192
        self._Izz = 0.0369

        # Rotor arm length (m) for torque calculation
        self._arm_length = 0.225

        # Rotor thrust and torque coefficients
        self._kt = 0.01  # Thrust coefficient
        self._kd = 0.001  # Drag coefficient

    # ── High-level interface ─────────────────────────────────────────

    def update(self, dt: Optional[float] = None) -> PhysicsState:
        """Advance the physics simulation by one time step.

        Args:
            dt: Time step in seconds.  Defaults to config value.

        Returns:
            Updated physics state.
        """
        if dt is not None:
            self._dt = dt

        self._integrate()
        self._update_state()
        return self.state

    def set_thrust(
        self,
        raw_thrust: Tuple[float, float, float],
    ) -> None:
        """Set the total thrust vector (body frame).

        Args:
            raw_thrust: (thrust_x, thrust_y, thrust_z) in N.
        """
        self._force_total = [raw_thrust[0], raw_thrust[1], raw_thrust[2]]

    def set_torque(
        self,
        raw_torque: Tuple[float, float, float],
    ) -> None:
        """Set the total torque vector (body frame).

        Args:
            raw_torque: (torque_x, torque_y, torque_z) in Nm.
        """
        self._torque_total = [raw_torque[0], raw_torque[1], raw_torque[2]]

    def set_rotor_speeds(
        self,
        rpms: List[float],
    ) -> None:
        """Set rotor speeds.  Each rotor speed is in RPM.

        Args:
            rpms: List of rotor speeds (one per rotor).
        """
        for i, rpm in enumerate(rpms):
            if i < len(self._rotors):
                self._rotors[i].speed = rpm

        # Compute thrust and torque per rotor
        for i, rotor in enumerate(self._rotors):
            rotor.thrust = self._kt * rpm ** 2
            rotor.torque = self._kd * rpm ** 2

    def apply_force(
        self,
        fx: float,
        fy: float,
        fz: float,
    ) -> None:
        """Apply an external force (NED frame)."""
        self._force_total[0] += fx
        self._force_total[1] += fy
        self._force_total[2] += fz

    def apply_torque(
        self,
        tx: float,
        ty: float,
        tz: float,
    ) -> None:
        """Apply an external torque (body frame)."""
        self._torque_total[0] += tx
        self._torque_total[1] += ty
        self._torque_total[2] += tz

    def reset(self) -> None:
        """Reset physics state to initial conditions."""
        self._position = [0.0, 0.0, 0.0]
        self._velocity = [0.0, 0.0, 0.0]
        self._orientation = [0.0, 0.0, 0.0]
        self._angular_velocity = [0.0, 0.0, 0.0]
        self._force_total = [0.0, 0.0, 0.0]
        self._torque_total = [0.0, 0.0, 0.0]
        for rotor in self._rotors:
            rotor.speed = 0.0
            rotor.thrust = 0.0
            rotor.torque = 0.0
        self._update_state()

    def set_position(
        self, x: float, y: float, z: float
    ) -> None:
        """Set the drone's position directly (useful for initialization)."""
        self._position = [x, y, z]
        self._update_state()

    def set_orientation(
        self, roll: float, pitch: float, yaw: float
    ) -> None:
        """Set the drone's orientation directly (radians)."""
        self._orientation = [roll, pitch, yaw]
        self._update_state()

    def get_state(self) -> Dict[str, Any]:
        """Return a dictionary of the physics state."""
        return {
            "position": {
                "x": self._position[0],
                "y": self._position[1],
                "z": self._position[2],
            },
            "velocity": {
                "vx": self._velocity[0],
                "vy": self._velocity[1],
                "vz": self._velocity[2],
            },
            "orientation": {
                "roll": self._orientation[0],
                "pitch": self._orientation[1],
                "yaw": self._orientation[2],
            },
            "angular_velocity": {
                "wx": self._angular_velocity[0],
                "wy": self._angular_velocity[1],
                "wz": self._angular_velocity[2],
            },
            "speed": self.state.speed(),
            "heading": self.state.heading(),
            "rotors": [
                {
                    "index": r.index,
                    "speed": r.speed,
                    "thrust": r.thrust,
                    "torque": r.torque,
                    "active": r.is_active,
                }
                for r in self._rotors
            ],
        }

    # ── Internal integration (fallback physics) ──────────────────────

    def _integrate(self) -> None:
        """Advance the physics state by one time step.

        Uses a simple Euler integration with:
        - Gravity
        - Aerodynamic drag
        - Ground collision
        - Rotor forces
        """
        dt = self._dt

        # Total force: gravity + applied forces + drag
        # NED frame: positive Z is downward, gravity is +Z
        fx = self._force_total[0]
        fy = self._force_total[1]
        fz = self._force_total[2] + self._mass * self._gravity

        # Aerodynamic drag (quadratic)
        speed = math.sqrt(
            self._velocity[0] ** 2
            + self._velocity[1] ** 2
            + self._velocity[2] ** 2
        )
        if speed > 0.01:
            drag_factor = (
                0.5 * self._air_density * self._drag_coeff * speed
            )
            fx -= drag_factor * self._velocity[0]
            fy -= drag_factor * self._velocity[1]
            fz -= drag_factor * self._velocity[2]

        # Acceleration
        ax = fx / self._mass
        ay = fy / self._mass
        az = fz / self._mass

        # Integrate velocity
        self._velocity[0] += ax * dt
        self._velocity[1] += ay * dt
        self._velocity[2] += az * dt

        # Integrate position
        self._position[0] += self._velocity[0] * dt
        self._position[1] += self._velocity[1] * dt
        self._position[2] += self._velocity[2] * dt

        # Ground collision (AirSim NED: z=0 is ground, negative is up)
        if self._position[2] > 0:
            self._position[2] = 0
            self._velocity[2] = min(0, self._velocity[2])

        # Angular dynamics
        torque = [0.0, 0.0, 0.0]
        for i in range(3):
            torque[i] = self._torque_total[i]
            torque[i] -= (
                self._angular_velocity[i] * 0.1
            )  # angular drag

        alpha_x = torque[0] / self._Ixx
        alpha_y = torque[1] / self._Iyy
        alpha_z = torque[2] / self._Izz

        self._angular_velocity[0] += alpha_x * dt
        self._angular_velocity[1] += alpha_y * dt
        self._angular_velocity[2] += alpha_z * dt

        self._orientation[0] += self._angular_velocity[0] * dt
        self._orientation[1] += self._angular_velocity[1] * dt
        self._orientation[2] += self._angular_velocity[2] * dt

        # Clamp orientation angles
        self._orientation[0] = self._clamp_angle(self._orientation[0])
        self._orientation[1] = self._clamp_angle(self._orientation[1])
        self._orientation[2] = self._clamp_angle(self._orientation[2])

        # Clear accumulators
        self._force_total = [0.0, 0.0, 0.0]
        self._torque_total = [0.0, 0.0, 0.0]

    def _update_state(self) -> None:
        """Sync internal state into the public PhysicsState."""
        self.state.position = (
            self._position[0],
            self._position[1],
            self._position[2],
        )
        self.state.velocity = (
            self._velocity[0],
            self._velocity[1],
            self._velocity[2],
        )
        self.state.acceleration = (
            self._force_total[0] / self._mass if self._mass else 0,
            self._force_total[1] / self._mass if self._mass else 0,
            self._force_total[2] / self._mass if self._mass else 0,
        )
        self.state.orientation = (
            self._orientation[0],
            self._orientation[1],
            self._orientation[2],
        )
        self.state.angular_velocity = (
            self._angular_velocity[0],
            self._angular_velocity[1],
            self._angular_velocity[2],
        )

    @staticmethod
    def _clamp_angle(angle: float) -> float:
        """Clamp the angle to [-pi, pi]."""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle

    # ── Aerodynamic helpers ──────────────────────────────────────────

    def compute_aerodynamic_force(
        self,
        speed: float,
        frontal_area: float = 0.01,
    ) -> float:
        """Compute aerodynamic drag force at the given speed.

        Args:
            speed: Airspeed (m/s).
            frontal_area: Cross-sectional area (m^2).

        Returns:
            Drag force magnitude in Newtons.
        """
        return (
            0.5
            * self._air_density
            * self._drag_coeff
            * frontal_area
            * speed ** 2
        )

    def compute_rotor_forces(self) -> Tuple[float, float, float, float]:
        """Compute total thrust, roll, pitch, and yaw torques from rotors.

        Returns:
            (thrust, roll_torque, pitch_torque, yaw_torque).
        """
        total_thrust = 0.0
        roll_torque = 0.0
        pitch_torque = 0.0
        yaw_torque = 0.0

        for rotor in self._rotors:
            total_thrust += rotor.thrust
            # Rotor positions (simplified cross-configuration)
            # Rotor 0: front-right (+x, +y)
            # Rotor 1: rear-left  (-x, -y)
            # Rotor 2: front-left (-x, +y)
            # Rotor 3: rear-right (+x, -y)
            cx = self._arm_length * math.cos(math.pi / 2 * rotor.index)
            cy = self._arm_length * math.sin(math.pi / 2 * rotor.index)
            roll_torque += cy * rotor.thrust
            pitch_torque += cx * rotor.thrust
            yaw_torque += (-1) ** rotor.index * rotor.torque

        return (total_thrust, roll_torque, pitch_torque, yaw_torque)

    # ── Wind simulation ──────────────────────────────────────────────

    def apply_wind(
        self,
        wind_speed: float,
        wind_direction: float,
        gust_factor: float = 0.0,
    ) -> None:
        """Apply wind force to the drone.

        Args:
            wind_speed: Wind speed in m/s.
            wind_direction: Wind direction in radians (from where it blows).
            gust_factor: Random gust amplitude factor (0-1).
        """
        import random

        base_fx = wind_speed * math.cos(wind_direction)
        base_fy = wind_speed * math.sin(wind_direction)

        if gust_factor > 0:
            base_fx *= 1.0 + random.uniform(-gust_factor, gust_factor)
            base_fy *= 1.0 + random.uniform(-gust_factor, gust_factor)

        drag_force = 0.5 * self._air_density * 0.3 * wind_speed ** 2 * 0.01
        self.apply_force(
            base_fx * drag_force,
            base_fy * drag_force,
            0.0,
        )

    # ── Ground effect ───────────────────────────────────────────────

    def get_ground_effect(self) -> float:
        """Compute ground effect multiplier based on height.

        Ground effect occurs when the drone is within 1m of the ground,
        providing additional lift efficiency.
        """
        height = abs(self._position[2])
        if height < 1.0:
            # Factor approaches 1.5 at ground level
            return 1.0 + 0.5 * (1.0 - height)
        return 1.0