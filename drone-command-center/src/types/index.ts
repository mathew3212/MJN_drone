// =============================================================================
// MJN Drone Command Center - Core Type Definitions
// Premium aerospace-grade telemetry and mission data types
// =============================================================================

export type DroneStatus = 'IDLE' | 'NAVIGATE' | 'AVOID' | 'RETURN_HOME' | 'LAND' | 'EMERGENCY' | 'COMPLETE';
export type MissionState = 'INIT' | 'TAKEOFF' | 'CRUISE' | 'INSPECT' | 'RETURN' | 'LAND' | 'COMPLETE' | 'ABORT';
export type EmergencyState = 'NORMAL' | 'LOW_BATTERY' | 'CRITICAL_BATTERY' | 'NO_PATH' | 'STUCK' | 'COLLISION_RISK';
export type ThemeMode = 'dark' | 'midnight' | 'blueprint' | 'graphite' | 'operator';
export type PanelState = 'docked' | 'floating' | 'collapsed' | 'fullscreen';

export interface Vector2 {
  x: number;
  y: number;
}

export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface DroneTelemetry {
  id: string;
  position: Vector2;
  altitude: number;
  speed: number;
  heading: number;
  pitch: number;
  roll: number;
  yaw: number;
  battery: number;
  voltage: number;
  current: number;
  temperature: number;
  signal_strength: number;
  gps_accuracy: number;
  cpu_usage: number;
  gpu_usage: number;
  memory_usage: number;
  flight_mode: string;
  status: DroneStatus;
  distance_target: number;
  flight_time: number;
  vertical_speed: number;
  sensor_fps: number;
  inference_time: number;
  confidence_score: number;
}

export interface MissionData {
  id: string;
  state: MissionState;
  progress: number;
  eta: string;
  elapsed: number;
  distance_remaining: number;
  waypoints: Vector2[];
  current_waypoint: number;
  path: Vector2[];
  predicted_path: Vector2[];
  visited_path: Vector2[];
}

export interface DroneHealth {
  battery_health: number;
  motor_temp: number;
  motor_rpm: number[];
  prop_wear: number;
  imu_status: 'OK' | 'WARN' | 'FAIL';
  gps_status: 'OK' | 'WARN' | 'FAIL';
  compass_status: 'OK' | 'WARN' | 'FAIL';
  lidar_status: 'OK' | 'WARN' | 'FAIL';
  camera_status: 'OK' | 'WARN' | 'FAIL';
  esc_temp: number[];
  vibration: number;
  last_maintenance: number;
}

export interface AirspaceData {
  zones_active: number;
  violations: number;
  tfr_active: number;
  risk_score: number;
  decision: string;
  restricted_zones: ZoneData[];
  no_fly_zones: ZoneData[];
  corridors: CorridorData[];
}

export interface ZoneData {
  id: string;
  name: string;
  vertices: Vector2[];
  center: Vector2;
  color: string;
  opacity: number;
  type: 'restricted' | 'caution' | 'prohibited' | 'temporary' | 'sensitive';
}

export interface CorridorData {
  id: string;
  points: Vector2[];
  width: number;
  altitude_min: number;
  altitude_max: number;
}

export interface WeatherData {
  wind_speed: number;
  wind_direction: number;
  visibility: number;
  cloud_cover: number;
  precipitation: number;
  turbulence: number;
  temperature: number;
  pressure: number;
  humidity: number;
}

export interface GraphDataPoint {
  time: number;
  value: number;
  label?: string;
}

export interface TelemetryGraph {
  id: string;
  title: string;
  unit: string;
  color: string;
  data: GraphDataPoint[];
  min: number;
  max: number;
  live: boolean;
}

export interface PredictionData {
  trajectory_confidence: number;
  risk_probability: number;
  collision_probability: number;
  path_smoothness: number;
  prediction_accuracy: number;
  decision_confidence: number;
  obstacle_risk: number;
  path_cost: number;
}

export interface StatusLED {
  label: string;
  status: 'ok' | 'warn' | 'error' | 'off';
  value?: string;
}

export interface PanelConfig {
  id: string;
  type: string;
  title: string;
  state: PanelState;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
}

export interface LayoutConfig {
  id: string;
  name: string;
  panels: PanelConfig[];
}

// Color theme type
export interface ThemeColors {
  bgDark: string;
  bgPanel: string;
  bgInner: string;
  bgCard: string;
  bgGlass: string;
  border: string;
  borderGlow: string;
  primary: string;
  secondary: string;
  success: string;
  warning: string;
  danger: string;
  info: string;
  cyan: string;
  emerald: string;
  orange: string;
  purple: string;
  textMain: string;
  textValue: string;
  textLabel: string;
  textDim: string;
  textMuted: string;
}

// F1/Bloomberg style chart config
export interface ChartConfig {
  id: string;
  type: 'line' | 'area' | 'multi-axis' | 'bar' | 'radar' | 'gauge';
  title: string;
  yLabel: string;
  unit: string;
  color: string;
  gradientFrom: string;
  gradientTo: string;
  data: { time: number; values: Record<string, number> }[];
  series: { key: string; name: string; color: string; yAxisId?: string }[];
  yAxes: { id: string; label: string; min: number; max: number; color: string }[];
  min?: number;
  max?: number;
  showGrid?: boolean;
  showCrosshair?: boolean;
  live?: boolean;
  animationDuration?: number;
  strokeWidth?: number;
  areaOpacity?: number;
}