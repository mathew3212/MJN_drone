'use client';

/**
 * Alert Engine - Intelligent Real-Time Alert Generation
 * 
 * This engine monitors the Drone State and system conditions,
 * generating alerts based on intelligent rules tied to LIVE system data.
 * 
 * Alerts are NOT pre-generated - they are triggered by actual conditions.
 * Every alert references real telemetry values.
 */

import { DroneEntity } from '@/types/droneEntity';
import { useEventStore, EventSeverity, EventSource } from '@/store/eventStore';

export interface AlertRule {
  id: string;
  condition: (drone: DroneEntity, previousDrone: DroneEntity | null) => boolean;
  enabled: boolean;
  throttleMs: number; // Don't trigger the same alert more than once per this duration
  lastTriggered?: number;
}

export class AlertEngine {
  private rules: Map<string, AlertRule> = new Map();
  private triggeredAlerts: Map<string, number> = new Map(); // alertId -> last trigger time
  private previousDrone: DroneEntity | null = null;

  constructor() {
    this.initializeRules();
  }

  private initializeRules() {
    // Battery alerts
    this.addRule('battery-critical', {
      condition: (drone) => drone.battery.percentage < 15 && drone.battery.percentage > 0,
      message: (drone) => `CRITICAL BATTERY: ${drone.battery.percentage.toFixed(0)}% - RETURN HOME IMMEDIATELY`,
      severity: 'EMERGENCY' as EventSeverity,
      source: 'BATTERY' as EventSource,
      throttle: 5000, // 5 seconds
    });

    this.addRule('battery-low', {
      condition: (drone) => drone.battery.percentage < 30 && drone.battery.percentage >= 15,
      message: (drone) => `LOW BATTERY: ${drone.battery.percentage.toFixed(0)}% - Recommend Return Home`,
      severity: 'WARNING' as EventSeverity,
      source: 'BATTERY' as EventSource,
      throttle: 10000,
    });

    this.addRule('battery-temperature-high', {
      condition: (drone) => drone.battery.temperature > 60,
      message: (drone) => `HIGH BATTERY TEMPERATURE: ${drone.battery.temperature.toFixed(1)}°C`,
      severity: 'WARNING' as EventSeverity,
      source: 'BATTERY' as EventSource,
      throttle: 10000,
    });

    // Signal strength alerts
    this.addRule('signal-lost', {
      condition: (drone) => drone.signal.strength < 20,
      message: (drone) => `SIGNAL LOST: ${drone.signal.strength}% - Communication degraded`,
      severity: 'CRITICAL' as EventSeverity,
      source: 'COMMUNICATION' as EventSource,
      throttle: 5000,
    });

    this.addRule('signal-weak', {
      condition: (drone) => drone.signal.strength < 40 && drone.signal.strength >= 20,
      message: (drone) => `WEAK SIGNAL: ${drone.signal.strength}% - Check antenna orientation`,
      severity: 'WARNING' as EventSeverity,
      source: 'COMMUNICATION' as EventSource,
      throttle: 15000,
    });

    // GPS alerts
    this.addRule('gps-lost', {
      condition: (drone) => drone.gps.satellites < 6,
      message: (drone) => `GPS QUALITY DEGRADED: ${drone.gps.satellites} satellites - RTK integrity reduced`,
      severity: 'WARNING' as EventSeverity,
      source: 'SENSOR' as EventSource,
      throttle: 10000,
    });

    this.addRule('high-hdop', {
      condition: (drone) => drone.gps.hdop > 5,
      message: (drone) => `GPS ACCURACY LOW: HDOP ${drone.gps.hdop.toFixed(2)} - Localization confidence reduced`,
      severity: 'WARNING' as EventSeverity,
      source: 'SENSOR' as EventSource,
      throttle: 15000,
    });

    // Mission alerts
    this.addRule('mission-progressing', {
      condition: (drone, prev) => {
        // Trigger when waypoint changes
        if (!prev) return false;
        return drone.currentWaypointIndex > prev.currentWaypointIndex;
      },
      message: (drone) => `WAYPOINT REACHED: ${drone.waypoints[drone.currentWaypointIndex - 1]?.label || 'WP'} → Next: ${drone.waypoints[drone.currentWaypointIndex]?.label || 'Landing'}`,
      severity: 'INFO' as EventSeverity,
      source: 'MISSION' as EventSource,
      throttle: 1000,
    });

    this.addRule('mission-completed', {
      condition: (drone) => drone.missionState === 'COMPLETE',
      message: () => `MISSION COMPLETE - All waypoints visited`,
      severity: 'INFO' as EventSeverity,
      source: 'MISSION' as EventSource,
      throttle: 1000,
    });

    // Navigation alerts
    this.addRule('planner-changed', {
      condition: (drone, prev) => {
        if (!prev) return false;
        return drone.planner.type !== prev.planner.type;
      },
      message: (drone) => `PLANNER SWITCHED: ${drone.planner.type} (${(drone.planner.confidence * 100).toFixed(0)}% confidence)`,
      severity: 'INFO' as EventSeverity,
      source: 'NAVIGATION' as EventSource,
      throttle: 1000,
    });

    this.addRule('low-prediction-confidence', {
      condition: (drone) => drone.planner.predictionConfidence < 0.7,
      message: (drone) => `LOW PREDICTION CONFIDENCE: ${(drone.planner.predictionConfidence * 100).toFixed(0)}% - Path uncertainty high`,
      severity: 'WARNING' as EventSeverity,
      source: 'PREDICTION' as EventSource,
      throttle: 15000,
    });

    // Weather alerts
    this.addRule('high-wind', {
      condition: (drone) => drone.overlays.weather?.windSpeed > 12,
      message: (drone) => `HIGH WIND: ${drone.overlays.weather?.windSpeed.toFixed(1)}m/s from ${drone.overlays.weather?.windDirection.toFixed(0)}° - Operation challenging`,
      severity: 'WARNING' as EventSeverity,
      source: 'WEATHER' as EventSource,
      throttle: 20000,
    });

    // Flight status alerts
    this.addRule('return-home-triggered', {
      condition: (drone, prev) => {
        if (!prev) return false;
        return drone.missionState === 'RETURN' && prev.missionState !== 'RETURN';
      },
      message: () => `RETURN HOME TRIGGERED - Drone heading to home position`,
      severity: 'WARNING' as EventSeverity,
      source: 'MISSION' as EventSource,
      throttle: 1000,
    });

    this.addRule('emergency-landing', {
      condition: (drone) => drone.status === 'EMERGENCY',
      message: () => `EMERGENCY LANDING - Executing emergency descent`,
      severity: 'EMERGENCY' as EventSeverity,
      source: 'SAFETY' as EventSource,
      throttle: 5000,
    });

    this.addRule('altitude-extreme', {
      condition: (drone) => drone.altitude > 500,
      message: (drone) => `HIGH ALTITUDE: ${drone.altitude.toFixed(0)}m - Ensure sufficient battery reserve`,
      severity: 'WARNING' as EventSeverity,
      source: 'SAFETY' as EventSource,
      throttle: 20000,
    });

    // Obstacle alerts
    this.addRule('collision-predicted', {
      condition: (drone) => drone.overlays.collisionPredictions && drone.overlays.collisionPredictions.length > 0,
      message: (drone) => `COLLISION PREDICTED - ${drone.overlays.collisionPredictions?.length || 0} obstacles in predicted path`,
      severity: 'CRITICAL' as EventSeverity,
      source: 'SAFETY' as EventSource,
      throttle: 5000,
    });

    this.addRule('obstacles-detected', {
      condition: (drone) => drone.overlays.obstacles && drone.overlays.obstacles.length > 5,
      message: (drone) => `MULTIPLE OBSTACLES DETECTED: ${drone.overlays.obstacles?.length || 0} objects - Planner active`,
      severity: 'WARNING' as EventSeverity,
      source: 'SENSOR' as EventSource,
      throttle: 15000,
    });

    // No-fly zone alerts
    this.addRule('entering-no-fly-zone', {
      condition: (drone) => drone.overlays.noFlyZones && drone.overlays.noFlyZones.length > 0,
      message: () => `ENTERING NO-FLY ZONE - Automatic avoidance engaged`,
      severity: 'CRITICAL' as EventSeverity,
      source: 'SAFETY' as EventSource,
      throttle: 5000,
    });

    this.addRule('entering-restricted-airspace', {
      condition: (drone) => drone.overlays.restrictedAirspace && drone.overlays.restrictedAirspace.length > 0,
      message: () => `APPROACHING RESTRICTED AIRSPACE - Stay within geofence`,
      severity: 'WARNING' as EventSeverity,
      source: 'SAFETY' as EventSource,
      throttle: 10000,
    });
  }

