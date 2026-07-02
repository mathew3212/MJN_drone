# MJN Drone OS - Visualization Subsystem Architecture

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                    Dashboard Layout                    │
├──────────────────────┬───────────────────────────────┤
│                      │                               │
│   3D Digital Twin    │    Tactical GIS Map           │
│   (React Three       │   (MapLibre GL JS)            │
│    Fiber)            │                               │
│                      │                               │
├──────────────────────┴───────────────────────────────┤
│  Mission Timeline  │  Telemetry  │  AI  │  Console   │
└──────────────────────────────────────────────────────┘
```

## Data Flow

```
Python Backend (Event Bus) → Zustand Store → React Components
        ↓                                            ↓
  DroneState (single source)            3D View  ←→  GIS View
                                               ↓
                                        Synchronized via
                                        shared Zustand store
```

## Key Principle
Both views subscribe to the SAME store. They NEVER compute navigation data themselves. The renderer only visualizes.