// =============================================================================
// MJN Drone Command Center - Global State Store
// Zustand-powered reactive state management for real-time telemetry
// =============================================================================

import { create } from 'zustand';
import {
  DroneTelemetry,
  MissionData,
  AirspaceData,
  WeatherData,
  PredictionData,
  DroneHealth,
  ThemeMode,
  PanelConfig,
  Vector2,
} from '@/types';

const BASE_TELEMETRY: DroneTelemetry = {
  id: 'MJN-01',
  position: { x: 50, y: 50 },
  altitude: 45,
  speed: 12.5,
  heading: 45,
  pitch: 0.5,
  roll: -1.2,
  yaw: 44.8,
  battery: 87,
  voltage: 22.4,
  current: 3.2,
  temperature: 42.1,
  signal_strength: 92,
  gps_accuracy: 0.8,
  cpu_usage: 34,
  gpu_usage: 45,
  memory_usage: 28,
  flight_mode: 'AUTO',
  status: 'NAVIGATE',
  distance_target: 560,
  flight_time: 342,
  vertical_speed: 0.5,
  sensor_fps: 30,
  inference_time: 12,
  confidence_score: 0.94,
};

const BASE_MISSION: MissionData = {
  id: 'M-2024-001',
  state: 'CRUISE',
  progress: 42,
  eta: '04:32',
  elapsed: 342,
  distance_remaining: 560,
  waypoints: [{ x: 10, y: 10 }, { x: 90, y: 20 }, { x: 50, y: 90 }, { x: 90, y: 90 }],
  current_waypoint: 2,
  path: [],
  predicted_path: [],
  visited_path: [{ x: 5, y: 5 }, { x: 15, y: 12 }, { x: 30, y: 18 }, { x: 42, y: 30 }],
};

const BASE_AIRSPACE: AirspaceData = {
  zones_active: 5,
  violations: 0,
  tfr_active: 1,
  risk_score: 0.12,
  decision: 'PROCEED',
  restricted_zones: [],
  no_fly_zones: [],
  corridors: [],
};

const BASE_WEATHER: WeatherData = {
  wind_speed: 8.5,
  wind_direction: 270,
  visibility: 15,
  cloud_cover: 30,
  precipitation: 0,
  turbulence: 0.2,
  temperature: 22,
  pressure: 1013,
  humidity: 45,
};

const BASE_PREDICTION: PredictionData = {
  trajectory_confidence: 0.92,
  risk_probability: 0.08,
  collision_probability: 0.02,
  path_smoothness: 0.88,
  prediction_accuracy: 0.95,
  decision_confidence: 0.97,
  obstacle_risk: 0.15,
  path_cost: 0.35,
};

const BASE_HEALTH: DroneHealth = {
  battery_health: 94,
  motor_temp: 48,
  motor_rpm: [4200, 4180, 4210, 4195],
  prop_wear: 12,
  imu_status: 'OK',
  gps_status: 'OK',
  compass_status: 'OK',
  lidar_status: 'OK',
  camera_status: 'OK',
  esc_temp: [42, 43, 41, 44],
  vibration: 0.08,
  last_maintenance: 72,
};

