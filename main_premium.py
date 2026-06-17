"""
MJN Premium Drone Simulation
=============================
World-class autonomous drone simulation platform.

Integrates:
  - Premium procedural world (cities, forests, rivers, roads, vehicles)
  - Premium dashboard (glassmorphism, HDR, live telemetry, cognitive viz)
  - Cinematic camera system (10 modes)
  - Vision engine (dynamic lighting, day/night, fog, bloom)
  - Cinematic flight dynamics (smooth acceleration, coordinated turns)
  - All existing autonomy, cognition, planning, and navigation systems

Usage:
    python main_premium.py

Controls:
    [C] - Cycle camera modes
    [R] - Reset / restart mission
    [ESC] - Exit
"""

import sys
import time
import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

# Add src to path
sys.path.insert(0, '.')

from src.core.drone import Drone
from src.core.world import World as BaseWorld
from src.core.enhanced_world import EnhancedWorld
from src.core.terrain import TerrainType
from src.core.weather import WeatherType

from src.mapping.occupancy_grid import OccupancyGrid
from src.mapping.cost_map import CostMap
from src.mapping.memory_manager import MemoryManager
from src.mapping.context_map import ContextMap
from src.mapping.perception_map import PerceptionMap

from src.planning.grid_planner import GridPlanner
from src.planning.dstar_lite import DStarLite
from src.planning.path_smoother import PathSmoother
from src.planning.path_follower import PathFollower
from src.navigation.local_planner import LocalPlanner

from src.control.pid_controller import PIDController
from src.control.motion_controller import MotionController

from src.navigation.navigation_state import NavigationState
from src.navigation.navigation_manager import NavigationManager

from src.sensors.gps import GPSSensor
from src.sensors.imu import IMUSensor
from src.sensors.sensor_fusion import SensorFusion
from src.sensors.sensor_engine import SensorEngine

from src.autonomy.drone_behaviors import DroneBehaviors
from src.autonomy.behavior_tree import Selector, Sequence, Condition, Action
from src.autonomy.battery_manager import BatteryManager
from src.autonomy.mission_manager import MissionManager
from src.autonomy.emergency_manager import EmergencyManager

from src.prediction.risk_predictor import RiskPredictor
from src.prediction.trajectory_predictor import TrajectoryPredictor
from src.prediction.learned_predictor import LearnedPredictor
from src.prediction.training import collect_training_data

from src.telemetry.metrics import Metrics
from src.telemetry.logger import MissionLogger

from src.core.cognitive_state import CognitiveState
from src.core.living_world import LivingWorld
from src.core.physics_engine import PhysicsEngine
from src.core.event_bus import get_event_bus
from src.core.multi_drone import DroneAgent, SwarmCoordinator, DroneStatus
from src.core.mission_engine import MissionEngine, MissionType
from src.core.knowledge_graph import KnowledgeGraph, WorldKnowledgeBuilder
from src.core.plugin_manager import PluginManager, PluginType
from src.core.data_recorder import DataRecorder
from src.core.ai_insight import AIInsightEngine

from src.visuals import (
    PremiumWorld,
    PremiumDashboard,
    draw_premium,
    reset_premium_dashboard,
    CinematicFlightController,
    CameraSystem,
    CameraMode,
    VisionEngine,
)

from src.workspace import MissionControlWorkspace, BrainIntegration, build_mission_snapshot

# ── Configuration ────────────────────────────────────────────────────────────
WORLD_WIDTH = 100
WORLD_HEIGHT = 100
NUM_OBSTACLES = 30
DRONE_START = (5.0, 5.0)
TARGET_POS = (90.0, 90.0)
SCAN_RADIUS = 10
FRAME_DELAY = 0.016  # ~60 FPS
USE_DSTAR = False
USE_ENHANCED_WORLD = True
PREMIUM_MODE = True  # Set False to fall back to standard simulation
USE_LIVING_WORLD = True
USE_PHYSICS_ENGINE = True


@dataclass
class PremiumMissionState:
    """Premium mission state with all subsystems."""
    world: BaseWorld
    premium_world: PremiumWorld
    living_world: LivingWorld
    physics_engine: PhysicsEngine
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
    cinematic_flight: CinematicFlightController
    camera_system: CameraSystem
    vision_engine: VisionEngine


