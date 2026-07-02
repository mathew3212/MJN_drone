# MJN Drone OS — Professional Ground Control Station

A production-grade autonomous drone Ground Control Station built with Next.js, Leaflet, and TypeScript. Designed for professional autonomous drone operations.

## Architecture

### Single Source of Truth
Every component reads from **`droneEntityStore`** (Zustand):
- No duplicate state
- No derived values in widgets
- No hardcoded positions
- Everything updates automatically via subscriptions

### State Stores
| Store | Purpose |
|-------|---------|
| `droneEntityStore` | Drone position, telemetry, mission, waypoints, battery, GPS, signal, path |
| `mapStore` | Map settings, follow mode, debug info, offline mode |
| `eventStore` | Mission events log with severity/source |

### Data Flow
```
MissionGenerator → GeneratedMission (home, waypoints, destination)
  ↓
SimulationEngine (20Hz time-based kinematics, waypoint-following)
  ↓
droneEntityStore.setDrone() ← SINGLE MUTATION POINT
  ↓
  ├── GISMap / MapEngine → Map rendering
  ├── MapFollowController → Camera behavior
  ├── PathManager → Route polylines
  ├── WaypointRenderer → Waypoint markers
  ├── LiveDroneMarker → Drone icon
  └── Dashboard widgets → Telemetry display
```

## Modules

### `simulationEngine.ts`
Mission-driven drone simulation at 20Hz. Uses Haversine distance for movement, smooth heading interpolation (45°/s max turn rate), distance-based battery model, and waypoint hover logic.

- start/stop/pause
- Waypoint-by-waypoint execution
- No random movement — drone only moves along mission path
- Generates structured telemetry every tick

### `missionGenerator.ts`
Generates unique missions on every launch. 12 mission types with appropriate waypoint patterns:
- Infrastructure inspection (linear poles)
- Solar farm / agricultural / mapping (grid pattern)
- Search and rescue (spiral expansion)
- Security patrol (perimeter rectangle)
- Package delivery (point-to-point)
- Bridge / pipeline / construction

All waypoints avoid restricted zones (no-fly, military, government).

### `droneEntityStore.ts`
Zustand store. Single source of truth for all drone state:
- Position: `latitude`, `longitude`, `altitude`
- Attitude: `heading`, `pitch`, `roll`, `yaw`
- Velocity: `velocity`, `verticalSpeed`, `acceleration`
- Battery: `percentage`, `voltage`, `current`, `power`, `temperature`, `cells`, `health`, `cycles`
- GPS: `satellites`, `hdop`, `vdop`, `fixType`, `accuracy`
- Signal: `strength`, `rssi`, `snr`, `quality`
- System: `cpuUsage`, `gpuUsage`, `ramUsage`, `heartbeat`, `motorRpm`, `motorTemperature`
- Sensors: LiDAR, camera, depth, radar, ultrasonic, optical flow, detection count, tracking IDs
- Weather: wind speed/direction, gusts, visibility, humidity, pressure, temperature, rain
- Planner: type, decision, confidence, inference time, reason
- Prediction: collision probability, mission success probability, obstacle risk, path cost
- Waypoints: full array with reached/current/upcoming status
- Path: visited, current, planned, predicted, return home, emergency
- Overlays: obstacles, no-fly zones, restricted airspace, geofence, weather, risk zones

### `MapEngine.ts`
Leaflet map with canvas overlay for tactical rendering. Subscribes to `droneEntityStore` and updates:
- Drone marker (via canvas at pixel coordinates from lat/lng)
- Path polylines
- Waypoint markers
- AI overlays (geofences, obstacles, no-fly zones)
- Scale bar, compass

