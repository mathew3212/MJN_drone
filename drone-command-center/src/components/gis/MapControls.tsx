'use client';

// =============================================================================
// MJN Drone OS - Map Controls (Enhanced)
// Zoom, Follow Modes, Auto Zoom, Heading Up, Provider Status, Debug Toggle
// =============================================================================

import { useMapStore } from './MapStore';
import { useDroneEntityStore } from '@/store/droneEntityStore';
import { MapEngine } from './MapEngine';
import { FollowMode } from './MapFollowController';

export default function MapControls({ engine }: { engine: MapEngine | null }) {
  const mapStore = useMapStore();
  const followMode = useMapStore((s) => s.followMode);
  const autoZoom = useMapStore((s) => s.autoZoom);
  const autoCenter = useMapStore((s) => s.autoCenter);
  const drone = useDroneEntityStore((s) => s.drone);

  const followModes: Array<{ mode: FollowMode; label: string; title: string }> = [
    { mode: 'follow', label: 'F', title: 'Follow Drone' },
    { mode: 'north-up', label: 'N', title: 'North Locked' },
    { mode: 'heading-up', label: 'H', title: 'Heading Up' },
    { mode: 'overview', label: 'M', title: 'Mission Overview' },
    { mode: 'free', label: 'E', title: 'Free Explore' },
  ];

  const handleModeClick = (mode: FollowMode) => {
    if (!engine) return;
    engine.setFollowMode(mode);
    if (mode === 'follow' || mode === 'north-up' || mode === 'heading-up') {
      mapStore.setAutoCenter(true);
    } else if (mode === 'overview') {
      const waypoints = drone.waypoints.map(w => ({ latitude: w.latitude, longitude: w.longitude }));
      // Mission overview handled in follow controller
    } else {
      mapStore.setAutoCenter(false);
    }
  };

  return (
    <div className="absolute top-2 right-2 z-10 flex flex-col gap-1 select-none">
      {/* Follow Mode Buttons */}
      {followModes.map((fm) => (
        <button
          key={fm.mode}
          onClick={() => handleModeClick(fm.mode)}
          className={'w-7 h-7 flex items-center justify-center rounded text-[9px] font-mono transition-all ' + (
            followMode === fm.mode
              ? 'bg-[#00D4FF] text-[#050505]'
              : 'bg-[rgba(26,26,46,0.8)] text-[#6B7FA0] hover:text-[#00D4FF]'
          )}
          title={fm.title}
        >
          {fm.label}
        </button>
      ))}

      {/* Separator */}
      <div className="w-full h-px bg-[rgba(74,90,120,0.3)] my-0.5" />

      {/* Auto Zoom Toggle */}
      <button
        onClick={() => {
          mapStore.setAutoZoom(!autoZoom);
          if (engine) engine.setFollowMode(followMode);
        }}
        className={'w-7 h-5 flex items-center justify-center rounded text-[7px] font-mono transition-all ' + (
          autoZoom ? 'bg-[#00FF88] text-[#050505]' : 'bg-[rgba(26,26,46,0.8)] text-[#6B7FA0] hover:text-[#00FF88]'
        )}
        title="Auto Zoom"
      >
        AZ
      </button>

      {/* Auto Center Toggle */}
      <button
        onClick={() => {
          mapStore.setAutoCenter(!autoCenter);
        }}
        className={'w-7 h-5 flex items-center justify-center rounded text-[7px] font-mono transition-all ' + (
          autoCenter ? 'bg-[#00FF88] text-[#050505]' : 'bg-[rgba(26,26,46,0.8)] text-[#6B7FA0] hover:text-[#00FF88]'
        )}
        title="Auto Center"
      >
        AC
      </button>

      {/* Separator */}
      <div className="w-full h-px bg-[rgba(74,90,120,0.3)] my-0.5" />

      {/* Zoom In */}
      <button
        onClick={() => {
          if (engine) {
            const currentZoom = useMapStore.getState().debug.zoom;
            engine.setView(drone.latitude, drone.longitude, Math.min(19, currentZoom + 1));
          }
        }}
        className="w-7 h-7 flex items-center justify-center rounded bg-[rgba(26,26,46,0.8)] text-[#6B7FA0] hover:text-[#00D4FF] text-xs"
        title="Zoom In"
      >
        +
      </button>

      {/* Zoom Out */}
      <button
        onClick={() => {
          if (engine) {
            const currentZoom = useMapStore.getState().debug.zoom;
            engine.setView(drone.latitude, drone.longitude, Math.max(1, currentZoom - 1));
          }
        }}
        className="w-7 h-7 flex items-center justify-center rounded bg-[rgba(26,26,46,0.8)] text-[#6B7FA0] hover:text-[#00D4FF] text-xs"
        title="Zoom Out"
      >
        -
      </button>

      {/* Compass Reset */}
      <button
        onClick={() => {
          if (engine) engine.jumpToDrone();
        }}
        className="w-7 h-7 flex items-center justify-center rounded bg-[rgba(26,26,46,0.8)] text-[#6B7FA0] hover:text-[#00D4FF] text-[9px] font-mono"
        title="Reset View / Jump to Drone"
      >
        T
      </button>

      {/* Separator */}
      <div className="w-full h-px bg-[rgba(74,90,120,0.3)] my-0.5" />

      {/* Debug Toggle */}
      <button
        onClick={() => mapStore.setShowDebug(!mapStore.showDebug)}
        className={'w-7 h-7 flex items-center justify-center rounded text-[9px] font-mono transition-all ' + (
          mapStore.showDebug ? 'bg-[#FFC857] text-[#050505]' : 'bg-[rgba(26,26,46,0.8)] text-[#6B7FA0] hover:text-[#FFC857]'
        )}
        title="Toggle Debug Panel"
      >
        D
      </button>

      {/* Drone Info */}
      <div className="w-7 flex flex-col items-center text-[6px] font-mono text-[#4A5A78]">
        <span>{drone.velocity.toFixed(0)}m/s</span>
        <span>{drone.battery.percentage.toFixed(0)}%</span>
      </div>

      {/* Provider Status Indicator */}
      <div
        className={'w-7 h-2 rounded text-[5px] font-mono flex items-center justify-center ' + (
          mapStore.mapReady ? 'bg-[#00FF88]' : mapStore.offlineMode ? 'bg-[#FFC857]' : 'bg-[#FF4D5A]'
        )}
        title={mapStore.mapReady ? 'Online' : mapStore.offlineMode ? 'Offline Mode' : 'Error'}
      />
    </div>
  );
}