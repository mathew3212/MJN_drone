'use client';

// =============================================================================
// MJN Drone OS - GPS Panel
// Reads GPS data from droneEntityStore (single source of truth)
// =============================================================================

import { useDroneEntityStore } from '@/store/droneEntityStore';

export default function GPSPanel() {
  const gps = useDroneEntityStore((s) => s.drone.gps);
  const lat = useDroneEntityStore((s) => s.drone.latitude);
  const lng = useDroneEntityStore((s) => s.drone.longitude);
  const alt = useDroneEntityStore((s) => s.drone.altitude);

  const fixColors: Record<string, string> = {
    'NO_FIX': '#FF4D5A',
    '2D': '#FFC857',
    '3D': '#06B6D4',
    'DGPS': '#00FF88',
    'RTK_FLOAT': '#00FF88',
    'RTK_FIXED': '#00FF88',
  };

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-1.5">
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Latitude</div>
          <div className="text-sm font-mono text-cyan-300">{lat.toFixed(6)}°</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Longitude</div>
          <div className="text-sm font-mono text-cyan-300">{lng.toFixed(6)}°</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Altitude</div>
          <div className="text-sm font-mono text-cyan-300">{alt.toFixed(1)} m</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Satellites</div>
          <div className="text-sm font-mono text-cyan-300">{gps.satellites}</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">HDOP</div>
          <div className="text-sm font-mono text-cyan-300">{gps.hdop.toFixed(2)}</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">VDOP</div>
          <div className="text-sm font-mono text-cyan-300">{gps.vdop.toFixed(2)}</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Fix Type</div>
          <div className="text-sm font-mono" style={{ color: fixColors[gps.fixType] || '#FFC857' }}>
            {gps.fixType}
          </div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Accuracy</div>
          <div className="text-sm font-mono text-cyan-300">{gps.accuracy.toFixed(2)} m</div>
        </div>
      </div>
    </div>
  );
}