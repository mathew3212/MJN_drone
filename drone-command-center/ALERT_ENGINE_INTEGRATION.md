# Alert Engine & Event Store - Integration & Validation Guide

## 📋 System Overview

The Alert Engine and Event Store create a real-time monitoring and alerting system that continuously evaluates the drone's operational state and generates contextual alerts.

### Architecture Flow
```
Simulator (main.py)
    ↓ (GPS + Telemetry)
WebSocket: localhost:8765
    ↓
SimulationBridge (src/store/simulationBridge.ts)
    ↓
DroneEntityStore (src/store/droneEntityStore.ts)
    ├─ Current: drone (DroneEntity)
    └─ Previous: previousDrone (DroneEntity)
    ↓
EVERY 50ms (20 Hz): Main Update Loop (src/app/page.tsx)
    ├─ useDroneStore.simulateUpdate()
    ├─ simulationBridge.update()
    ├─ useDroneEntityStore.getState().drone
    ├─ updateVisualization()
    ├─ syncGCSFromDroneStore()
    └─ 🚨 alertEngine.evaluate(currentDrone, previousDrone)
    ↓
EVENT GENERATION
    ├─ Condition Evaluation (20+ rules)
    ├─ State Change Detection (previousDrone comparison)
    ├─ Throttling (per-rule min time between triggers)
    └─ useEventStore.addEvent()
    ↓
EVENT DISTRIBUTION
    ├─ EventConsole (Full event log with filtering)
    ├─ AlertPanel (Critical/Emergency banner alerts)
    └─ useEventStore subscribers
```

---

## 🔧 Components Created/Modified

### 1. **AlertEngine** (`src/lib/alertEngine.ts`)
**Purpose:** Intelligent real-time alert generation based on live drone state

**Key Features:**
- 20+ data-driven alert rules
- State change detection (previousDrone comparison)
- Per-rule throttling to prevent alert spam
- Every condition references real telemetry values
- Automatic suggested action generation

**Alert Rules Implemented:**
- Battery: critical (<15%), low (<30%), high-temp (>60°C)
- Signal: lost (<20%), weak (<40%)
- GPS: degraded (<6 satellites), high HDOP (>5)
- Mission: waypoint reached, mission completed
- Navigation: planner switched, low prediction confidence
- Weather: high wind (>12 m/s)
- Flight: return home triggered, emergency landing, high altitude
- Safety: collision predicted, obstacles detected, no-fly zone entered, restricted airspace

**Public Methods:**
- `evaluate(drone, previousDrone)` - Evaluate all rules and generate events
- `disableRule(ruleId)` - Disable a specific rule
- `enableRule(ruleId)` - Enable a rule
- `resetThrottle(ruleId)` - Reset throttle timer for manual re-trigger
- `getRuleIds()` - List all available rules

---

### 2. **EventStore** (`src/store/eventStore.ts`)
**Purpose:** Centralized event logging with structured data

**Key Types:**
```typescript
type EventSeverity = 'DEBUG' | 'INFO' | 'WARNING' | 'CRITICAL' | 'EMERGENCY'
type EventSource = 'MISSION' | 'NAVIGATION' | 'SENSOR' | 'SYSTEM' | 'BATTERY' | 
                   'COMMUNICATION' | 'SAFETY' | 'USER' | 'WEATHER' | 'PREDICTION'

interface SystemEvent {
  id: string;
  timestamp: number;
  severity: EventSeverity;
  source: EventSource;
  title: string;
  description: string;
  suggestedAction?: string;
  data?: Record<string, any>;
  resolved?: boolean;
  resolvedAt?: number;
}
```

**Key Methods:**
- `addEvent(event)` - Add new event to log
- `resolveEvent(eventId)` - Mark event as resolved
- `clearEvents()` - Clear all events
- `getEventsBySource(source)` - Filter by source
- `getEventsBySeverity(severity)` - Filter by severity
- `getUnresolvedEvents()` - Get active alerts
- `markEventsAsRead()` - Clear unread counter

**Storage:**
- Max 1000 events (configurable via `setMaxEvents()`)
- New events prepended to list
- Oldest events automatically pruned

---

### 3. **EventConsole** (`src/components/gcs/EventConsole.tsx`)
**Purpose:** Comprehensive event log display with filtering and search

**Features:**
- Real-time event listing (newest first)
- Filter by severity (DEBUG, INFO, WARNING, CRITICAL, EMERGENCY)
- Filter by source (MISSION, NAVIGATION, SENSOR, etc.)
- Full-text search across title, description, source
- One-click event resolution
- Auto-scroll to latest events
- Shows resolved event count
- Suggested actions displayed inline

**UI Layout:**
- Top controls: Severity filter buttons + Source dropdown + Search input
- Main area: Event list with severity color coding
- Footer: Total/unresolved event count
- Each event shows: Timestamp, Severity, Source, Title, Description, Suggested Action

