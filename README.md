# MJN Autonomous Drone Navigation System

## Overview

**MJN Drone** is a fully autonomous drone navigation and mission simulation system built in Python. It simulates a quadrotor drone navigating a 2D grid world (100×100 cells) from a start position to a target destination while avoiding static and dynamic obstacles. The system integrates **perception**, **mapping**, **planning**, **prediction**, **decision-making**, **control**, and **visualization** into a cohesive mission loop.

The project is designed as a research-grade platform for testing autonomous navigation algorithms, sensor fusion techniques, cognitive architectures, and behavior-based mission execution. It also supports integration with **AirSim** (Microsoft's realistic drone simulator) via a dedicated bridge module.

---

## Architecture (Layers & Modules)

The system is organized into **11+ package directories** under `src/`, each representing a distinct architectural layer:

```
mjn_drone/
├── main.py                     # Entry point: standard simulation
├── main_airsim.py              # Entry point: AirSim simulation
├── requirements.txt            # Python dependencies
├── src/
│   ├── core/                   # Core simulation primitives
│   ├── autonomy/               # Mission and behavior management
│   ├── control/                # Flight controllers (PID, motion, flight manager)
│   ├── navigation/             # Navigation state machine & local planners
│   ├── planning/               # Path planners (D* Lite, grid, local, path follower, smoother)
│   ├── mapping/                # Mapping (occupancy grid, cost map, spatial index, memory)
│   ├── sensors/                # Virtual sensors (GPS, IMU, LiDAR, compass, camera, sensor fusion)
│   ├── perception/             # Perception modules (future/planned)
│   ├── prediction/             # Motion prediction (attention-based, learned, scene memory)
│   ├── cognition/              # Cognitive architecture (world model, memory, attention, uncertainty, learning)
│   ├── telemetry/              # Telemetry, metrics, visualization, dashboards
│   ├── airsim/                 # AirSim integration bridge (world, drone, physics, sensors, mission)
│   ├── tests/                  # Unit and integration tests
│   └── __init__.py
├── benchmark_flight_manager.py # Performance benchmarking
├── test_*.py                   # Various test scripts
├── gen.py / gen_all.py / gen_check.py  # Code generation / validation utilities
└── NAVIGATION_REPORT.md        # Navigation capabilities report
```

---

## Key Features & Capabilities

### 1. Core Simulation (`src/core/`)
- **Drone Model (`drone.py`):** High-performance quadrotor simulation with continuous 2D dynamics tracking position (x, y), velocity (vx, vy), acceleration (ax, ay), jerk, yaw/heading angle, and speed.
- **8 Flight Modes:** ECO, NORMAL, CRUISE, SPORT, TURBO, EMERGENCY, PRECISION, LANDING — each with configurable performance envelopes (max speed, acceleration, jerk, yaw rate, energy consumption).
- **World Model (`world.py`, `enhanced_world.py`, `terrain.py`, `weather.py`):** 2D grid world with static obstacles, dynamic bouncing obstacles, terrain types, and weather conditions that affect drone performance.
- **Grid Map (`grid_map.py`):** 100×100 cell grid with obstacle representation.
- **Coordinate System (`coordinate_system.py`):** Coordinate transforms and conversions.
- **Simulation Clock (`simulation_clock.py`):** Time management for deterministic simulation.
- **Configuration (`configuration.py`):** Centralized configuration management.

### 2. Sensors (`src/sensors/`)
- **GPS (`gps.py`):** Global positioning with configurable noise and drift.
- **IMU (`imu.py`):** Inertial measurement unit with bias and noise models.
- **LiDAR (`lidar.py`):** 360° ray-cast obstacle detection.
- **Compass (`compass.py`):** Heading/magnetometer sensor.
- **Virtual Camera (`virtual_camera.py`):** Simulated optical sensor.
- **Sensor Fusion (`sensor_fusion.py`):** Kalman filter-based multi-sensor integration for state estimation.

### 3. Mapping (`src/mapping/`)
- **Occupancy Grid (`occupancy_grid.py`):** Probabilistic occupancy grid mapping from sensor data.
- **Cost Map (`cost_map.py`):** Cost-based terrain representation for path planning.
- **Spatial Index (`spatial_index.py`):** Efficient spatial queries (quadtree-based).
- **Memory Manager (`memory_manager.py`):** Persistent map memory across missions.
- **Obstacle Generator (`obstacle_generator.py`):** Dynamic obstacle generation.
- **Collision Detector (`collision_detector.py`):** Collision prediction and detection.

### 4. Planning (`src/planning/`)
- **D* Lite (`dstar_lite.py`):** Incremental heuristic search algorithm for dynamic re-planning (optimal for environments with moving obstacles).
- **Grid Planner (`grid_planner.py`):** A*/Dijkstra-based grid path search.
- **Local Planner (`local_planner.py`):** Reactive obstacle avoidance (Velocity Obstacle / ORCA-like).
- **Path Follower (`path_follower.py`):** Pure pursuit and carrot-chasing path tracking with lookahead.
- **Path Smoother (`path_smoother.py`):** Trajectory smoothing (B-spline / gradient-based).

### 5. Control (`src/control/`)
- **PID Controller (`pid_controller.py`):** Multi-axis PID controller with anti-windup.
- **Motion Controller (`motion_controller.py`):** High-level motion control interface.
- **Flight Manager (`flight_manager.py`):** Centralized flight executive managing mode transitions, velocity/acceleration profiling, and control allocation.

### 6. Navigation (`src/navigation/`)
- **Navigation State Machine (`navigation_state.py`, `navigation_manager.py`):** Manages navigation phases (INIT → TAKEOFF → NAVIGATE → AVOID → REACHED → LAND).
- **Local Planner (`local_planner.py`):** Real-time local navigation and obstacle avoidance.

### 7. Autonomy (`src/autonomy/`)
- **Mission Manager (`mission_manager.py`):** Orchestrates the full mission lifecycle — waypoint sequencing, replanning triggers, and mission status tracking.
- **Emergency Manager (`emergency_manager.py`):** Safety layer handling collision threats, low battery, sensor failure, geofence violations with graded responses (WARN → ALERT → CRITICAL → EMERGENCY_STOP).
- **Drone Behaviors (`drone_behaviors.py`):** Behavior tree-based autonomous behaviors (explore, track, avoid, return-to-home, etc.).

### 8. Prediction (`src/prediction/`)
- **Attention Predictor (`attention_predictor.py`):** Transformer-based trajectory prediction using attention mechanisms.
- **Learned Predictor (`learned_predictor.py`):** ML-based motion prediction for dynamic obstacles.
- **Scene Memory (`scene_memory.py`):** Episodic memory for observed scenes.
- **Training (`training.py`):** Training pipeline for prediction models.

### 9. Cognition (`src/cognition/`)
- **Cognitive Architecture (`cognitive_architecture.py`):** Integrated cognitive system combining world model, hierarchical memory, attention, uncertainty estimation, and learning.
- **World Model (`world_model.py`):** Internal belief state representation.
- **Hierarchical Memory (`hierarchical_memory.py`):** Multi-level memory (episodic, semantic, procedural).
- **Attention (`attention.py`):** Selective attention mechanism.
- **Uncertainty (`uncertainty.py`):** Bayesian uncertainty quantification.
- **Probabilistic (`probabilistic.py`):** Probabilistic state estimation.
- **Bayesian (`bayesian.py`):** Bayesian inference for belief updates.
- **RL Interface (`rl_interface.py`):** Reinforcement learning interface.
- **Mission Context (`mission_context.py`):** Mission-aware context management.
- **Explainability (`explainability.py`):** Decision explanation generation.
- **Adaptive Planner (`adaptive_planner.py`):** Self-adaptive planning strategies.
- **Self Evaluation (`self_evaluation.py`):** Performance self-assessment.
- **Confidence (`confidence.py`):** Confidence estimation for decisions.
- **Learning (`learning.py`):** Online learning modules.

### 10. AirSim Integration (`src/airsim/`)
- **AirSim Bridge (`airsim_bridge.py`):** Connects the Python simulation to Microsoft AirSim for realistic 3D physics and visuals.
- **AirSim Drone (`airsim_drone.py`):** AirSim quadrotor wrapper.
- **AirSim World (`airsim_world.py`):** World synchronization.
- **AirSim Sensors (`airsim_sensors.py`):** Sensor data from AirSim.
- **AirSim Physics (`airsim_physics.py`):** Physics engine interface.
- **AirSim Mission (`airsim_mission.py`):** Mission execution in AirSim.
- **AirSim Config (`airsim_config.py`):** Configuration for AirSim connection.

### 11. Telemetry & Visualization (`src/telemetry/`)
- **Metrics (`metrics.py`):** Performance metrics collection (path length, time, energy, smoothness, etc.).
- **Visualization (`visualization.py`):** Real-time grid world visualization (Pygame/Matplotlib).
- **Flight Dashboard (`flight_dashboard.py`):** Interactive dashboard for monitoring.
- **Military Viz (`military_viz.py`):** Specialized military-themed visualization.

---

## Technologies Used

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core programming language |
| **NumPy** | Numerical computing, linear algebra, state estimation |
| **SciPy** | Signal processing, interpolation, optimization |
| **Matplotlib** | Visualization, plotting |
| **Pygame** | Interactive real-time 2D visualization |
| **NetworkX** | Graph algorithms for path planning |
| **PyTorch** | Deep learning for prediction and cognition |
| **scikit-learn** | Classical ML for prediction |
| **AirSim (Python API)** | Realistic 3D drone simulation (optional) |
| **Pandas** | Data logging and analysis |
| **B-spline / Interpolation** | Path smoothing |
| **Kalman Filters** | Sensor fusion and state estimation |
| **Behavior Trees** | Autonomous decision-making |
| **D* Lite** | Incremental search for dynamic environments |

---

## How the Modules Interact

The mission loop (in `main.py` / `src/autonomy/mission_manager.py`) follows this data flow:

```
┌─────────────────────────────────────────────────────────────────┐
│                     MISSION LOOP                                 │
│                                                                   │
│  Sensors (GPS, IMU, LiDAR, Compass)                              │
│      │                                                            │
│      ▼                                                            │
│  Sensor Fusion ──► State Estimation (pos, vel, heading)         │
│      │                                                            │
│      ├──► Mapping (Occupancy Grid + Cost Map)                    │
│      │       │                                                    │
│      │       ▼                                                    │
│      │   Spatial Index ──► Collision Detection                   │
│      │       │                                                    │
│      │       ▼                                                    │
│      │   D* Lite / Grid Planner ◄── Prediction Module            │
│      │       │         ▲            (dynamic obstacle forecasts)  │
│      │       │         │                                          │
│      │       ▼         │                                          │
│      │   Path Smoother ─┘                                         │
│      │       │                                                    │
│      │       ▼                                                    │
│      │   Path Follower (Pure Pursuit)                             │
│      │       │                                                    │
│      │       ▼                                                    │
│      │   Local Planner (reactive avoidance)                       │
│      │       │                                                    │
│      ▼       ▼                                                    │
│  Flight Manager ──► Mode Selection                               │
│      │               (ECO / NORMAL / SPORT / etc.)                │
│      │                                                            │
│      ▼                                                            │
│  PID Controller ──► Motion Controller                             │
│      │                                                            │
│      ▼                                                            │
│  Drone Dynamics (position, velocity, acceleration update)        │
│      │                                                            │
│      ▼                                                            │
│  Telemetry (metrics logging + visualization)                     │
│      │                                                            │
│      ▼                                                            │
│  Emergency Manager (collision check, battery, geofence)          │
│      │                                                            │
│      ▼                                                            │
│  Cognitive Architecture (optional loop)                          │
│      │  - World Model update                                      │
│      │  - Attention / Uncertainty / Confidence                    │
│      │  - Adaptive Replanning                                     │
│      │  - Self-Evaluation                                         │
│      │                                                            │
│      ▼                                                            │
│  Mission Manager (waypoint progressing, replan triggers)          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Interaction Points

1. **Sensors → Sensor Fusion → State Estimation**: Raw sensor data is fused via Kalman filter to produce a reliable state estimate.

2. **Mapping → Planning**: The occupancy grid and cost map provide the environment representation that planners use.

3. **Prediction → Planning**: Dynamic obstacle trajectory predictions are fed into D* Lite to enable proactive replanning.

4. **Planning → Control**: Path waypoints are sent to the Path Follower, which generates velocity/heading commands for the controllers.

5. **Control → Drone**: PID and Motion Controllers compute actuation commands that update the drone's dynamics.

6. **Drone → Sensors**: The drone's new state feeds back into sensor models (closed-loop simulation).

7. **Emergency Manager → Flight Manager**: Safety-critical events trigger mode changes and override normal control.

8. **Cognition → All Layers**: The cognitive architecture provides meta-reasoning, uncertainty-aware decision making, and adaptive behavior.

---

## Running the Simulation

### Standard Simulation (Python-only, no AirSim)
```bash
python main.py
```
Runs the full autonomous mission in a 2D grid world with visualization.

### AirSim Simulation (requires AirSim)
```bash
python main_airsim.py
```
Runs the same mission in Microsoft AirSim's realistic 3D environment.

### Testing
```bash
# Run specific tests
python -m pytest src/tests/

# Run individual test files
python src/tests/test_planner.py
python src/tests/test_flight_manager.py

# Run dashboard
python test_dashboard.py

# Run benchmarks
python benchmark_flight_manager.py
```

---

## Summary

MJN Drone is a **comprehensive autonomous drone navigation research platform** that bridges:

- **Classical robotics** (PID, D* Lite, occupancy grids, Kalman filters)
- **Modern AI** (deep learning prediction, attention mechanisms, cognitive architectures)
- **Simulation** (custom 2D grid world + Microsoft AirSim 3D integration)

It is designed to be modular, extensible, and well-suited for testing navigation algorithms, sensor configurations, planning strategies, and autonomous behaviors in a controlled simulation environment before deployment on real drone hardware.