# MJN Drone OS GCS - Quick Reference Summary

## 🎯 At a Glance

| Aspect | Details |
|--------|---------|
| **Framework** | Next.js 15 + React 18 |
| **State Management** | Zustand (5 stores) |
| **Mapping** | Leaflet 1.9+ |
| **3D Graphics** | Three.js |
| **Frontend Components** | 37 files (8,000+ LOC) |
| **Update Frequency** | 20 Hz (50ms loop) |
| **Production Readiness** | ~20% (simulation/dev only) |

---

## 📊 Core Stores (5 Total)

### 1. **DroneEntityStore** ⭐ PRIMARY
- Single source of truth for entire system
- Complete DroneEntity object with all flight data
- All components subscribe here

### 2. **DroneStore** (Legacy)
- Synthetic telemetry generator (x,y grid coordinates)
- Telemetry history (time series data)
- Used when backend unavailable

### 3. **GCSStore**
- Professional dashboard state
- Mission, planner, health, alerts, AI metrics
- Synced from DroneStore

### 4. **VisualizationStore**
- 3D Digital Twin state
- GIS Map visualization state
- Camera modes, waypoints, overlays

### 5. **SimulationBridge**
- Backend integration layer
- Translates raw telemetry → DroneEntity
- Supports: Internal, PX4, Gazebo, AirSim, MAVSDK, Real

---

## 🗂️ Component Organization

### Dashboard Panels (18 total)
```
HeaderBar (status, GPS, CPU, emergency)
├─ 3D Map (6×4)
├─ Speed Chart (3×2)
├─ Altitude Chart (3×2)
├─ Battery Chart (3×2)
├─ CPU Chart (3×2)
├─ Drone Status (3×2)
├─ Mission Timeline (3×2)
├─ Airspace (3×4)
├─ Health Panel (3×3)
├─ Prediction (3×3)
├─ Signal (3×3)
├─ GPS Accuracy (3×3)
├─ Graph Workspace (6×3)
├─ LeftPanel (Battery/Motors/Sensors)
├─ RightPanel (Mission/Planner/Risk)
├─ AIPanel (AI Decision/Metrics)
├─ BottomInstruments (Compass/Gauges)
└─ EventConsole (Alert Feed)
```

### GIS Map (15 components)
- MapEngine (Leaflet coordinator)
- LiveDroneMarker (animated drone)
- PathManager (6 path types)
- WaypointRenderer (waypoint markers)
- MapFollowController (5 follow modes)
- AIOverlayRenderer (obstacles, risks, predictions)
- TileProvider (4 sources + fallback)
- OfflineCache (IndexedDB)
- MapStore (GIS state)

### 3D Scene (5 components)
- DigitalTwinScene (Three.js coordinator)
- DroneModel (3D drone geometry)
- TerrainMesh (terrain)
- Buildings (building geometry)
- CameraController (3D camera modes)

---

## 📈 Data Flow (50ms Loop)

```
Python Backend
    ↓ WebSocket
SimulationBridge.update()
    ↓ Transform
DroneEntityStore.setDrone()
    ↓ Cascade
├─ GCSStore (dashboard)
├─ VisualizationStore (3D/GIS)
├─ Components (charts, panels)
└─ GISMap/3D Scene (rendering)
    ↓ Re-render
UI Updates
```

---

## ✅ What Exists

### Fully Implemented ✓
- ✅ Real-time telemetry UI (20 Hz)
- ✅ Professional dashboard layout
- ✅ Leaflet GIS map with drone marker & paths
- ✅ 3D digital twin (Three.js)
- ✅ Battery, motor, sensor monitoring
- ✅ Mission progress tracking
- ✅ AI planner state visualization
- ✅ Multiple backend support (abstraction)
- ✅ Offline tile caching
- ✅ Cyberpunk UI theme
- ✅ Type-safe (full TypeScript)

---

## ❌ Missing for Production

### Critical Gaps
1. **❌ User Authentication** - No login/roles
2. **❌ Data Persistence** - No database
3. **❌ Multi-Drone Support** - Only MJN-01 hardcoded
4. **❌ Mission Planning UI** - Fixed 5-waypoint mission
5. **❌ MAVLink Protocol** - WebSocket only
6. **❌ Automated Testing** - Zero tests
7. **❌ Deployment** - No Docker/CI-CD
8. **❌ Monitoring** - No observability
9. **❌ Communication Redundancy** - Single link
10. **❌ Server-Side Failsafe** - UI-level only