---

### 4. **AlertPanel** (`src/components/gcs/AlertPanel.tsx`)
**Purpose:** Prominent display of critical system alerts

**Features:**
- Only shows CRITICAL and EMERGENCY level alerts
- Fixed position at top of screen (z-index: 50)
- Red banner with glow effect for EMERGENCY
- Orange banner for CRITICAL
- Shows: Severity label, Title, Full description, Suggested action
- One-click ACK button to resolve alert
- Auto-hides when no critical alerts
- Animated entrance/exit (Framer Motion)

---

### 5. **Main Dashboard Integration** (`src/app/page.tsx`)
**Changes Made:**
- Imported alertEngine from `@/lib/alertEngine`
- Added AlertPanel component import
- Integrated alert evaluation into main update loop (50ms interval)
- Calls `alertEngine.evaluate(currentDrone, previousDrone)` every tick
- AlertPanel rendered in layout after HeaderBar

---

## ✅ Validation Checklist

### Data Source Verification
- [ ] Every alert condition references actual telemetry fields
- [ ] No hardcoded values in alert conditions
- [ ] All data sourced from DroneEntity (single source of truth)
- [ ] PreviousDrone tracked for state-change detection
- [ ] Alert throttling prevents spam

### Integration Points
- [ ] AlertEngine imported in page.tsx
- [ ] alertEngine.evaluate() called in 50ms update loop
- [ ] EventStore events populated with alerts
- [ ] EventConsole subscribes to useEventStore
- [ ] AlertPanel subscribes to useEventStore
- [ ] Both components re-render when new events added

### UI/UX Verification
- [ ] Critical alerts appear as banner at top
- [ ] EventConsole shows all events with correct formatting
- [ ] Filters work (severity, source, search)
- [ ] Events can be marked as resolved
- [ ] Severity color coding consistent across components
- [ ] Timestamps display correctly
- [ ] Suggested actions appear when available

### Performance
- [ ] Alert evaluation < 1ms per cycle (20 Hz sustainable)
- [ ] Event list scrolls smoothly with 100+ events
- [ ] No memory leaks (max 1000 events capped)
- [ ] Map still renders at 60 FPS with alerts active

---

## 🧪 Testing Procedures

### Manual Testing - Battery Alerts
1. Start dashboard
2. Watch battery percentage in left panel
3. Observe battery decrease over time
4. When battery < 30%: Should see WARNING alert in EventConsole
5. When battery < 15%: Should see EMERGENCY alert in AlertPanel
6. Click ACK to resolve alert

### Manual Testing - Signal Loss
1. Watch signal strength (right side of drone marker)
2. Signal randomly varies due to simulator noise
3. When signal < 20%: Should trigger CRITICAL alert
4. Check EventConsole for "SIGNAL LOST" event
5. Verify suggested action: "Move closer to transmitter"

### Manual Testing - Mission Progress
1. Start mission with waypoints
2. When drone reaches waypoint: Should see INFO event
3. Event should show: "WAYPOINT REACHED: [current] → Next: [next]"
4. Events not duplicated (throttle working)

### Manual Testing - Collision Prediction
1. In simulator, set up scenario with obstacles
2. When predicted path intersects obstacle:
3. Should see CRITICAL alert in AlertPanel
4. EventConsole shows collision details
5. Suggested action: "Update path or abort mission"

### Automated Testing - Event Store
```typescript
// Test event creation
const store = useEventStore.getState();
store.addEvent({
  severity: 'CRITICAL',
  source: 'BATTERY',
  title: 'Test Alert',
  description: 'This is a test',
  suggestedAction: 'Check battery'
});

// Verify event was added
expect(store.events.length).toBe(1);
expect(store.eventCount).toBe(1);

// Test filtering
const critical = store.getEventsBySeverity('CRITICAL');
expect(critical.length).toBe(1);

// Test resolution
store.resolveEvent(store.events[0].id);
expect(store.events[0].resolved).toBe(true);
```

---

## 📊 Alert Rule Reference

### Battery Rules
```
battery-critical: percentage < 15%
  Severity: EMERGENCY
  Action: "Execute immediate RTL"

battery-low: percentage < 30%
  Severity: WARNING
  Action: "Plan return within 3 minutes"

battery-temperature-high: temperature > 60°C
  Severity: WARNING
  Action: "Reduce throttle, consider landing"
```

### Signal Rules
```
signal-lost: strength < 20%
  Severity: CRITICAL
  Action: "Move closer to transmitter"

signal-weak: strength < 40%
  Severity: WARNING
  Action: "Improve line-of-sight"
```

### GPS Rules
```
gps-lost: satellites < 6
  Severity: WARNING
  Action: "Move to open sky, wait for RTK lock"

high-hdop: hdop > 5
  Severity: WARNING
  Action: "Increase altitude for better view"
```

