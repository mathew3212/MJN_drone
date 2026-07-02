'use client';

// =============================================================================
// MJN Drone OS - Tactical GIS Mission Map (Leaflet Engine)
// Fully integrates: Live Drone Marker, Path Manager, Waypoint Renderer,
// Map Follow Controller, AI Overlays, Mission Playback, Debug Panel.
// =============================================================================

import { useRef, useEffect, useState } from 'react';
import { useMapStore } from './MapStore';
import { MapEngine, MapEngineStatus } from './MapEngine';
import { tileProvider } from './TileProvider';
import MapControls from './MapControls';
import DebugPanel from './DebugPanel';
import MissionPlayback from './MissionPlayback';

export default function GISMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<MapEngine | null>(null);
  const [engineStatus, setEngineStatus] = useState<string>('Initializing...');
  const [engineReady, setEngineReady] = useState(false);
  const [engine, setEngine] = useState<MapEngine | null>(null);
  const showDebug = useMapStore((s) => s.showDebug);
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let running = true;
    const engine = new MapEngine();
    engineRef.current = engine;
    setEngine(engine);

    // Set Leaflet tile error handling
    window.addEventListener('leaflet-tile-error', ((e: CustomEvent) => {
      if (!running) return;
      tileProvider.tryFallback(e.detail || 'Tile error');
    }) as EventListener);

    engine.initialize({
      container,
      onStatusChange: (status: MapEngineStatus, msg: string) => {
        if (!running) return;
        setEngineStatus(msg);
        if (status === 'ready' || status === 'offline') {
          setEngineReady(true);
        }
      },
      onTileError: (err: string) => {
        if (!running) return;
        console.warn('[GIS] Tile error:', err);
        tileProvider.tryFallback(err).then((hasFallback) => {
          if (!hasFallback && running) {
            useMapStore.getState().setOfflineMode(true);
            setEngineReady(true);
            setEngineStatus('Tactical grid active');
          } else if (hasFallback && running) {
            const status = tileProvider.getStatus();
            useMapStore.getState().setDebug({
              provider: status.currentName,
              providerIndex: status.currentIndex,
            });
            setEngineStatus(`Fallback: ${status.currentName}`);
          }
        });
      },
    });

    return () => {
      running = false;
      engine.destroy();
      engineRef.current = null;
    };
  }, []);

  return (
    <div 
      ref={containerRef} 
      className="relative w-full h-full overflow-hidden" 
      style={{ background: '#0A0A1A', minHeight: '200px' }}
    >
      {/* Status Bar */}
      {!engineReady && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[10000] flex flex-col items-center gap-2">
          <div className="w-6 h-6 border-2 border-[#00D4FF] border-t-transparent rounded-full animate-spin" />
          <span className="text-[10px] font-mono text-[#6B7FA0]">{engineStatus}</span>
        </div>
      )}

      {/* Status banner when ready */}
      {engineReady && (
        <div className="absolute top-1 left-1 z-[10001] pointer-events-none">
          <span className="text-[7px] font-mono text-[rgba(74,90,120,0.5)]">
            {engineStatus}
          </span>
        </div>
      )}

      {/* Controls */}
      <MapControls engine={engine} />

      {/* Mission Playback */}
      <MissionPlayback />

      {/* Debug Panel */}
      {showDebug && <DebugPanel />}

      {/* Offline Mode Indicator */}
      {useMapStore.getState().offlineMode && engineReady && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 translate-y-8 z-[10001]">
          <span className="text-[8px] font-mono text-[#FFC857] bg-[rgba(5,5,5,0.8)] px-2 py-1 rounded">
            OFFLINE MODE - TACTICAL GRID
          </span>
        </div>
      )}
    </div>
  );
}
