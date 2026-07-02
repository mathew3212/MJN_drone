'use client';

// =============================================================================
// MJN Drone OS - DroneEntity Store
// Single source of truth for the entire GCS.
// Every component subscribes to this store.
// When DroneEntity changes → Marker, Heading, Polyline, Mission, Widgets all update.
// =============================================================================

import { create } from 'zustand';
import { DroneEntity, BackendType, FlightStatus, HealthStatus, MissionState, PlannerType } from '@/types/droneEntity';

const BANGALORE_LAT = 12.9716;
const BANGALORE_LNG = 77.5946;

function createDefaultDroneEntity(): DroneEntity {
  const now = Date.now();
  return {
    id: 'MJN-01',
    latitude: BANGALORE_LAT + 0.02,
    longitude: BANGALORE_LNG + 0.015,
    altitude: 945,
    heading: 45,
    pitch: 0.5,
    roll: -1.2,
    yaw: 44.8,
    velocity: 12.5,
    verticalSpeed: 0.5,
    acceleration: 0.2,
    battery: {
      percentage: 87,
      voltage: 22.4,
      current: 3.2,
      power: 71.7,
      temperature: 42,
      cells: [4.2, 4.1, 4.1, 4.0],
      health: 94,
      cycles: 72,
    },
    signal: {
      strength: 92,
      quality: 0.95,
      linkMargin: 18,
      interference: 0.05,
      rssi: -65,
      snr: 28,
    },
    planner: {
      type: 'HPP-RRT*',
      decision: 'PROCEED',
      confidence: 0.94,
      reason: 'Path clear, no obstacles within 50m',
      inferenceTime: 12,
      predictionConfidence: 0.92,
      localizationQuality: 0.95,
    },
    missionState: 'CRUISE',
    status: 'NAVIGATE',
    health: 'OK',
    gps: {
      satellites: 14,
      hdop: 0.8,
      vdop: 1.2,
      fixType: 'RTK_FLOAT',
      accuracy: 0.8,
    },
    imu: {
      accelerationX: 0,
      accelerationY: 0,
      accelerationZ: 9.81,
      angularVelocityX: 0.01,
      angularVelocityY: -0.02,
      angularVelocityZ: 0.03,
      compassHeading: 45,
    },
    telemetry: {
      groundSpeed: 12.5,
      airSpeed: 13.2,
      verticalSpeed: 0.5,
      climbRate: 0.3,
      distanceToHome: 560,
      distanceToTarget: 420,
      flightTime: 342,
      timeToHome: 45,
      timeToTarget: 34,
    },
    prediction: {
      trajectoryConfidence: 0.92,
      collisionProbability: 0.02,
      pathSmoothness: 0.88,
      predictionAccuracy: 0.95,
      decisionConfidence: 0.97,
      obstacleRisk: 0.15,
      pathCost: 0.35,
      predictedCollisionTime: null,
      missionSuccessProbability: 0.96,
    },
    system: {
      cpuUsage: 34,
      gpuUsage: 28,
      ramUsage: 45,
      storageUsage: 12,
      diskUsage: 12,
      telemetryRate: 20,
      heartbeat: 1,
      rosStatus: 'OK',
      px4Status: 'OK',
      networkRx: 1.2,
      networkTx: 0.8,
      motorRpm: [4200, 4180, 4210, 4195],
      motorTemperature: [48, 47, 49, 46],
      escTemperature: [42, 43, 41, 44],
    },
    sensors: {
      lidar: 'OK',
      camera: 'OK',
      depthCamera: 'OK',
      radar: 'OK',
      ultrasonic: 'OK',
      opticalFlow: 'OK',
      detectionCount: 3,
      trackingIds: ['trk-001', 'trk-002', 'trk-003'],
      sensorConfidence: 0.94,
    },
    weather: {
      windSpeed: 8.5,
      windDirection: 270,
      gusts: 12,
      visibility: 15,
      humidity: 45,
      pressure: 1013,
      temperature: 22,
      rain: 0,
      forecast: [],
      warnings: [],
    },
    waypoints: [
      { id: 'wp-home', latitude: BANGALORE_LAT + 0.01, longitude: BANGALORE_LNG + 0.01, altitude: 920, type: 'home', label: 'HOME', reached: true, order: 0, eta: 0 },
      { id: 'wp-1', latitude: BANGALORE_LAT + 0.025, longitude: BANGALORE_LNG + 0.03, altitude: 950, type: 'inspect', label: 'INSPECT-A', reached: false, order: 1, eta: 45 },
      { id: 'wp-2', latitude: BANGALORE_LAT + 0.04, longitude: BANGALORE_LNG + 0.02, altitude: 960, type: 'inspect', label: 'INSPECT-B', reached: false, order: 2, eta: 120 },
      { id: 'wp-3', latitude: BANGALORE_LAT + 0.035, longitude: BANGALORE_LNG + 0.045, altitude: 940, type: 'hover', label: 'HOVER-ZONE', reached: false, order: 3, eta: 200 },
      { id: 'wp-landing', latitude: BANGALORE_LAT + 0.01, longitude: BANGALORE_LNG + 0.01, altitude: 920, type: 'land', label: 'LANDING', reached: false, order: 4, eta: 300 },
    ],
    currentWaypointIndex: 1,
    path: {
      visited: [
        { latitude: BANGALORE_LAT + 0.01, longitude: BANGALORE_LNG + 0.01, altitude: 920, timestamp: now - 5000 },
        { latitude: BANGALORE_LAT + 0.013, longitude: BANGALORE_LNG + 0.012, altitude: 930, timestamp: now - 4000 },
        { latitude: BANGALORE_LAT + 0.016, longitude: BANGALORE_LNG + 0.014, altitude: 940, timestamp: now - 3000 },
        { latitude: BANGALORE_LAT + 0.018, longitude: BANGALORE_LNG + 0.015, altitude: 945, timestamp: now - 2000 },
        { latitude: BANGALORE_LAT + 0.02, longitude: BANGALORE_LNG + 0.015, altitude: 945, timestamp: now - 1000 },
      ],
      current: [],
      planned: [
        { latitude: BANGALORE_LAT + 0.025, longitude: BANGALORE_LNG + 0.03, altitude: 950 },
        { latitude: BANGALORE_LAT + 0.04, longitude: BANGALORE_LNG + 0.02, altitude: 960 },
        { latitude: BANGALORE_LAT + 0.035, longitude: BANGALORE_LNG + 0.045, altitude: 940 },
        { latitude: BANGALORE_LAT + 0.01, longitude: BANGALORE_LNG + 0.01, altitude: 920 },
      ],
      returnHome: [],
      emergency: [],
      predicted: [],
    },
    overlays: {
      obstacles: [],
      restrictedAirspace: [],
      noFlyZones: [],
      weather: { windSpeed: 8.5, windDirection: 270, visibility: 15, turbulence: 0.2 },
      riskZones: [],
      collisionPredictions: [],
      safeLandingZones: [],
      geofence: [],
      emergencyLandingZones: [],
      powerLines: [],
    },
    timestamp: now,
    backend: 'internal-simulator',
    connected: true,
    missionId: 'M-2024-001',
    missionProgress: 42,
    missionEta: '04:32',
  };
}

