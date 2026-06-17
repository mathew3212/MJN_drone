"""
MJN Drone Mission — AirSim Mode
================================
Entry point for running MJN autonomous drone missions using
AirSim's realistic 3D physics and sensor simulation.

Falls back to the native 2D simulation when AirSim is not available.

Usage:
    # With AirSim running:
    python main_airsim.py

    # Force 2D fallback mode:
    python main_airsim.py --no-airsim

    # With custom settings:
    python main_airsim.py --ip 127.0.0.1 --port 41451 --speed 2.0
"""

import argparse
import logging
import sys
import time
from typing import Optional

import numpy as np

from src.airsim import (
    AirSimConfig,
    AirSimBridge,
    AirSimMissionRunner,
)
from src.airsim.airsim_config import (
    AirSimConnectionConfig,
    AirSimDroneConfig,
    AirSimSensorConfig,
    AirSimWorldConfig,
)
from src.core.drone import Drone
from src.core.config import (
    DRONE_START,
    TARGET_POS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
    NUM_OBSTACLES,
)
from src.core.world import World
from src.mapping.cost_map import CostMap
from src.mapping.context_map import ContextMap
from src.core.cognitive_state import CognitiveState
from src.mapping.memory_manager import MemoryManager
from src.mapping.occupancy_grid import OccupancyGrid
from src.mapping.perception_map import PerceptionMap
from src.prediction.risk_predictor import RiskPredictor
from src.prediction.trajectory_predictor import TrajectoryPredictor
from src.prediction.learned_predictor import LearnedPredictor
from src.prediction.training import collect_training_data
from src.sensors.sensor_engine import SensorEngine
from src.sensors.gps import GPSSensor
from src.sensors.imu import IMUSensor
from src.sensors.sensor_fusion import SensorFusion
from src.autonomy.behavior_tree import Selector, Sequence, Condition, Action
from src.autonomy.drone_behaviors import DroneBehaviors
from src.autonomy.battery_manager import BatteryManager
from src.autonomy.mission_manager import MissionManager
from src.autonomy.emergency_manager import EmergencyManager
from src.telemetry.metrics import Metrics
from src.telemetry.logger import MissionLogger
from src.planning.grid_planner import GridPlanner
from src.planning.path_smoother import PathSmoother
from src.planning.path_follower import PathFollower
from src.control.motion_controller import MotionController
from src.control.pid_controller import PIDController
from src.navigation.navigation_manager import NavigationManager
from src.navigation.navigation_state import NavigationState
from src.navigation.local_planner import LocalPlanner

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="MJN Drone Mission with AirSim integration",
    )
    parser.add_argument(
        "--no-airsim",
        action="store_true",
        help="Disable AirSim and use native 2D simulation.",
    )
    parser.add_argument(
        "--ip",
        type=str,
        default="127.0.0.1",
        help="AirSim server IP address.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=41451,
        help="AirSim server port.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=3.0,
        help="Drone flight speed (m/s).",
    )
    parser.add_argument(
        "--altitude",
        type=float,
        default=-3.0,
        help="Flight altitude (NED, negative = up).",
    )
    parser.add_argument(
        "--scan-radius",
        type=float,
        default=8.0,
        help="LiDAR scan radius (meters).",
    )
    parser.add_argument(
        "--enable-weather",
        action="store_true",
        help="Enable weather effects.",
    )
    parser.add_argument(
        "--wind-speed",
        type=float,
        default=0.0,
        help="Wind speed (m/s).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def create_airsim_config(args: argparse.Namespace) -> AirSimConfig:
    """Create AirSim configuration from command-line arguments."""
    return AirSimConfig(
        connection=AirSimConnectionConfig(
            ip=args.ip,
            port=args.port,
        ),
        drone=AirSimDroneConfig(
            default_speed=args.speed,
        ),
        sensors=AirSimSensorConfig(),
        world=AirSimWorldConfig(
            enable_weather=args.enable_weather,
        ),
    )


def run_airsim_mission(args: argparse.Namespace) -> None:
    """Run a full mission with AirSim integration.

    This is the main mission loop that:
    1. Sets up the AirSim bridge
    2. Creates all MJN subsystems
    3. Synchronizes the 2D world with AirSim
    4. Runs the navigation/planning/autonomy loop
    5. Reads real sensor data from AirSim
    6. Provides seamless fallback to 2D
    """
    # ── Create configs ───────────────────────────────────────────
    airsim_config = create_airsim_config(args)
    use_airsim = not args.no_airsim

    # ── Initialize AirSim mission runner ─────────────────────────
    mission_runner = AirSimMissionRunner(
        airsim_config=airsim_config,
    )
    mission_runner.mission_config.use_airsim = use_airsim
    mission_runner.mission_config.scan_radius = args.scan_radius
    mission_runner.mission_config.flight_speed = args.speed
    mission_runner.mission_config.flight_altitude = args.altitude
    mission_runner.mission_config.enable_weather = args.enable_weather
    mission_runner.mission_config.wind_speed = args.wind_speed

    print("=" * 60)
    print("  MJN Autonomous Drone Navigation System")
    print("  AirSim 3D Mode" if use_airsim else "  Native 2D Mode")
    print("=" * 60)

    # ── Setup AirSim connection ──────────────────────────────────
    success = mission_runner.setup()

    if use_airsim and not mission_runner.bridge.is_airsim_active():
        print("\n⚠  AirSim not available. Falling back to 2D mode.\n")

    # ── Create MJN subsystems ───────────────────────────────────
    world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_OBSTACLES)
    drone = mission_runner.drone
    battery = BatteryManager()
    emergency_manager = EmergencyManager()

    behaviors = DroneBehaviors(
        drone, world, battery=battery,
        emergency_manager=emergency_manager,
    )

    behavior_tree = Selector([
        Sequence([
            Condition(behaviors.low_battery),
            Action(behaviors.return_home),
        ]),
        Sequence([
            Condition(behaviors.collision_risk),
            Action(behaviors.avoid_collision),
        ]),
        Sequence([
            Condition(behaviors.mission_active),
            Action(behaviors.navigate),
        ]),
    ])

    sensor_engine = SensorEngine(scan_radius=args.scan_radius)
    occupancy_grid = OccupancyGrid(WORLD_WIDTH, WORLD_HEIGHT)
    perception_map = PerceptionMap(WORLD_WIDTH, WORLD_HEIGHT)
    memory_engine = MemoryManager(WORLD_WIDTH, WORLD_HEIGHT)
    context_map = ContextMap(WORLD_WIDTH, WORLD_HEIGHT)
    cognitive_map = CognitiveState(WORLD_WIDTH, WORLD_HEIGHT)
    risk_predictor = RiskPredictor(WORLD_WIDTH, WORLD_HEIGHT)
    trajectory_predictor = TrajectoryPredictor(WORLD_WIDTH, WORLD_HEIGHT)
    learned_predictor = LearnedPredictor(WORLD_WIDTH, WORLD_HEIGHT)
    cost_map = CostMap(WORLD_WIDTH, WORLD_HEIGHT)

    planner = GridPlanner(occupancy_grid, cost_map)
    path_smoother = PathSmoother(interpolation_points=5)
    heading_pid = PIDController()
    path_follower = PathFollower(heading_pid=heading_pid)
    motion_controller = MotionController()
    navigation_state = NavigationState()
    local_planner = LocalPlanner()
    navigation_manager = NavigationManager(
        planner, path_follower, motion_controller, navigation_state,
    )

    metrics = Metrics()
    logger_inst = MissionLogger()
    mission_manager = MissionManager(DRONE_START, TARGET_POS)

    # ── Sync obstacles to AirSim ────────────────────────────────
    if mission_runner.bridge.is_airsim_active():
        obstacle_list = list(world.obstacles)
        mission_runner.sync_obstacles(obstacle_list)
        print(
            f"Synced {len(obstacle_list)} obstacles to AirSim."
        )

    # ── GPS / IMU / Fusion ──────────────────────────────────────
    gps = GPSSensor()
    imu = IMUSensor()
    fusion = SensorFusion()

    # ── Loop state ──────────────────────────────────────────────
    step = 0
    last_position: Optional[tuple] = None
    global_path = None
    prev_drone_position = drone.position

    print("\nStarting mission...\n")

    while not mission_manager.is_complete():
        # ── Battery check ───────────────────────────────────
        if battery.is_empty():
            print("\nBattery depleted. Mission aborted.")
            break

        # ── AirSim step update ──────────────────────────────
        step_result = mission_runner.step_update()

        # Check AirSim battery
        if mission_runner.bridge.is_airsim_active():
            airsim_batt = step_result.get("battery", {})
            remaining = airsim_batt.get("remaining_percent", 100)
            if remaining <= 0:
                print("\nAirSim battery depleted. Mission aborted.")
                break

        # Check collision
        if step_result.get("collision", False):
            print(f"\n⚠ Collision at step {step}!")
            emergency_manager.state = emergency_manager.CRITICAL

        # ── Update mission manager ──────────────────────────
        mission_manager.update(drone.position)

        if (
            mission_manager.state == mission_manager.INSPECT_TARGET
            and metrics.target_reach_step == -1
        ):
            metrics.target_reach_step = step

        if prev_drone_position != drone.position:
            dist = ((drone.x - prev_drone_position[0]) ** 2
                    + (drone.y - prev_drone_position[1]) ** 2) ** 0.5
            metrics.total_distance_travelled += dist
            prev_drone_position = drone.position

        # ── Behavior tree ───────────────────────────────────
        behavior_tree.run()

        # ── World update ────────────────────────────────────
        world.update()
        trajectory_predictor.update(world.dynamic_obstacles)
        risk_predictor.update(world.dynamic_obstacles)
        learned_predictor.update(world.dynamic_obstacles)
        collect_training_data(
            learned_predictor, world.dynamic_obstacles, step
        )

        # ── Sensor scan ────────────────────────────────────
        if mission_runner.bridge.is_airsim_active():
            # Use AirSim LiDAR data
            visible_obstacles_raw = step_result.get(
                "airsim_obstacles", []
            )
            # Convert to list of tuples expected by MJN
            visible_obstacles = [
                tuple(o) if isinstance(o, (list, tuple))
                else (o, o)
                for o in visible_obstacles_raw
            ]
        else:
            # Use 2D sensor engine
            visible_obstacles = sensor_engine.scan(drone, world)

        perception_map.update(visible_obstacles)
        memory_engine.update(visible_obstacles)

        # ── Goal & map updates ──────────────────────────────
        goal = mission_manager.get_current_goal()
        if goal is not None:
            context_map.update(goal)
            cognitive_map.update(
                perception_map, memory_engine, context_map,
                risk_predictor,
            )
        cost_map.update(
            perception_map, memory_engine, context_map,
            risk_predictor, trajectory_predictor,
            last_position=last_position,
            learned_predictor=learned_predictor,
        )

        # ── Occupancy grid ──────────────────────────────────
        occupancy_grid.update_from_scan(
            visible_obstacles, drone.x, drone.y,
            sensor_engine.scan_radius,
        )

        # ── INSPECT_TARGET state ────────────────────────────
        if mission_manager.state == mission_manager.INSPECT_TARGET:
            time.sleep(0.02)
            mission_runner.print_step_report()
            step += 1
            continue

        if mission_manager.state in (
            mission_manager.LAND, mission_manager.COMPLETE
        ):
            time.sleep(0.02)
            step += 1
            continue

        # ── Path planning ───────────────────────────────────
        path = None
        if goal is not None:
            if global_path is None or local_planner.allow_replan():
                global_path = navigation_manager.replan(
                    drone.position, goal,
                )
            path = global_path

        smooth_path = path_smoother.smooth(path)

        # ── Emergency evaluation ────────────────────────────
        emergency_state = emergency_manager.evaluate(
            drone, battery, path, sensor_ok=True,
        )

        if emergency_state == emergency_manager.CRITICAL_BATTERY:
            print("\n🚨 CRITICAL BATTERY! Emergency Landing.")
            break
        if emergency_state == emergency_manager.LOW_BATTERY:
            mission_manager.state = mission_manager.RETURN_HOME
        if emergency_state == emergency_manager.NO_PATH:
            print("\n⚠ NO PATH AVAILABLE.")
            break
        if emergency_state == emergency_manager.STUCK:
            print("\n⚠ DRONE STUCK.")
            break

        # ── Move drone ──────────────────────────────────────
        local_target = local_planner.update(
            drone.position, global_path
        )
        if local_target:
            if mission_runner.bridge.is_airsim_active():
                # Move in AirSim 3D space
                mission_runner.move_to_grid_waypoint(
                    local_target[0], local_target[1]
                )
            else:
                # 2D movement
                motion_controller.update(
                    path_follower, drone, local_target
                )
        last_position = drone.position

        # ── Stuck detection ─────────────────────────────────
        if (
            local_planner.stuck_frames > 0
            and local_planner.update_stuck_detector(
                drone.position
            )
        ):
            global_path = None
            metrics.stuck_events.append((step, drone.position))

        # ── GPS / IMU / Sensor Fusion ──────────────────────
        if mission_runner.bridge.is_airsim_active():
            gps_x, gps_y = step_result.get(
                "gps", (drone.x, drone.y)
            )
        else:
            dx = drone.x - prev_drone_position[0]
            dy = drone.y - prev_drone_position[1]
            gps_x, gps_y = gps.read(drone.x, drone.y)
            imu_dx, imu_dy = imu.read(dx, dy)
            fusion.update(gps_x, gps_y, imu_dx, imu_dy)

        # ── Battery update ──────────────────────────────────
        dist_moved = metrics.direct_distance(
            prev_drone_position, drone.position
        )
        battery.update(
            distance_travelled=dist_moved,
            obstacle_count=len(visible_obstacles),
        )

        # ── Metrics & logging ───────────────────────────────
        explored = (
            np.count_nonzero(
                np.asarray(occupancy_grid.grid)
                != occupancy_grid.UNKNOWN
            )
            / (WORLD_WIDTH * WORLD_HEIGHT) * 100
        )
        metrics.update(
            len(path) if path else 0,
            len(visible_obstacles),
            drone.position,
            dist_moved,
        )
        logger_inst.log(
            step, drone.x, drone.y,
            len(path) if path else 0,
            len(visible_obstacles),
            explored,
        )

        step += 1
        mission_runner.print_step_report()

        time.sleep(0.02)

    else:
        print("\n🎯 Target reached! Mission complete.")

    # ── Teardown ─────────────────────────────────────────────────
    mission_runner.land_and_shutdown()

    # ── Final report ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  MISSION REPORT")
    print("=" * 60)
    airsim_report = mission_runner.get_final_report()
    print(f"  AirSim used:     {airsim_report['airsim_used']}")
    print(f"  Total steps:     {airsim_report['total_steps']}")
    print(f"  Distance:        {airsim_report['total_distance_m']:.2f} m")
    print(f"  Collisions:      {airsim_report['collision_events']}")
    print(f"  Final battery:   {airsim_report['final_battery']:.1f}%")
    print("-" * 60)
    metrics.report(DRONE_START, TARGET_POS, 0)
    battery.report()
    print("=" * 60)


def main() -> None:
    """Top-level entry point."""
    args = parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        run_airsim_mission(args)
    except KeyboardInterrupt:
        print("\nMission stopped by user.")
    except Exception as exc:
        logging.exception("Mission failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()