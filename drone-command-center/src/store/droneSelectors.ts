'use client';

import { DroneEntity, HealthStatus, MissionState, SystemInfo, WaypointInfo } from '@/types/droneEntity';
import { DroneEntityStoreState } from './droneEntityStore';

export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const secs = total % 60;
  return `${minutes}m ${secs}s`;
}

function systemHealthFromStatuses(...statuses: Array<'OK' | 'WARN' | 'FAIL'>): HealthStatus {
  if (statuses.includes('FAIL')) return 'CRITICAL';
  if (statuses.includes('WARN')) return 'WARN';
  return 'OK';
}

export function missionStatusLabel(state: MissionState): 'RUNNING' | 'PAUSED' | 'COMPLETE' | 'ABORTED' | 'STANDBY' {
  if (state === 'COMPLETE') return 'COMPLETE';
  if (state === 'ABORT' || state === 'EMERGENCY') return 'ABORTED';
  if (state === 'HOVER') return 'PAUSED';
  if (state === 'INIT') return 'STANDBY';
  return 'RUNNING';
}

export function connectionStatusLabel(store: Pick<DroneEntityStoreState, 'simulationConnected' | 'droneConnected'>): 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' {
  if (store.simulationConnected && store.droneConnected) return 'CONNECTED';
  if (!store.simulationConnected && !store.droneConnected) return 'DISCONNECTED';
  return 'RECONNECTING';
}

export function getCurrentWaypoint(drone: DroneEntity): WaypointInfo | null {
  return drone.waypoints[drone.currentWaypointIndex] ?? null;
}

export function getRemainingWaypoints(drone: DroneEntity): WaypointInfo[] {
  return drone.waypoints.filter((waypoint) => waypoint.order >= drone.currentWaypointIndex && !waypoint.reached);
}

export function getObstacleCount(drone: DroneEntity): number {
  return drone.overlays.obstacles.length + drone.overlays.collisionPredictions.length;
}

export function getRiskScore(drone: DroneEntity): number {
  return Math.max(
    drone.prediction.obstacleRisk,
    drone.overlays.collisionPredictions.reduce((max, prediction) => Math.max(max, prediction.probability), 0),
  );
}

export function getEmergencyStatus(drone: DroneEntity): 'NONE' | 'LOW_BATTERY' | 'CRITICAL' | 'OBSTACLE' | 'FAILSAFE' {
  if (drone.status === 'EMERGENCY' || drone.health === 'CRITICAL') return 'CRITICAL';
  if (drone.overlays.collisionPredictions.length > 0) return 'OBSTACLE';
  if (drone.battery.percentage < 30) return 'LOW_BATTERY';
  if (!drone.connected) return 'FAILSAFE';
  return 'NONE';
}

export function getReturnHomeActive(drone: DroneEntity): boolean {
  return drone.missionState === 'RETURN' || drone.status === 'RETURN_HOME' || drone.path.returnHome.length > 0;
}

export function getObjectiveLabel(drone: DroneEntity): string {
  const currentWaypoint = getCurrentWaypoint(drone);
  if (!currentWaypoint) return 'Mission complete';
  return `${currentWaypoint.label} (${currentWaypoint.type})`;
}

export function getMissionName(drone: DroneEntity): string {
  return `${drone.id} / ${getObjectiveLabel(drone)}`;
}

export function getSystemStatus(system: SystemInfo): HealthStatus {
  return systemHealthFromStatuses(system.rosStatus, system.px4Status);
}
