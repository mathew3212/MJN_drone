'use client';

// =====================================================================================
// MJN Drone OS - Weather Panel
// Reads weather data from droneEntityStore (single source of truth)
// =====================================================================================

import { useDroneEntityStore } from '@/store/droneEntityStore';

function WindDirectionArrow({ degrees }: { degrees: number }) {
  // Meteorological convention: 0° = North, 90° = East, 180° = South, 270° = West
  // Arrow points INTO the wind (where it's coming from)
  return (
    <span
      className="inline-block text-sm"
      style={{ transform: `rotate(${degrees}deg)`, display: 'inline-block' }}
    >
      ↑
    </span>
  );
}

function getWindDirectionLabel(degrees: number): string {
  const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const index = Math.round(degrees / 22.5) % 16;
  return directions[index];
}

function getWarningColor(severity: string): string {
  const s = severity.toUpperCase();
  if (s.includes('EXTREME') || s.includes('SEVERE')) return '#FF4D5A';
  if (s.includes('HIGH') || s.includes('WARNING')) return '#FFC857';
  if (s.includes('MODERATE') || s.includes('ADVISORY')) return '#FF9F43';
  return '#00D4FF';
}

export default function WeatherPanel() {
  const weather = useDroneEntityStore((s) => s.drone.weather);
  const windDirLabel = getWindDirectionLabel(weather.windDirection);

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-1.5">
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Wind Speed</div>
          <div className="text-sm font-mono text-cyan-300">{weather.windSpeed.toFixed(1)} m/s</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Wind Direction</div>
          <div className="text-sm font-mono text-cyan-300 flex items-center gap-1">
            <WindDirectionArrow degrees={weather.windDirection} />
            <span>{weather.windDirection.toFixed(0)}° {windDirLabel}</span>
          </div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Gusts</div>
          <div className="text-sm font-mono text-cyan-300">{weather.gusts.toFixed(1)} m/s</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Visibility</div>
          <div className="text-sm font-mono text-cyan-300">{weather.visibility.toFixed(1)} km</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Humidity</div>
          <div className="text-sm font-mono text-cyan-300">{weather.humidity.toFixed(0)}%</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Pressure</div>
          <div className="text-sm font-mono text-cyan-300">{weather.pressure.toFixed(0)} hPa</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Temperature</div>
          <div className="text-sm font-mono text-cyan-300">{weather.temperature.toFixed(1)}°C</div>
        </div>
        <div className="bg-black/30 rounded px-2 py-1.5">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider">Rain Level</div>
          <div className="text-sm font-mono text-cyan-300">{weather.rain.toFixed(1)} mm/h</div>
        </div>
      </div>

      {weather.warnings.length > 0 && (
        <div className="space-y-1">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider px-1">Weather Warnings</div>
          {weather.warnings.map((warning, idx) => (
            <div
              key={idx}
              className="bg-black/30 rounded px-2 py-1.5 flex items-center gap-1.5"
            >
              <span
                className="w-1.5 h-1.5 rounded-full shrink-0"
                style={{ backgroundColor: getWarningColor(warning), boxShadow: `0 0 4px ${getWarningColor(warning)}` }}
              />
              <span
                className="text-[10px] font-mono font-bold"
                style={{ color: getWarningColor(warning) }}
              >
                {warning}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
