"""
MJN Autonomous Drone Navigation System
=======================================
Main entry point for the drone mission simulation.

Integrates all subsystems: sensors, mapping, planning, prediction,
autonomy (behavior tree, emergency management, battery), telemetry,
and visualization into a cohesive mission loop.
"""

import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.core.cognitive_state import CognitiveState
from src.core.config import DRONE_START, NUM_OBSTACLES, TARGET_POS, WORLD_HEIGHT, WORLD_WIDTH
from src.mapping.context_map import ContextMap
from src.mapping.cost_map import CostMap
from src.core.drone import Drone
from src.planning.dstar_lite import DStarLite
from src.planning.grid_planner import GridPlanner
from src.planning.path_smoother import PathSmoother
from src.telemetry.logger import MissionLogger
from src.mapping.memory_manager import MemoryManager
from src.telemetry.metrics import Metrics
from src.mapping.occupancy_grid import OccupancyGrid
from src.mapping.perception_map import PerceptionMap
from src.prediction.risk_predictor import RiskPredictor
from src.sensors.sensor_engine import SensorEngine
from src.sensors.gps import GPSSensor
from src.sensors.imu import IMUSensor
from src.sensors.sensor_fusion import SensorFusion
from src.prediction.trajectory_predictor import TrajectoryPredictor
from src.prediction.learned_predictor import LearnedPredictor
from src.prediction.training import collect_training_data
from src.autonomy.behavior_tree import Selector, Sequence, Condition, Action
from src.autonomy.drone_behaviors import DroneBehaviors
from src.autonomy.battery_manager import BatteryManager
from src.autonomy.mission_manager import MissionManager
from src.autonomy.emergency_manager import EmergencyManager
from src.telemetry.military_viz import draw, reset_dashboard
from src.core.world import World
from src.core.enhanced_world import EnhancedWorld
from src.core.weather import WeatherType
from src.planning.path_follower import PathFollower
from src.control.motion_controller import MotionController
from src.control.pid_controller import PIDController
from src.navigation.navigation_state import NavigationState
from src.navigation.navigation_manager import NavigationManager
from src.navigation.local_planner import LocalPlanner

# ── Configuration ──────────────────────────────────────────────────────────
USE_DSTAR = False
SCAN_RADIUS = 8
FRAME_DELAY = 0.02
HOME_POSITION = DRONE_START
USE_ENHANCED_WORLD = True
WEATHER_CHANGE_INTERVAL = 200  # steps between weather changes


@dataclass
class MissionState:
    """Container for all mission subsystem instances."""
    world: World
    drone: Drone
    sensor_engine: SensorEngine
    occupancy_grid: OccupancyGrid
    perception_map: PerceptionMap
    memory_map: MemoryManager
    context_map: ContextMap
    cognitive_map: CognitiveState
    risk_map: RiskPredictor
    trajectory_predictor: TrajectoryPredictor
    learned_predictor: LearnedPredictor
    cost_map: CostMap
    behaviors: DroneBehaviors
    behavior_tree: Selector
    planner: DStarLite | GridPlanner
    path_smoother: PathSmoother
    metrics: Metrics
    logger: MissionLogger
    battery: BatteryManager
    mission_manager: MissionManager
    emergency_manager: EmergencyManager
    path_follower: PathFollower
    motion_controller: MotionController
    navigation_state: NavigationState
    navigation_manager: NavigationManager
    local_planner: LocalPlanner