  private addRule(id: string, config: {
    condition: (drone: DroneEntity, prev: DroneEntity | null) => boolean;
    message: (drone: DroneEntity) => string;
    severity: EventSeverity;
    source: EventSource;
    throttle: number;
  }) {
    this.rules.set(id, {
      id,
      condition: config.condition,
      enabled: true,
      throttleMs: config.throttle,
      // Store message generation for later
      // @ts-ignore - storing function for later use
      messageGen: config.message,
      // @ts-ignore
      severity: config.severity,
      // @ts-ignore
      source: config.source,
    });
  }

  /**
   * Evaluate all rules and generate alerts for conditions that are true.
   * Called every time drone state updates.
   */
  public evaluate(drone: DroneEntity, previousDrone: DroneEntity | null = null): void {
    const eventStore = useEventStore.getState();
    const now = Date.now();

    for (const [ruleId, rule] of this.rules) {
      if (!rule.enabled) continue;

      // Check throttle
      const lastTrigger = this.triggeredAlerts.get(ruleId) || 0;
      if (now - lastTrigger < rule.throttleMs) {
        continue;
      }

      // Evaluate condition
      try {
        const shouldTrigger = rule.condition(drone, previousDrone ?? this.previousDrone);
        
        if (shouldTrigger) {
          this.triggeredAlerts.set(ruleId, now);
          
          // Get message and other properties
          const messageGen = (rule as any).messageGen;
          const severity = (rule as any).severity;
          const source = (rule as any).source;
          
          if (messageGen && severity && source) {
            const message = messageGen(drone);
            
            eventStore.addEvent({
              severity,
              source,
              title: message.split(':')[0].trim(),
              description: message,
              suggestedAction: this.getSuggestedAction(ruleId, drone),
              data: {
                ruleId,
                droneState: drone.missionState,
                battery: drone.battery.percentage,
                signal: drone.signal.strength,
              },
            });
          }
        }
      } catch (err) {
        console.error(`Error evaluating rule ${ruleId}:`, err);
      }
    }

    // Update previous drone for next evaluation
    this.previousDrone = drone;
  }

