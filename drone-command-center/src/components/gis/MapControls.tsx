'use client';

import { useState } from 'react';
import { useMapStore } from './MapStore';
import { MapEngine } from './MapEngine';
import { TILE_PROVIDERS } from './TileProvider';

const buttonClass = 'h-9 w-9 grid place-items-center bg-white text-[#3c4043] text-xl shadow-sm transition hover:bg-[#f8f9fa] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#1a73e8]';

export default function MapControls({ engine }: { engine: MapEngine | null }) {
  const [showLayers, setShowLayers] = useState(false);
  const [locationError, setLocationError] = useState('');
  const followMode = useMapStore((state) => state.followMode);
  const providerIndex = useMapStore((state) => state.debug.providerIndex);

  const recenterDrone = () => {
    engine?.jumpToDrone();
    engine?.setFollowMode('follow');
  };

  const useMyLocation = async () => {
    setLocationError('');
    try {
      await engine?.locateUser();
    } catch (error) {
      setLocationError(error instanceof Error ? error.message : 'Could not get your location');
      window.setTimeout(() => setLocationError(''), 4_000);
    }
  };

  return (
    <>
      <div className="absolute right-3 top-3 z-[1001] flex flex-col overflow-hidden rounded-md shadow-md">
        <button type="button" className={`${buttonClass} border-b border-[#dadce0]`} onClick={() => engine?.zoomBy(1)} aria-label="Zoom in" title="Zoom in">+</button>
        <button type="button" className={buttonClass} onClick={() => engine?.zoomBy(-1)} aria-label="Zoom out" title="Zoom out">−</button>
      </div>

      <div className="absolute bottom-8 right-3 z-[1001] flex flex-col gap-2">
        {locationError && <div className="max-w-56 rounded bg-white px-3 py-2 text-xs text-[#5f6368] shadow-md">{locationError}</div>}
        <button type="button" className={`${buttonClass} rounded-md`} onClick={useMyLocation} aria-label="Use my location" title="Use my location">◎</button>
        <button type="button" className={`${buttonClass} rounded-md text-base ${followMode === 'follow' ? 'text-[#1a73e8]' : ''}`} onClick={recenterDrone} aria-label="Recenter on drone" title="Recenter on drone">⌖</button>
        <button type="button" className={`${buttonClass} rounded-md text-sm`} onClick={() => engine?.fitMission()} aria-label="Show full mission" title="Show full mission">▱</button>
        <div className="relative">
          {showLayers && (
            <div className="absolute bottom-11 right-0 w-40 overflow-hidden rounded-md bg-white py-1 text-sm text-[#3c4043] shadow-lg">
              {TILE_PROVIDERS.slice(0, 4).map((provider, index) => (
                <button key={provider.id} type="button" className={`block w-full px-3 py-2 text-left hover:bg-[#f1f3f4] ${index === providerIndex ? 'font-medium text-[#1a73e8]' : ''}`} onClick={() => { engine?.setBaseLayer(provider.id); setShowLayers(false); }}>
                  {provider.name.replace('OpenStreetMap', 'Map').replace('Esri Satellite', 'Satellite')}
                </button>
              ))}
            </div>
          )}
          <button type="button" className={`${buttonClass} rounded-md text-sm`} onClick={() => setShowLayers((open) => !open)} aria-label="Choose map type" title="Map type">▧</button>
        </div>
      </div>
    </>
  );
}