def create_mission() -> MissionState:
    """Instantiate all mission subsystems and wire them together.

    Returns:
        Fully initialised MissionState with all components connected.
    """
    if USE_ENHANCED_WORLD:
        world = EnhancedWorld(WORLD_WIDTH, WORLD_HEIGHT, NUM_OBSTACLES)
    else:
        world = World(WORLD_WIDTH, WORLD_HEIGHT, NUM_OBSTACLES)
    drone = Drone(DRONE_START)
    battery = BatteryManager()
    emergency_manager = EmergencyManager()

    # Behaviors — now receives references to battery and emergency_manager
    behaviors = DroneBehaviors(drone, world, battery=battery, emergency_manager=emergency_manager)

    behavior_tree = Selector([
        # Priority 1: Low battery → return home
        Sequence([
            Condition(behaviors.low_battery),
            Action(behaviors.return_home),
        ]),
        # Priority 2: Collision risk → evade
        Sequence([
            Condition(behaviors.collision_risk),
            Action(behaviors.avoid_collision),
        ]),
        # Priority 3: Normal mission navigation
        Sequence([
            Condition(behaviors.mission_active),
            Action(behaviors.navigate),
        ]),
    ])

    sensor_engine = SensorEngine(scan_radius=SCAN_RADIUS)
    occupancy_grid = OccupancyGrid(WORLD_WIDTH, WORLD_HEIGHT)
    perception_engine = PerceptionMap(WORLD_WIDTH, WORLD_HEIGHT)
    memory_engine = MemoryManager(WORLD_WIDTH, WORLD_HEIGHT)
    context_engine = ContextMap(WORLD_WIDTH, WORLD_HEIGHT)
    cognitive_engine = CognitiveState(WORLD_WIDTH, WORLD_HEIGHT)
    risk_predictor = RiskPredictor(WORLD_WIDTH, WORLD_HEIGHT)
    trajectory_predictor = TrajectoryPredictor(WORLD_WIDTH, WORLD_HEIGHT)
    learned_predictor = LearnedPredictor(WORLD_WIDTH, WORLD_HEIGHT)
    cost_map = CostMap(WORLD_WIDTH, WORLD_HEIGHT)
    planner = create_planner(occupancy_grid, cost_map)
    path_smoother = PathSmoother(interpolation_points=5)
    heading_pid = PIDController()
    path_follower = PathFollower(
        heading_pid=heading_pid
    )
    motion_controller = MotionController()
    navigation_state = NavigationState()
    local_planner = LocalPlanner()
    navigation_manager = NavigationManager(
        planner,
        path_follower,
        motion_controller,
        navigation_state,
    )
    metrics = Metrics()
    logger = MissionLogger()
    mission_manager = MissionManager(DRONE_START, TARGET_POS)

    return MissionState(
        world=world,
        drone=drone,
        sensor_engine=sensor_engine, # Removed duplicate sensor_engine
        occupancy_grid=occupancy_grid,
        perception_map=perception_engine,
        memory_map=memory_engine,
        context_map=context_engine,
        cognitive_map=cognitive_engine,
        risk_map=risk_predictor,
        trajectory_predictor=trajectory_predictor,
        learned_predictor=learned_predictor,
        behaviors=behaviors,
        behavior_tree=behavior_tree,
        cost_map=cost_map,
        planner=planner,
        path_smoother=path_smoother,
        metrics=metrics,
        battery=battery,
        logger=logger,
        mission_manager=mission_manager,
        emergency_manager=emergency_manager,
        path_follower=path_follower,
        motion_controller=motion_controller,
        navigation_state=navigation_state,
        navigation_manager=navigation_manager,
        local_planner=local_planner,
    )


def create_planner(occupancy_grid: OccupancyGrid, cost_map: Optional[CostMap] = None) -> DStarLite | GridPlanner:
    """Factory: returns DStarLite or GridPlanner based on USE_DSTAR flag."""
    if USE_DSTAR:
        return DStarLite(occupancy_grid)
    return GridPlanner(occupancy_grid, cost_map)


def explored_percent(occupancy_grid: OccupancyGrid) -> float:
    """Fraction of the grid that has been explored (not UNKNOWN)."""
    grid = np.asarray(occupancy_grid.grid)
    explored_cells = np.count_nonzero(grid != occupancy_grid.UNKNOWN)
    total_cells = occupancy_grid.width * occupancy_grid.height
    return (explored_cells / total_cells) * 100 if total_cells else 0.0


def print_step_report(step: int, planner: object, drone: Drone, path: list | None,
                       visible_obstacles: list, explored: float,
                       battery: Optional[BatteryManager] = None) -> None:
    """Print a per-step summary to the console."""
    print(f"\nStep {step}")
    print(f"Planner: {planner.__class__.__name__}")
    print(f"Drone Position: {drone.position}")
    print(f"Path Length: {len(path)}")
    print(f"Visible Obstacles: {len(visible_obstacles) if visible_obstacles else 0}")
    print(f"Map Explored: {explored:.2f}%")
    if battery:
        print(f"Battery: {battery.percentage():.2f}%")
    print("-" * 60)


