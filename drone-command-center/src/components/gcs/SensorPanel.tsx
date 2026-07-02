'use client';

// =============================================================================
// MJN Drone OS - Sensor Panel
// Reads sensor status from droneEntityStore (single source of truth)
// =============================================================================

import { useDroneEntityStore } from '@/store/droneEntityStore';

const STATUS_COLORS: Record<string, string> = {
  OK: '#22C55E',
  WARN: '#EAB308',
  FAIL: '#EF4444',
};

const STATUS_BG: Record<string, string> = {
  OK: 'rgba(34,197,94,0.15)',
  WARN: 'rgba(234,179,8,0.15)',
  FAIL: 'rgba(239,68,68,0.15)',
};

interface SensorRowProps {
  label: string;
  status: 'OK' | 'WARN' | 'FAIL';
}

function SensorRow({ label, status }: SensorRowProps) {
  return (
    <div className="flex items-center justify-between px-2 py-1.5 rounded bg-black/20">
      <span className="text-xs text-gray-400 uppercase tracking-wider">{label}</span>
      <span
        className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded"
        style={{
          color: STATUS_COLORS[status],
          backgroundColor: STATUS_BG[status],
        }}
      >
        {status}
      </span>
    </div>
  );
}

export default function SensorPanel() {
  const sensors = useDroneEntityStore((s) => s.drone.sensors);

  return (
    <div className="space-y-2">
      <div className="space-y-1">
        <SensorRow label="LiDAR" status={sensors.lidar} />
        <SensorRow label="Camera" status={sensors.camera} />
        <SensorRow label="Depth Camera" status={sensors.depthCamera} />
        <SensorRow label="Radar" status={sensors.radar} />
        <SensorRow label="Ultrasonic" status={sensors.ultrasonic} />
        <SensorRow label="Optical Flow" status={sensors.opticalFlow} />
      </div>

      <div className="bg-black/30 rounded px-2 py-1.5">
        <div className="text-[10px] text-gray-500 uppercase tracking-wider">Detection Count</div>
        <div className="text-sm font-mono text-cyan-300">{sensors.detectionCount}</div>
      </div>

      <div className="bg-black/30 rounded px-2 py-1.5">
        <div className="text-[10px] text-gray-500 uppercase tracking-wider">Tracking IDs</div>
        <div className="text-xs font-mono text-cyan-300 truncate">
          {sensors.trackingIds.join(', ')}
        </div>
      </div>

      <div className="bg-black/30 rounded px-2 py-1.5">
        <div className="text-[10px] text-gray-500 uppercase tracking-wider">Sensor Confidence</div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${(sensors.sensorConfidence * 100).toFixed(0)}%`,
                backgroundColor: sensors.sensorConfidence > 0.8 ? '#22C55E' : sensors.sensorConfidence > 0.5 ? '#EAB308' : '#EF4444',
              }}
            />
          </div>
          <span className="text-xs font-mono text-cyan-300">{(sensors.sensorConfidence * 100).toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
}