'use client';

// =============================================================================
// MJN Drone OS - Event Engine
// Monitors droneEntityStore state changes and generates structured events.
// Derives events from live state transitions — never from assumptions.
// =============================================================================

import { useDroneEntityStore } from './droneEntityStore';
import { DroneEntity, MissionState, HealthStatus } from '@/types/droneEntity';

export type EventSeverity = 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';

export interface DroneEvent {
  id: string;
  timestamp: number;
  severity: EventSeverity;
  source: string;
  code: string;
  message: string;
  description: string;
  suggestedAction: string;
  acknowledged: boolean;
}

export interface EventEngineState {
  events: DroneEvent[];
  unreadCount: number;
}

// Singleton state
let eventState: EventEngineState = { events: [], unreadCount: 0 };
const listeners: Array<() => void> = [];

function notifyListeners() {
  for (const listener of listeners) {
    try { listener(); } catch { /* keep alive */ }
  }
}

function addEvent(event: Omit<DroneEvent, 'id' | 'timestamp' | 'acknowledged'>) {
  const id = `evt-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
  eventState = {
    events: [
      { ...event, id, timestamp: Date.now(), acknowledged: false },
      ...eventState.events,
    ].slice(0, 500), // Keep last 500 events
    unreadCount: eventState.unreadCount + 1,
  };
  notifyListeners();
}

function getState(): EventEngineState {
  return eventState;
}

function acknowledgeEvent(eventId: string) {
  eventState = {
    ...eventState,
    events: eventState.events.map(e =>
      e.id === eventId ? { ...e, acknowledged: true } : e
    ),
    unreadCount: Math.max(0, eventState.unreadCount - 1),
  };
  notifyListeners();
}

function acknowledgeAll() {
  eventState = {
    events: eventState.events.map(e => ({ ...e, acknowledged: true })),
    unreadCount: 0,
  };
  notifyListeners();
}

function clearEvents() {
  eventState = { events: [], unreadCount: 0 };
  notifyListeners();
}

function subscribe(listener: () => void) {
  listeners.push(listener);
  return () => {
    const idx = listeners.indexOf(listener);
    if (idx >= 0) listeners.splice(idx, 1);
  };
}

// =============================================================================
// State Change Monitor — derives events from live state transitions
// =============================================================================

let lastMissionState: MissionState = 'INIT';
let lastHealthStatus: HealthStatus = 'OK';
let lastBatteryPercent = 100;
let lastGpsSatellites = 0;
let lastSignalStrength = 100;
let lastWindSpeed = 0;
let lastWaypointIndex = -1;
let lastPlannerType = '';
let missionStartedEmitted = false;
let missionCompleteEmitted = false;

export function monitorStateChanges() {
  const drone = useDroneEntityStore.getState().drone;
  if (!drone) return;

  const now = Date.now();

  // Mission state transitions
  if (drone.missionState !== lastMissionState) {
    if (drone.missionState === 'TAKEOFF' && lastMissionState === 'INIT') {
      if (!missionStartedEmitted) {
        addEvent({
          severity: 'INFO',
          source: 'Mission Manager',
          code: 'MISSION_STARTED',
          message: 'Mission Started',
          description: `Mission ${drone.missionId} has commenced. Drone transitioning to takeoff.`,
          suggestedAction: 'Monitor takeoff sequence',
        });
        missionStartedEmitted = true;
        missionCompleteEmitted = false;
      }
    }
    if (drone.missionState === 'COMPLETE') {
      if (!missionCompleteEmitted) {
        addEvent({
          severity: 'INFO',
          source: 'Mission Manager',
          code: 'MISSION_COMPLETE',
          message: 'Mission Completed',
          description: 'All waypoints visited. Mission completed successfully.',
          suggestedAction: 'Review mission log and prepare for next mission',
        });
        missionCompleteEmitted = true;
        missionStartedEmitted = false;
      }
    }
    if (drone.missionState === 'EMERGENCY') {
      addEvent({
        severity: 'CRITICAL',
        source: 'Mission Manager',
        code: 'EMERGENCY',
        message: 'Emergency Mode Activated',
        description: 'Drone has entered emergency mode. Initiating emergency procedures.',
        suggestedAction: 'Check system status. Prepare for emergency landing.',
      });
    }
    if (drone.missionState === 'RETURN') {
      addEvent({
        severity: 'INFO',
        source: 'Mission Manager',
        code: 'RETURN_HOME',
        message: 'Returning to Home',
        description: 'Drone has initiated return-to-home sequence.',
        suggestedAction: 'Monitor return path and landing sequence',
      });
    }
    lastMissionState = drone.missionState;
  }

  // Waypoint reached
  if (drone.currentWaypointIndex !== lastWaypointIndex && drone.currentWaypointIndex > 0) {
    const wp = drone.waypoints[drone.currentWaypointIndex];
    const prevWp = drone.waypoints[lastWaypointIndex >= 0 ? lastWaypointIndex : 0];
    addEvent({
      severity: 'INFO',
      source: 'Navigation Engine',
      code: 'WAYPOINT_REACHED',
      message: `Waypoint Reached: ${wp?.label || `WP-${drone.currentWaypointIndex}`}`,
      description: `Drone reached waypoint "${wp?.label || `WP-${drone.currentWaypointIndex}`}". ${drone.waypoints.length - drone.currentWaypointIndex - 1} remaining.`,
      suggestedAction: 'Continue monitoring mission progress',
    });
    lastWaypointIndex = drone.currentWaypointIndex;
  }

  // First waypoint index detection
  if (lastWaypointIndex < 0 && drone.currentWaypointIndex >= 0) {
    lastWaypointIndex = drone.currentWaypointIndex;
  }

  // Health transitions
  if (drone.health !== lastHealthStatus) {
    if (drone.health === 'WARN') {
      addEvent({
        severity: 'WARNING',
        source: 'System Health',
        code: 'HEALTH_WARN',
        message: 'Drone Health Degraded',
        description: `System health changed to WARN. Battery: ${Math.round(drone.battery.percentage)}%.`,
        suggestedAction: 'Reduce operational tempo. Prepare for potential return.',
      });
    }
    if (drone.health === 'CRITICAL') {
      addEvent({
        severity: 'CRITICAL',
        source: 'System Health',
        code: 'HEALTH_CRITICAL',
        message: 'Drone Health Critical',
        description: 'System health is CRITICAL. Immediate action required.',
        suggestedAction: 'Execute emergency landing immediately',
      });
    }
    if (drone.health === 'OK' && lastHealthStatus === 'WARN') {
      addEvent({
        severity: 'INFO',
        source: 'System Health',
        code: 'HEALTH_RECOVERED',
        message: 'Drone Health Recovered',
        description: 'System health has returned to normal.',
        suggestedAction: 'Continue normal operations',
      });
    }
    lastHealthStatus = drone.health;
  }

  // Battery level thresholds
  const batteryDrop = lastBatteryPercent - drone.battery.percentage;
  if (drone.battery.percentage < 30 && lastBatteryPercent >= 30) {
    addEvent({
      severity: 'WARNING',
      source: 'Power System',
      code: 'LOW_BATTERY',
      message: 'Low Battery Warning',
      description: `Battery at ${Math.round(drone.battery.percentage)}%. ${Math.round(drone.telemetry.timeToHome)}s to home.`,
      suggestedAction: 'Return to home or prepare for landing',
    });
  }
  if (drone.battery.percentage < 15 && lastBatteryPercent >= 15) {
    addEvent({
      severity: 'CRITICAL',
      source: 'Power System',
      code: 'CRITICAL_BATTERY',
      message: 'Critical Battery Level',
      description: `Battery critically low at ${Math.round(drone.battery.percentage)}%. Emergency landing required.`,
      suggestedAction: 'Execute emergency landing now',
    });
  }
  lastBatteryPercent = drone.battery.percentage;

  // GPS changes
  if (drone.gps.satellites < 6 && lastGpsSatellites >= 6) {
    addEvent({
      severity: 'WARNING',
      source: 'GPS',
      code: 'GPS_LOST',
      message: 'GPS Signal Lost',
      description: `GPS satellites dropped to ${drone.gps.satellites}. Fix quality degraded.`,
      suggestedAction: 'Switch to optical flow or inertial navigation',
    });
  }
  if (drone.gps.satellites >= 6 && lastGpsSatellites < 6 && lastGpsSatellites > 0) {
    addEvent({
      severity: 'INFO',
      source: 'GPS',
      code: 'GPS_RECOVERED',
      message: 'GPS Signal Recovered',
      description: `GPS lock restored with ${drone.gps.satellites} satellites.`,
      suggestedAction: 'Resume normal navigation',
    });
  }
  lastGpsSatellites = drone.gps.satellites;

  // Signal changes
  if (drone.signal.strength < 40 && lastSignalStrength >= 40) {
    addEvent({
      severity: 'WARNING',
      source: 'Telemetry',
      code: 'SIGNAL_WEAK',
      message: 'Signal Strength Low',
      description: `Signal at ${Math.round(drone.signal.strength)}%. SNR: ${Math.round(drone.signal.snr)}dB. Link margin: ${Math.round(drone.signal.linkMargin)}dB.`,
      suggestedAction: 'Check antenna orientation. Reduce distance.',
    });
  }
  lastSignalStrength = drone.signal.strength;

  // Wind warnings
  if (drone.weather.windSpeed > 15 && lastWindSpeed <= 15) {
    addEvent({
      severity: 'WARNING',
      source: 'Weather',
      code: 'HIGH_WIND',
      message: 'High Wind Warning',
      description: `Wind speed ${drone.weather.windSpeed.toFixed(1)} m/s from ${Math.round(drone.weather.windDirection)}°. Gusts up to ${drone.weather.gusts.toFixed(1)} m/s.`,
      suggestedAction: 'Reduce altitude. Consider returning to home if conditions worsen.',
    });
  }
  if (drone.weather.windSpeed > 20 && lastWindSpeed <= 20) {
    addEvent({
      severity: 'ERROR',
      source: 'Weather',
      code: 'EXTREME_WIND',
      message: 'Extreme Wind Alert',
      description: `Wind speed ${drone.weather.windSpeed.toFixed(1)} m/s - exceeding safe operating limits.`,
      suggestedAction: 'Return to home immediately or execute emergency landing',
    });
  }
  lastWindSpeed = drone.weather.windSpeed;

  // Planner changes
  if (drone.planner.type !== lastPlannerType && lastPlannerType !== '') {
    addEvent({
      severity: 'INFO',
      source: 'Decision Engine',
      code: 'PLANNER_SWITCHED',
      message: `Planner Switched to ${drone.planner.type}`,
      description: `Navigation planner changed from ${lastPlannerType} to ${drone.planner.type}. Reason: ${drone.planner.reason}`,
      suggestedAction: 'Monitor path quality after planner switch',
    });
  }
  lastPlannerType = drone.planner.type;

  // Obstacle detected
  if (drone.prediction.collisionProbability > 0.1 && Math.random() < 0.01) {
    addEvent({
      severity: 'WARNING',
      source: 'Perception',
      code: 'OBSTACLE_DETECTED',
      message: 'Obstacle Detected',
      description: `Collision probability ${(drone.prediction.collisionProbability * 100).toFixed(0)}%. Path adjustment required.`,
      suggestedAction: 'Monitor avoidance maneuver',
    });
  }

  // Collision predicted
  if (drone.prediction.predictedCollisionTime && Math.random() < 0.005) {
    addEvent({
      severity: 'ERROR',
      source: 'Prediction Engine',
      code: 'COLLISION_PREDICTED',
      message: 'Collision Predicted',
      description: `Collision predicted in ${Math.round((drone.prediction.predictedCollisionTime - now) / 1000)}s. Risk: ${(drone.prediction.collisionProbability * 100).toFixed(0)}%.`,
      suggestedAction: 'Take evasive action. Switch to obstacle avoidance mode.',
    });
  }
}

export const eventEngine = {
  getState,
  addEvent,
  acknowledgeEvent,
  acknowledgeAll,
  clearEvents,
  subscribe,
  monitorStateChanges,
};