def build_memory_display(memory_engine: MemoryManager) -> object:
    """Build a lightweight object with a .grid property for the heatmap."""
    memory_map_display = type("MemoryMap", (), {})()
    memory_map_display.grid = memory_engine.get_heatmap()
    return memory_map_display


def update_dashboard(
    world: World,
    drone: Drone,
    sensor_engine: SensorEngine,
    occupancy_grid: OccupancyGrid,
    perception_map: PerceptionMap,
    risk_map: RiskPredictor,
    memory_map: object,
    smooth_path: list,
    behavior_state: str,
    mission_state: str,
    current_target: tuple,
    planner_name: str,
    battery_percentage: float,
    emergency_state: str = "NORMAL",
    memory_density: Optional[float] = None,
    active_cells: Optional[int] = None,
    context_map: Optional[ContextMap] = None,
    cognitive_map: Optional[CognitiveState] = None,
    explored_percent_val: float = 0.0,
) -> None:
    """Forward current simulation state to the visualization dashboard."""
    draw(
        world,
        drone,
        current_target,
        path=smooth_path,
        occupancy_grid=occupancy_grid,
        sensor_radius=sensor_engine.scan_radius,
        perception_map=perception_map,
        risk_map=risk_map,
        memory_map=memory_map,
        context_map=context_map,
        cognitive_map=cognitive_map,
        behavior_state=behavior_state,
        mission_state=mission_state,
        planner_name=planner_name,
        emergency_state=emergency_state,
        battery_percentage=battery_percentage,
        memory_density=memory_density,
        active_cells=active_cells,
        explored_percent=explored_percent_val,
    )