### `PathManager.ts`
Efficient Leaflet polyline rendering for 6 path layers:
- Visited: bright emerald (#00FF88)
- Current: bright orange (#FF6633)
- Planned: electric blue (#00D4FF)
- Predicted: yellow (#FFC857)
- Return home: purple dashed (#9D6CFF)
- Emergency: red dashed (#FF4D5A)

Append-only updates — never redraws entire polyline.

### `WaypointRenderer.ts`
Leaflet markers for waypoints:
- Home: violet (#A855F7) house icon, 14px
- Destination: red (#EF4444) target icon, 14px
- Current waypoint: cyan (#00D4FF), pulsing ring
- Completed: dark blue (#4A5A78) with checkmark
- Upcoming: muted blue (#6B7FA0)

Each has a permanent tooltip showing label, WP#, altitude, ETA.

### `MapFollowController.ts`
Camera behavior:
- `follow` — drone at 35% from screen bottom (Google Maps style), map scrolls underneath
- `north-up` — fixed north orientation, drone centered
- `heading-up` — map rotates with drone heading
- `overview` — fit entire mission in view
- `free` — operator can pan/zoom freely

Smooth interpolation for pan, zoom, and bearing.

### `LiveDroneMarker.ts`
Canvas-rendered drone icon at its geographic pixel position. Includes:
- Drone silhouette with heading arrow
- Battery ring (green/yellow/red)
- Signal ring
- GPS accuracy circle
- Selection highlight
- Shadow

### `eventEngine.ts`
Derives structured events from state transitions:
- Mission started / completed
- Waypoint reached
- GPS lost / recovered
- High wind
- Low battery
- Return home triggered
- Emergency landing
- Motor failure

Each event has timestamp, severity, source, description, suggested action.

### `AlertPanel.ts`
Floating critical alerts with ACK button. Generated from live conditions:
- Entering no-fly zone
- Approaching restricted airspace
- Strong wind ahead
- Low battery
- Collision predicted
- Signal weak
- Localization confidence low
- Obstacle detected

### `AttitudeIndicator.ts` / `Compass.ts`
Canvas-drawn flight instruments:
- Artificial horizon with sky/ground gradient
- Pitch lines (±30°)
- Roll rotation with aircraft symbol
- Yaw indicator
- N/E/S/W cardinal directions
- 10° tick marks

### `GeocodingService.ts`
Reverse geocoding for home and destination addresses:
- Primary: OpenStreetMap Nominatim API
- Fallback: Local Bangalore locality database
- 3-second timeout
- In-memory cache

Addresses displayed throughout the UI.

## File Structure

```
drone-command-center/
├── src/
│   ├── app/
│   │   ├── page.tsx          Main dashboard (top bar, sidebars, bottom instruments)
│   │   ├── layout.tsx        Root layout
│   │   └── globals.css       Global styles (charcoal theme)
│   ├── components/
│   │   ├── gcs/
│   │   │   ├── AlertPanel.tsx      Floating alert overlay
│   │   │   ├── AIPanel.tsx         AI/brain engine status
│   │   │   ├── AttitudeIndicator.tsx Canvas artificial horizon
│   │   │   ├── Compass.tsx         Canvas heading indicator
│   │   │   ├── EventConsole.tsx    Structured event log
│   │   │   └── MarkerInfoPanel.tsx  Click-activated info panel
│   │   ├── gis/
│   │   │   ├── GISMap.tsx           Leaflet map container
│   │   │   ├── MapEngine.ts         Map lifecycle + render loop
│   │   │   ├── MapFollowController.ts Camera behavior
│   │   │   ├── PathManager.ts       Route polylines
│   │   │   ├── WaypointRenderer.ts  Waypoint markers
│   │   │   ├── LiveDroneMarker.ts   Drone marker (canvas)
│   │   │   ├── AIOverlayRenderer.ts Geofences/obstacles
│   │   │   ├── MapControls.tsx      Map settings
│   │   │   ├── MissionPlayback.tsx  Mission timeline
│   │   │   └── DebugPanel.tsx       Developer overlay
│   │   └── layout/
│   │       ├── GlassPanel.tsx  Glass-morphism panel wrapper
│   │       ├── StatusBar.tsx    Compact status display
│   │       └── EventConsole.tsx Event log panel
│   ├── store/
│   │   ├── droneEntityStore.ts    Zustand store (single source of truth)
│   │   ├── simulationEngine.ts    20Hz drone simulation
│   │   ├── missionGenerator.ts    Mission/waypoint generation
│   │   ├── eventEngine.ts          State-change event detection
│   │   ├── mapStore.ts             Map state/settings
│   │   └── simulationBridge.ts     Backend connectivity
│   ├── hooks/
│   │   └── useEventEngine.ts      Event subscription hook
│   └── types/
│       └── droneEntity.ts          DroneEntity interface
├── package.json
├── tsconfig.json
└── next.config.ts
```

## Running

```bash
cd drone-command-center
npm run dev
```

Open http://localhost:3000

## Design Principles

- **Mission first**: Map is the primary workspace
- **Information before decoration**: Every pixel has purpose
- **Restrained palette**: Deep charcoal (#0D0D0D), dark graphite, off-white, specific accent colors
- **8px spacing grid**: Consistent padding and margins
- **Typography**: System sans-serif, JetBrains Mono for numbers
- **No clash**: No overlapping widgets, no conflicting information
- **Single source of truth**: One store, one state, one subscription per value

## Geospatial Workflow

```
MissionGenerator
  → Generates valid lat/lng for home, waypoints, destination
  → Avoids no-fly zones, restricted airspace
  → Uses Haversine for all distance calculations

SimulationEngine
  → Moves drone via velocity × dt along waypoint path
  → Smooth heading interpolation before translation
  → Slow-down before waypoint arrival
  → Hover at inspection points

droneEntityStore
  → latitude, longitude, altitude (WGS84)
  → heading (0-360°)
  → Every value is geographic

Map Engine
  → Leaflet renders tiles via Web Mercator projection
  → latLngToContainerPoint converts geo → screen
  → Drone marker positioned at [lat, lng] pixel coordinates
  → Paths drawn as geographic polylines
  → Map follow mode pans/rotates the Leaflet map camera
```

## Mission Lifecycle

1. **Generate** — MissionGenerator creates home, waypoints, destination
2. **Takeoff** — Drone ascends to cruise altitude
3. **Navigate** — Drone follows waypoints sequentially:
   - Rotate toward target (max 45°/s)
   - Accelerate to cruise speed
   - Decelerate on approach
   - Hover if required
   - Snap to waypoint on arrival
4. **Return** — Final waypoint is RTH, drone returns home at 1.2× speed
5. **Land** — Mission complete, drone idle at home

## Color System

| Element | Color | Hex |
|---------|-------|-----|
| Background | Deep charcoal | #0D0D0D |
| Cards | Dark graphite | #1A1A1A |
| Borders | Subtle | #222 |
| Text primary | Off-white | #E8E8E8 |
| Text muted | Gray | #888, #666 |
| Success | Green | #22C55E |
| Warning | Amber | #EAB308 |
| Critical | Red | #EF4444 |
| Navigation cyan | Blue | #06B6D4 |
| Visited path | Emerald | #00FF88 |
| Active segment | Orange | #FF6633 |
| Planned route | Cyan | #00D4FF |
| Return home | Purple | #9D6CFF |
| Emergency | Red | #FF4D5A |

## Validation Checklist

- ✅ Every widget reads from `droneEntityStore`
- ✅ Map coordinates match telemetry coordinates
- ✅ Drone heading matches IMU heading
- ✅ Battery widget matches Battery State
- ✅ Mission path matches Navigation output
- ✅ Waypoints match Mission Manager
- ✅ Planner status matches Decision Engine
- ✅ Event Log matches real events
- ✅ Alerts generated from live conditions
- ✅ No conflicting values exist
- ✅ Dashboard survives refresh
- ✅ Reconnection restores sync
- ✅ No random GPS noise or teleportation
- ✅ Drone only moves after mission generation
- ✅ Home/destination have address strings