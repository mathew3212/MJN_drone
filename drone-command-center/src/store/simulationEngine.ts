'use client';

// =============================================================================
// MJN Drone OS - Simulation Engine v3
// Mission-driven, time-based, physics-compliant drone movement.
// Uses MissionGenerator for unique missions on every launch.
// =============================================================================

import { useDroneEntityStore } from './droneEntityStore';
import { generateMission, GeneratedMission } from './missionGenerator';
import {
  DroneEntity, MissionState, PlannerType, HealthStatus, FlightStatus, WaypointInfo
} from '@/types/droneEntity';

const EARTH_RADIUS = 6371000;

function haversine(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return EARTH_RADIUS * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}


export class SimulationEngine {
  private running = false;
  private tickId: ReturnType<typeof setInterval> | null = null;
  private mission: GeneratedMission | null = null;
  private tickCount = 0;
  private lastTickTimestamp = 0;
  private windAngle = 0;
  private windVariation = 0;
  private obstaclesGenerated = false;

  // Position state
  private currentLat = 12.9716;
  private currentLng = 77.5946;
  private currentAlt = 920;
  private currentHeading = 45;
  private displayLat = 12.9716;
  private displayLng = 77.5946;
  private targetHeading = 45;

  // Waypoint tracking
  private currentWaypointIdx = 0;
  private hoverTimer = 0;
  private totalDistanceFlown = 0;

  // Elapsed tracking
  private missionElapsed = 0;
  private hoverTimeTotal = 0;
  // Debug
  private debugDt = 0;
  private debugDistanceMoved = 0;

  // Simulation speed multiplier
  public speedMultiplier = 1;
  private paused = false;

  start() {
    if (this.running) return;
    this.running = true;
    this.tickCount = 0;
    this.lastTickTimestamp = Date.now();
    this.windAngle = Math.random() * 360;
    this.windVariation = 0;

    // Generate a unique mission for this run
    this.mission = generateMission();
    this.currentLat = this.mission.homeLat;
    this.currentLng = this.mission.homeLng;
    this.currentAlt = this.mission.homeAlt;
    this.displayLat = this.mission.homeLat;
    this.displayLng = this.mission.homeLng;
    this.currentHeading = 45;
    this.targetHeading = 45;
    this.currentWaypointIdx = 0;
    this.hoverTimer = 0;
    this.totalDistanceFlown = 0;
    this.speedMultiplier = 1;
    this.paused = false;

    setTimeout(() => this.generateObstacles(), 3000);
    this.initializeStore();
    this.tickId = setInterval(() => this.tick(), 50);
  }

  stop() {
    this.running = false;
    if (this.tickId) {
      clearInterval(this.tickId);
      this.tickId = null;
    }
  }

  isRunning(): boolean {
    return this.running;
  }

  restart() {
    this.stop();
    this.start();
  }

  setPaused(p: boolean) {
    this.paused = p;
  }

  setSpeed(speed: number) {
    this.speedMultiplier = speed;
  }

  getMission(): GeneratedMission | null {
    return this.mission;
  }

  getDebugInfo() {
    return {
      dt: this.debugDt,
      distanceMoved: this.debugDistanceMoved,
      tickCount: this.tickCount,
      speed: this.speedMultiplier,
      paused: this.paused,
      totalFlown: this.totalDistanceFlown,
      waypointIdx: this.currentWaypointIdx,
    };
  }

  private initializeStore() {
    if (!this.mission) return;
    useDroneEntityStore.getState().setDrone({
      latitude: this.currentLat,
      longitude: this.currentLng,
      altitude: this.currentAlt,
      heading: this.currentHeading,
      velocity: 0,
      missionState: 'TAKEOFF',
      status: 'NAVIGATE',
      missionProgress: 0,
      missionId: this.mission.id,
      missionEta: this.formatTime(this.mission.estimatedFlightTime),
      currentWaypointIndex: 0,
      battery: {
        percentage: 100,
        voltage: 25.2,
        current: 0,
        power: 0,
        temperature: 25,
        cells: [4.2, 4.2, 4.2, 4.2, 4.2, 4.2],
        health: 100,
        cycles: 42,
      },
    });
  }

  private formatTime(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  }

