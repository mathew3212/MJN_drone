'use client';

// =============================================================================
// MJN Drone OS - Telemetry Bar
// Displays live telemetry data from droneEntityStore (single source of truth)
// =============================================================================

import { useDroneEntityStore } from '@/store/droneEntityStore';

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export default function TelemetryBar() {
  const telemetry = useDroneEntityStore((s) => s.drone.telemetry);
  const verticalSpeed = useDroneEntityStore((s) => s.drone.verticalSpeed);

  return (
    <div className="flex items-center gap-4 px-3 py-1.5 bg-black/20 rounded-lg overflow-x-auto">
      <div className="flex items-center gap-1.5 min-w-fit">
        <span className="text-[10px] text-gray-500 uppercase">GS</span>
        <span className="text-xs font-mono text-cyan-300">{telemetry.groundSpeed.toFixed(1)} m/s</span>
      </div>
      <div className="w-px h-4 bg-gray-700" />
      <div className="flex items-center gap-1.5 min-w-fit">
        <span className="text-[10px] text-gray-500 uppercase">AS</span>
        <span className="text-xs font-mono text-cyan-300">{telemetry.airSpeed.toFixed(1)} m/s</span>
      </div>
      <div className="w-px h-4 bg-gray-700" />
      <div className="flex items-center gap-1.5 min-w-fit">
        <span className="text-[10px] text-gray-500 uppercase">VS</span>
        <span className="text-xs font-mono" style={{ color: verticalSpeed >= 0 ? '#22C55E' : '#EF4444' }}>
          {telemetry.verticalSpeed.toFixed(1)} m/s
        </span>
      </div>
      <div className="w-px h-4 bg-gray-700" />
      <div className="flex items-center gap-1.5 min-w-fit">
        <span className="text-[10px] text-gray-500 uppercase">Climb</span>
        <span className="text-xs font-mono text-cyan-300">{telemetry.climbRate.toFixed(1)} m/s</span>
      </div>
      <div className="w-px h-4 bg-gray-700" />
      <div className="flex items-center gap-1.5 min-w-fit">
        <span className="text-[10px] text-gray-500 uppercase">D2H</span>
        <span className="text-xs font-mono text-cyan-300">{telemetry.distanceToHome.toFixed(0)} m</span>
      </div>
      <div className="w-px h-4 bg-gray-700" />
      <div className="flex items-center gap-1.5 min-w-fit">
        <span className="text-[10px] text-gray-500 uppercase">D2T</span>
        <span className="text-xs font-mono text-cyan-300">{telemetry.distanceToTarget.toFixed(0)} m</span>
      </div>
      <div className="w-px h-4 bg-gray-700" />
      <div className="flex items-center gap-1.5 min-w-fit">
        <span className="text-[10px] text-gray-500 uppercase">Flight</span>
        <span className="text-xs font-mono text-cyan-300">{formatTime(telemetry.flightTime)}</span>
      </div>
      <div className="w-px h-4 bg-gray-700" />
      <div className="flex items-center gap-1.5 min-w-fit">
        <span className="text-[10px] text-gray-500 uppercase">T2H</span>
        <span className="text-xs font-mono text-cyan-300">{formatTime(telemetry.timeToHome)}</span>
      </div>
    </div>
  );
}
