    // =============================================================================
// MJN GCS - Ground Control Station Type Definitions
// Production-grade types for professional autonomous drone operations
// =============================================================================

export interface GCSHeader {
  missionStatus: 'RUNNING' | 'PAUSED' | 'COMPLETE' | 'ABORTED' | 'STANDBY';
  connectionStatus: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'STANDBY';
  flightMode: string;
  missionTimer: number;
  utcTime: string;
  gpsQuality: number;
  windSpeed: number;
  cpuUsage: number;
  memoryUsage: number;
  telemetryRate: number;
  droneCount: number;
  emergency: boolean;
}

export interface MotorStatus {
  rpm: number[];
  temperature: number[];
  escTemp: number[];
  current: number[];
  voltage: number[];
  status: ('OK' | 'WARN' | 'FAIL')[];
}

export interface DroneHealthDetailed {
  battery: {
    percentage: number;
    voltage: number;
    current: number;
    power: number;
    temperature: number;
    cells: number[];
    health: number;
    cycles: number;
  };
  motors: MotorStatus;
  sensors: {
    gps: { status: 'OK' | 'WARN' | 'FAIL'; satellites: number; hdop: number };
    imu: { status: 'OK' | 'WARN' | 'FAIL'; temperature: number; gyro: number[]; accel: number[] };
    compass: { status: 'OK' | 'WARN' | 'FAIL'; heading: number; deviation: number };
    barometer: { status: 'OK' | 'WARN' | 'FAIL'; pressure: number; altitude: number };
    lidar: { status: 'OK' | 'WARN' | 'FAIL'; range: number; fov: number };
    camera: { status: 'OK' | 'WARN' | 'FAIL'; fps: number; temperature: number };
    radar: { status: 'OK' | 'WARN' | 'FAIL'; range: number; targets: number };
    ultrasonic: { status: 'OK' | 'WARN' | 'FAIL'; range: number };
  };
  system: {
    cpu: number;
    gpu: number;
    ram: number;
    disk: number;
    network: { rx: number; tx: number; signal: number };
    uptime: number;
  };
}

export interface MissionDetailed {
  id: string;
  name: string;
  progress: number;
  eta: string;
  currentWaypoint: number;
  totalWaypoints: number;
  distanceRemaining: number;
  timeRemaining: number;
  state: string;
  planner: {
    decision: string;
    reason: string;
    confidence: number;
    predictionConfidence: number;
    localizationQuality: number;
    obstacleCount: number;
    riskScore: number;
    successProbability: number;
    returnHome: boolean;
    emergencyStatus: 'NONE' | 'LOW_BATTERY' | 'CRITICAL' | 'OBSTACLE' | 'FAILSAFE';
  };
}

export interface Alert {
  id: string;
  timestamp: number;
  type: 'info' | 'warn' | 'error' | 'critical' | 'success';
  source: string;
  message: string;
  acknowledged: boolean;
  duration?: number;
}

export interface AIInsight {
  planner: string;
  decision: string;
  reason: string;
  confidence: number;
  obstacleCount: number;
  predictedCollisionTime: number | null;
  predictedLandingZone: { lat: number; lng: number } | null;
  energyEstimate: number;
  riskScore: number;
  successProbability: number;
  alternativeRoute: { lat: number; lng: number }[];
  plannerLatency: number;
  inferenceTime: number;
}

export interface WeatherDetailed {
  wind: { speed: number; direction: number; gusts: number };
  visibility: number;
  cloudCover: number;
  temperature: number;
  humidity: number;
  pressure: number;
  precipitation: number;
  rain: number;
  forecast: { time: number; wind: number; temp: number; precipitation: number }[];
}

export interface GCSState {
  header: GCSHeader;
  health: DroneHealthDetailed;
  mission: MissionDetailed;
  alerts: Alert[];
  ai: AIInsight;
  weather: WeatherDetailed;
  selectedTab: 'mission' | 'health' | 'ai' | 'weather';
  eventFilter: string;
  searchQuery: string;
  settings: {
    followDrone: boolean;
    autoCenter: boolean;
    speedControl: number;
    mapStyle: string;
  };
  
  // Actions
  setHeader: (data: Partial<GCSHeader>) => void;
  setHealth: (data: Partial<DroneHealthDetailed>) => void;
  setMission: (data: Partial<MissionDetailed>) => void;
  addAlert: (alert: Omit<Alert, 'id' | 'timestamp'>) => void;
  acknowledgeAlert: (id: string) => void;
  setAI: (data: Partial<AIInsight>) => void;
  setWeather: (data: Partial<WeatherDetailed>) => void;
  setEventFilter: (filter: string) => void;
  setSearchQuery: (query: string) => void;
  toggleFollowDrone: () => void;
  setSpeedControl: (speed: number) => void;
}