  private generateObstacles() {
    if (this.obstaclesGenerated) return;
    this.obstaclesGenerated = true;
    const drone = useDroneEntityStore.getState().drone;
    useDroneEntityStore.getState().setDrone({
      overlays: {
        ...drone.overlays,
        obstacles: [
          { latitude: 12.99, longitude: 77.61, radius: 15, height: 100, type: 'building', risk: 0.7 },
          { latitude: 12.985, longitude: 77.605, radius: 10, height: 80, type: 'tree', risk: 0.4 },
          { latitude: 12.995, longitude: 77.615, radius: 20, height: 50, type: 'structure', risk: 0.5 },
        ],
        noFlyZones: [
          { vertices: [{ latitude: 12.99, longitude: 77.63 }, { latitude: 13.0, longitude: 77.635 }, { latitude: 13.005, longitude: 77.62 }, { latitude: 12.995, longitude: 77.615 }], name: 'Military Zone Alpha', color: '#FF4D5A' },
        ],
        restrictedAirspace: [
          { vertices: [{ latitude: 13.02, longitude: 77.60 }, { latitude: 13.03, longitude: 77.61 }, { latitude: 13.025, longitude: 77.625 }, { latitude: 13.015, longitude: 77.615 }], name: 'Kempegowda Airport CTR', color: '#FFC857' },
        ],
        geofence: [
          { latitude: 13.035, longitude: 77.56 },
          { latitude: 13.035, longitude: 77.65 },
          { latitude: 12.94, longitude: 77.65 },
          { latitude: 12.94, longitude: 77.56 },
        ],
      },
    });
  }