export interface DroneEntityStoreState {
  drone: DroneEntity;
  previousDrone: DroneEntity | null;
  updateRate: number;
  latency: number;
  simulationConnected: boolean;
  droneConnected: boolean;
  currentBackend: BackendType;
  updateCount: number;
  lastUpdateTime: number;

  // Actions
  setDrone: (drone: Partial<DroneEntity>) => void;
  replaceDrone: (drone: DroneEntity) => void;
  setBackend: (backend: BackendType) => void;
  setConnectionState: (simConnected: boolean, droneConnected: boolean) => void;
  reset: () => void;
}

export const useDroneEntityStore = create<DroneEntityStoreState>((set, get) => ({
  drone: createDefaultDroneEntity(),
  previousDrone: null,
  updateRate: 0,
  latency: 0,
  simulationConnected: true,
  droneConnected: true,
  currentBackend: 'internal-simulator',
  updateCount: 0,
  lastUpdateTime: Date.now(),

  setDrone: (partial) => set((state) => {
    const now = Date.now();
    const elapsed = now - state.lastUpdateTime;
    const rate = elapsed > 0 ? Math.round(1000 / elapsed) : 60;
    return {
      previousDrone: { ...state.drone },
      drone: { ...state.drone, ...partial, timestamp: now },
      updateRate: Math.min(rate, 120),
      latency: elapsed,
      updateCount: state.updateCount + 1,
      lastUpdateTime: now,
    };
  }),

  replaceDrone: (drone) => set((state) => {
    const now = Date.now();
    const elapsed = now - state.lastUpdateTime;
    const rate = elapsed > 0 ? Math.round(1000 / elapsed) : 60;
    return {
      previousDrone: { ...state.drone },
      drone: { ...drone, timestamp: now },
      updateRate: Math.min(rate, 120),
      latency: elapsed,
      updateCount: state.updateCount + 1,
      lastUpdateTime: now,
    };
  }),

  setBackend: (backend) => set({ currentBackend: backend, drone: { ...get().drone, backend } }),

  setConnectionState: (simConnected, droneConnected) => set({
    simulationConnected: simConnected,
    droneConnected: droneConnected,
    drone: { ...get().drone, connected: droneConnected },
  }),

  reset: () => set({
    drone: createDefaultDroneEntity(),
    previousDrone: null,
    updateCount: 0,
    lastUpdateTime: Date.now(),
  }),
}));
