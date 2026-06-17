"""
AirSim Sensor Suite
====================
Unified sensor interface for AirSim's simulated sensors.
Reads camera, LiDAR, IMU, GPS, barometer, and magnetometer data
from the AirSim simulator and provides a consistent API.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Tuple, Dict, Any

import numpy as np

from src.airsim.airsim_config import AirSimSensorConfig

logger = logging.getLogger(__name__)

# Attempt to import airsim
try:
    import airsim

    AIRSIM_AVAILABLE = True
except ImportError:
    airsim = None
    AIRSIM_AVAILABLE = False
    logger.warning(
        "AirSim Python package not installed. "
        "Install it with: pip install airsim"
    )


# ── Sensor data types ──────────────────────────────────────────────


class CameraType(Enum):
    """AirSim camera types."""

    FRONT = 0  # front-facing camera
    FRONT_LEFT = 1
    FRONT_RIGHT = 2
    BACK = 3
    BACK_LEFT = 4
    BACK_RIGHT = 5
    BOTTOM = 6
    TOP = 7


@dataclass
class CameraData:
    """Data from a camera sensor."""

    image_data: Optional[np.ndarray] = None
    width: int = 0
    height: int = 0
    depth_image: Optional[np.ndarray] = None
    segmentation: Optional[np.ndarray] = None
    camera_type: CameraType = CameraType.FRONT

    # Camera pose
    position: Tuple[float, float, float] = (0, 0, 0)
    orientation: Tuple[float, float, float, float] = (1, 0, 0, 0)

    @property
    def has_image(self) -> bool:
        return self.image_data is not None


@dataclass
class LidarPoint:
    """A single LiDAR point."""

    x: float
    y: float
    z: float
    intensity: float = 0.0
    distance: float = 0.0


@dataclass
class LidarData:
    """Data from a LiDAR sensor."""

    points: List[LidarPoint] = field(default_factory=list)
    timestamp: float = 0.0
    num_rays: int = 0

    @property
    def count(self) -> int:
        return len(self.points)

    def get_distances(self) -> List[float]:
        """Return list of distances to each point."""
        return [p.distance for p in self.points]

    def get_positions(self) -> List[Tuple[float, float, float]]:
        """Return list of (x, y, z) positions."""
        return [(p.x, p.y, p.z) for p in self.points]

    def to_array(self) -> np.ndarray:
        """Convert to numpy array of shape (N, 3)."""
        if not self.points:
            return np.empty((0, 3))
        arr = np.array([[p.x, p.y, p.z] for p in self.points])
        return arr

    def filter_by_range(
        self, min_range: float, max_range: float
    ) -> "LidarData":
        """Return a filtered LidarData with only points in range."""
        filtered = [
            p
            for p in self.points
            if min_range <= p.distance <= max_range
        ]
        result = LidarData(points=filtered, timestamp=self.timestamp)
        result.num_rays = len(filtered)
        return result


@dataclass
class IMUData:
    """Data from the IMU sensor."""

    acceleration: Tuple[float, float, float] = (0, 0, 0)
    angular_velocity: Tuple[float, float, float] = (0, 0, 0)
    orientation: Tuple[float, float, float, float] = (1, 0, 0, 0)
    timestamp: float = 0.0


@dataclass
class GPSData:
    """Data from the GPS sensor."""

    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    accuracy: float = 3.0  # meters
    timestamp: float = 0.0

    @property
    def position(self) -> Tuple[float, float, float]:
        return (self.latitude, self.longitude, self.altitude)


@dataclass
class BarometerData:
    """Data from the barometric sensor."""

    altitude: float = 0.0
    pressure: float = 101325.0  # Pa
    temperature: float = 25.0  # Celsius
    timestamp: float = 0.0


@dataclass
class MagnetometerData:
    """Data from the magnetometer / compass sensor."""

    magnetic_field: Tuple[float, float, float] = (0, 0, 0)
    heading: float = 0.0  # degrees
    timestamp: float = 0.0


# ── SensorSuite ────────────────────────────────────────────────────


class AirSimSensorSuite:
    """
    Unified sensor interface for AirSim.

    Reads all available sensor data from the AirSim simulator
    and provides a consistent API.
    """

    def __init__(self, config: AirSimSensorConfig) -> None:
        self.config = config
        self.client = None
        self.vehicle_name = "Drone1"
        self.connected = False

    def set_client(
        self, client: Any, vehicle_name: str = "Drone1"
    ) -> None:
        """Set the AirSim client for the sensor suite.

        Args:
            client: AirSim MultirotorClient instance.
            vehicle_name: Name of the vehicle.
        """
        self.client = client
        self.vehicle_name = vehicle_name
        self.connected = True

    # ── Camera ───────────────────────────────────────────────────────

    def get_camera_image(
        self,
        camera_type: CameraType = CameraType.FRONT,
        image_type: str = "rgb",
    ) -> CameraData:
        """Get an image from the specified camera.

        Args:
            camera_type: Which camera to read from.
            image_type: "rgb", "depth", or "segmentation".

        Returns:
            CameraData with the image.
        """
        if not self._check_connection():
            return CameraData()

        camera_enum = airsim.ImageRequest(
            self._camera_name(camera_type),
            self._image_type_enum(image_type),
            pixels_as_float=True,
            compress=False,
        )

        try:
            responses = self.client.simGetImages(
                [camera_enum], vehicle_name=self.vehicle_name
            )
            if not responses:
                return CameraData()

            response = responses[0]
            if response is None or not response.image_data_uint8:
                return CameraData()

            img = np.frombuffer(
                response.image_data_uint8, dtype=np.uint8
            ).reshape(response.height, response.width, -1)

            cam_data = CameraData(
                image_data=img,
                width=response.width,
                height=response.height,
                camera_type=camera_type,
            )
            return cam_data
        except Exception as exc:
            logger.error("Camera read failed: %s", exc)
            return CameraData()

    def get_depth_image(
        self,
        camera_type: CameraType = CameraType.FRONT,
    ) -> CameraData:
        """Get depth image from the specified camera."""
        return self.get_camera_image(camera_type, image_type="depth")

    def get_segmentation_image(
        self,
        camera_type: CameraType = CameraType.FRONT,
    ) -> CameraData:
        """Get segmentation image from the specified camera."""
        return self.get_camera_image(
            camera_type, image_type="segmentation"
        )

    # ── LiDAR ────────────────────────────────────────────────────────

    def get_lidar_data(
        self,
        sensor_name: str = "lidar",
    ) -> LidarData:
        """Read LiDAR data from the AirSim simulator.

        Args:
            sensor_name: Name of the LiDAR sensor in AirSim.

        Returns:
            LidarData containing the scan.
        """
        if not self._check_connection():
            return LidarData()

        try:
            raw = self.client.getLidarData(
                sensor_name, self.vehicle_name
            )
            points: List[LidarPoint] = []
            for i in range(0, len(raw.point_cloud), 3):
                if i + 2 < len(raw.point_cloud):
                    px = raw.point_cloud[i]
                    py = raw.point_cloud[i + 1]
                    pz = raw.point_cloud[i + 2]
                    dist = math.sqrt(px ** 2 + py ** 2 + pz ** 2)
                    points.append(
                        LidarPoint(
                            x=px, y=py, z=pz,
                            distance=dist,
                        )
                    )
            return LidarData(
                points=points,
                timestamp=raw.time_stamp,
                num_rays=len(points),
            )
        except Exception as exc:
            logger.error("LiDAR read failed: %s", exc)
            return LidarData()

    # ── IMU ──────────────────────────────────────────────────────────

    def get_imu_data(self) -> IMUData:
        """Read IMU data from AirSim."""
        if not self._check_connection():
            return IMUData()

        try:
            raw = self.client.getImuData()
            return IMUData(
                acceleration=(
                    raw.linear_acceleration.x_val,
                    raw.linear_acceleration.y_val,
                    raw.linear_acceleration.z_val,
                ),
                angular_velocity=(
                    raw.angular_velocity.x_val,
                    raw.angular_velocity.y_val,
                    raw.angular_velocity.z_val,
                ),
                orientation=(
                    raw.orientation.w_val,
                    raw.orientation.x_val,
                    raw.orientation.y_val,
                    raw.orientation.z_val,
                ),
                timestamp=raw.time_stamp,
            )
        except Exception as exc:
            logger.error("IMU read failed: %s", exc)
            return IMUData()

    # ── GPS ──────────────────────────────────────────────────────────

    def get_gps_data(self) -> GPSData:
        """Read GPS data from AirSim."""
        if not self._check_connection():
            return GPSData()

        try:
            raw = self.client.getGpsData()
            return GPSData(
                latitude=raw.gnss.geo_point.latitude,
                longitude=raw.gnss.geo_point.longitude,
                altitude=raw.gnss.geo_point.altitude,
                timestamp=raw.time_stamp,
            )
        except Exception as exc:
            logger.error("GPS read failed: %s", exc)
            return GPSData()

    # ── Barometer ────────────────────────────────────────────────────

    def get_barometer_data(self) -> BarometerData:
        """Read barometer data from AirSim."""
        if not self._check_connection():
            return BarometerData()

        try:
            raw = self.client.getBarometerData()
            return BarometerData(
                altitude=raw.altitude,
                pressure=raw.pressure,
                temperature=raw.temperature,
                timestamp=raw.time_stamp,
            )
        except Exception as exc:
            logger.error("Barometer read failed: %s", exc)
            return BarometerData()

    # ── Magnetometer ─────────────────────────────────────────────────

    def get_magnetometer_data(self) -> MagnetometerData:
        """Read magnetometer data from AirSim."""
        if not self._check_connection():
            return MagnetometerData()

        try:
            raw = self.client.getMagnetometerData()
            mag = raw.magnetic_field_body
            heading = math.atan2(mag.y_val, mag.x_val)
            heading_deg = math.degrees(heading)
            if heading_deg < 0:
                heading_deg += 360
            return MagnetometerData(
                magnetic_field=(mag.x_val, mag.y_val, mag.z_val),
                heading=heading_deg,
                timestamp=raw.time_stamp,
            )
        except Exception as exc:
            logger.error("Magnetometer read failed: %s", exc)
            return MagnetometerData()

    # ── Collision ────────────────────────────────────────────────────

    def get_collision_info(self) -> Dict[str, Any]:
        """Read collision info from AirSim."""
        if not self._check_connection():
            return {"has_collided": False}

        try:
            col = self.client.simGetCollisionInfo(
                vehicle_name=self.vehicle_name
            )
            return {
                "has_collided": col.has_collided,
                "penetration_depth": col.penetration_depth,
                "normal": {
                    "x": col.normal.x_val,
                    "y": col.normal.y_val,
                    "z": col.normal.z_val,
                },
                "position": {
                    "x": col.point.x_val,
                    "y": col.point.y_val,
                    "z": col.point.z_val,
                },
            }
        except Exception:
            return {"has_collided": False}

    # ── Camera helper ────────────────────────────────────────────────

    def _camera_name(self, camera_type: CameraType) -> str:
        """Map a CameraType enum to an AirSim camera name."""
        names = {
            CameraType.FRONT: "front_center",
            CameraType.FRONT_LEFT: "front_left",
            CameraType.FRONT_RIGHT: "front_right",
            CameraType.BACK: "back_center",
            CameraType.BACK_LEFT: "back_left",
            CameraType.BACK_RIGHT: "back_right",
            CameraType.BOTTOM: "bottom_center",
            CameraType.TOP: "top_center",
        }
        return names.get(camera_type, "front_center")

    def _image_type_enum(self, image_type: str) -> int:
        """Map a string image type to AirSim ImageType enum value."""
        mapping = {
            "rgb": 0,
            "depth": 1,
            "segmentation": 2,
        }
        return mapping.get(image_type, 0)

    def _check_connection(self) -> bool:
        """Check if the client is available."""
        if self.client is None or not self.connected:
            logger.warning(
                "SensorSuite: no client connected. "
                "Call set_client() first."
            )
            return False
        return True

    # ── Read all sensors at once ─────────────────────────────────────

    def read_all(self) -> Dict[str, Any]:
        """Read all available sensor data in one call.

        Returns:
            Dictionary with all sensor data.
        """
        result: Dict[str, Any] = {}

        if self.config.camera_enabled:
            result["camera"] = self.get_camera_image()
        if self.config.lidar_enabled:
            result["lidar"] = self.get_lidar_data()
        if self.config.imu_enabled:
            result["imu"] = self.get_imu_data()
        if self.config.gps_enabled:
            result["gps"] = self.get_gps_data()
        if self.config.barometer_enabled:
            result["barometer"] = self.get_barometer_data()
        if self.config.magnetometer_enabled:
            result["magnetometer"] = self.get_magnetometer_data()
        result["collision"] = self.get_collision_info()

        return result

    # ── Fallback (no AirSim) ─────────────────────────────────────────

    def get_simulated_lidar(
        self,
        position: Tuple[float, float, float],
        heading: float,
        range_limit: float = 50.0,
        num_rays: int = 32,
    ) -> LidarData:
        """Generate a simulated LiDAR scan without AirSim.

        This is a fallback method for when AirSim is not connected.
        It produces a simple line-of-sight scan.

        Args:
            position: Drone position (x, y, z).
            heading: Drone yaw in radians.
            range_limit: Maximum scan distance.
            num_rays: Number of rays to cast.

        Returns:
            LidarData with simulated scan.
        """
        angles = np.linspace(
            heading - math.pi,
            heading + math.pi,
            num_rays,
            endpoint=False,
        )
        points: List[LidarPoint] = []
        for angle in angles:
            dist = range_limit * (0.5 + 0.5 * np.random.random())
            px = position[0] + dist * math.cos(angle)
            py = position[1] + dist * math.sin(angle)
            pz = position[2]
            points.append(
                LidarPoint(x=px, y=py, z=pz, distance=dist)
            )
        return LidarData(points=points, num_rays=num_rays)

    def get_simulated_gps(
        self,
        position: Tuple[float, float, float],
    ) -> GPSData:
        """Generate simulated GPS data without AirSim.

        Args:
            position: Drone position (x, y, z).

        Returns:
            GPSData with simulated readings.
        """
        # Simulate a location near the origin
        lat = position[0] * 0.001  # crude mapping
        lon = position[1] * 0.001
        alt = position[2]
        noise = lambda: np.random.normal(0, 0.001)
        return GPSData(
            latitude=lat + noise(),
            longitude=lon + noise(),
            altitude=alt,
        )

    def get_simulated_imu(
        self,
        position: Tuple[float, float, float],
        velocity: Tuple[float, float, float],
    ) -> IMUData:
        """Generate simulated IMU data without AirSim.

        Args:
            position: Drone position.
            velocity: Current velocity.

        Returns:
            IMUData with simulated readings.
        """
        accel_noise = lambda: np.random.normal(0, 0.01)
        return IMUData(
            acceleration=(
                accel_noise(),
                accel_noise(),
                -9.81 + accel_noise(),
            ),
            angular_velocity=(
                np.random.normal(0, 0.01),
                np.random.normal(0, 0.01),
                np.random.normal(0, 0.01),
            ),
        )