### Mission Rules
```
mission-progressing: currentWaypointIndex > previous
  Severity: INFO
  Action: "N/A"

mission-completed: missionState === 'COMPLETE'
  Severity: INFO
  Action: "N/A"
```

### Safety Rules
```
collision-predicted: collisionPredictions.length > 0
  Severity: CRITICAL
  Action: "Update path or abort mission"

entering-no-fly-zone: noFlyZones.length > 0
  Severity: CRITICAL
  Action: "RTL immediately"

altitude-extreme: altitude > 500m
  Severity: WARNING
  Action: "Ensure sufficient battery reserve"
```

---

## 🔍 Debugging & Troubleshooting

### Alert Not Triggering
**Symptoms:** Expected alert doesn't appear in EventConsole

**Debug Steps:**
1. Check DroneEntity value: Open browser DevTools → Console
   ```javascript
   useDroneEntityStore.getState().drone.battery.percentage
   ```
2. Verify condition is true for alert
3. Check throttle timer hasn't prevented trigger:
   ```javascript
   const engine = alertEngine;
   console.log(engine.getRuleIds());
   ```
4. Verify EventStore has events:
   ```javascript
   useEventStore.getState().events.length
   ```

### Alerts Spamming
**Symptoms:** Same alert repeatedly added every frame

**Causes:** Throttle too short or condition always true
- Battery alerts throttle: 5000ms (5 sec)
- Signal alerts throttle: 5000-15000ms
- Adjust with AlertEngine rule throttle value

### EventConsole Not Updating
**Symptoms:** New events added but console doesn't show

**Debug:**
1. Verify events in store: `useEventStore.getState().events`
2. Check subscription: Console should re-render
3. Verify filter isn't hiding events: Check severity/source filters
4. Browser console for errors (Framer Motion, animations)

### Performance Issues
**Symptoms:** Dashboard sluggish, map stutters with alerts

**Optimization:**
1. Limit event history: `useEventStore.getState().setMaxEvents(500)`
2. Disable non-critical rules: `alertEngine.disableRule('rule-id')`
3. Check Safari/Firefox: Some browsers slower with Framer Motion

---

## 📝 Integration Checklist

### Implementation Complete ✅
- [x] AlertEngine created with 20+ rules
- [x] EventStore created with event management
- [x] EventConsole component created with filtering
- [x] AlertPanel component created for critical alerts
- [x] Alert evaluation wired into 50ms update loop
- [x] AlertPanel integrated into main layout
- [x] EventConsole subscribed to EventStore
- [x] Severity and source color coding consistent

### Testing Needed
- [ ] Run dashboard and verify alerts appear
- [ ] Test battery decrease triggers correct alerts
- [ ] Test signal variation creates signal alerts
- [ ] Test mission waypoints trigger events
- [ ] Test filtering works in EventConsole
- [ ] Verify AlertPanel shows only critical/emergency
- [ ] Test event resolution ("ACK" button)
- [ ] Check performance at 100+ events

### Next Steps
1. Run dashboard: `npm run dev` in drone-command-center/
2. Monitor browser DevTools Performance tab
3. Generate test events by adjusting telemetry
4. Verify all alert types trigger correctly
5. Document any custom alert needs for specific mission types

---

## 🎯 Data Flow Example - Battery Critical

```
1. Simulator: battery decreases to 14%
2. 50ms interval triggers simulateUpdate()
3. Legacy droneStore updated with battery: 14
4. SimulationBridge.update() called
5. DroneEntityStore.setDrone() updates battery.percentage
   - previousDrone = <old state with battery: 16>
   - drone = <new state with battery: 14>
6. alertEngine.evaluate(drone, previousDrone) called
7. Rule 'battery-critical' evaluates: 14 < 15 → TRUE
8. Check throttle: Last triggered 10 seconds ago, throttle is 5sec → CAN FIRE
9. Generate event:
   {
     id: 'EVT-1734567890-abc123',
     timestamp: 1734567890,
     severity: 'EMERGENCY',
     source: 'BATTERY',
     title: 'CRITICAL BATTERY: 14%',
     description: 'CRITICAL BATTERY: 14% - RETURN HOME IMMEDIATELY',
     suggestedAction: 'Execute immediate RTL (Return To Launch)',
     data: { battery: 14, droneState: 'FLYING' }
   }
10. useEventStore.addEvent() adds event to store
11. EventConsole subscribes, re-renders with new event
12. AlertPanel subscribes, displays red banner
13. User sees both console entry and banner alert
14. User clicks "ACK" button to resolve alert
```

---

## 📚 References

- **AlertEngine:** `src/lib/alertEngine.ts`
- **EventStore:** `src/store/eventStore.ts`
- **EventConsole:** `src/components/gcs/EventConsole.tsx`
- **AlertPanel:** `src/components/gcs/AlertPanel.tsx`
- **Integration:** `src/app/page.tsx` (lines 40-102)
- **DroneEntity:** `src/types/droneEntity.ts`
