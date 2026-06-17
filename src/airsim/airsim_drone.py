"""
AirSim Drone
=============
3D drone class that wraps the AirSim multirotor API.
Provides realistic physics-based movement, takeoff, landing,
and path following in a 3D environment.
"""

from __future__ import annotations

import math
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Tuple, Dict, Any

from src.airsim.airsim_config import AirSimConfig, AirSimDroneConfig

logger = logging.getLogger(__name__)

# Attempt to import airsim; provide a graceful fallback when unavailable.
try:
    import airsim
    import airsim.types as airsim_types

    AIRSIM_AVAILABLE = True
except ImportError:
    airsim = None  # type: ignore[assignment]
    airsim_types = None  # type: ignore[assignment]
    AIRSIM_AVAILABLE = False
    logger.warning(
        "AirSim Python package not installed. "
        "Install it with: pip install airsim"
    )


class DroneState(Enum):
    """Possible high-level drone states."""

    GROUNDED = "grounded"
    TAKING_OFF = "taking_off"
    IN_AIR = "in_air"
    FLYING = "flying"
    LANDING = "landing"
    HOVERING = "hovering"
    EMERGENCY = "emergency"


@dataclass
class Pose3D:
    """Represents a 3D position and orientation."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    heading: float = 0.0  # yaw in radians
    pitch: float = 0.0
    roll: float = 0.0

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def distance_to(self, other: "Pose3D") -> float:
        """Euclidean distance to another pose."""
        return math.sqrt(
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        )


@dataclass
class Velocity3D:
    """3D velocity vector."""

    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0

    def speed(self) -> float:
        return math.sqrt(self.vx ** 2 + self.vy ** 2 + self.vz ** 2)

    def heading(self) -> float:
        return math.atan2(self.vy, self.vx)


@dataclass
class BatteryState:
    """Battery telemetry."""

    voltage: float = 16.8
    remaining_percent: float = 100.0
    temperature: float = 25.0
    current_draw_amps: float = 0.0
    time_remaining_seconds: float = 0.0
    is_charging: bool = False


class AirSimDrone:
    """
    3D drone controlled via the AirSim Python API.

    Wraps AirSim's MultirotorClient to provide:
    - Connection management
    - Takeoff / Landing
    - Position, velocity, and orientation commands
    - Kinematic state reading
    - Battery monitoring
    - Coordinate mapping between AirSim and MJN grid coordinates
    """

    def __init__(self, config: AirSimConfig) -> None:
        self.config = config
        self.drone_cfg = config.drone
        self.vehicle_name = self.drone_cfg.vehicle_name

        # AirSim client connection
        self.client: Optional[Any] = None
        self.connected: bool = False
        self.sim_running: bool = False

        # Drone state
        self.state = DroneState.GROUNDED
        self.pose = Pose3D()
        self.velocity = Velocity3D()
        self.battery = BatteryState()
        self.heading = 0.0

        # For compatibility with the 2D Drone interface
        self.x = 0.0
        self.y = 0.0
        self.speed = 0.0

        # World-to-grid mapping
        self._grid_origin_x = 0.0
        self._grid_origin_y = 0.0
        self._grid_scale = 1.0  # meters per grid cell

        # Takeoff reference
        self._home_z = 0.0

    # ── Connection ───────────────────────────────────────────────────

    def connect(self) -> bool:
        """Connect to the AirSim simulator.

        Returns:
            True if connection was successful, False otherwise.
        """
        if not AIRSIM_AVAILABLE:
            logger.error(
                "Cannot connect: airsim package not installed."
            )
            return False

        try:
            self.client = airsim.MultirotorClient(
                ip=self.config.connection.ip,
                port=self.config.connection.port,
            )
            self.client.confirmConnection()
            self.connected = True
            logger.info(
                "Connected to AirSim at %s:%s",
                self.config.connection.ip,
                self.config.connection.port,
            )
            return True
        except Exception as exc:
            logger.error("AirSim connection failed: %s", exc)
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from the AirSim simulator."""
        if self.client is not None:
            try:
                self.client.armDisarm(False, self.vehicle_name)
            except Exception:
                pass
            self.client = None
        self.connected = False
        self.sim_running = False

    def is_connected(self) -> bool:
        """Check whether we are connected to AirSim."""
        return self.connected and self.client is not None

    # ── Simulation control ──────────────────────────────────────────

    def start_simulation(self) -> bool:
        """Start or resume the AirSim simulation.

        Returns:
            True on success.
        """
        if not self.is_connected():
            logger.error("Cannot start simulation: not connected.")
            return False
        try:
            self.client.simStart(True, True)
            self.sim_running = True
            logger.info("AirSim simulation started.")
            return True
        except Exception as exc:
            logger.error("Failed to start simulation: %s", exc)
            return False

    def pause_simulation(self) -> bool:
        """Pause the AirSim simulation."""
        if not self.is_connected():
            return False
        try:
            self.client.simPause(True)
            return True
        except Exception as exc:
            logger.error("Failed to pause simulation: %s", exc)
            return False

    def resume_simulation(self) -> bool:
        """Resume a paused AirSim simulation."""
        if not self.is_connected():
            return False
        try:
            self.client.simPause(False)
            return True
        except Exception as exc:
            logger.error("Failed to resume simulation: %s", exc)
            return False

    def get_sim_time(self) -> float:
        """Return the simulation timestamp in seconds."""
        if not self.is_connected():
            return 0.0
        try:
            return self.client.simGetTimeOfDay().time_taken
        except Exception:
            return 0.0

    # ── Takeoff / Landing ────────────────────────────────────────────

    def arm(self) -> bool:
        """Arm the drone (enable motors)."""
        if not self.is_connected():
            return False
        try:
            self.client.enableApiControl(True, self.vehicle_name)
            self.client.armDisarm(True, self.vehicle_name)
            logger.info("Drone armed.")
            return True
        except Exception as exc:
            logger.error("Arm failed: %s", exc)
            return False

    def takeoff(
        self,
        altitude: Optional[float] = None,
    ) -> bool:
        """Command the drone to take off to the specified altitude.

        Args:
            altitude: Desired altitude in meters (negative is up in
                AirSim's NED frame).  Defaults to config value.

        Returns:
            True if takeoff completed successfully.
        """
        if not self.is_connected():
            return False

        alt = altitude or self.drone_cfg.takeoff_altitude
        self.state = DroneState.TAKING_OFF
        logger.info("Taking off to altitude %.1f m", alt)

        try:
            self.arm()
            self.client.takeoffAsync().join()
            time.sleep(0.5)
            # Move to the desired altitude
            self.client.moveToZAsync(
                alt, self.drone_cfg.default_speed,
                vehicle_name=self.vehicle_name,
            ).join()
            self._home_z = alt
            self.state = DroneState.IN_AIR
            self._update_kinematics()
            logger.info("Takeoff complete.  Position: %s", self.pose)
            return True
        except Exception as exc:
            logger.error("Takeoff failed: %s", exc)
            self.state = DroneState.EMERGENCY
            return False

    def land(self) -> bool:
        """Command the drone to land.

        Returns:
            True if landing completed successfully.
        """
        if not self.is_connected():
            return False

        self.state = DroneState.LANDING
        logger.info("Landing drone.")

        try:
            self.client.landAsync().join()
            self.state = DroneState.GROUNDED
            self._update_kinematics()
            self.client.armDisarm(False, self.vehicle_name)
            self.client.enableApiControl(False, self.vehicle_name)
            logger.info("Landing complete.")
            return True
        except Exception as exc:
            logger.error("Landing failed: %s", exc)
            self.state = DroneState.EMERGENCY
            return False

    # ── Movement commands ────────────────────────────────────────────

    def move_to_position(
        self,
        x: float,
        y: float,
        z: float,
        speed: Optional[float] = None,
        yaw: Optional[float] = None,
    ) -> bool:
        """Move to a 3D position in AirSim coordinates.

        Args:
            x, y, z: Target position (NED frame).
            speed: Desired speed (m/s).  Uses config default if None.
            yaw: Desired yaw angle in degrees.  None = no constraint.

        Returns:
            True on success.
        """
        if not self.is_connected():
            return False

        spd = speed or self.drone_cfg.default_speed
        self.state = DroneState.FLYING

        try:
            yaw_mode = airsim.YawMode(
                is_rate=False,
                yaw_or_rate=yaw if yaw is not None else 0,
            )
            self.client.moveToPositionAsync(
                x, y, z, spd,
                yaw_mode=yaw_mode,
                vehicle_name=self.vehicle_name,
            ).join()
            self._update_kinematics()
            return True
        except Exception as exc:
            logger.error("move_to_position failed: %s", exc)
            return False

    def move_by_velocity(
        self,
        vx: float,
        vy: float,
        vz: float,
        duration: float = 0.5,
    ) -> bool:
        """Send a velocity command for a specified duration.

        Args:
            vx, vy, vz: Velocity components in NED (m/s).
            duration: How long to apply the velocity (seconds).

        Returns:
            True on success.
        """
        if not self.is_connected():
            return False

        try:
            self.client.moveByVelocityAsync(
                vx, vy, vz, duration,
                vehicle_name=self.vehicle_name,
            ).join()
            self._update_kinematics()
            return True
        except Exception as exc:
            logger.error("move_by_velocity failed: %s", exc)
            return False

    def hover(self) -> bool:
        """Hover in place (zero velocity).

        Returns:
            True on success.
        """
        if not self.is_connected():
            return False

        self.state = DroneState.HOVERING
        try:
            self.client.hoverAsync().join()
            return True
        except Exception as exc:
            logger.error("hover failed: %s", exc)
            return False

    def move_along_path(
        self,
        waypoints: List[Tuple[float, float, float]],
        speed: Optional[float] = None,
    ) -> bool:
        """Follow a sequence of 3D waypoints.

        Args:
            waypoints: Ordered list of (x, y, z) NED positions.
            speed: Desired speed (m/s).

        Returns:
            True if all waypoints reached.
        """
        if not self.is_connected():
            return False

        spd = speed or self.drone_cfg.default_speed
        self.state = DroneState.FLYING
        try:
            for wp in waypoints:
                self.client.moveToPositionAsync(
                    wp[0], wp[1], wp[2], spd,
                    vehicle_name=self.vehicle_name,
                ).join()
                self._update_kinematics()
            return True
        except Exception as exc:
            logger.error("move_along_path failed: %s", exc)
            return False

    def set_yaw(self, yaw_degrees: float, rate: bool = False) -> bool:
        """Set the drone's yaw.

        Args:
            yaw_degrees: Target yaw in degrees.
            rate: If True, yaw_or_rate is treated as a rate (deg/s).

        Returns:
            True on success.
        """
        if not self.is_connected():
            return False
        try:
            self.client.rotateToYawAsync(
                yaw_degrees,
                vehicle_name=self.vehicle_name,
            ).join()
            self._update_kinematics()
            return True
        except Exception as exc:
            logger.error("set_yaw failed: %s", exc)
            return False

    # ── Kinematics ───────────────────────────────────────────────────

    def _update_kinematics(self) -> None:
        """Read current kinematic state from AirSim and update locals."""
        if not self.is_connected():
            return

        try:
            state = self.client.multirotorState(
                vehicle_name=self.vehicle_name,
            )
            # Position
            pos = state.kinematics_estimated.position
            self.pose.x = pos.x_val
            self.pose.y = pos.y_val
            self.pose.z = pos.z_val

            # Orientation (yaw)
            orient = state.kinematics_estimated.orientation
            self.pose.heading = self._quat_to_yaw(orient)
            self.heading = self.pose.heading

            # Velocity
            vel = state.kinematics_estimated.linear_velocity
            self.velocity.vx = vel.x_val
            self.velocity.vy = vel.y_val
            self.velocity.vz = vel.z_val

            # Acceleration
            acc = state.kinematics_estimated.linear_acceleration
            self.pose.pitch = math.atan2(
                acc.z_val,
                math.sqrt(acc.x_val ** 2 + acc.y_val ** 2 + 1e-6),
            )
            self.pose.roll = math.atan2(acc.y_val, acc.x_val + 1e-6)

            # Compatibility with 2D Drone
            self.x = self.pose.x
            self.y = self.pose.y
            self.speed = self.velocity.speed()

            # Battery
            self._update_battery()

        except Exception as exc:
            logger.error("Failed to read kinematics: %s", exc)

    def _update_battery(self) -> None:
        """Read battery telemetry from AirSim."""
        if not self.is_connected():
            return
        try:
            batt = self.client.getBatteryState(self.vehicle_name)
            self.battery.voltage = batt.voltage
            self.battery.remaining_percent = batt.remaining_percent
            self.battery.temperature = getattr(
                batt, "temperature", 25.0
            )
            self.battery.current_draw_amps = getattr(
                batt, "current_draw_amps", 0.0
            )
        except Exception:
            # Battery API may not be available in all AirSim builds
            pass

    def get_kinematics(self) -> Dict[str, Any]:
        """Return a dictionary of the current kinematic state."""
        if not self.is_connected():
            return {}
        try:
            state = self.client.multirotorState(
                vehicle_name=self.vehicle_name,
            )
            k = state.kinematics_estimated
            return {
                "position": {
                    "x": k.position.x_val,
                    "y": k.position.y_val,
                    "z": k.position.z_val,
                },
                "orientation": {
                    "w": k.orientation.w_val,
                    "x": k.orientation.x_val,
                    "y": k.orientation.y_val,
                    "z": k.orientation.z_val,
                },
                "velocity": {
                    "x": k.linear_velocity.x_val,
                    "y": k.linear_velocity.y_val,
                    "z": k.linear_velocity.z_val,
                },
                "acceleration": {
                    "x": k.linear_acceleration.x_val,
                    "y": k.linear_acceleration.y_val,
                    "z": k.linear_acceleration.z_val,
                },
                "angular_velocity": {
                    "x": k.angular_velocity.x_val,
                    "y": k.angular_velocity.y_val,
                    "z": k.angular_velocity.z_val,
                },
            }
        except Exception:
            return {}

    # ── Collision ────────────────────────────────────────────────────

    def check_collision(self) -> bool:
        """Check if the drone has collided with anything."""
        if not self.is_connected():
            return False
        try:
            col = self.client.simGetCollisionInfo(
                vehicle_name=self.vehicle_name
            )
            return col.has_collided
        except Exception:
            return False

    # ── Coordinate conversion helpers ────────────────────────────────

    def grid_to_airsim(
        self,
        grid_x: float,
        grid_y: float,
    ) -> Tuple[float, float]:
        """Convert grid coordinates to AirSim NED coordinates.

        Args:
            grid_x: X position on the 2D grid.
            grid_y: Y position on the 2D grid.

        Returns:
            (airsim_x, airsim_y) in NED frame.
        """
        airsim_x = (grid_x - self._grid_origin_x) * self._grid_scale
        airsim_y = (grid_y - self._grid_origin_y) * self._grid_scale
        return (airsim_x, airsim_y)

    def airsim_to_grid(
        self,
        airsim_x: float,
        airsim_y: float,
    ) -> Tuple[float, float]:
        """Convert AirSim NED coordinates back to grid coordinates.

        Args:
            airsim_x: X position in NED frame.
            airsim_y: Y position in NED frame.

        Returns:
            (grid_x, grid_y) on the 2D grid.
        """
        grid_x = airsim_x / self._grid_scale + self._grid_origin_x
        grid_y = airsim_y / self._grid_scale + self._grid_origin_y
        return (grid_x, grid_y)

    def set_grid_mapping(
        self,
        origin_x: float,
        origin_y: float,
        scale: float = 1.0,
    ) -> None:
        """Set the mapping between grid and AirSim coordinates.

        Args:
            origin_x: Grid X that corresponds to AirSim (0, 0).
            origin_y: Grid Y that corresponds to AirSim (0, 0).
            scale: Meters per grid cell.
        """
        self._grid_origin_x = origin_x
        self._grid_origin_y = origin_y
        self._grid_scale = scale

    def get_grid_position(self) -> Tuple[float, float]:
        """Get the current drone position in grid coordinates."""
        return self.airsim_to_grid(self.pose.x, self.pose.y)

    # ── AirSim coordinate utilities ──────────────────────────────────

    @staticmethod
    def _quat_to_yaw(orient) -> float:
        """Extract yaw angle (radians) from AirSim quaternion."""
        w = orient.w_val
        x = orient.x_val
        y = orient.y_val
        z = orient.z_val
        return math.atan2(
            2.0 * (w * z + x * y),
            1.0 - 2.0 * (y * y + z * z),
        )

    # ── Context manager ──────────────────────────────────────────────

    def __enter__(self) -> "AirSimDrone":
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.disconnect()