def create_premium_mission() -> PremiumMissionState:
    """Create the premium mission with all subsystems."""
    # ── World ──
    if USE_ENHANCED_WORLD:
        world = EnhancedWorld(WORLD_WIDTH, WORLD_HEIGHT, NUM_OBSTACLES)
    else:
        world = BaseWorld(WORLD_WIDTH, WORLD_HEIGHT, NUM_OBSTACLES)

    # ── Premium World ──
    premium_world = PremiumWorld(WORLD_WIDTH, WORLD_HEIGHT, seed=42)

    # Merge premium world obstacles into base world
    for ox, oy in premium_world.get_obstacle_set():
        if 0 <= ox < WORLD_WIDTH and 0 <= oy < WORLD_HEIGHT:
            world.obstacles.add((ox, oy))

    # ── Drone ──
    drone = Drone(DRONE_START)

    # ── Autonomy ──
    battery = BatteryManager()
    emergency_manager = EmergencyManager()
    behaviors = DroneBehaviors(
        drone, world,
        battery=battery,
        emergency_manager=emergency_manager,
    )

    behavior_tree = Selector([
        Sequence([Condition(behaviors.low_battery), Action(behaviors.return_home)]),
        Sequence([Condition(behaviors.collision_risk), Action(behaviors.avoid_collision)]),
        Sequence([Condition(behaviors.mission_active), Action(behaviors.navigate)]),
    ])

    # ── Sensors ──
    sensor_engine = SensorEngine(scan_radius=SCAN_RADIUS)
    occupancy_grid = OccupancyGrid(WORLD_WIDTH, WORLD_HEIGHT)
    perception_map = PerceptionMap(WORLD_WIDTH, WORLD_HEIGHT)
    memory_map = MemoryManager(WORLD_WIDTH, WORLD_HEIGHT)
    context_map = ContextMap(WORLD_WIDTH, WORLD_HEIGHT)
    cognitive_map = CognitiveState(WORLD_WIDTH, WORLD_HEIGHT)
    risk_predictor = RiskPredictor(WORLD_WIDTH, WORLD_HEIGHT)
    trajectory_predictor = TrajectoryPredictor(WORLD_WIDTH, WORLD_HEIGHT)
    learned_predictor = LearnedPredictor(WORLD_WIDTH, WORLD_HEIGHT)
    cost_map = CostMap(WORLD_WIDTH, WORLD_HEIGHT)

    # ── Planning ──
    if USE_DSTAR:
        planner = DStarLite(occupancy_grid)
    else:
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

    # ── Premium systems ──
    cinematic_flight = CinematicFlightController()
    camera_system = CameraSystem()
    vision_engine = VisionEngine()

    # ── Telemetry ──
    metrics = Metrics()
    logger = MissionLogger()
    mission_manager = MissionManager(DRONE_START, TARGET_POS)

    # ── Living World ──
    living_world = LivingWorld(WORLD_WIDTH, WORLD_HEIGHT, seed=42)
    physics_engine = PhysicsEngine()

    # ── Phase 4: Autonomous Operating Systems ──
    event_bus = get_event_bus()
    swarm = SwarmCoordinator()
    mission_engine = MissionEngine()
    knowledge_graph = KnowledgeGraph()
    knowledge_builder = WorldKnowledgeBuilder(knowledge_graph)
    plugin_mgr = PluginManager()
    data_recorder = DataRecorder()
    ai_insight = AIInsightEngine(data_recorder)

    # Register buildings in knowledge graph
    for i, bld in enumerate(living_world.buildings):
        knowledge_builder.register_building(
            f"building_{i}", bld.x, bld.y, bld.floors, bld.building_type,
            bld.has_landing_pad,
        )
    # Register charging stations
    for i, (cx, cy) in enumerate(living_world.charging_stations):
        knowledge_builder.register_charging_station(f"charge_{i}", cx, cy)

    return PremiumMissionState(
        world=world,
        premium_world=premium_world,
        living_world=living_world,
        physics_engine=physics_engine,
        drone=drone,
        sensor_engine=sensor_engine,
        occupancy_grid=occupancy_grid,
        perception_map=perception_map,
        memory_map=memory_map,
        context_map=context_map,
        cognitive_map=cognitive_map,
        risk_map=risk_predictor,
        trajectory_predictor=trajectory_predictor,
        learned_predictor=learned_predictor,
        cost_map=cost_map,
        behaviors=behaviors,
        behavior_tree=behavior_tree,
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
        cinematic_flight=cinematic_flight,
        camera_system=camera_system,
        vision_engine=vision_engine,
    )