const DEFAULT_PANELS: PanelConfig[] = [
  { id: 'mission-3d-map', type: '3d-map', title: '3D Mission Map', state: 'docked', x: 0, y: 0, w: 6, h: 4 },
  { id: 'telemetry-speed', type: 'telem-graph', title: 'Speed', state: 'docked', x: 6, y: 0, w: 3, h: 2 },
  { id: 'telemetry-altitude', type: 'telem-graph', title: 'Altitude', state: 'docked', x: 9, y: 0, w: 3, h: 2 },
  { id: 'telemetry-battery', type: 'telem-graph', title: 'Battery', state: 'docked', x: 6, y: 2, w: 3, h: 2 },
  { id: 'telemetry-cpu', type: 'telem-graph', title: 'CPU Usage', state: 'docked', x: 9, y: 2, w: 3, h: 2 },
  { id: 'drone-status', type: 'drone-status', title: 'Drone Status', state: 'docked', x: 12, y: 0, w: 3, h: 2 },
  { id: 'mission-timeline', type: 'mission-timeline', title: 'Mission Timeline', state: 'docked', x: 12, y: 2, w: 3, h: 2 },
  { id: 'airspace', type: 'airspace', title: 'Airspace', state: 'docked', x: 15, y: 0, w: 3, h: 4 },
  { id: 'drone-health', type: 'drone-health', title: 'Drone Health', state: 'docked', x: 0, y: 4, w: 3, h: 3 },
  { id: 'prediction-panel', type: 'prediction', title: 'Prediction', state: 'docked', x: 3, y: 4, w: 3, h: 3 },
  { id: 'telemetry-signal', type: 'telem-graph', title: 'Signal Strength', state: 'docked', x: 6, y: 4, w: 3, h: 3 },
  { id: 'telemetry-gps', type: 'telem-graph', title: 'GPS Accuracy', state: 'docked', x: 9, y: 4, w: 3, h: 3 },
  { id: 'graph-workspace', type: 'graph-workspace', title: 'Graph Workspace', state: 'docked', x: 12, y: 4, w: 6, h: 3 },
  { id: 'event-console', type: 'event-console', title: 'Event Console', state: 'docked', x: 0, y: 7, w: 18, h: 2 },
];

export interface TelemetryHistory {
  speed: { time: number; value: number }[];
  altitude: { time: number; value: number }[];
  battery: { time: number; value: number }[];
  cpu: { time: number; value: number }[];
  signal: { time: number; value: number }[];
  gps: { time: number; value: number }[];
  temperature: { time: number; value: number }[];
  confidence: { time: number; value: number }[];
  motorTemp: { time: number; value: number }[];
  windSpeed: { time: number; value: number }[];
  obstacleRisk: { time: number; value: number }[];
}

interface DroneStore {
  // Telemetry
  telemetry: DroneTelemetry;
  telemetryHistory: TelemetryHistory;
  
  // Mission
  mission: MissionData;
  
  // Systems
  airspace: AirspaceData;
  weather: WeatherData;
  prediction: PredictionData;
  health: DroneHealth;
  
  // UI State
  theme: ThemeMode;
  selectedDrone: string;
  timeAcceleration: number;
  isPaused: boolean;
  fps: number;
  
  // Panels
  panels: PanelConfig[];
  focusedPanel: string | null;
  
  // Event Log
  events: { id: number; time: string; type: 'info' | 'warn' | 'error' | 'success'; message: string }[];
  
  // Actions
  setTheme: (theme: ThemeMode) => void;
  setTelemetry: (data: Partial<DroneTelemetry>) => void;
  setMission: (data: Partial<MissionData>) => void;
  updatePanels: (panels: PanelConfig[]) => void;
  togglePanelState: (panelId: string) => void;
  focusPanel: (panelId: string | null) => void;
  addEvent: (type: 'info' | 'warn' | 'error' | 'success', message: string) => void;
  simulateUpdate: () => void;
  togglePause: () => void;
  setTimeAcceleration: (accel: number) => void;
}

let eventCounter = 0;
let timeCounter = 0;