### Estimated Effort to Production: **6-12 months**

---

## 🎮 GIS Map Features

### Follow Modes (5)
1. **follow-drone**: Center on drone, auto-rotate
2. **north-locked**: North always up
3. **heading-up**: Drone heading up
4. **mission-overview**: 2x zoom-out
5. **free-explore**: Manual pan/zoom

### Overlays (15+ toggleable)
- Grid, weather, geofences, no-fly zones
- Waypoints, paths (6 types)
- Obstacles, risk zones, collision predictions
- Safe landing zones, wind, compass, scale

### Tile Providers (4 + Fallback)
- OpenStreetMap (Standard)
- Mapbox (Satellite)
- USGS (Topographic)
- Stamen (Urban)
- Fallback: Tactical grid (offline)

---

## 🏗️ Architecture Quality

| Aspect | Rating | Notes |
|--------|--------|-------|
| Code Organization | ⭐⭐⭐⭐ | Clean, well-structured |
| Type Safety | ⭐⭐⭐⭐⭐ | Excellent (full TS) |
| State Management | ⭐⭐⭐⭐ | Zustand is efficient |
| Performance | ⭐⭐⭐ | Good (20Hz loop) |
| Testability | ⭐ | No tests yet |
| Accessibility | ⭐ | No WCAG compliance |
| Production Readiness | ⭐⭐ | 20% ready |

---

## 📁 File Summary

```
Files: 50+
├─ Stores: 5
├─ Components: 37
├─ Types: 4
├─ Hooks: 0 (gap!)
├─ Utils: 2
└─ App: 4

Total LOC: ~8,000+
```

---

## 🚀 Next Steps (If Going to Production)

### Phase 1 (4-5 weeks) - Foundation
1. Add authentication (JWT)
2. Add database (PostgreSQL)
3. Multi-drone support
4. Testing framework

### Phase 2 (5-6 weeks) - Capabilities
5. Mission planning UI
6. Telemetry archival (InfluxDB)
7. Advanced map features
8. Docker & CI/CD

### Phase 3 (6-7 weeks) - Production
9. MAVLink server
10. Redundant communication
11. Failsafe enforcement
12. Monitoring & alerting

### Phase 4 (4-5 weeks) - Operational
13. Reporting & analytics
14. Maintenance scheduling
15. Accessibility
16. Performance tuning

---

## 🎓 Key Insights

### Strengths
- Clean architecture with clear data flow
- Efficient state management (Zustand selectors)
- Beautiful, professional UI
- Multi-backend abstraction layer
- Type-safe throughout
- Real-time responsive dashboard

### Weaknesses
- All state in browser memory (no persistence)
- Single drone hardcoded
- No mission builder UI
- Heavy reliance on synthetic data generator
- No testing infrastructure
- No custom React hooks (stores direct)

### Best For
✅ Simulation  
✅ Training  
✅ Prototyping  
✅ Single-operator testing  
❌ Multi-operator production  
❌ Real flight operations  
❌ Regulatory compliance

---

## 📚 Files to Study First

1. **[page.tsx](drone-command-center/src/app/page.tsx)** - Data flow orchestration
2. **[droneEntityStore.ts](drone-command-center/src/store/droneEntityStore.ts)** - Primary state
3. **[simulationBridge.ts](drone-command-center/src/store/simulationBridge.ts)** - Backend integration
4. **[GISMap.tsx](drone-command-center/src/components/gis/GISMap.tsx)** - Map implementation
5. **[DigitalTwinScene.tsx](drone-command-center/src/components/3d/DigitalTwinScene.tsx)** - 3D scene

---

## 💾 See Also

- Full Analysis: [GCS_CODEBASE_ANALYSIS.md](GCS_CODEBASE_ANALYSIS.md)
- Memory Store: `/memories/repo/mjn_gcs_comprehensive_analysis.md`
- Backend: `main.py` (Python simulation)

---

**Last Updated**: July 2, 2026  
**Analysis Tool**: GitHub Copilot (Claude Haiku)  
**Scope**: Complete codebase thorough exploration