  private getSuggestedAction(ruleId: string, drone: DroneEntity): string {
    const suggestions: Record<string, string> = {
      'battery-critical': 'Execute immediate RTL (Return To Launch)',
      'battery-low': 'Plan return within 3 minutes, RTL if battery < 10%',
      'battery-temperature-high': 'Reduce throttle, consider landing to cool battery',
      'signal-lost': 'Move closer to transmitter or check antenna',
      'signal-weak': 'Improve line-of-sight to transmitter',
      'gps-lost': 'Move to open sky, wait for RTK lock',
      'high-hdop': 'Increase altitude or relocate for better satellite view',
      'collision-predicted': 'Update path or abort mission',
      'entering-no-fly-zone': 'RTL immediately',
      'entering-restricted-airspace': 'Return within geofence boundary',
      'high-wind': 'Land or return to launch',
      'emergency-landing': 'Prepare for landing, clear landing zone',
    };
    
    return suggestions[ruleId] || 'Monitor situation';
  }

  public disableRule(ruleId: string): void {
    const rule = this.rules.get(ruleId);
    if (rule) {
      rule.enabled = false;
    }
  }

  public enableRule(ruleId: string): void {
    const rule = this.rules.get(ruleId);
    if (rule) {
      rule.enabled = true;
    }
  }

  public resetThrottle(ruleId: string): void {
    this.triggeredAlerts.delete(ruleId);
  }

  public getRuleIds(): string[] {
    return Array.from(this.rules.keys());
  }
}

// Singleton instance
export const alertEngine = new AlertEngine();
