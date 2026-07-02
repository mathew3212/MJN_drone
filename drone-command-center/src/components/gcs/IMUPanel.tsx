'use client';

// =============================================================================
// MJN Drone OS - IMU Panel
// Reads IMU data from droneEntityStore (single source of truth)
// =============================================================================

import { useDroneEntityStore } from '@/store/droneEntityStore';

function attitudeColor(value: number): string {
  const abs = Math.abs(value);
  if (abs < 5) return '#06B6D4';
  if (abs < 15) return '#FFC857';
  return '#FF4D5A';
}

export default function IMUPanel() {
  const yaw = useDroneEntityStore((s) => s.drone.yaw);
  const pitch = useDroneEntityStore((s) => s.drone.pitch);
  const roll = useDroneEntityStore((s) => s.drone.roll);
  const heading = useDroneEntityStore((s) => s.drone.heading);
  const imu = useDroneEntityStore((s) => s.drone.imu);

  return (
    <div className="space-y-2">
      {/* Attitude */}
      <div className="grid grid-cols-3 gap-1.5">
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Yaw</div>
          <div className="text-sm font-mono" style={{ color: attitudeColor(yaw) }}>
            {yaw.toFixed(1)}°
          </div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Pitch</div>
          <div className="text-sm font-mono" style={{ color: attitudeColor(pitch) }}>
            {pitch.toFixed(1)}°
          </div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Roll</div>
          <div className="text-sm font-mono" style={{ color: attitudeColor(roll) }}>
            {roll.toFixed(1)}°
          </div>
        </div>
      </div>

      {/* Acceleration */}
      <div>
        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Acceleration (m/s²)</div>
        <div className="grid grid-cols-3 gap-1.5">
          <div className="bg-black/30 rounded px-2 py-1">
            <div className="text-[9px] text-gray-600">X</div>
            <div className="text-xs font-mono text-cyan-300">{imu.accelerationX.toFixed(2)}</div>
          </div>
          <div className="bg-black/30 rounded px-2 py-1">
            <div className="text-[9px] text-gray-600">Y</div>
            <div className="text-xs font-mono text-cyan-300">{imu.accelerationY.toFixed(2)}</div>
          </div>
          <div className="bg-black/30 rounded px-2 py-1">
            <div className="text-[9px] text-gray-600">Z</div>
            <div className="text-xs font-mono text-cyan-300">{imu.accelerationZ.toFixed(2)}</div>
          </div>
        </div>
      </div>

      {/* Angular Velocity */}
      <div>
        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Angular Velocity (°/s)</div>
        <div className="grid grid-cols-3 gap-1.5">
          <div className="bg-black/30 rounded px-2 py-1">
            <div className="text-[9px] text-gray-600">X</div>
            <div className="text-xs font-mono text-cyan-300">{(imu.angularVelocityX * 180 / Math.PI).toFixed(1)}</div>
          </div>
          <div className="bg-black/30 rounded px-2 py-1">
            <div className="text-[9px] text-gray-600">Y</div>
            <div className="text-xs font-mono text-cyan-300">{(imu.angularVelocityY * 180 / Math.PI).toFixed(1)}</div>
          </div>
          <div className="bg-black/30 rounded px-2 py-1">
            <div className="text-[9px] text-gray-600">Z</div>
            <div className="text-xs font-mono text-cyan-300">{(imu.angularVelocityZ * 180 / Math.PI).toFixed(1)}</div>
          </div>
        </div>
      </div>

      {/* Compass */}
      <div className="bg-black/30 rounded px-2 py-1.5">
        <div className="text-[10px] text-gray-500 uppercase tracking-wider">Compass Heading</div>
        <div className="text-sm font-mono text-cyan-300">
          {imu.compassHeading.toFixed(1)}° {getCompassLabel(imu.compassHeading)}
        </div>
      </div>
    </div>
  );
}

function getCompassLabel(deg: number): string {
  const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const index = Math.round(deg / 22.5) % 16;
  return directions[index];
}