export const useDroneStore = create<DroneStore>((set, get) => ({
  telemetry: { ...BASE_TELEMETRY },
  telemetryHistory: {
    speed: [],
    altitude: [],
    battery: [],
    cpu: [],
    signal: [],
    gps: [],
    temperature: [],
    confidence: [],
    motorTemp: [],
    windSpeed: [],
    obstacleRisk: [],
  },
  
  mission: { ...BASE_MISSION },
  airspace: { ...BASE_AIRSPACE },
  weather: { ...BASE_WEATHER },
  prediction: { ...BASE_PREDICTION },
  health: { ...BASE_HEALTH },
  
  theme: 'dark',
  selectedDrone: 'MJN-01',
  timeAcceleration: 1,
  isPaused: false,
  fps: 60,
  
  panels: DEFAULT_PANELS,
  focusedPanel: null,
  
  events: [
    { id: eventCounter++, time: '14:32:05', type: 'success', message: 'System initialized — all subsystems nominal' },
    { id: eventCounter++, time: '14:32:08', type: 'info', message: 'GPS lock acquired — 12 satellites' },
    { id: eventCounter++, time: '14:32:10', type: 'success', message: 'Mission M-2024-001 started — proceeding to WP-1' },
    { id: eventCounter++, time: '14:32:15', type: 'info', message: 'Autonomous mode engaged' },
    { id: eventCounter++, time: '14:33:22', type: 'warn', message: 'Wind advisory — 8.5 m/s from W' },
    { id: eventCounter++, time: '14:35:00', type: 'info', message: 'Reached WP-1 — proceeding to WP-2' },
  ],
  
  setTheme: (theme) => set({ theme }),
  
  setTelemetry: (data) => set((state) => ({
    telemetry: { ...state.telemetry, ...data },
  })),
  
  setMission: (data) => set((state) => ({
    mission: { ...state.mission, ...data },
  })),
  
  updatePanels: (panels) => set({ panels }),
  
  togglePanelState: (panelId) => set((state) => ({
    panels: state.panels.map((p) =>
      p.id === panelId
        ? {
            ...p,
            state: p.state === 'docked' ? 'fullscreen' : p.state === 'fullscreen' ? 'collapsed' : p.state === 'collapsed' ? 'docked' : 'docked',
          }
        : p
    ),
  })),
  
  focusPanel: (panelId) => set({ focusedPanel: panelId }),
  
  addEvent: (type, message) => set((state) => ({
    events: [
      ...state.events.slice(-99),
      {
        id: eventCounter++,
        time: new Date().toLocaleTimeString(),
        type,
        message,
      },
    ],
  })),
  
  togglePause: () => set((state) => ({ isPaused: !state.isPaused })),
  
  setTimeAcceleration: (accel) => set({ timeAcceleration: accel }),
  
  simulateUpdate: () => {
    if (get().isPaused) return;
    
    timeCounter++;
    const t = timeCounter;
    const now = Date.now();
    
    // Simulate realistic telemetry variations
    const telemetry = get().telemetry;
    const mission = get().mission;
    const weather = get().weather;
    const airspace = get().airspace;
    const prediction = get().prediction;
    
    const newSpeed = Math.max(0, telemetry.speed + (Math.random() - 0.5) * 1.5);
    const newAltitude = Math.max(5, Math.min(150, telemetry.altitude + (Math.random() - 0.5) * 2));
    const newBattery = Math.max(0, telemetry.battery - 0.02 * get().timeAcceleration);
    const newHeading = (telemetry.heading + (Math.random() - 0.5) * 3) % 360;
    const newProgress = Math.min(100, mission.progress + 0.1 * get().timeAcceleration);
    const newCpu = Math.max(10, Math.min(95, 34 + Math.sin(t * 0.1) * 15 + (Math.random() - 0.5) * 10));
    const newSignal = Math.max(60, Math.min(100, 92 + Math.sin(t * 0.05) * 5 + (Math.random() - 0.5) * 3));
    const newGps = Math.max(0.3, Math.min(3, 0.8 + Math.sin(t * 0.03) * 0.2 + (Math.random() - 0.5) * 0.2));
    const newTemp = Math.max(35, Math.min(85, 42 + Math.sin(t * 0.08) * 5 + (Math.random() - 0.5) * 3));
    const newConfidence = Math.max(0.7, Math.min(1, 0.94 + Math.sin(t * 0.02) * 0.03 + (Math.random() - 0.5) * 0.02));
    
    const newPos: Vector2 = {
      x: telemetry.position.x + Math.cos(telemetry.heading * Math.PI / 180) * 0.3,
      y: telemetry.position.y + Math.sin(telemetry.heading * Math.PI / 180) * 0.3,
    };
    
    const newWind = Math.max(0, 8.5 + Math.sin(t * 0.04) * 3 + (Math.random() - 0.5) * 1);
    const newObstacleRisk = Math.max(0, Math.min(1, 0.15 + Math.sin(t * 0.07) * 0.1 + (Math.random() - 0.5) * 0.05));
    
    const newElapsed = mission.elapsed + 1 * get().timeAcceleration;
    
    // Update visited path
    const newVisited = [...mission.visited_path, newPos].slice(-50);
    
    // Update prediction points
    const predPath = Array.from({ length: 20 }, (_, i) => ({
      x: newPos.x + Math.cos((telemetry.heading + i * 5) * Math.PI / 180) * (i + 1) * 1.5,
      y: newPos.y + Math.sin((telemetry.heading + i * 5) * Math.PI / 180) * (i + 1) * 1.5,
    }));
    
    // Update telemetry history (max 100 points per series)
    const appendHistory = (arr: { time: number; value: number }[], val: number) => {
      const next = [...arr, { time: now, value: val }];
      return next.length > 150 ? next.slice(-150) : next;
    };
    
    // Airspace risk oscillation
    const newAirspaceRisk = Math.max(0, Math.min(1, airspace.risk_score + (Math.random() - 0.5) * 0.02));
    
    set({
      telemetry: {
        ...telemetry,
        speed: newSpeed,
        altitude: newAltitude,
        battery: newBattery,
        heading: newHeading,
        position: newPos,
        cpu_usage: newCpu,
        signal_strength: newSignal,
        gps_accuracy: newGps,
        temperature: newTemp,
        confidence_score: newConfidence,
        inference_time: Math.max(5, 12 + Math.sin(t * 0.06) * 3 + (Math.random() - 0.5) * 2),
        flight_time: newElapsed,
        distance_target: Math.max(0, telemetry.distance_target - 0.5),
      },
      mission: {
        ...mission,
        progress: newProgress,
        elapsed: newElapsed,
        visited_path: newVisited,
        predicted_path: predPath,
      },
      weather: {
        ...weather,
        wind_speed: newWind,
        wind_direction: (weather.wind_direction + (Math.random() - 0.5) * 5) % 360,
      },
      airspace: {
        ...airspace,
        risk_score: newAirspaceRisk,
      },
      prediction: {
        ...prediction,
        trajectory_confidence: newConfidence,
        risk_probability: newObstacleRisk,
        obstacle_risk: newObstacleRisk,
        path_smoothness: Math.max(0.5, 0.88 + Math.sin(t * 0.03) * 0.1),
        prediction_accuracy: Math.max(0.7, 0.95 + Math.sin(t * 0.04) * 0.03),
        decision_confidence: Math.max(0.7, 0.97 + Math.sin(t * 0.02) * 0.02),
      },
      telemetryHistory: {
        speed: appendHistory(get().telemetryHistory.speed, newSpeed),
        altitude: appendHistory(get().telemetryHistory.altitude, newAltitude),
        battery: appendHistory(get().telemetryHistory.battery, newBattery),
        cpu: appendHistory(get().telemetryHistory.cpu, newCpu),
        signal: appendHistory(get().telemetryHistory.signal, newSignal),
        gps: appendHistory(get().telemetryHistory.gps, newGps),
        temperature: appendHistory(get().telemetryHistory.temperature, newTemp),
        confidence: appendHistory(get().telemetryHistory.confidence, newConfidence),
        motorTemp: appendHistory(get().telemetryHistory.motorTemp, 48 + Math.sin(t * 0.05) * 5 + (Math.random() - 0.5) * 2),
        windSpeed: appendHistory(get().telemetryHistory.windSpeed, newWind),
        obstacleRisk: appendHistory(get().telemetryHistory.obstacleRisk, newObstacleRisk),
      },
    });
  },
}));