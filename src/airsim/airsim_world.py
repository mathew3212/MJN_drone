"""
AirSim World Manager
====================
Manages the AirSim simulation environment.
Handles scene loading, spawning objects, weather conditions,
and environment configuration.
"""

from __future__ import annotations

import math
import logging
import random
from typing import Optional, List, Tuple, Dict, Any

from src.airsim.airsim_config import AirSimWorldConfig

logger = logging.getLogger(__name__)

try:
    import airsim

    AIRSIM_AVAILABLE = True
except ImportError:
    airsim = None
    AIRSIM_AVAILABLE = False


class AirSimWorldManager:
    """
    Manages the AirSim simulation environment.

    Handles:
    - Scene loading and configuration
    - Spawning/removing objects (obstacles, buildings, etc.)
    - Weather and lighting settings
    - Terrain configuration
    - Generating a 3D world that matches the MJN 2D grid
    """

    def __init__(self, config: AirSimWorldConfig) -> None:
        self.config = config
        self.client = None
        self.spawned_objects: List[Dict[str, Any]] = []
        self.obstacles: List[Dict[str, float]] = []
        self.shipped = False

    def set_client(self, client: Any) -> None:
        """Set the AirSim client."""
        self.client = client

    # ── Scene management ─────────────────────────────────────────────

    def configure_scene(self) -> bool:
        """Configure the AirSim scene.

        Returns:
            True on success.
        """
        if self.client is None:
            logger.error("WorldManager: no client set.")
            return False

        try:
            # Set time of day
            self.client.simSetTimeOfDay(
                timeOfDay=f"{self.config.time_of_day:.0f}:00:00",
                isünlight_initialized=True,
                sun_intensity=self.config.sun_intensity,
                enable_shadows=self.config.enable_shadows,
            )

            # Configure fog
            if self.config.enable_fog:
                self.client.simEnableFog(True)
                self.client.simSetFogDensity(
                    self.config.fog_density
                )
            else:
                self.client.simEnableFog(False)

            logger.info(
                "Scene configured: time=%.0f, shadows=%s, fog=%s",
                self.config.time_of_day,
                self.config.enable_shadows,
                self.config.enable_fog,
            )
            return True
        except Exception as exc:
            logger.error("Scene configuration failed: %s", exc)
            return False

    # ── Object spawning ──────────────────────────────────────────────

    def spawn_obstacles(
        self,
        obstacle_list: List[Tuple[int, int]],
        size_range: Tuple[float, float] = (1.0, 3.0),
        scale: float = 1.0,
    ) -> int:
        """Spawn 3D obstacles in AirSim from the 2D obstacle list.

        Args:
            obstacle_list: List of (grid_x, grid_y) positions.
            size_range: (min, max) size of spawned objects (meters).
            scale: Scale factor for coordinate mapping.

        Returns:
            Number of spawned objects.
        """
        if self.client is None:
            logger.error("WorldManager: no client set.")
            return 0

        count = 0
        for i, (gx, gy) in enumerate(obstacle_list):
            # Convert to AirSim coordinates
            x = gx * scale
            y = gy * scale
            z = -0.5  # half-buried in ground

            # Random size
            size = random.uniform(*size_range)

            # Create a simple box as obstacle
            try:
                object_name = f"obstacle_{i}"
                self.client.simSpawnObject(
                    object_name,
                    "ObstacleCube",  # a simple mesh
                    airsim.Pose(
                        airsim.Vector3r(x, y, z),  # type: ignore[union-attr]
                        airsim.Quaternionr(),  # type: ignore[union-attr]
                    ),
                    scale_by_camera_fus=False,
                )

                # Set the scale of the object
                self.client.simSetObjectScale(
                    object_name,
                    airsim.Vector3r(size, size, size),  # type: ignore[union-attr]
                )

                self.spawned_objects.append({
                    "name": object_name,
                    "type": "obstacle",
                    "x": x,
                    "y": y,
                    "z": z,
                    "size": size,
                })
                self.obstacles.append({
                    "grid_x": gx,
                    "grid_y": gy,
                    "airsim_x": x,
                    "airsim_y": y,
                })
                count += 1
            except Exception as exc:
                logger.warning(
                    "Failed to spawn obstacle at (%s,%s): %s",
                    gx, gy, exc,
                )

        logger.info("Spawned %d obstacles in AirSim.", count)
        return count

    def spawn_dynamic_obstacles(
        self,
        positions: List[Tuple[float, float]],
        size: float = 1.5,
        scale: float = 1.0,
    ) -> int:
        """Spawn dynamic obstacles in the AirSim scene.

        Args:
            positions: List of (x, y) grid positions.
            size: Size of each obstacle.
            scale: Scale factor.

        Returns:
            Number of spawned objects.
        """
        if self.client is None:
            return 0

        count = 0
        for i, (gx, gy) in enumerate(positions):
            x = gx * scale
            y = gy * scale
            z = -0.5

            try:
                name = f"dynamic_obs_{i}"
                self.client.simSpawnObject(
                    name,
                    "ObstacleSphere",
                    airsim.Pose(
                        airsim.Vector3r(x, y, z),  # type: ignore[union-attr]
                        airsim.Quaternionr(),  # type: ignore[union-attr]
                    ),
                    scale_by_camera_fus=False,
                )
                self.client.simSetObjectScale(
                    name,
                    airsim.Vector3r(size, size, size),  # type: ignore[union-attr]
                )
                self.spawned_objects.append({
                    "name": name,
                    "type": "dynamic",
                    "x": x, "y": y, "z": z, "size": size,
                })
                count += 1
            except Exception as exc:
                logger.warning("Failed to spawn dynamic obstacle: %s", exc)

        return count

    def spawn_drone(self) -> bool:
        """Spawn the drone vehicle in the AirSim scene.

        Returns:
            True on success.
        """
        if self.client is None:
            return False

        try:
            sp = self.config.spawn_position
            pose = airsim.Pose(  # type: ignore[union-attr]
                airsim.Vector3r(sp[0], sp[1], sp[2]),  # type: ignore[union-attr]
                airsim.Quaternionr(  # type: ignore[union-attr]
                    airsim.to_quaternion(  # type: ignore[union-attr]
                        math.radians(self.config.spawn_heading), 0, 0  # type: ignore[union-attr]
                    )
                ),
            )
            self.client.simSetVehiclePose(pose, ignore_collision=True)
            logger.info("Drone spawned at %s.", sp)
            return True
        except Exception as exc:
            logger.error("Drone spawn failed: %s", exc)
            return False

    def remove_object(self, name: str) -> bool:
        """Remove a spawned object from the scene.

        Args:
            name: Object name.

        Returns:
            True on success.
        """
        if self.client is None:
            return False
        try:
            self.client.simDestroyObject(name)
            self.spawned_objects = [
                o for o in self.spawned_objects if o.get("name") != name
            ]
            return True
        except Exception:
            return False

    def clear_all(self) -> None:
        """Remove all spawned objects."""
        for obj in self.spawned_objects:
            self.remove_object(obj["name"])
        self.spawned_objects.clear()
        self.obstacles.clear()

    # ── Weather ──────────────────────────────────────────────────────

    def set_weather(
        self,
        wind_speed: float = 0.0,
        wind_direction: float = 0.0,
        rain_intensity: float = 0.0,
        fog_density: float = 0.0,
        cloudiness: float = 0.0,
    ) -> None:
        """Configure weather conditions.

        Args:
            wind_speed: Wind speed in m/s.
            wind_direction: Wind direction in degrees.
            rain_intensity: Rain intensity (0-1).
            fog_density: Fog density (0-1).
            cloudiness: Cloud cover (0-1).
        """
        if self.client is None:
            return

        try:
            self.client.simSetWeather(
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                rain_intensity=rain_intensity,
                fog_density=fog_density,
                cloudiness=cloudiness,
            )
            logger.info(
                "Weather: wind=%.1f m/s, rain=%.1f, fog=%.1f",
                wind_speed, rain_intensity, fog_density,
            )
        except Exception as exc:
            logger.error("Set weather failed: %s", exc)

    # ── Coordinate helpers ───────────────────────────────────────────

    def grid_to_airsim_position(
        self,
        grid_x: float,
        grid_y: float,
        altitude: float = -3.0,
        scale: float = 1.0,
    ) -> Tuple[float, float, float]:
        """Convert grid coordinates to AirSim 3D position.

        Args:
            grid_x: Grid X.
            grid_y: Grid Y.
            altitude: Flight altitude (negative is up in NED).
            scale: Meters per grid cell.

        Returns:
            (x, y, z) in AirSim NED frame.
        """
        return (
            grid_x * scale,
            grid_y * scale,
            altitude,
        )

    def get_spawn_points_from_grid(
        self,
        obstacle_positions: List[Tuple[int, int]],
        scale: float = 1.0,
        height: float = -0.5,
    ) -> List[Tuple[float, float, float]]:
        """Convert a list of grid obstacle positions to AirSim spawn positions.

        Args:
            obstacle_positions: List of (grid_x, grid_y) obstacle cells.
            scale: Meters per grid cell.
            height: Z height for spawning.

        Returns:
            List of (x, y, z) AirSim positions.
        """
        return [
            (gx * scale, gy * scale, height)
            for gx, gy in obstacle_positions
        ]

    # ── Information ──────────────────────────────────────────────────

    def get_scene_info(self) -> Dict[str, Any]:
        """Return information about the current scene configuration."""
        return {
            "scene_name": self.config.scene_name,
            "num_spawned_objects": len(self.spawned_objects),
            "num_obstacles": len(self.obstacles),
            "time_of_day": self.config.time_of_day,
            "sun_intensity": self.config.sun_intensity,
            "enable_shadows": self.config.enable_shadows,
            "enable_fog": self.config.enable_fog,
        }

    def get_obstacles_as_grid(self) -> List[Tuple[int, int]]:
        """Return spawned obstacles as grid cell positions."""
        return [
            (int(o.get("grid_x", 0)), int(o.get("grid_y", 0)))
            for o in self.obstacles
        ]