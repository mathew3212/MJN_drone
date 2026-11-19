'use client';

// =============================================================================
// MJN Drone OS - GIS Debug Overlay (Enhanced)
// Real-time diagnostics showing every system state including simulation bridge.
// =============================================================================

import { useMapStore } from './MapStore';
import { useDroneEntityStore } from '@/store/droneEntityStore';

export default function DebugPanel() {
  const debug = useMapStore((s) => s.debug);
  const mapReady = useMapStore((s) => s.mapReady);
  const offlineMode = useMapStore((s) => s.offlineMode);
  const entityStore = useDroneEntityStore.getState();
  const drone = entityStore.drone;
  const updateRate = entityStore.updateRate;
  const latency = entityStore.latency;
  const simConnected = entityStore.simulationConnected ?? false;
  const droneConnected = entityStore.droneConnected ?? false;
  const backend = entityStore.currentBackend ?? 'simulation';

  const rows: Array<[string, string]> = [
    // Map status
    ['Map Loaded', debug.mapLoaded ? 'YES' : 'NO'],
    ['Map Ready', mapReady ? 'YES' : 'NO'],
    ['Offline Mode', offlineMode ? 'YES' : 'NO'],
    ['Provider', debug.provider],
    ['Tile Errors', String(debug.tileErrors)],
    ['Zoom', debug.zoom.toFixed(1)],
    ['Center', debug.centerLat.toFixed(4) + ', ' + debug.centerLng.toFixed(4)],

    // Simulation
    ['Sim Connected', String(simConnected)],
    ['Drone Connected', droneConnected ? 'YES' : 'NO'],
    ['Backend', backend],
    ['Update Rate', updateRate + ' Hz'],
    ['Latency', latency + ' ms'],

    // Position
    ['Latitude', drone.latitude.toFixed(5)],
    ['Longitude', drone.longitude.toFixed(5)],
    ['Altitude', drone.altitude.toFixed(1) + ' m'],
    ['Velocity', drone.velocity.toFixed(1) + ' m/s'],

    // Mission
    ['Mission ID', drone.missionId],
    ['Waypoint', String(drone.currentWaypointIndex) + ' / ' + String(drone.waypoints.length - 1)],
    ['Progress', drone.missionProgress.toFixed(1) + '%'],
    ['Status', drone.status],

    // GPS
    ['Satellites', String(drone.gps.satellites)],
    ['HDOP', drone.gps.hdop.toFixed(2)],
    ['Accuracy', drone.gps.accuracy.toFixed(2) + ' m'],

    // Battery
    ['Battery', drone.battery.percentage.toFixed(1) + '%'],
    ['Voltage', drone.battery.voltage.toFixed(1) + ' V'],

    // Signal
    ['Signal', drone.signal.strength.toFixed(0) + '%'],

    // Render
    ['FPS', String(debug.fps)],
    ['GPU', debug.gpu],
  ];

  if (debug.lastError) {
    rows.push(['Last Error', debug.lastError.substring(0, 60)]);
  }

  const getValueColor = (value: string): string => {
    if (value === 'YES' || value.startsWith('CONNECTED') || value === 'OK') return '#00FF88';
    if (value === 'NO' || value.startsWith('DISCONNECTED') || value === 'FAIL') return '#FF4D5A';
    if (value === 'NO FIX') return '#FFC857';
    return '#8A9BB5';
  };

  return (
    <div className="absolute bottom-2 left-2 z-20 bg-[rgba(5,5,5,0.92)] border border-[rgba(26,26,46,0.8)] rounded p-2 font-mono text-[7px] leading-tight pointer-events-auto max-w-[320px] max-h-[400px] overflow-y-auto">
      <div className="text-[#FFC857] font-bold text-[9px] mb-1 uppercase tracking-wider flex items-center justify-between">
        <span>GIS Debug</span>
        <span className="text-[#4A5A78] text-[7px] font-normal">droneEntityStore v1.0</span>
      </div>

      {/* Connection Status Bar */}
      <div className="flex gap-1 mb-1.5">
        <div className={'px-1 py-0.5 rounded text-[6px] font-mono ' + (simConnected ? 'bg-[rgba(0,255,136,0.15)] text-[#00FF88]' : 'bg-[rgba(255,77,90,0.15)] text-[#FF4D5A]')}>
          SIM: {simConnected ? 'ONLINE' : 'OFFLINE'}
        </div>
        <div className={'px-1 py-0.5 rounded text-[6px] font-mono ' + (droneConnected ? 'bg-[rgba(0,255,136,0.15)] text-[#00FF88]' : 'bg-[rgba(255,77,90,0.15)] text-[#FF4D5A]')}>
          DRONE: {droneConnected ? 'ONLINE' : 'OFFLINE'}
        </div>
        <div className="px-1 py-0.5 rounded text-[6px] font-mono bg-[rgba(0,212,255,0.1)] text-[#00D4FF]">
          {backend.toUpperCase()}
        </div>
      </div>

      {rows.map(([label, value]) => {
        const color = getValueColor(value);
        return (
          <div key={label} className="flex justify-between gap-2 py-[1px]">
            <span className="text-[#4A5A78] whitespace-nowrap">{label}:</span>
            <span className="text-right truncate max-w-[180px]" style={{ color }}>{value}</span>
          </div>
        );
      })}
    </div>
  );
}
