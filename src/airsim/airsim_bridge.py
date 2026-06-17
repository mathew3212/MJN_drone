"""
AirSim Bridge
==============
Central bridge that connects the existing MJN simulation subsystems
to the AirSim 3D environment.  Translates between the 2D grid-based
drone model and the 3D AirSim world, enabling seamless switching
between simulation modes.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any

from src.airsim.airsim_config import AirSimConfig
from src.airsim.airsim_drone import AirSimDrone, DroneState
from src.airsim.airsim_physics import AirSimPhysicsModel
from src.airsim.airsim_sensors import (
    AirSimSensorSuite,
    LidarData,
    IMUData,
    GPSData,
    CameraData,
)

logger = logging.getLogger(__name__)


class SimulationMode:
    """Constants for simulation mode selection."""

    NATIVE_2D = "native_2d"
    AIRSIM_3D = "airsim_3d"
    HYBRID = "hybrid"


@dataclass
class BridgeState:
    """State of the bridge between MJN and AirSim."""

    mode: str = SimulationMode.NATIVE_2D
    connected: bool = False
    drone_active: bool = False
    last_lidar_points: int = 0
    last_gps_valid: bool = False
    last_imu_valid: bool = False
    collision_count: int = 0


class AirSimBridge:
    """
    Bridge between the MJN simulation and AirSim.

    Provides:
    - Connection lifecycle management
    - 2D ↔ 3D coordinate conversion
    - Sensor data translation (AirSim → MJN)
    - Command translation (MJN → AirSim)
    - Automatic fallback to 2D when AirSim is unavailable
    """

    def __init__(self, config: Optional[AirSimConfig] = None) -> None:
        self.config = config or AirSimConfig()
        self.drone = AirSimDrone(self.config)
        self.physics = AirSimPhysicsModel(self.config.physics)
        self.sensors = AirSimSensorSuite(self.config.sensors)
        self.state = BridgeState()

        # Grid ↔ AirSim mapping
        self._grid_width = 100
        self._grid_height = 100
        self._airsim_scale = 1.0  # AirSim meters per grid cell
        self._airsim_z_offset = -3.0  # default flight altitude

        # Sensor cache
        self._cached_lidar: Optional[LidarData] = None
        self._cached_imu: Optional[IMUData] = None
        self._cached_gps: Optional[GPSData] = None
        self._cached_camera: Optional[CameraData] = None

    # ── Lifecycle ────────────────────────────────────────────────────

    def initialize(
        self,
        grid_width: int = 100,
        grid_height: int = 100,
        use_airsim: bool = True,
    ) -> bool:
        """Initialize the bridge.

        Args:
            grid_width: Width of the MJN 2D grid.
            grid_height: Height of the MJN 2D grid.
            use_airsim: Whether to attempt AirSim connection.

        Returns:
            True if initialization succeeded (or 2D fallback is active).
        """
        self._grid_width = grid_width
        self._grid_height = grid_height
        self.state.mode = (
            SimulationMode.AIRSIM_3D
            if use_airsim
            else SimulationMode.NATIVE_2D
        )

        if not use_airsim:
            logger.info("Bridge: using native 2D simulation.")
            return True

        # Attempt AirSim connection
        if self.drone.connect():
            self.state.connected = True
            self.sensors.set_client(
                self.drone.client,
                self.drone.vehicle_name,
            )
            logger.info(
                "Bridge: connected to AirSim in 3D mode."
            )
            return True

        # Fallback
        logger.warning(
            "Bridge: AirSim unavailable, falling back to 2D."
        )
        self.state.mode = SimulationMode.NATIVE_2D
        return False

    def shutdown(self) -> None:
        """Shut down the bridge and disconnect from AirSim."""
        if self.state.connected:
            self.drone.disconnect()
            self.state.connected = False
            self.state.drone_active = False
        logger.info("Bridge: shut down.")

    def is_airsim_active(self) -> bool:
        """Check if AirSim mode is currently active."""
        return (
            self.state.mode == SimulationMode.AIRSIM_3D
            and self.state.connected
            and self.drone.is_connected()
        )

    # ── Takeoff / Landing ────────────────────────────────────────────

    def takeoff(
        self,
        altitude: Optional[float] = None,
    ) -> bool:
        """Take off in AirSim mode.

        Args:
            altitude: Desired flight altitude (m, NED).

        Returns:
            True on success.
        """
        if not self.is_airsim_active():
            logger.info("Bridge: takeoff in 2D mode (no-op).")
            return True

        result = self.drone.takeoff(altitude)
        if result:
            self.state.drone_active = True
        return result

    def land(self) -> bool:
        """Land the drone."""
        if not self.is_airsim_active():
            logger.info("Bridge: land in 2D mode (no-op).")
            return True

        result = self.drone.land()
        if result:
            self.state.drone_active = False
        return result

    # ── Movement ─────────────────────────────────────────────────────

    def move_grid_waypoint(
        self,
        grid_x: float,
        grid_y: float,
        speed: float = 3.0,
    ) -> bool:
        """Move the drone to a grid coordinate (2D → 3D conversion).

        Args:
            grid_x: Target X on the 2D grid.
            grid_y: Target Y on the 2D grid.
            speed: Movement speed (m/s in AirSim).

        Returns:
            True on success.
        """
        if not self.is_airsim_active():
            # In 2D mode, update drone coordinates directly
            return True

        airsim_x, airsim_y = self.drone.grid_to_airsim(
            grid_x, grid_y
        )
        return self.drone.move_to_position(
            airsim_x, airsim_y, self._airsim_z_offset,
            speed=speed,
        )

    def move_grid_velocity(
        self,
        vx_grid: float,
        vy_grid: float,
        duration: float = 0.5,
    ) -> bool:
        """Send a velocity command in grid coordinates.

        Args:
            vx_grid: Grid X velocity.
            vy_grid: Grid Y velocity.
            duration: Command duration (seconds).

        Returns:
            True on success.
        """
        if not self.is_airsim_active():
            return True

        vx = vx_grid * self._airsim_scale
        vy = vy_grid * self._airsim_scale
        return self.drone.move_by_velocity(vx, vy, 0.0, duration)

    def hover(self) -> bool:
        """Hover in place."""
        if not self.is_airsim_active():
            return True
        return self.drone.hover()

    # ── Sensor integration ───────────────────────────────────────────

    def read_lidar(
        self,
        scan_radius: float = 8.0,
    ) -> List[Tuple[int, int]]:
        """Read LiDAR data and convert to grid obstacle cells.

        Args:
            scan_radius: Max obstacle detection range.

        Returns:
            List of (grid_x, grid_y) obstacle positions.
        """
        if not self.is_airsim_active():
            return []

        self._cached_lidar = self.sensors.get_lidar_data()
        self.state.last_lidar_points = self._cached_lidar.count

        # Convert LiDAR points to grid coordinates
        obstacles: List[Tuple[int, int]] = []
        for pt in self._cached_lidar.points:
            if pt.distance <= scan_radius:
                gx, gy = self.drone.airsim_to_grid(pt.x, pt.y)
                ix = round(gx)
                iy = round(gy)
                if 0 <= ix < self._grid_width and 0 <= iy < self._grid_height:
                    obstacles.append((ix, iy))
        return obstacles

    def read_imu(self) -> Dict[str, Any]:
        """Read IMU data and return in a format compatible with MJN."""
        if not self.is_airsim_active():
            return self._fallback_imu()

        self._cached_imu = self.sensors.get_imu_data()
        self.state.last_imu_valid = True
        return {
            "acceleration": self._cached_imu.acceleration,
            "angular_velocity": self._cached_imu.angular_velocity,
            "orientation": self._cached_imu.orientation,
        }

    def read_gps(self) -> Tuple[float, float]:
        """Read GPS data and return in grid coordinates.

        Returns:
            (grid_x, grid_y) position from GPS.
        """
        if not self.is_airsim_active():
            return self._fallback_gps()

        self._cached_gps = self.sensors.get_gps_data()
        self.state.last_gps_valid = True

        # For AirSim local GPS, map directly from the drone pose
        grid_x, grid_y = self.drone.get_grid_position()
        return (grid_x, grid_y)

    def read_camera(
        self,
        image_type: str = "rgb",
    ) -> Optional[Any]:
        """Read camera image data.

        Returns:
            CameraData object or None.
        """
        if not self.is_airsim_active():
            return None

        self._cached_camera = self.sensors.get_camera_image(
            image_type=image_type
        )
        return self._cached_camera

    def check_collision(self) -> bool:
        """Check for drone collision."""
        if not self.is_airsim_active():
            return False

        result = self.drone.check_collision()
        if result:
            self.state.collision_count += 1
        return result

    # ── Coordinate conversion ────────────────────────────────────────

    def grid_to_airsim_3d(
        self,
        grid_x: float,
        grid_y: float,
        altitude: Optional[float] = None,
    ) -> Tuple[float, float, float]:
        """Convert grid coordinates to AirSim 3D position.

        Args:
            grid_x: Grid X position.
            grid_y: Grid Y position.
            altitude: Flight altitude in AirSim NED. Defaults to config.

        Returns:
            (airsim_x, airsim_y, airsim_z) in NED frame.
        """
        z = altitude or self._airsim_z_offset
        ax, ay = self.drone.grid_to_airsim(grid_x, grid_y)
        return (ax, ay, z)

    def airsim_to_grid_2d(
        self,
        airsim_x: float,
        airsim_y: float,
    ) -> Tuple[int, int]:
        """Convert AirSim 3D position to grid cell.

        Args:
            airsim_x: X in NED frame.
            airsim_y: Y in NED frame.

        Returns:
            (grid_x, grid_y) as integer grid cell.
        """
        gx, gy = self.drone.airsim_to_grid(airsim_x, airsim_y)
        return (round(gx), round(gy))

    def update_drone_from_airsim(self, mjn_drone: Any) -> None:
        """Update the MJN drone's 2D position from AirSim state.

        This keeps the MJN simulation's drone object in sync with
        AirSim's 3D state (projected to 2D).

        Args:
            mjn_drone: MJN Drone instance to update.
        """
        if not self.is_airsim_active():
            return

        self.drone._update_kinematics()
        grid_x, grid_y = self.drone.get_grid_position()
        mjn_drone.x = grid_x
        mjn_drone.y = grid_y
        mjn_drone.heading = self.drone.heading
        mjn_drone.speed = self.drone.speed

    def get_airsim_position(self) -> Optional[Tuple[float, float, float]]:
        """Get the current 3D position from AirSim.

        Returns:
            (x, y, z) in NED frame, or None if not connected.
        """
        if not self.is_airsim_active():
            return None
        return self.drone.pose.to_tuple()

    def get_battery_info(self) -> Dict[str, float]:
        """Get battery telemetry.

        Returns:
            Dictionary with battery information.
        """
        return {
            "voltage": self.drone.battery.voltage,
            "remaining_percent": self.drone.battery.remaining_percent,
            "temperature": self.drone.battery.temperature,
            "current_draw_amps": self.drone.battery.current_draw_amps,
        }

    # ── Physics integration ──────────────────────────────────────────

    def update_physics(
        self,
        dt: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Update the physics model and return state.

        When AirSim is active, physics is handled by AirSim directly.
        When in 2D/hybrid mode, the local physics model is used.

        Args:
            dt: Time step in seconds.

        Returns:
            Physics state dictionary.
        """
        if self.is_airsim_active():
            # Physics is managed by AirSim; just read the state
            kin = self.drone.get_kinematics()
            if kin:
                return kin
            return self.physics.get_state()

        # Use local physics model
        return self.physics.update(dt).speed()

    # ── Fallback helpers ─────────────────────────────────────────────

    def _fallback_imu(self) -> Dict[str, Any]:
        """Return simulated IMU data when AirSim is not available."""
        return {
            "acceleration": (0.0, 0.0, -9.81),
            "angular_velocity": (0.0, 0.0, 0.0),
            "orientation": (1.0, 0.0, 0.0, 0.0),
        }

    def _fallback_gps(self) -> Tuple[float, float]:
        """Return a fallback GPS position."""
        return (self._grid_width / 2, self._grid_height / 2)

    # ── Status ───────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary."""
        return {
            "mode": self.state.mode,
            "connected": self.state.connected,
            "drone_active": self.state.drone_active,
            "airsim_available": self.is_airsim_active(),
            "drone_state": self.drone.state.value,
            "position_3d": self.drone.pose.to_tuple(),
            "grid_position": self.drone.get_grid_position(),
            "heading": math.degrees(self.drone.heading),
            "speed": self.drone.speed,
            "battery_percent": self.drone.battery.remaining_percent,
            "lidar_points": self.state.last_lidar_points,
            "collision_count": self.state.collision_count,
        }

    def __enter__(self) -> "AirSimBridge":
        return self

    def __exit__(self, *args) -> None:
        self.shutdown()