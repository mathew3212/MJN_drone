"""
AirSim Configuration
====================
Configuration parameters for the AirSim integration.
Provides settings for connection, vehicle, sensors, and physics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AirSimConnectionConfig:
    """Connection settings for the AirSim API."""

    ip: str = "127.0.0.1"
    port: int = 41451
    timeout_seconds: float = 30.0
    vehicle_name: str = "Drone1"
    use_simulation_time: bool = False


@dataclass
class AirSimDroneConfig:
    """Drone-specific configuration for AirSim."""

    vehicle_name: str = "Drone1"
    max_speed: float = 5.0
    max_acceleration: float = 3.0
    max_yaw_rate: float = 90.0
    takeoff_altitude: float = -3.0
    landing_speed: float = 0.5
    nav_mode: str = "Multirotor"
    default_altitude: float = -3.0
    default_speed: float = 3.0


@dataclass
class AirSimSensorConfig:
    """Sensor configuration for AirSim."""

    # Camera
    camera_enabled: bool = True
    camera_width: int = 640
    camera_height: int = 480
    camera_fov: float = 90.0

    # LiDAR
    lidar_enabled: bool = True
    lidar_num_rays: int = 32
    lidar_max_range: float = 50.0
    lidar_min_range: float = 0.5
    lidar_frame: str = "lidar"

    # IMU
    imu_enabled: bool = True

    # GPS
    gps_enabled: bool = True

    # Barometer
    barometer_enabled: bool = True

    # Magnetometer / Compass
    magnetometer_enabled: bool = True


@dataclass
class AirSimPhysicsConfig:
    """Physics simulation configuration for AirSim."""

    gravity: float = 9.81
    air_density: float = 1.225
    drag_coefficient: float = 0.3
    rotor_count: int = 4
    max_thrust: float = 18.0
    max_torque: float = 2.0
    sim_time_step: float = 0.02  # 50 Hz
    real_time_factor: float = 1.0
    enable_collision: bool = True
    enable_wind: bool = False
    wind_speed: float = 0.0
    wind_direction: float = 0.0


@dataclass
class AirSimWorldConfig:
    """World/scene configuration for AirSim."""

    scene_name: str = "Default"
    enable_shadows: bool = True
    enable_fog: bool = False
    enable_weather: bool = False
    fog_density: float = 0.01
    time_of_day: float = 12.0
    sun_intensity: float = 1.0
    spawn_position: tuple = (0.0, 0.0, 0.0)
    spawn_heading: float = 0.0
    terrain_enabled: bool = True
    object_count: int = 50


@dataclass
class AirSimConfig:
    """Master configuration for the AirSim integration."""

    connection: AirSimConnectionConfig = field(
        default_factory=AirSimConnectionConfig
    )
    drone: AirSimDroneConfig = field(
        default_factory=AirSimDroneConfig
    )
    sensors: AirSimSensorConfig = field(
        default_factory=AirSimSensorConfig
    )
    physics: AirSimPhysicsConfig = field(
        default_factory=AirSimPhysicsConfig
    )
    world: AirSimWorldConfig = field(
        default_factory=AirSimWorldConfig
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "connection": self.connection.__dict__,
            "drone": self.drone.__dict__,
            "sensors": self.sensors.__dict__,
            "physics": self.physics.__dict__,
            "world": self.world.__dict__,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AirSimConfig":
        """Create from dictionary."""
        return cls(
            connection=AirSimConnectionConfig(**d.get("connection", {})),
            drone=AirSimDroneConfig(**d.get("drone", {})),
            sensors=AirSimSensorConfig(**d.get("sensors", {})),
            physics=AirSimPhysicsConfig(**d.get("physics", {})),
            world=AirSimWorldConfig(**d.get("world", {})),
        )