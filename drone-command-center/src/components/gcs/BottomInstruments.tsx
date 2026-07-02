'use client';

// =============================================================================
// MJN Drone OS - Bottom Instruments Panel
// Professional instrumentation bar with attitude, compass, speed, altitude.
// =============================================================================

import { useDroneEntityStore } from '@/store/droneEntityStore';
import AttitudeIndicator from './AttitudeIndicator';
import Compass from './Compass';
import TelemetryBar from './TelemetryBar';

export default function BottomInstruments() {
  const drone = useDroneEntityStore((s) => s.drone);
  const velocity = useDroneEntityStore((s) => s.drone.velocity);
  const altitude = useDroneEntityStore((s) => s.drone.altitude);
  const battery = useDroneEntityStore((s) => s.drone.battery);

  return (
    <div className="h-20 bg-[rgba(8,8,16,0.92)] backdrop-blur-xl border-t border-[rgba(26,26,46,0.6)] flex items-center px-3 gap-4">
      {/* Attitude Indicator */}
      <div className="flex-shrink-0">
        <AttitudeIndicator />
      </div>

      {/* Divider */}
      <div className="w-px h-12 bg-[rgba(26,26,46,0.6)]" />

      {/* Compass */}
      <div className="flex-shrink-0">
        <Compass />
      </div>

      {/* Divider */}
      <div className="w-px h-12 bg-[rgba(26,26,46,0.6)]" />

      {/* Altitude */}
      <div className="flex flex-col items-center min-w-[60px]">
        <div className="text-[9px] text-gray-500 uppercase tracking-wider">ALT</div>
        <div className="text-lg font-mono font-bold text-cyan-300 tabular-nums leading-tight">
          {altitude.toFixed(0)}
        </div>
        <div className="text-[9px] text-gray-600">meters</div>
      </div>

      {/* Speed */}
      <div className="flex flex-col items-center min-w-[60px]">
        <div className="text-[9px] text-gray-500 uppercase tracking-wider">SPD</div>
        <div className="text-lg font-mono font-bold text-cyan-300 tabular-nums leading-tight">
          {velocity.toFixed(1)}
        </div>
        <div className="text-[9px] text-gray-600">m/s</div>
      </div>

      <div className="w-px h-12 bg-[rgba(26,26,46,0.6)]" />

      {/* Vertical Speed */}
      <div className="flex flex-col items-center min-w-[60px]">
        <div className="text-[9px] text-gray-500 uppercase tracking-wider">V/S</div>
        <div className="text-lg font-mono font-bold leading-tight" style={{ color: drone.verticalSpeed >= 0 ? '#22C55E' : '#EF4444' }}>
          {drone.telemetry.verticalSpeed.toFixed(1)}
        </div>
        <div className="text-[9px] text-gray-600">m/s</div>
      </div>

      <div className="w-px h-12 bg-[rgba(26,26,46,0.6)]" />

      {/* Signal */}
      <div className="flex flex-col items-center min-w-[50px]">
        <div className="text-[9px] text-gray-500 uppercase tracking-wider">SIG</div>
        <div className="flex items-center gap-1">
          <div className="w-10 h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${drone.signal.strength}%`,
                backgroundColor: drone.signal.strength > 60 ? '#22C55E' : drone.signal.strength > 30 ? '#EAB308' : '#EF4444',
              }}
            />
          </div>
        </div>
        <div className="text-[9px] font-mono text-cyan-300">{drone.signal.strength.toFixed(0)}%</div>
      </div>

      <div className="w-px h-12 bg-[rgba(26,26,46,0.6)]" />

      {/* Battery */}
      <div className="flex flex-col items-center min-w-[80px]">
        <div className="text-[9px] text-gray-500 uppercase tracking-wider">BAT</div>
        <div className="flex items-center gap-2">
          <div className="w-12 h-3 bg-gray-800 rounded-full overflow-hidden border border-gray-700">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${battery.percentage}%`,
                backgroundColor: battery.percentage > 50 ? '#22C55E' : battery.percentage > 20 ? '#EAB308' : '#EF4444',
              }}
            />
          </div>
          <span className="text-sm font-mono font-bold text-cyan-300 tabular-nums">{battery.percentage.toFixed(0)}%</span>
        </div>
        <div className="text-[9px] text-gray-600">{battery.voltage.toFixed(1)}V / {battery.current.toFixed(1)}A</div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Telemetry info strip */}
      <div className="hidden lg:block">
        <TelemetryBar />
      </div>
    </div>
  );
}