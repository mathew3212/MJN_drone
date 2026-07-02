'use client';

import { useEffect, useState } from 'react';
import { useDroneEntityStore } from '@/store/droneEntityStore';
import { connectionStatusLabel, formatClock, missionStatusLabel } from '@/store/droneSelectors';

const STATUS_COLORS: Record<string, string> = {
  RUNNING: '#00FF88',
  PAUSED: '#FFC857',
  COMPLETE: '#00D4FF',
  ABORTED: '#FF4D5A',
  STANDBY: '#4A5A78',
};

const CONNECTION_COLORS: Record<string, string> = {
  CONNECTED: '#00FF88',
  DISCONNECTED: '#FF4D5A',
  RECONNECTING: '#FFC857',
};

function UsageBar({ value }: { value: number }) {
  const color = value > 80 ? '#FF4D5A' : value > 60 ? '#FFC857' : '#00D4FF';
  return (
    <div className="w-12 h-1 bg-[rgba(26,26,46,0.6)] rounded-full overflow-hidden">
      <div className="h-full rounded-full transition-all duration-300" style={{ width: `${value}%`, background: color }} />
    </div>
  );
}

export default function HeaderBar() {
  const missionState = useDroneEntityStore((s) => s.drone.missionState);
  const status = useDroneEntityStore((s) => s.drone.status);
  const telemetry = useDroneEntityStore((s) => s.drone.telemetry);
  const gps = useDroneEntityStore((s) => s.drone.gps);
  const weather = useDroneEntityStore((s) => s.drone.weather);
  const system = useDroneEntityStore((s) => s.drone.system);
  const droneCount = 1;
  const simulationConnected = useDroneEntityStore((s) => s.simulationConnected);
  const droneConnected = useDroneEntityStore((s) => s.droneConnected);
  const [clientTime, setClientTime] = useState('');

  useEffect(() => {
    const syncClock = () => setClientTime(new Date().toLocaleTimeString('en-US', { hour12: false }));
    syncClock();
    const timer = setInterval(syncClock, 1000);
    return () => clearInterval(timer);
  }, []);

  const missionStatus = missionStatusLabel(missionState);
  const connectionStatus = connectionStatusLabel({ simulationConnected, droneConnected });
  const statusColor = STATUS_COLORS[missionStatus] || '#4A5A78';
  const connColor = CONNECTION_COLORS[connectionStatus] || '#4A5A78';
  const emergency = status === 'EMERGENCY' || missionState === 'EMERGENCY' || missionState === 'ABORT';

  return (
    <div className="h-10 px-4 flex items-center justify-between border-b border-[rgba(26,26,46,0.6)] select-none" style={{ background: 'rgba(5,5,5,0.9)', backdropFilter: 'blur(16px)' }}>
      <div className="flex items-center gap-4">
        <span className="text-[9px] font-bold tracking-[0.2em] text-[#6B7FA0] font-mono">MJN GCS</span>
        <div className="h-3 w-px bg-[rgba(26,26,46,0.6)]" />
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: statusColor, boxShadow: `0 0 4px ${statusColor}` }} />
          <span className="text-[10px] font-mono font-bold tracking-wider" style={{ color: statusColor }}>{missionStatus}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full animate-pulse" style={{ backgroundColor: connColor }} />
          <span className="text-[9px] font-mono text-[#4A5A78]">{connectionStatus}</span>
        </div>
        <span className="text-[10px] font-mono text-[#9D6CFF] font-bold">{status}</span>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-[10px] font-mono text-[#6B7FA0]">{formatClock(telemetry.flightTime)}</span>
        <span className="text-[9px] font-mono text-[#4A5A78]">{clientTime}</span>
        <div className="h-3 w-px bg-[rgba(26,26,46,0.6)]" />
        <span className="text-[9px] font-mono text-[#00FF88]">GPS {gps.satellites} sat</span>
        <span className="text-[9px] font-mono text-[#06B6D4]">W {weather.windSpeed.toFixed(1)}</span>
        <span className="text-[9px] font-mono text-[#FFC857]">{system.telemetryRate} Hz</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <span className="text-[8px] font-mono text-[#4A5A78]">CPU</span>
          <UsageBar value={system.cpuUsage} />
          <span className="text-[8px] font-mono text-[#4A5A78]">{system.cpuUsage}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[8px] font-mono text-[#4A5A78]">MEM</span>
          <UsageBar value={system.ramUsage} />
          <span className="text-[8px] font-mono text-[#4A5A78]">{system.ramUsage}%</span>
        </div>
        <div className="h-3 w-px bg-[rgba(26,26,46,0.6)]" />
        <span className="text-[9px] font-mono text-[#6B7FA0]">AIR {droneCount}</span>

        {emergency && (
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-[rgba(255,77,90,0.15)] border border-[rgba(255,77,90,0.3)] rounded">
            <span className="w-1.5 h-1.5 rounded-full bg-[#FF4D5A] animate-pulse" style={{ boxShadow: '0 0 6px #FF4D5A' }} />
            <span className="text-[9px] font-mono text-[#FF4D5A] font-bold">EMERGENCY</span>
          </div>
        )}
      </div>
    </div>
  );
}
