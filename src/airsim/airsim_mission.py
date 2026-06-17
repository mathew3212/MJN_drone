"""
AirSim Mission Runner
=====================
Integrates the AirSim bridge with the existing MJN mission framework.
Provides a mission loop that uses AirSim for realistic 3D physics
and sensor data while leveraging MJN's navigation, planning, and
autonomy subsystems.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any

from src.airsim.airsim_config import AirSimConfig
from src.airsim.airsim_bridge import AirSimBridge, SimulationMode
from src.airsim.airsim_world import AirSimWorldManager
from src.core.drone import Drone
from src.core.config import (
    DRONE_START,
    TARGET_POS,
    WORLD_WIDTH,
    WORLD_HEIGHT,
)

logger = logging.getLogger(__name__)


@dataclass
class AirSimMissionConfig:
    """Configuration for an AirSim-powered mission."""

    grid_width: int = WORLD_WIDTH
    grid_height: int = WORLD_HEIGHT
    drone_start: Tuple[int, int] = DRONE_START
    target_pos: Tuple[int, int] = TARGET_POS
    flight_altitude: float = -3.0
    flight_speed: float = 3.0
    scan_radius: float = 8.0
    frame_delay: float = 0.02
    use_airsim: bool = True
    sync_obstacles_to_airsim: bool = True
    obstacle_scale: float = 1.0
    enable_weather: bool = False
    wind_speed: float = 0.0


@dataclass
class AirSimMissionState:
    """Runtime state of an AirSim mission."""

    step: int = 0
    active: bool = False
    drone_ready: bool = False
    obstacles_synced: int = 0
    total_distance: float = 0.0
    collision_events: int = 0
    last_gps: Optional[Tuple[float, float]] = None
    last_battery: float = 100.0


class AirSimMissionRunner:
    """
    Runs a mission with AirSim-backed 3D simulation.

    Integrates:
    - AirSim bridge for drone control and sensors
    - AirSim world manager for scene setup
    - Existing MJN mission subsystems (planner, navigation, autonomy)
    - Seamless fallback to 2D when AirSim is unavailable
    """

    def __init__(
        self,
        airsim_config: Optional[AirSimConfig] = None,
        mission_config: Optional[AirSimMissionConfig] = None,
    ) -> None:
        self.airsim_config = airsim_config or AirSimConfig()
        self.mission_config = mission_config or AirSimMissionConfig()
        self.mission_state = AirSimMissionState()

        # Bridge and world manager
        self.bridge = AirSimBridge(self.airsim_config)
        self.world_manager = AirSimWorldManager(
            self.airsim_config.world
        )

        # MJN drone (for 2D compatibility)
        self.drone = Drone(self.mission_config.drone_start)

        # Path and telemetry
        self.current_path: List[Tuple[int, int]] = []
        self.current_goal: Optional[Tuple[int, int]] = None

    # ── Setup ────────────────────────────────────────────────────────

    def setup(self) -> bool:
        """Initialize the AirSim bridge and prepare the mission.

        Returns:
            True if setup succeeded (or 2D fallback is active).
        """
        success = self.bridge.initialize(
            grid_width=self.mission_config.grid_width,
            grid_height=self.mission_config.grid_height,
            use_airsim=self.mission_config.use_airsim,
        )

        if self.bridge.is_airsim_active():
            # Set up the world manager
            self.world_manager.set_client(self.bridge.drone.client)

            # Configure scene
            self.world_manager.configure_scene()

            # Spawn the drone
            self.world_manager.spawn_drone()

            # Take off
            success = self.bridge.takeoff(
                altitude=self.mission_config.flight_altitude
            )

            if self.mission_config.enable_weather:
                self.world_manager.set_weather(
                    wind_speed=self.mission_config.wind_speed,
                )

        self.mission_state.active = True
        self.mission_state.drone_ready = True
        logger.info(
            "Mission setup complete. AirSim: %s",
            self.bridge.is_airsim_active(),
        )
        return success

    def sync_obstacles(
        self,
        obstacle_grid: List[Tuple[int, int]],
    ) -> int:
        """Synchronize obstacles from the MJN grid to AirSim.

        Args:
            obstacle_grid: List of (grid_x, grid_y) obstacle positions.

        Returns:
            Number of 3D objects spawned.
        """
        if not self.bridge.is_airsim_active():
            return 0

        count = self.world_manager.spawn_obstacles(
            obstacle_grid, scale=self.mission_config.obstacle_scale,
        )
        self.mission_state.obstacles_synced = count
        return count

    # ── Per-step update ──────────────────────────────────────────────

    def step_update(
        self,
        visible_obstacles: Optional[List[Tuple[int, int]]] = None,
    ) -> Dict[str, Any]:
        """Execute one simulation step.

        Args:
            visible_obstacles: Obstacles detected by sensors this step.

        Returns:
            Dictionary with step telemetry.
        """
        result: Dict[str, Any] = {
            "step": self.mission_state.step,
            "airsim_active": self.bridge.is_airsim_active(),
        }

        if self.bridge.is_airsim_active():
            # Update drone from AirSim 3D state
            self.bridge.update_drone_from_airsim(self.drone)

            # Read sensors
            gps = self.bridge.read_gps()
            self.mission_state.last_gps = gps
            result["gps"] = gps

            imu = self.bridge.read_imu()
            result["imu"] = imu

            # Check battery
            batt = self.bridge.get_battery_info()
            self.mission_state.last_battery = batt["remaining_percent"]
            result["battery"] = batt

            # Check collision
            if self.bridge.check_collision():
                self.mission_state.collision_events += 1
                result["collision"] = True
                logger.warning("Step %d: collision detected!",
                               self.mission_state.step)
            else:
                result["collision"] = False

            # Read LiDAR and convert to grid obstacles
            airsim_obstacles = self.bridge.read_lidar(
                scan_radius=self.mission_config.scan_radius,
            )
            result["airsim_obstacles"] = airsim_obstacles
        else:
            # 2D mode: just use the MJN drone's current position
            result["grid_position"] = self.drone.position

        # Track distance
        self.mission_state.total_distance += self.drone.speed * 0.02

        self.mission_state.step += 1
        return result

    # ── Movement commands ────────────────────────────────────────────

    def move_to_grid_waypoint(
        self,
        grid_x: float,
        grid_y: float,
    ) -> bool:
        """Move the drone to a grid waypoint.

        Args:
            grid_x: Target X on the 2D grid.
            grid_y: Target Y on the 2D grid.

        Returns:
            True on success.
        """
        if self.bridge.is_airsim_active():
            return self.bridge.move_grid_waypoint(
                grid_x, grid_y,
                speed=self.mission_config.flight_speed,
            )
        else:
            # 2D mode: directly set drone position
            self.drone.x = grid_x
            self.drone.y = grid_y
            return True

    def hover(self) -> bool:
        """Hover in place."""
        if self.bridge.is_airsim_active():
            return self.bridge.hover()
        return True

    # ── Telemetry ────────────────────────────────────────────────────

    def get_telemetry(self) -> Dict[str, Any]:
        """Get comprehensive mission telemetry."""
        telemetry: Dict[str, Any] = {
            "mission_step": self.mission_state.step,
            "mission_active": self.mission_state.active,
            "drone_position_2d": self.drone.position,
            "airsim_active": self.bridge.is_airsim_active(),
            "total_distance": self.mission_state.total_distance,
            "collision_events": self.mission_state.collision_events,
            "battery_percent": self.mission_state.last_battery,
        }

        if self.bridge.is_airsim_active():
            status = self.bridge.get_status()
            telemetry["airsim_status"] = status
            telemetry["drone_state_3d"] = status.get("drone_state")
            telemetry["position_3d"] = status.get("position_3d")
            telemetry["heading_deg"] = status.get("heading", 0)
            telemetry["speed_ms"] = status.get("speed", 0)
        else:
            telemetry["drone_state_2d"] = {
                "x": self.drone.x,
                "y": self.drone.y,
                "heading": self.drone.heading,
                "speed": self.drone.speed,
            }

        return telemetry

    def print_step_report(self) -> None:
        """Print a formatted step report to the console."""
        step = self.mission_state.step
        mode = "AirSim 3D" if self.bridge.is_airsim_active() else "2D"
        pos = self.drone.position
        batt = self.mission_state.last_battery
        dist = self.mission_state.total_distance
        cols = self.mission_state.collision_events

        print(f"\n--- Step {step} [{mode}] ---")
        print(f"  Position: {pos}")
        print(f"  Battery:  {batt:.1f}%")
        print(f"  Distance: {dist:.2f} m")
        print(f"  Collisions: {cols}")
        print("-" * 40)

    # ── Teardown ─────────────────────────────────────────────────────

    def land_and_shutdown(self) -> None:
        """Land the drone and shut down the bridge."""
        logger.info("Mission: landing drone and shutting down.")
        if self.bridge.is_airsim_active():
            self.bridge.land()
        self.world_manager.clear_all()
        self.bridge.shutdown()
        self.mission_state.active = False
        logger.info(
            "Mission complete after %d steps, %.2f m traveled.",
            self.mission_state.step,
            self.mission_state.total_distance,
        )

    def get_final_report(self) -> Dict[str, Any]:
        """Return a final mission report."""
        return {
            "total_steps": self.mission_state.step,
            "total_distance_m": self.mission_state.total_distance,
            "collision_events": self.mission_state.collision_events,
            "obstacles_synced": self.mission_state.obstacles_synced,
            "final_battery": self.mission_state.last_battery,
            "airsim_used": self.bridge.is_airsim_active(),
        }

    # ── Context manager ──────────────────────────────────────────────

    def __enter__(self) -> "AirSimMissionRunner":
        self.setup()
        return self

    def __exit__(self, *args) -> None:
        self.land_and_shutdown()