def run_premium_mission():
    """Run the premium mission loop."""
    print("\n" + "=" * 60)
    print("  MJN DRONE — Premium Autonomous Simulation Platform")
    print("  World-class drone simulation with cinematic quality")
    print("=" * 60)
    print("\n  Controls:")
    print("    [C] Cycle camera modes")
    print("    [R] Reset mission")
    print("    [Q/ESC] Exit")
    print("=" * 60 + "\n")

    mission = create_premium_mission()

    # Unpack
    world = mission.world
    premium_world = mission.premium_world
    living_world = mission.living_world
    physics_engine = mission.physics_engine
    drone = mission.drone
    sensor_engine = mission.sensor_engine
    occupancy_grid = mission.occupancy_grid
    perception_map = mission.perception_map
    memory_map = mission.memory_map
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
    cinematic_flight = mission.cinematic_flight
    camera_system = mission.camera_system
    vision_engine = mission.vision_engine

    # GPS/IMU/Fusion
    gps = GPSSensor()
    imu = IMUSensor()
    fusion = SensorFusion()

    # ── Mission Control Workspace + Brain Integration ──
    from src.airspace import AirspaceManager
    airspace_manager = AirspaceManager(world_width=WORLD_WIDTH, world_height=WORLD_HEIGHT)
    workspace = MissionControlWorkspace(
        world_width=WORLD_WIDTH, world_height=WORLD_HEIGHT,
        figsize=(18, 10), figure_name="Workspace Widgets",
    )
    brain_integration = BrainIntegration(workspace)
    brain_integration.setup_standard_layout()
    # Set up the workspace figure and render all widgets
    workspace.setup_figure()
    workspace.render_all()

    # ── Phase 4 systems (created at loop level for scope access) ──
    event_bus = get_event_bus()
    swarm = SwarmCoordinator()
    mission_engine = MissionEngine()
    knowledge_graph = KnowledgeGraph()
    knowledge_builder = WorldKnowledgeBuilder(knowledge_graph)
    plugin_mgr = PluginManager()
    data_recorder = DataRecorder()
    ai_insight = AIInsightEngine(data_recorder)

    # Populate knowledge graph
    for i, bld in enumerate(living_world.buildings):
        knowledge_builder.register_building(
            f"building_{i}", bld.x, bld.y, bld.floors, bld.building_type,
            bld.has_landing_pad,
        )
    for i, (cx, cy) in enumerate(living_world.charging_stations):
        knowledge_builder.register_charging_station(f"charge_{i}", cx, cy)

    # Brain activity log
    brain_log = []

    # Loop state
    step_counter = 0
    emergency_state = emergency_manager.NORMAL
    global_path = None
    prev_drone_position = drone.position
    camera_mode = CameraMode.CHASE
    running = True
    smooth_path = None  # Fresh each frame

    # Key handler
    def on_key(event):
        nonlocal running, camera_mode
        if event.key == 'c':
            camera_system.cycle_mode()
            camera_mode = camera_system.current_mode
            print(f"  Camera: {camera_system.get_mode_name()}")
        elif event.key == 'r':
            print("\n  🔄 Resetting mission...")
            reset_premium_dashboard()
            # Will restart by raising KeyboardInterrupt
            raise KeyboardInterrupt("RESTART")
        elif event.key in ('q', 'escape'):
            running = False

    # Connect key handler
    fig = None
    try:
        # Initial dashboard creation to get figure
        from matplotlib import pyplot as plt
        from src.visuals.premium_dashboard import _premium_dashboard

        while running and not mission_manager.is_complete():
            # ── Check battery ──
            if battery.is_empty():
                print("\nBattery depleted. Mission aborted.")
                break
            if battery.is_low():
                print("\n⚠ LOW BATTERY WARNING")

            # ── Update mission ──
            mission_manager.update(drone.position)
            goal = mission_manager.get_current_goal()

            # ── Behavior tree ──
            behavior_tree.run()
            behavior_avoided = (behaviors.state == "AVOID")

            # ── Update living world ──
            living_world.update(drone_pos=(drone.x, drone.y))

            # ── Update world ──
            world.update()
            premium_world.update_moving_entities()

            # Get weather effects from living world
            weather_fx = living_world.get_weather_effects()

            trajectory_predictor.update(world.dynamic_obstacles)
            risk_map.update(world.dynamic_obstacles)
            learned_predictor.update(world.dynamic_obstacles)
            collect_training_data(learned_predictor, world.dynamic_obstacles, step_counter)

            # ── Sensor scan ──
            visible_obstacles = sensor_engine.scan(drone, world)
            perception_map.update(visible_obstacles)
            memory_map.update(visible_obstacles)

            # ── Update maps ──
            if goal is not None:
                context_map.update(goal)
                cognitive_map.update(perception_map, memory_map, context_map, risk_map)
                cost_map.update(
                    perception_map, memory_map, context_map, risk_map,
                    trajectory_predictor,
                    last_position=getattr(local_planner, '_last_pos', None),
                    learned_predictor=learned_predictor,
                )
            else:
                cost_map.update(
                    perception_map, memory_map, context_map, risk_map,
                    trajectory_predictor,
                    last_position=getattr(local_planner, '_last_pos', None),
                    learned_predictor=learned_predictor,
                )

            occupancy_grid.update_from_scan(
                visible_obstacles, drone.x, drone.y, sensor_engine.scan_radius,
            )

            # ── Handle inspect/land/complete ──
            if mission_manager.state in (
                mission_manager.INSPECT_TARGET,
                mission_manager.LAND,
                mission_manager.COMPLETE,
            ):
                # Determine the correct target to display
                if mission_manager.state == mission_manager.INSPECT_TARGET:
                    display_target = mission_manager.target_position
                else:
                    display_target = mission_manager.home_position
                # Still update the dash
                draw_premium(
                    world=world, drone=drone, target=display_target,
                    smooth_path=None,
                    occupancy_grid=occupancy_grid,
                    perception_map=perception_map,
                    risk_map=risk_map, memory_map=memory_map,
                    context_map=context_map, cognitive_map=cognitive_map,
                    premium_world=premium_world,
                    behavior_state=behaviors.state,
                    mission_state=mission_manager.state,
                    planner_name=planner.__class__.__name__,
                    emergency_state=emergency_state,
                    battery_percentage=battery.percentage(),
                    memory_density=memory_map.memory_density(),
                    active_cells=memory_map.active_cells(),
                    explored_percent=_explored_pct(occupancy_grid),
                    camera_mode=camera_mode,
                    living_world=living_world,
                )
                # Connect key handler
                if _premium_dashboard:
                    _premium_dashboard.fig.canvas.mpl_connect('key_press_event', on_key)
                time.sleep(FRAME_DELAY)
                continue

            # ── Path planning ──
            path = None
            if goal is not None:
                if global_path is None or local_planner.allow_replan():
                    global_path = navigation_manager.replan(drone.position, goal)
                path = global_path

            # ── Cinematic path smoothing ──
            if path:
                cinematic_path = cinematic_flight.update_path_smoothing(path)
                smooth_path = path_smoother.smooth(cinematic_path)
            else:
                smooth_path = None

            # ── Emergency evaluation ──
            emergency_state = emergency_manager.evaluate(
                drone, battery, path, sensor_ok=True,
            )

            if emergency_state in (
                emergency_manager.CRITICAL_BATTERY,
                emergency_manager.NO_PATH,
                emergency_manager.STUCK,
            ):
                if emergency_state == emergency_manager.CRITICAL_BATTERY:
                    print("\n🚨 CRITICAL BATTERY! Emergency Landing.")
                elif emergency_state == emergency_manager.NO_PATH:
                    print("\n⚠ NO PATH AVAILABLE. Aborted.")
                elif emergency_state == emergency_manager.STUCK:
                    print("\n⚠ DRONE STUCK. Aborted.")
                break

            if emergency_state == emergency_manager.LOW_BATTERY:
                print("\n⚠ LOW BATTERY! Returning Home.")
                mission_manager.state = mission_manager.RETURN_HOME

            # ── Cinematic flight control ──
            if not behavior_avoided and global_path:
                cinematic_flight.set_path(global_path)
                target_x, target_y, target_heading = cinematic_flight.update(
                    drone.x, drone.y, drone.heading,
                    dt=FRAME_DELAY,
                )

                # Use the global path for the local planner
                local_target = local_planner.update(
                    drone.position,
                    global_path,
                )
                if local_target:
                    motion_controller.update(path_follower, drone, local_target)
            else:
                target_heading = drone.heading

            # ── Compute actual speed & heading from position delta ──
            # (path_follower sets drone.x/y directly but never updates drone.speed)
            dx = drone.x - prev_drone_position[0]
            dy = drone.y - prev_drone_position[1]
            drone.speed = math.hypot(dx, dy) / max(FRAME_DELAY, 0.001)
            if drone.speed > 0.01:
                drone.heading = math.atan2(dy, dx)

            # ── Stuck detection ──
            if local_planner.stuck_frames > 0 and local_planner.update_stuck_detector(drone.position):
                print(f"Step {step_counter}: Drone Stuck -> Replanning")
                global_path = None
                metrics.stuck_events.append((step_counter, drone.position))

            # ── GPS/IMU ──
            gps_x, gps_y = gps.read(drone.x, drone.y)
            imu_dx, imu_dy = imu.read(dx, dy)
            estimated_position = fusion.update(gps_x, gps_y, imu_dx, imu_dy)

            # ── Battery ──
            current_dist = math.hypot(dx, dy)
            battery.update(
                distance_travelled=current_dist,
                obstacle_count=len(visible_obstacles),
            )

            # ── Update previous position for next frame ──
            prev_drone_position = drone.position

            # ── Record telemetry for data recorder ──
            data_recorder.record_telemetry(
                drone_id="drone_0",
                x=drone.x, y=drone.y,
                altitude=0.0, heading=drone.heading,
                speed=drone.speed, battery=battery.percentage(),
                status=mission_manager.state,
                mission_state=mission_manager.state,
                behavior_state=behaviors.state,
            )
            if path:
                data_recorder.record_planning(
                    "drone_0", planner.__class__.__name__,
                    len(path), len(path) * 1.2, "",
                )

            # ── Metrics ──
            explored = _explored_pct(occupancy_grid)
            drone_speed = current_dist
            metrics.update(
                len(path) if path else 0,
                len(visible_obstacles),
                drone.position,
                drone_speed,
            )
            logger.log(
                step_counter, drone.x, drone.y,
                len(path) if path else 0,
                len(visible_obstacles),
                explored,
            )

            step_counter += 1

            # ── Log brain activity ──
            brain_entry = {
                "step": step_counter,
                "decision": behaviors.state,
                "planner": planner.__class__.__name__ if path else "IDLE",
                "path_len": len(path) if path else 0,
                "obstacles": len(visible_obstacles),
                "battery": battery.percentage(),
                "distance_to_target": math.hypot(
                    goal[0] - drone.x, goal[1] - drone.y
                ) if goal else 0,
                "emergency": emergency_state,
                "mission": mission_manager.state,
                "explored": explored,
            }
            brain_log.append(brain_entry)
            if len(brain_log) > 300:
                brain_log.pop(0)

            # ── Status print (compact) ──
            if step_counter % 20 == 0:
                print(
                    f"  Step {step_counter:4d} | "
                    f"Pos ({drone.x:5.1f}, {drone.y:5.1f}) | "
                    f"Bat {battery.percentage():5.1f}% | "
                    f"Cam {camera_system.get_mode_name():12s} | "
                    f"Expl {explored:5.1f}%"
                )

            # ── Sync workspace with brain ──
            mission_snapshot = {
                "drone": drone,
                "battery": battery,
                "world": world,
                "current_path": path,
                "visible_obstacles": visible_obstacles,
                "current_risk": risk_map.current_risk if hasattr(risk_map, "current_risk") else 0.0,
                "ai_confidence": 0.85,
                "mission_progress": (step_counter / 1000.0) * 100,
                "target_x": goal[0] if goal else 90.0,
                "target_y": goal[1] if goal else 90.0,
                "airspace_zone_count": airspace_manager.geofence.get_zone_count(),
                "airspace_violations": airspace_manager.geofence.get_violation_count(),
                "airspace_risk_score": airspace_manager.update((drone.x, drone.y), 0.0, 0).get("airspace_risk_score", 0.0),
            }
            snapshot = build_mission_snapshot(mission_snapshot)
            brain_integration.update(snapshot)

            # ── Update workspace widget graphs (live data) ──
            try:
                workspace.update_and_render()
            except Exception:
                pass

            # ── Update premium dashboard ──
            draw_premium(
                world=world,
                drone=drone,
                target=goal,
                smooth_path=smooth_path,
                occupancy_grid=occupancy_grid,
                perception_map=perception_map,
                risk_map=risk_map,
                memory_map=memory_map,
                context_map=context_map,
                cognitive_map=cognitive_map,
                premium_world=premium_world,
                behavior_state=behaviors.state,
                mission_state=mission_manager.state,
                planner_name=planner.__class__.__name__,
                emergency_state=emergency_state,
                battery_percentage=battery.percentage(),
                memory_density=memory_map.memory_density(),
                active_cells=memory_map.active_cells(),
                explored_percent=explored,
                camera_mode=camera_mode,
                living_world=living_world,
                brain_log=brain_log,
                drone_speed=drone.speed,
                drone_altitude=0.0,
                battery_drain_rate=battery.percentage(),
                visible_obstacles=len(visible_obstacles),
                weather_fx=weather_fx,
                airspace_manager=airspace_manager,
            )

            # Connect key handler to the dashboard figure
            if _premium_dashboard:
                _premium_dashboard.fig.canvas.mpl_connect('key_press_event', on_key)

            # ── FPS control ──
            time.sleep(FRAME_DELAY)

        else:
            print("\n🎯 Mission complete! Target reached.")
            # Show final view for a few seconds
            for _ in range(50):
                draw_premium(
                    world=world, drone=drone, target=goal,
                    smooth_path=smooth_path,
                    occupancy_grid=occupancy_grid,
                    perception_map=perception_map,
                    risk_map=risk_map, memory_map=memory_map,
                    context_map=context_map, cognitive_map=cognitive_map,
                    premium_world=premium_world,
                    behavior_state=behaviors.state,
                    mission_state=mission_manager.COMPLETE,
                    planner_name=planner.__class__.__name__,
                    emergency_state=emergency_state,
                    battery_percentage=battery.percentage(),
                    memory_density=memory_map.memory_density(),
                    active_cells=memory_map.active_cells(),
                    explored_percent=_explored_pct(occupancy_grid),
                    camera_mode=camera_mode,
                )
                time.sleep(FRAME_DELAY)

    except KeyboardInterrupt:
        print("\n\nMission stopped by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close workspace figure if it exists
        try:
            if workspace.fig is not None:
                plt.close(workspace.fig)
        except Exception:
            pass
        print("\n" + "=" * 60)
        print("  Mission Summary")
        print("=" * 60)
        metrics.report(DRONE_START, TARGET_POS, 0)
        battery.report()

        # ── Phase 4: AI Insight Report ──
        data_recorder.advance_frame()
        report = ai_insight.generate_report("main_mission")
        print(f"\n  AI INSIGHT REPORT — Grade: {report.grade}")
        for section, text in report.sections.items():
            print(f"    {section}: {text}")
        print(f"  Suggestions:")
        for s in report.suggestions:
            print(f"    → {s}")
        print(f"  Knowledge Graph: {knowledge_graph.get_stats()}")
        print(f"  Event Bus: {event_bus.event_count} events, {event_bus.subscriber_count} subscribers")

        print(f"\n  Total Steps: {step_counter}")
        print(f"  Camera Modes Available: 10")
        print(f"  Premium World Features: "
              f"Cities, Forests, Rivers, Roads, Vehicles, Pedestrians, Birds")
        print(f"  Living World: {len(living_world.vehicles)} vehicles, "
              f"{len(living_world.pedestrians)} pedestrians, "
              f"{len(living_world.bird_flocks)} bird flocks")
        print(f"  Living World Events: {len(living_world.event_history)} generated")
        print(f"  World Time: Day {living_world.weather.day_count}, "
              f"Traffic: {living_world.traffic_density:.0%}")
        print(f"  Visual Effects: Dynamic Lighting, Day/Night, Fog, Bloom")
        print(f"  Phase 4: Event Bus, Multi-Drone, Mission Engine, Knowledge Graph")
        print(f"           Plugin Manager, Data Recorder, AI Insight Engine")
        print("=" * 60)


def _explored_pct(occupancy_grid: OccupancyGrid) -> float:
    """Fraction of the grid that has been explored."""
    grid = np.asarray(occupancy_grid.grid)
    explored_cells = np.count_nonzero(grid != occupancy_grid.UNKNOWN)
    total_cells = occupancy_grid.width * occupancy_grid.height
    return (explored_cells / total_cells) * 100 if total_cells else 0.0


def main():
    """Top-level entry point."""
    print("Initializing MJN Premium Drone Simulation...")
    try:
        run_premium_mission()
    finally:
        reset_premium_dashboard()


if __name__ == "__main__":
    main()