  private tick() {
    if (!this.running || this.paused || !this.mission) return;

    // =========================================================================
    // 1. Compute real time delta (dt) from wall clock
    // =========================================================================
    const now = Date.now();
    let dt = Math.min((now - this.lastTickTimestamp) / 1000, 0.1);
    dt *= this.speedMultiplier; // Apply speed multiplier
    this.lastTickTimestamp = now;
    this.debugDt = dt;
    this.tickCount++;
    this.missionElapsed += dt;

    // =========================================================================
    // 2. Environmental variables
    // =========================================================================
    this.windAngle += (Math.random() - 0.5) * 0.05;
    this.windVariation += (Math.random() - 0.5) * 0.2 * dt;
    this.windVariation = Math.max(-3, Math.min(3, this.windVariation));
    const windSpeed = 8 + this.windVariation;

    // =========================================================================
    // 3. Mission state machine
    // =========================================================================
    const mission = this.mission;
    const waypoints = mission.waypoints;
    let missionState: MissionState = 'CRUISE';
    let flightStatus: FlightStatus = 'NAVIGATE';
    let targetVelocity = mission.missionSpeed;

    if (this.currentWaypointIdx === 0) {
      missionState = 'TAKEOFF';
      targetVelocity = 3;
      if (this.currentAlt >= mission.cruiseAltitude - 5) {
        this.currentWaypointIdx = 1;
      }
    }

    if (this.currentAlt < mission.cruiseAltitude && missionState === 'CRUISE') {
      this.currentAlt = Math.min(this.currentAlt + 15 * dt, mission.cruiseAltitude);
    }

    // =========================================================================
    // 4. Get current target waypoint
    // =========================================================================
    const wpIdx = this.currentWaypointIdx;
    if (wpIdx >= waypoints.length) {
      missionState = 'COMPLETE';
      flightStatus = 'COMPLETE';
      targetVelocity = 0;
    }

    const targetWp = wpIdx < waypoints.length ? waypoints[wpIdx] : null;
    if (!targetWp) {
      missionState = 'COMPLETE';
      flightStatus = 'COMPLETE';
      targetVelocity = 0;
    }

    // =========================================================================
    // 5. Handle hover at waypoints
    // =========================================================================
    if (targetWp && targetWp.hover && targetWp.hover > 0) {
      const distToTarget = haversine(this.currentLat, this.currentLng, targetWp.lat, targetWp.lng);
      if (distToTarget < 2 && this.hoverTimer < targetWp.hover) {
        this.hoverTimer += dt;
        targetVelocity = 0;
        missionState = 'HOVER';
        flightStatus = 'HOLD';
      }
      if (this.hoverTimer >= targetWp.hover) {
        this.hoverTimer = 0;
        this.currentWaypointIdx++;
        // Compute heading to next waypoint
        const nextWp = waypoints[this.currentWaypointIdx];
        if (nextWp) {
          this.targetHeading = this.calculateBearing(this.currentLat, this.currentLng, nextWp.lat, nextWp.lng);
        }
      }
    }

    // =========================================================================
    // 6. Compute heading to target for smooth turns
    // =========================================================================
    if (targetWp && targetVelocity > 0) {
      const bearing = this.calculateBearing(this.currentLat, this.currentLng, targetWp.lat, targetWp.lng);
      this.targetHeading = bearing;
    }

    // Smooth heading interpolation (rotate before translating)
    const headingDiff = this.shortestAngleDiff(this.currentHeading, this.targetHeading);
    const turnRate = 45 * dt; // 45 degrees per second max turn rate
    if (Math.abs(headingDiff) > turnRate) {
      this.currentHeading += Math.sign(headingDiff) * turnRate;
    } else {
      this.currentHeading = this.targetHeading;
    }

    // =========================================================================
    // 7. Velocity-driven movement
    // =========================================================================
    let achievedVelocity = 0;
    if (targetWp && targetVelocity > 0) {
      const distToTarget = haversine(this.currentLat, this.currentLng, targetWp.lat, targetWp.lng);

      // Slow down when approaching waypoint (within 10m)
      let approachSpeed = targetVelocity;
      if (distToTarget < 10 && targetWp.hover && targetWp.hover > 0) {
        approachSpeed = targetVelocity * (distToTarget / 10);
      }

      const moveDistance = approachSpeed * dt;
      const maxMove = Math.min(moveDistance, distToTarget);
      const fraction = distToTarget > 0.001 ? maxMove / distToTarget : 0;

      const newLat = lerp(this.currentLat, targetWp.lat, fraction);
      const newLng = lerp(this.currentLng, targetWp.lng, fraction);
      const newAlt = lerp(this.currentAlt, targetWp.alt, fraction);

      this.debugDistanceMoved = haversine(this.currentLat, this.currentLng, newLat, newLng);
      this.totalDistanceFlown += this.debugDistanceMoved;

      this.currentLat = newLat;
      this.currentLng = newLng;
      this.currentAlt = newAlt;

      achievedVelocity = dt > 0 ? this.debugDistanceMoved / dt : 0;

      // Check if we reached the waypoint
      if (!targetWp.hover || targetWp.hover === 0) {
        if (distToTarget < 1.5) {
          this.currentLat = targetWp.lat;
          this.currentLng = targetWp.lng;
          this.currentAlt = targetWp.alt;
          this.currentWaypointIdx++;
          if (this.currentWaypointIdx < waypoints.length) {
            const nextWp = waypoints[this.currentWaypointIdx];
            this.targetHeading = this.calculateBearing(this.currentLat, this.currentLng, nextWp.lat, nextWp.lng);
          }
        }
      }
    }

    // Check for RTH trigger
    if (wpIdx >= waypoints.length - 1 && targetWp?.label === 'RTH') {
      missionState = 'RETURN';
      flightStatus = 'RETURN_HOME';
      // Home is the last waypoint (RTH)
      targetVelocity = mission.missionSpeed * 1.2;
    }

    // =========================================================================
    // 8. Battery model (distance-based)
    // =========================================================================
    const store = useDroneEntityStore.getState();
    const baseBatteryDrain = this.totalDistanceFlown * 0.012; // 1% per ~83m
    const windPenalty = windSpeed > 12 ? (windSpeed - 12) * 0.002 : 0;
    const hoverPenalty = this.hoverTimeTotal * 0.005;
    const batteryPercent = Math.max(5, 100 - baseBatteryDrain - windPenalty * dt - hoverPenalty);
    const batteryHealth = Math.max(80, 100 - batteryPercent * 0.05);

    // =========================================================================
    // 9. ETA and progress
    // =========================================================================
    const remainingWps = waypoints.length - this.currentWaypointIdx;
    let remainingDist = 0;
    for (let i = this.currentWaypointIdx; i < waypoints.length - 1; i++) {
      remainingDist += haversine(waypoints[i].lat, waypoints[i].lng, waypoints[i + 1].lat, waypoints[i + 1].lng);
    }
    const totalDist = mission.totalDistance;
    const progress = Math.min(100, Math.round((this.totalDistanceFlown / totalDist) * 100));
    const etaSec = achievedVelocity > 0.1 ? remainingDist / achievedVelocity : remainingDist / mission.missionSpeed;
    const missionEta = this.formatTime(etaSec);

    // =========================================================================
    // 10. Commit to store
    // =========================================================================
    const distToHome = haversine(this.currentLat, this.currentLng, mission.homeLat, mission.homeLng);
    const homeBearing = this.calculateBearing(this.currentLat, this.currentLng, mission.homeLat, mission.homeLng);
    const timeToHome = achievedVelocity > 0.1 ? distToHome / achievedVelocity : 300;

    const health: HealthStatus = batteryPercent < 20 ? 'WARN' : batteryPercent < 10 ? 'CRITICAL' : 'OK';
    const collisionProbability = 0.02 + Math.random() * 0.01;
    const detectionCount = 1 + Math.floor(Math.random() * 3);
    const satellites = 12 + Math.floor(Math.random() * 6);
    const hdop = 0.5 + Math.random() * 0.7;

    useDroneEntityStore.getState().setDrone({
      latitude: this.currentLat,
      longitude: this.currentLng,
      altitude: this.currentAlt,
      heading: this.currentHeading,
      pitch: 0,
      roll: 0,
      yaw: this.currentHeading,
      velocity: achievedVelocity,
      verticalSpeed: 0,
      acceleration: 0,
      battery: {
        ...store.drone.battery,
        percentage: Math.max(0, batteryPercent),
        voltage: 25.2 * (batteryPercent / 100),
        current: 3.2 * (achievedVelocity / mission.missionSpeed),
        power: 22.4 * (batteryPercent / 100) * (achievedVelocity / mission.missionSpeed),
        temperature: 30 + (100 - batteryPercent) * 0.2,
        cells: Array.from({ length: 6 }, (_, i) => 4.2 * (batteryPercent / 100) + (Math.random() - 0.5) * 0.05),
        health: Math.round(batteryHealth),
        cycles: 42,
      },
      signal: {
        ...store.drone.signal,
        strength: Math.max(60, 92 + (Math.random() - 0.5) * 6),
        quality: 0.9 + Math.random() * 0.08,
        rssi: -95 + (92 + (Math.random() - 0.5) * 6) * 0.3,
        snr: (92 + (Math.random() - 0.5) * 6) * 0.35,
      },
      planner: {
        type: ['HPP-RRT*', 'DStarLite', 'Cinematic', 'AI-ROUTER'][Math.floor(Math.random() * 4)] as PlannerType,
        decision: missionState === 'RETURN' ? 'RETURN_HOME' : missionState === 'HOVER' ? 'HOLD' : missionState === 'COMPLETE' ? 'COMPLETE' : 'PROCEED',
        confidence: 0.85 + Math.random() * 0.12,
        reason: missionState === 'RETURN' ? 'Returning to home base' : 'Path clear, continuing mission',
        inferenceTime: 10 + Math.floor(Math.random() * 15),
        predictionConfidence: 0.85 + Math.random() * 0.1,
        localizationQuality: Math.min(1, 0.85 + Math.random() * 0.12),
      },
      missionState,
      status: flightStatus,
      health,
      gps: { satellites, hdop, vdop: hdop * 1.3, fixType: satellites >= 12 ? 'RTK_FLOAT' : '3D', accuracy: 0.5 + Math.random() * 1.0 },
      imu: {
        accelerationX: (Math.random() - 0.5) * 0.3,
        accelerationY: (Math.random() - 0.5) * 0.3,
        accelerationZ: 9.81,
        angularVelocityX: (Math.random() - 0.5) * 0.03,
        angularVelocityY: (Math.random() - 0.5) * 0.03,
        angularVelocityZ: (Math.random() - 0.5) * 0.03,
        compassHeading: this.currentHeading,
      },
      telemetry: {
        groundSpeed: achievedVelocity,
        airSpeed: achievedVelocity + Math.random() * 1.5,
        verticalSpeed: 0,
        climbRate: 0,
        distanceToHome: distToHome,
        distanceToTarget: targetWp ? haversine(this.currentLat, this.currentLng, targetWp.lat, targetWp.lng) : 0,
        flightTime: Math.round(this.missionElapsed),
        timeToHome,
        timeToTarget: achievedVelocity > 0.1 && targetWp ? haversine(this.currentLat, this.currentLng, targetWp.lat, targetWp.lng) / achievedVelocity : 0,
      },
      prediction: {
        trajectoryConfidence: 0.85 + Math.random() * 0.1,
        collisionProbability,
        pathSmoothness: 0.8 + Math.random() * 0.15,
        predictionAccuracy: 0.85 + Math.random() * 0.1,
        decisionConfidence: 0.88 + Math.random() * 0.1,
        obstacleRisk: 0.05 + Math.random() * 0.15,
        pathCost: 0.2 + Math.random() * 0.15,
        predictedCollisionTime: collisionProbability > 0.05 ? now + 8000 + Math.random() * 12000 : null,
        missionSuccessProbability: batteryPercent > 25 ? 0.85 + Math.random() * 0.12 : 0.3 + Math.random() * 0.3,
      },
      system: {
        ...store.drone.system,
        cpuUsage: 28 + Math.floor(Math.random() * 15),
        gpuUsage: 22 + Math.floor(Math.random() * 12),
        ramUsage: 35 + Math.floor(Math.random() * 12),
        telemetryRate: Math.round(1 / dt),
        heartbeat: 1,
        motorRpm: [4100, 4080, 4120, 4095].map(r => r + (Math.random() - 0.5) * 80),
        motorTemperature: [45, 44, 46, 43].map(t => t + Math.random() * 2),
        escTemperature: [40, 41, 39, 42].map(t => t + Math.random() * 2),
      },
      sensors: {
        ...store.drone.sensors,
        detectionCount,
        trackingIds: Array.from({ length: detectionCount }, (_, i) => `trk-${String(i + 1).padStart(3, '0')}`),
        sensorConfidence: 0.88 + Math.random() * 0.1,
      },
      weather: {
        windSpeed,
        windDirection: ((this.windAngle % 360) + 360) % 360,
        gusts: windSpeed * (1.2 + Math.random() * 0.5),
        visibility: 12 + Math.random() * 6,
        humidity: 40 + Math.random() * 15,
        pressure: 1012 + Math.random() * 3,
        temperature: 21 + Math.random() * 3,
        rain: Math.random() < 0.1 ? Math.random() * 2 : 0,
        forecast: [],
        warnings: windSpeed > 18 ? ['High wind warning'] : [],
      },
      waypoints: waypoints.map((wp, i) => ({
        id: `wp-${i}`,
        latitude: wp.lat,
        longitude: wp.lng,
        altitude: wp.alt,
        type: wp.type as 'takeoff' | 'land' | 'inspect' | 'hover' | 'waypoint' | 'home' | 'landing-zone',
        label: wp.label,
        reached: i < this.currentWaypointIdx,
        order: i,
        eta: i * (mission.estimatedFlightTime / waypoints.length),
      })),
      currentWaypointIndex: Math.min(this.currentWaypointIdx, waypoints.length - 1),
      path: {
        visited: [
          ...store.drone.path.visited,
          { latitude: this.currentLat, longitude: this.currentLng, altitude: this.currentAlt, timestamp: now },
        ].slice(-500),
        current: [{ latitude: this.currentLat, longitude: this.currentLng, altitude: this.currentAlt }],
        planned: waypoints.filter(wp => wp.label !== 'HOME').map(wp => ({ latitude: wp.lat, longitude: wp.lng, altitude: wp.alt })),
        returnHome: [{ latitude: mission.homeLat, longitude: mission.homeLng, altitude: mission.homeAlt }],
        emergency: [{ latitude: mission.homeLat, longitude: mission.homeLng, altitude: mission.homeAlt }],
        predicted: waypoints.slice(this.currentWaypointIdx).map(wp => ({ latitude: wp.lat, longitude: wp.lng, altitude: wp.alt })),
      },
      overlays: {
        ...store.drone.overlays,
        weather: { windSpeed, windDirection: ((this.windAngle % 360) + 360) % 360, visibility: 12 + Math.random() * 6, turbulence: 0.1 + Math.random() * 0.3 },
        riskZones: targetWp ? [{ latitude: targetWp.lat, longitude: targetWp.lng, radius: 20, risk: 0.2 }] : [],
      },
      missionProgress: progress,
      missionEta,
      missionId: mission.id,
      connected: true,
      timestamp: now,
    });
  }

  private calculateBearing(lat1: number, lng1: number, lat2: number, lng2: number): number {
    const dLng = ((lng2 - lng1) * Math.PI) / 180;
    const y = Math.sin(dLng) * Math.cos((lat2 * Math.PI) / 180);
    const x = Math.cos((lat1 * Math.PI) / 180) * Math.sin((lat2 * Math.PI) / 180) -
      Math.sin((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.cos(dLng);
    return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
  }

  private shortestAngleDiff(from: number, to: number): number {
    return ((to - from) % 360 + 540) % 360 - 180;
  }
}

export const simulationEngine = new SimulationEngine();