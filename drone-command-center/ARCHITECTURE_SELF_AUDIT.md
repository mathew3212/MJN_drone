# MJN Drone OS Architecture And Self-Audit

## Runtime Architecture

```text
Internal Simulator / WebSocket Backend
        |
        v
simulationBridge.ts
        |
        v
useDroneEntityStore (authoritative live state)
        |
        +--> GIS map engine
        |     - LiveDroneMarker
        |     - PathManager
        |     - WaypointRenderer
        |     - AIOverlayRenderer
        |
        +--> GCS header
        +--> Health panel
        +--> Mission panel
        +--> AI panel
        +--> Bottom instruments
        |
        +--> alertEngine.ts
                |
                v
           useEventStore
                |
                +--> AlertPanel
                +--> EventConsole
```

## What Is Now Authoritative

- The visible GCS route at `src/app/page.tsx` now renders operational telemetry from `useDroneEntityStore`.
- Header, health, mission, AI, and bottom instruments subscribe directly to `useDroneEntityStore`.
- Alerts and the event console read from `useEventStore`.
- GIS rendering already subscribes directly to `useDroneEntityStore` through `MapEngine`.

## Widgets Verified Against Shared State

- Header bar: mission state, connection state, timer, GPS satellites, wind, telemetry rate, CPU, RAM.
- Left panel: battery, battery cells, motor RPM, motor temperature, ESC temperature, GPS/IMU/compass/baro, lidar/camera/radar/optical-flow, CPU/GPU/RAM/disk/network.
- Right panel: mission ID, mission progress, ETA, current waypoint, remaining distance/time, objective, planner decision, confidence, localization quality, risk, success probability, return-home state, emergency state.
- AI panel: planner type, decision, planner confidence, risk score, mission success probability, predicted collision time, path cost, prediction accuracy, landing zone.
- Bottom instruments: attitude, heading, speed, altitude, vertical speed, battery, signal, wind.
- GIS map: drone marker, heading, paths, waypoints, overlays, home marker, debug metrics.
- Event surfaces: initialization event plus alert-engine-generated events from live drone conditions.

## Remaining Non-Authoritative Or Legacy Modules

- `src/store/droneStore.ts` still exists and is only acting as the internal simulator input source.
- `src/store/gcsStore.ts` still contains duplicated dashboard state, but the main app route no longer depends on it for visible telemetry.
- `src/store/visualizationStore.ts` still contains duplicated visualization state for older 3D components.
- `src/components/Dashboard.tsx`, `src/components/3d/*`, and `src/components/overlay/BrainOverlay.tsx` still reference legacy stores and are not yet migrated.

## Missing Integrations

- `MapStyleControls.tsx` still updates `visualizationStore` and is not yet wired into the Leaflet map engine style/provider pipeline.
- The internal simulator still originates from `droneStore` instead of a backend publishing `DroneEntity` directly.
- Some requested domain overlays in the directive are not yet backed by real sources: airports, helipads, hospitals, schools, power lines, population density, terrain elevation, restricted airspace feeds, and weather raster layers.
- Offline tiles and PMTiles are not fully integrated into the currently mounted Leaflet engine.
- The legacy 3D views still need migration if they are meant to remain part of production scope.

## Traceability Notes

- Displayed values on the current main GCS route can now be traced to `useDroneEntityStore` or `useEventStore`.
- Derived labels such as mission status, emergency status, and objective are computed in `src/store/droneSelectors.ts` from authoritative live state instead of separate widget-local state.
- The app still needs a future cleanup pass to remove or migrate the unused duplicate stores so the codebase fully matches the runtime architecture.
