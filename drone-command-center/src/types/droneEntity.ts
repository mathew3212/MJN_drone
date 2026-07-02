'use client';

// =============================================================================
// MJN Drone OS - DroneEntity Type Definition
// First-class drone object that the entire system subscribes to.
// Every backend (Simulator, PX4, Gazebo, AirSim, MAVSDK) publishes this.
// =============================================================================

export type PlannerType = 'HPP-RRT*' | 'GridPlanner' | 'DStarLite' | 'Cinematic' | 'AI-ROUTER' | 'NONE';
export type MissionState = 'INIT' | 'TAKEOFF' | 'CRUISE' | 'INSPECT' | 'HOVER' | 'RETURN' | 'LAND' | 'COMPLETE' | 'ABORT' | 'EMERGENCY';
export type FlightStatus = 'IDLE' | 'NAVIGATE' | 'AVOID' | 'HOLD' | 'RETURN_HOME' | 'LAND' | 'EMERGENCY' | 'COMPLETE';
export type HealthStatus = 'OK' | 'WARN' | 'CRITICAL' | 'FAIL';
export type ConnectionState = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED' | 'LOST';
export type BackendType = 'internal-simulator' | 'px4-sitl' | 'gazebo' | 'airsim' | 'mavsdk' | 'real-drone';

export interface PlannerInfo {
  type: PlannerType;
  decision: string;
  confidence: number;
  reason: string;
  inferenceTime: number;
  predictionConfidence: number;
  localizationQuality: number;
}

export interface GPSInfo {
  satellites: number;
  hdop: number;
  vdop: number;
  fixType: 'NO_FIX' | '2D' | '3D' | 'DGPS' | 'RTK_FLOAT' | 'RTK_FIXED';
  accuracy: number;
}

export interface BatteryInfo {
  percentage: number;
  voltage: number;
  current: number;
  power: number;
  temperature: number;
  cells: number[];
  health: number;
  cycles: number;
}

export interface SignalInfo {
  strength: number;
  quality: number;
  linkMargin: number;
  interference: number;
  rssi: number;
  snr: number;
}

export interface TelemetryInfo {
  groundSpeed: number;
  airSpeed: number;
  verticalSpeed: number;
  climbRate: number;
  distanceToHome: number;
  distanceToTarget: number;
  flightTime: number;
  timeToHome: number;
  timeToTarget: number;
}

export interface IMUInfo {
  accelerationX: number;
  accelerationY: number;
  accelerationZ: number;
  angularVelocityX: number;
  angularVelocityY: number;
  angularVelocityZ: number;
  compassHeading: number;
}

export interface PredictionInfo {
  trajectoryConfidence: number;
  collisionProbability: number;
  pathSmoothness: number;
  predictionAccuracy: number;
  decisionConfidence: number;
  obstacleRisk: number;
  pathCost: number;
  predictedCollisionTime: number | null;
  missionSuccessProbability: number;
}

export interface SystemInfo {
  cpuUsage: number;
  gpuUsage: number;
  ramUsage: number;
  storageUsage: number;
  diskUsage: number;
  telemetryRate: number;
  heartbeat: number;
  rosStatus: 'OK' | 'WARN' | 'FAIL';
  px4Status: 'OK' | 'WARN' | 'FAIL';
  networkRx: number;
  networkTx: number;
  motorRpm: number[];
  motorTemperature: number[];
  escTemperature: number[];
}

export interface SensorStatusInfo {
  lidar: 'OK' | 'WARN' | 'FAIL';
  camera: 'OK' | 'WARN' | 'FAIL';
  depthCamera: 'OK' | 'WARN' | 'FAIL';
  radar: 'OK' | 'WARN' | 'FAIL';
  ultrasonic: 'OK' | 'WARN' | 'FAIL';
  opticalFlow: 'OK' | 'WARN' | 'FAIL';
  detectionCount: number;
  trackingIds: string[];
  sensorConfidence: number;
}

export interface WeatherInfo {
  windSpeed: number;
  windDirection: number;
  gusts: number;
  visibility: number;
  humidity: number;
  pressure: number;
  temperature: number;
  rain: number;
  forecast: Array<{ time: number; wind: number; temp: number; precipitation: number }>;
  warnings: string[];
}

export interface WaypointInfo {
  id: string;
  latitude: number;
  longitude: number;
  altitude: number;
  type: 'takeoff' | 'land' | 'inspect' | 'hover' | 'waypoint' | 'home' | 'landing-zone';
  label: string;
  reached: boolean;
  order: number;
  eta: number;
}

export interface PathInfo {
  visited: Array<{ latitude: number; longitude: number; altitude: number; timestamp: number }>;
  current: Array<{ latitude: number; longitude: number; altitude: number }>;
  planned: Array<{ latitude: number; longitude: number; altitude: number }>;
  returnHome: Array<{ latitude: number; longitude: number; altitude: number }>;
  emergency: Array<{ latitude: number; longitude: number; altitude: number }>;
  predicted: Array<{ latitude: number; longitude: number; altitude: number }>;
}

export interface OverlayInfo {
  obstacles: Array<{ latitude: number; longitude: number; radius: number; height: number; type: string; risk: number }>;
  restrictedAirspace: Array<{ vertices: Array<{ latitude: number; longitude: number }>; name: string; color: string }>;
  noFlyZones: Array<{ vertices: Array<{ latitude: number; longitude: number }>; name: string; color: string }>;
  weather: { windSpeed: number; windDirection: number; visibility: number; turbulence: number };
  riskZones: Array<{ latitude: number; longitude: number; radius: number; risk: number }>;
  collisionPredictions: Array<{ latitude: number; longitude: number; probability: number; timeToImpact: number }>;
  safeLandingZones: Array<{ latitude: number; longitude: number; radius: number; suitability: number }>;
  geofence: Array<{ latitude: number; longitude: number }>;
  emergencyLandingZones: Array<{ latitude: number; longitude: number; radius: number }>;
  powerLines: Array<{ start: { latitude: number; longitude: number }; end: { latitude: number; longitude: number } }>;
}

export interface DroneEntity {
  id: string;
  latitude: number;
  longitude: number;
  altitude: number;
  heading: number;
  pitch: number;
  roll: number;
  yaw: number;
  velocity: number;
  verticalSpeed: number;
  acceleration: number;
  battery: BatteryInfo;
  signal: SignalInfo;
  planner: PlannerInfo;
  missionState: MissionState;
  status: FlightStatus;
  health: HealthStatus;
  gps: GPSInfo;
  imu: IMUInfo;
  telemetry: TelemetryInfo;
  prediction: PredictionInfo;
  system: SystemInfo;
  sensors: SensorStatusInfo;
  weather: WeatherInfo;
  waypoints: WaypointInfo[];
  currentWaypointIndex: number;
  path: PathInfo;
  overlays: OverlayInfo;
  timestamp: number;
  backend: BackendType;
  connected: boolean;
  missionId: string;
  missionProgress: number;
  missionEta: string;
}
