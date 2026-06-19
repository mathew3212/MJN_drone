# MJN Autonomous Drone Navigation System

A fully autonomous drone navigation and mission simulation platform with both a **Python simulation engine** and a **Next.js command center dashboard**.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Python Simulation (Backend)](#python-simulation-backend)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
  - [Running Simulations](#running-simulations)
  - [Testing](#testing)
  - [Architecture Overview](#architecture-overview)
- [Drone Command Center (Web UI)](#drone-command-center-web-ui)
  - [Prerequisites](#prerequisites-1)
  - [Setup](#setup-1)
  - [Running](#running)
  - [Features](#features)
- [Modules Reference](#modules-reference)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

---

## Project Structure

```
mjn_drone/
├── main.py                     # Entry point: standard 2D simulation
├── main_premium.py             # Entry point: premium simulation (cinematic, living world, airspace)
├── main_airsim.py              # Entry point: AirSim 3D simulation
├── requirements.txt            # Python dependencies
├── benchmark_flight_manager.py # Performance benchmarking
├── test_*.py                   # Test scripts (airsim, airspace, cognitive, dashboard, mission)
├── gen.py / gen_all.py / gen_check.py  # Code generation / validation utilities
├── .gitignore
├── NAVIGATION_REPORT.md        # Navigation capabilities report
│
├── src/                        # Python simulation source
│   ├── airsim/                 # AirSim integration bridge
│   ├── airspace/               # Airspace management (geofence, altitude, corridors, restricted zones)
│   ├── autonomy/               # Mission management, behavior trees, emergency, battery
│   ├── cognition/              # Cognitive architecture (world model, memory, attention, learning)
│   ├── control/                # PID, motion controller, flight manager
│   ├── core/                   # Core primitives: drone, world, terrain, weather, event bus, physics
│   ├── mapping/                # Occupancy grid, cost map, spatial index, memory map
│   ├── navigation/             # Navigation state machine, managers, local planner
│   ├── perception/             # Perception modules (extensible)
│   ├── planning/               # Path planners: D* Lite, grid, local, path follower, smoother
│   ├── prediction/             # Trajectory prediction, risk, attention predictors, training
│   ├── sensors/                # GPS, IMU, LiDAR, compass, virtual camera, sensor fusion
│   ├── telemetry/              # Metrics, logging, visualization, dashboards, military viz
│   ├── tests/                  # Unit and integration tests
│   ├── visuals/                # Premium world, camera system, vision engine, dashboard
│   ├── workspace/              # Mission control workspace, brain integration, theme manager
│   └── __init__.py
│
├── drone-command-center/       # Next.js web dashboard
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── public/                 # Static assets
│   └── src/
│       ├── app/                # Next.js App Router pages
│       │   ├── layout.tsx
│       │   ├── page.tsx
│       │   └── globals.css
│       ├── components/
│       │   ├── Dashboard.tsx
│       │   ├── 3d/             # Three.js / React Three Fiber components
│       │   │   ├── ErrorBoundary.tsx
│       │   │   ├── MissionMapCanvas.tsx
│       │   │   └── digital-twin/
│       │   │       ├── DroneModel.tsx
│       │   │       ├── TerrainMesh.tsx
│       │   │       └── Buildings.tsx
│       │   ├── charts/         # Chart components
│       │   │   └── PremiumLineChart.tsx
│       │   ├── layout/         # Layout components
│       │   │   ├── StatusBar.tsx
│       │   │   ├── EventConsole.tsx
│       │   │   └── GlassPanel.tsx
│       │   ├── panels/         # (extensible)
│       │   └── widgets/        # (extensible)
│       ├── hooks/              # (extensible)
│       ├── lib/
│       │   ├── theme.ts
│       │   └── world/          # World generation utilities
│       ├── store/              # State management (Zustand)
│       │   └── droneStore.ts
│       └── types/              # TypeScript definitions
│           └── index.ts
└── venv/                       # Python virtual environment (generated)
```

---

## Python Simulation (Backend)

### Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)
- Recommended: A virtual environment

### Setup

```bash
# Create and activate a virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Running Simulations

There are three entry points, each for a different simulation mode:

| Command | Description |
|---|---|
| `python main.py` | Standard 2D grid world simulation. Runs a full autonomous mission with a single drone navigating from start to target, avoiding obstacles. Includes visualization, sensor simulation, path planning, and telemetry. |
| `python main_premium.py` | Premium simulation with cinematic visuals, living world (vehicles, pedestrians, birds), airspace management, knowledge graph, event bus, multi-drone support, and an interactive workspace dashboard. Press `C` to cycle camera modes, `R` to reset. |
| `python main_airsim.py` | AirSim 3D simulation. Connects to Microsoft AirSim for realistic physics and visuals. Falls back to 2D mode if AirSim is not available. Use `--no-airsim` to force 2D mode. |

#### Additional Commands

```bash
# Benchmark the flight manager performance
python benchmark_flight_manager.py

# Code generation utilities
python gen.py          # Generate obstacle sets
python gen_all.py      # Generate all test scenarios
python gen_check.py    # Validate generated scenarios
```

### Testing

```bash
# Run all unit tests
python -m pytest src/tests/

# Run individual test scripts
python test_airsim.py
python test_airspace.py
python test_cognitive.py
python test_dashboard.py
python test_mission.py

# Run specific module tests
python -m pytest src/tests/test_planner.py
python -m pytest src/tests/test_flight_manager.py
python -m pytest src/tests/test_battery.py
python -m pytest src/tests/test_behavior_tree.py
python -m pytest src/tests/test_emergency.py
python -m pytest src/tests/test_memory_manager.py
python -m pytest src/tests/test_military_modules.py
```

### Architecture Overview

The system follows a layered robotics architecture:

```
Sensors → Sensor Fusion → State Estimation
    ↓
Mapping (Occupancy Grid + Cost Map)
    ↓
Planning (D* Lite / Grid Planner → Path Smoother → Path Follower)
    ↓
Control (PID → Motion Controller)
    ↓
Drone Dynamics
    ↓
Telemetry & Visualization
    ↓
Emergency Manager & Cognitive Architecture (feedback)
    ↓
Mission Manager (waypoint progression)
```

**Key modules:**
- **`src/core/`**: Drone dynamics, world representation, terrain, weather, physics engine, event bus
- **`src/sensors/`**: Virtual GPS, IMU, LiDAR, compass, camera with noise models and Kalman filter fusion
- **`src/mapping/`**: Probabilistic occupancy grid, cost maps, spatial index, memory
- **`src/planning/`**: D\* Lite incremental replanning, A\*/Dijkstra grid planner, local reactive avoidance, path smoothing
- **`src/control/`**: PID controller with anti-windup, motion controller, flight mode manager
- **`src/autonomy/`**: Behavior tree-based decision-making, emergency handling, battery management
- **`src/cognition/`**: Cognitive architecture with world model, hierarchical memory, attention, uncertainty quantification
- **`src/airspace/`**: Geofencing, altitude management, corridors, restricted zones, temporary restrictions
- **`src/workspace/`**: Mission control workspace, brain integration, theme management
- **`src/visuals/`**: Premium world rendering, cinematic camera system (10 modes), vision engine

---

## Drone Command Center (Web UI)

A modern Next.js dashboard for monitoring and controlling drone missions, featuring 3D digital twin visualization, real-time telemetry charts, and an interactive command interface.

### Prerequisites

- **Node.js 18+**
- **npm** (included with Node.js)

### Setup

```bash
# Navigate to the command center directory
cd drone-command-center

# Install dependencies
npm install
```

### Running

```bash
# Development server
npm run dev

# Production build
npm run build
npm start

# Lint
npm run lint
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Features

- **3D Digital Twin**: Real-time 3D drone visualization using React Three Fiber with terrain mesh and buildings
- **Live Telemetry**: Status bar showing drone position, battery, speed, and mission state
- **Event Console**: Real-time log of mission events
- **Interactive Charts**: Premium line charts for telemetry data visualization
- **Glass Panel UI**: Modern glassmorphism design system with theme support
- **Zustand State Management**: Efficient reactive state for drone data

**Tech Stack:** Next.js 16, React 19, TypeScript, Three.js / React Three Fiber, Zustand, Recharts, Framer Motion, GSAP, Tailwind CSS

---

## Modules Reference

| Package | Description |
|---|---|
| `src/core/` | Core simulation primitives: drone model, world, terrain, weather, grid map, coordinate system, simulation clock, configuration |
| `src/sensors/` | Virtual sensors: GPS, IMU, LiDAR, compass, virtual camera, sensor engine, Kalman filter fusion |
| `src/mapping/` | Mapping: occupancy grid, cost map, context map, perception map, memory manager, spatial index, collision detector |
| `src/planning/` | Path planning: D\* Lite, grid planner (A\*), local planner, path follower, path smoother |
| `src/control/` | Control: PID controller, motion controller, flight manager |
| `src/navigation/` | Navigation: state machine, navigation manager, local planner |
| `src/autonomy/` | Autonomy: mission manager, behavior tree, drone behaviors, emergency manager, battery manager |
| `src/prediction/` | Prediction: trajectory predictor, attention predictor, learned predictor, risk predictor, scene memory, training |
| `src/cognition/` | Cognition: cognitive architecture, world model, hierarchical memory, attention, uncertainty, bayesian, learning |
| `src/airsim/` | AirSim integration: bridge, drone wrapper, world sync, sensors, physics, mission, config |
| `src/airspace/` | Airspace: manager, geofence, altitude manager, corridors, restricted zones, database, visualization |
| `src/telemetry/` | Telemetry: metrics, logger, visualization, flight dashboard, military visualization |
| `src/visuals/` | Visuals: premium world, camera system, vision engine, cinematic flight, premium dashboard |
| `src/workspace/` | Workspace: mission control workspace, brain integration, command palette, theme manager, layout profiles |
| `src/tests/` | Tests: unit and integration tests for all major modules |

---

## Configuration

Key configuration constants are defined at the top of each entry point:

- **`main.py`**: `USE_DSTAR`, `SCAN_RADIUS`, `FRAME_DELAY`, `USE_ENHANCED_WORLD`, `WEATHER_CHANGE_INTERVAL`
- **`main_premium.py`**: `PREMIUM_MODE`, `USE_LIVING_WORLD`, `USE_PHYSICS_ENGINE`, `WORLD_WIDTH`, `WORLD_HEIGHT`, `NUM_OBSTACLES`
- **`main_airsim.py`**: Command-line arguments: `--ip`, `--port`, `--speed`, `--altitude`, `--scan-radius`, `--enable-weather`, `--wind-speed`, `--no-airsim`

Additional configuration is available in:
- `src/core/config.py` - Core simulation constants
- `src/airsim/airsim_config.py` - AirSim connection parameters
- `drone-command-center/next.config.ts` - Next.js configuration

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.