def run_mission() -> tuple[Metrics, BatteryManager, int]:
    """Execute the main mission loop — the core simulation.

    The loop orchestrates:
      1. Behavior tree (battery/collision checks)
      2. World/dynamic obstacle updates
      3. Sensor scanning and perception
      4. Memory, context, cost, and cognitive map updates
      5. Path planning and smoothing
      6. Emergency evaluation
      7. Drone movement
      8. Metrics and logging
      9. Dashboard visualisation

    Returns:
        Tuple of (Metrics, BatteryManager) for final reporting.
    """
    mission = create_mission()

    # ── Unpack mission state ──────────────────────────────────────────
    world = mission.world
    drone = mission.drone
    sensor_engine = mission.sensor_engine
    occupancy_grid = mission.occupancy_grid
    perception_map = mission.perception_map
    memory_engine = mission.memory_map
    context_map = mission.context_map
    cognitive_map = mission.cognitive_map
    risk_map = mission.risk_map
    trajectory_predictor = mission.trajectory_predictor
    learned_predictor = mission.learned_predictor
    behaviors = mission.behaviors
    behavior_tree = mission.behavior_tree
    cost_map = mission.cost_map
    planner = mission.planner
    metrics = mission.metrics
    battery = mission.battery
    logger = mission.logger
    mission_manager = mission.mission_manager
    emergency_manager = mission.emergency_manager
    path_smoother = mission.path_smoother
    path_follower = mission.path_follower
    motion_controller = mission.motion_controller
    navigation_state = mission.navigation_state
    navigation_manager = mission.navigation_manager
    local_planner = mission.local_planner

    # ── GPS / IMU / Sensor Fusion ─────────────────────────────────
    gps = GPSSensor()
    imu = IMUSensor()
    fusion = SensorFusion()

    # ── Loop state ────────────────────────────────────────────────────
    step_counter = 0
    last_position: Optional[tuple] = None
    emergency_state = emergency_manager.NORMAL
    global_path = None
    prev_drone_position = drone.position
    drone_speed = 0.0

    # ── Weather cycling (enhanced world only) ────────────────────────
    import random as _rand
    weather_types = list(WeatherType)
    enhanced = hasattr(world, "weather")
    if enhanced and world.weather:
        world.weather.set_weather(_rand.choice([
            WeatherType.CLEAR, WeatherType.CLEAR, WeatherType.CLEAR,
            WeatherType.CLOUDY, WeatherType.OVERCAST,
        ]))

    while not mission_manager.is_complete():
        # ── Battery check ─────────────────────────────────────────
        if battery.is_empty():
            print("\nBattery depleted. Mission aborted.")
            break

        if battery.is_low():
            print("\n⚠ LOW BATTERY WARNING")

        # ── Update mission manager with current position ──────────
        mission_manager.update(drone.position)

        # Record target reach and return home steps
        if mission_manager.state == mission_manager.INSPECT_TARGET and metrics.target_reach_step == -1:
            metrics.target_reach_step = step_counter
        elif mission_manager.state == mission_manager.LAND and metrics.return_home_step == -1:
            metrics.return_home_step = step_counter

        # Update total distance travelled
        if prev_drone_position != drone.position:
            metrics.total_distance_travelled += ((drone.x - prev_drone_position[0])**2 + (drone.y - prev_drone_position[1])**2)**0.5
            prev_drone_position = drone.position

        # ── Run behavior tree (handles low battery / collision) ──
        behavior_tree.run()
        # Track if behavior tree triggered an avoid action that moved the drone
        behavior_avoided = (behaviors.state == "AVOID")

        # ── Weather cycling ─────────────────────────────────────
        if enhanced and step_counter > 0 and step_counter % WEATHER_CHANGE_INTERVAL == 0:
            new_weather = _rand.choice(weather_types)
            world.weather.set_weather(new_weather)
            print(f"\n🌤 Weather changed to: {new_weather.name}")

        # ── Update world state ────────────────────────────────────
        world.update()
        trajectory_predictor.update(world.dynamic_obstacles)
        risk_map.update(world.dynamic_obstacles)
        learned_predictor.update(world.dynamic_obstacles)
        collect_training_data(learned_predictor, world.dynamic_obstacles, step_counter)

        # ── Sensor scan ───────────────────────────────────────────
        visible_obstacles = sensor_engine.scan(drone, world)
        perception_map.update(visible_obstacles)
        memory_engine.update(visible_obstacles)

        # ── Get current goal from mission manager ─────────────────
        goal = mission_manager.get_current_goal()

        # ── Update maps ───────────────────────────────────────────
        if goal is not None:
            context_map.update(goal)
            cognitive_map.update(perception_map, memory_engine, context_map, risk_map)
            cost_map.update(
                perception_map,
                memory_engine,
                context_map,
                risk_map,
                trajectory_predictor,
                last_position=last_position,
                learned_predictor=learned_predictor,
            )
        else:
            cost_map.update(
                perception_map,
                memory_engine,
                context_map,
                risk_map,
                trajectory_predictor,
                last_position=last_position,
                learned_predictor=learned_predictor,
            )

        # ── Update occupancy grid from sensor data ────────────────
        occupancy_grid.update_from_scan(
            visible_obstacles,
            drone.x,
            drone.y,
            sensor_engine.scan_radius,
        )

        # ── Handle INSPECT_TARGET state (hover + show dashboard) ─
        if mission_manager.state == mission_manager.INSPECT_TARGET:
            update_dashboard(
                world, drone, sensor_engine, occupancy_grid,
                perception_map, risk_map, build_memory_display(memory_engine),
                smooth_path=None,
                behavior_state=behaviors.state,
                mission_state=mission_manager.state,
                current_target=mission_manager.target_position,
                planner_name=planner.__class__.__name__,
                battery_percentage=battery.percentage(),
                emergency_state=emergency_state,
                memory_density=memory_engine.memory_density(),
                active_cells=memory_engine.active_cells(),
                context_map=context_map,
                cognitive_map=cognitive_map,
                explored_percent_val=explored_percent(occupancy_grid),
            )
            time.sleep(FRAME_DELAY)
            continue

        # ── Skip planning for LAND / COMPLETE states ──────────────
        if mission_manager.state in (mission_manager.LAND, mission_manager.COMPLETE):
            time.sleep(FRAME_DELAY)
            continue

        # ── Path planning (with global replan gating) ──────────────
        path = None
        if goal is not None:
            if (
                global_path is None
                or local_planner.allow_replan()
            ):
                global_path = navigation_manager.replan(drone.position, goal)
            path = global_path

        smooth_path = path_smoother.smooth(path)

        # ── Emergency evaluation ───────────────────────────────────
        emergency_state = emergency_manager.evaluate(
            drone, battery, path, sensor_ok=True,
        )

        # ── Handle emergency states ────────────────────────────────
        if emergency_state == emergency_manager.CRITICAL_BATTERY:
            print("\n🚨 CRITICAL BATTERY! Emergency Landing.")
            break

        if emergency_state == emergency_manager.LOW_BATTERY:
            print("\n⚠ LOW BATTERY! Returning Home.")
            mission_manager.state = mission_manager.RETURN_HOME

        if emergency_state == emergency_manager.NO_PATH:
            print("\n⚠ NO PATH AVAILABLE. Mission aborted.")
            break

        if emergency_state == emergency_manager.STUCK:
            print("\n⚠ DRONE STUCK. Mission aborted.")
            break

        # ── Move drone along path via LocalPlanner ───────────────
        prev_pos = drone.position
        # When behavior tree triggered avoidance, skip path follower
        # movement this frame to prevent oscillation
        if not behavior_avoided:
            local_target = local_planner.update(
                drone.position,
                global_path
            )
            if local_target:
                motion_controller.update(
                    path_follower,
                    drone,
                    local_target
                )
        last_position = prev_pos  # anti-oscillation

        # ── Stuck detection → global replan trigger ─────────────
        if (
            local_planner.stuck_frames > 0
            and local_planner.update_stuck_detector(
                drone.position
            )
        ):
            print(
                f"Step {step_counter}: "
                "Drone Stuck -> Replanning"
            )
            global_path = None
            metrics.stuck_events.append((step_counter, drone.position))

        # ── GPS / IMU / Sensor Fusion ─────────────────────────
        dx = drone.x - prev_pos[0]
        dy = drone.y - prev_pos[1]
        gps_x, gps_y = gps.read(drone.x, drone.y)
        imu_dx, imu_dy = imu.read(dx, dy)
        estimated_position = fusion.update(gps_x, gps_y, imu_dx, imu_dy)

        # ── Speed calculation for metrics flow ────────────────
        current_distance_moved = metrics.direct_distance(prev_pos, drone.position)
        drone_speed = current_distance_moved

        # ── Telemetry ─────────────────────────────────────────
        print(f"GPS: ({gps_x:.2f}, {gps_y:.2f})")
        print(f"Estimated: {estimated_position}")

        battery.update(
            distance_travelled=current_distance_moved,
            obstacle_count=len(visible_obstacles),
        )

        # ── Metrics & logging ──────────────────────────────────────
        explored = explored_percent(occupancy_grid)
        metrics.update(len(path) if path else 0, len(visible_obstacles), drone.position, drone_speed)
        logger.log(
            step_counter,
            drone.x,
            drone.y,
            len(path) if path else 0,
            len(visible_obstacles),
            explored,
        )

        step_counter += 1
        print_step_report(
            step_counter, planner, drone,
            path or [], visible_obstacles, explored, battery,
        )

        # ── Update dashboard ───────────────────────────────────────
        memory_map_display = build_memory_display(memory_engine)
        update_dashboard(
            world, drone, sensor_engine, occupancy_grid,
            perception_map, risk_map, memory_map_display,
            smooth_path,
            behaviors.state,
            mission_manager.state,
            goal,
            planner.__class__.__name__,
            battery.percentage(),
            emergency_state=emergency_state,
            memory_density=memory_engine.memory_density(),
            active_cells=memory_engine.active_cells(),
            context_map=context_map,
            cognitive_map=cognitive_map,
            explored_percent_val=explored,
        )

        time.sleep(FRAME_DELAY)

    else:
        print("\n🎯 Target reached! Mission complete.")

    return metrics, battery


def print_final_report(metrics: Metrics, battery: Optional[BatteryManager] = None) -> None:
    """Print mission summary and battery report."""
    metrics.report(DRONE_START, TARGET_POS, 0)
    if battery:
        battery.report()
    print("\nMission Log: mission_log.csv")


def main() -> None:
    """Top-level entry point with clean teardown."""
    try:
        metrics, battery = run_mission()
        print_final_report(metrics, battery)
    except KeyboardInterrupt:
        print("\nMission stopped by user.")
    finally:
        import matplotlib.pyplot as plt
        reset_dashboard()
        plt.ioff()
        plt.show()


if __name__ == "__main__":
    main()