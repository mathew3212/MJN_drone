'use client';

// =============================================================================
// MJN Drone OS - Marker Info Panel
// Displays detailed information about a selected map marker.
// Opens when clicking Home, Destination, Waypoint, or Drone markers.
// =============================================================================

import { useEffect, useState } from 'react';
import { X, Navigation, Home, Target, MapPin } from 'lucide-react';
import { useDroneEntityStore } from '@/store/droneEntityStore';

export type MarkerType = 'home' | 'destination' | 'drone' | 'waypoint' | 'emergency';

export interface MarkerInfo {
  type: MarkerType;
  name: string;
  latitude: number;
  longitude: number;
  altitude: number;
  label?: string;
}

interface MarkerInfoPanelProps {
  marker: MarkerInfo | null;
  onClose: () => void;
}

function haversine(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 6371000 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

const ICONS: Record<MarkerType, { icon: string; color: string }> = {
  home: { icon: '🏠', color: '#22C55E' },
  destination: { icon: '🎯', color: '#EF4444' },
  drone: { icon: '🛸', color: '#00D4FF' },
  waypoint: { icon: '📍', color: '#06B6D4' },
  emergency: { icon: '⚠️', color: '#FF6B35' },
};

interface ResolvedAddress {
  displayName: string;
  road?: string;
  houseNumber?: string;
  city?: string;
}

async function reverseGeocode(lat: number, lng: number): Promise<ResolvedAddress> {
  try {
    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&zoom=18`, {
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout?.(3000) as any,
    });
    if (!res.ok) throw new Error('Geocode failed');
    const data = (await res.json()) as any;
    const a: ResolvedAddress = {
      displayName: data.display_name || `${lat.toFixed(5)}, ${lng.toFixed(5)}`,
      road: data.address?.road,
      houseNumber: data.address?.house_number,
      city: data.address?.city || data.address?.town || data.address?.village || 'Bangalore',
    };
    return a;
  } catch {
    return {
      displayName: `${lat.toFixed(5)}, ${lng.toFixed(5)} · Bangalore, Karnataka, India`,
      road: undefined,
      houseNumber: undefined,
      city: 'Bangalore',
    };
  }
}

export default function MarkerInfoPanel({ marker, onClose }: MarkerInfoPanelProps) {
  const drone = useDroneEntityStore((s) => s.drone);
  const [address, setAddress] = useState<ResolvedAddress | null>(null);
  const [loadingAddress, setLoadingAddress] = useState(false);

  useEffect(() => {
    if (!marker) return;
    setLoadingAddress(true);
    reverseGeocode(marker.latitude, marker.longitude)
      .then((addr) => {
        setAddress(addr);
        setLoadingAddress(false);
      })
      .catch(() => setLoadingAddress(false));
  }, [marker?.latitude, marker?.longitude, marker?.type]);

  if (!marker) return null;

  const icon = ICONS[marker.type];
  const distToDrone = haversine(drone.latitude, drone.longitude, marker.latitude, marker.longitude);
  const bearing = ((Math.atan2(
    marker.longitude - drone.longitude,
    marker.latitude - drone.latitude
  ) * 180) / Math.PI + 360) % 360;

  return (
    <div className="absolute top-2 right-2 z-20 w-72 bg-[rgba(8,8,16,0.95)] backdrop-blur-xl rounded-xl border border-[rgba(26,26,46,0.6)] shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2 flex items-center justify-between border-b border-[rgba(26,26,46,0.6)]"
        style={{ backgroundColor: `${icon.color}10` }}>
        <div className="flex items-center gap-2">
          <span className="text-lg">{icon.icon}</span>
          <div>
            <div className="text-xs font-mono font-bold uppercase tracking-wider" style={{ color: icon.color }}>
              {marker.type.toUpperCase()}
            </div>
            <div className="text-sm font-mono text-white">{marker.name}</div>
          </div>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
          <X size={16} />
        </button>
      </div>

      {/* Address */}
      <div className="px-3 py-2 border-b border-[rgba(26,26,46,0.4)]">
        <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-1">Address</div>
        {loadingAddress ? (
          <div className="text-xs font-mono text-gray-400 animate-pulse">Resolving address...</div>
        ) : (
          <div className="text-xs font-mono text-cyan-300">{address?.displayName || `${marker.latitude.toFixed(5)}, ${marker.longitude.toFixed(5)}`}</div>
        )}
        {address?.road && <div className="text-[10px] text-gray-500">{address.road}{address.houseNumber ? `, ${address.houseNumber}` : ''}</div>}
      </div>

      {/* Coordinates */}
      <div className="px-3 py-2 border-b border-[rgba(26,26,46,0.4)]">
        <div className="grid grid-cols-2 gap-1">
          <div>
            <div className="text-[9px] text-gray-500 uppercase">Latitude</div>
            <div className="text-xs font-mono text-cyan-300">{marker.latitude.toFixed(6)}°</div>
          </div>
          <div>
            <div className="text-[9px] text-gray-500 uppercase">Longitude</div>
            <div className="text-xs font-mono text-cyan-300">{marker.longitude.toFixed(6)}°</div>
          </div>
          <div>
            <div className="text-[9px] text-gray-500 uppercase">Altitude</div>
            <div className="text-xs font-mono text-cyan-300">{marker.altitude.toFixed(0)} m</div>
          </div>
          <div>
            <div className="text-[9px] text-gray-500 uppercase">Elevation</div>
            <div className="text-xs font-mono text-cyan-300">{marker.altitude.toFixed(0)} m MSL</div>
          </div>
        </div>
      </div>

      {/* Distance & Bearing */}
      <div className="px-3 py-2 border-b border-[rgba(26,26,46,0.4)]">
        <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-1.5">From Drone</div>
        <div className="grid grid-cols-2 gap-1">
          <div>
            <div className="text-[9px] text-gray-600">Distance</div>
            <div className="text-xs font-mono text-cyan-300">{distToDrone.toFixed(0)} m</div>
          </div>
          <div>
            <div className="text-[9px] text-gray-600">Bearing</div>
            <div className="text-xs font-mono text-cyan-300">{bearing.toFixed(0)}°</div>
          </div>
        </div>
      </div>

      {/* Mission info */}
      <div className="px-3 py-2">
        <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-1.5">Mission</div>
        <div className="grid grid-cols-2 gap-1">
          <div>
            <div className="text-[9px] text-gray-600">Mission ID</div>
            <div className="text-xs font-mono text-cyan-300">{drone.missionId}</div>
          </div>
          <div>
            <div className="text-[9px] text-gray-600">Status</div>
            <div className="text-xs font-mono" style={{ color: drone.health === 'OK' ? '#22C55E' : '#FFC857' }}>{drone.missionState}</div>
          </div>
          <div>
            <div className="text-[9px] text-gray-600">Wind</div>
            <div className="text-xs font-mono text-cyan-300">{drone.weather.windSpeed.toFixed(0)} m/s</div>
          </div>
          <div>
            <div className="text-[9px] text-gray-600">Locality</div>
            <div className="text-xs font-mono text-cyan-300">{address?.city || 'Bangalore'}</div>
          </div>
        </div>
      </div>
    </div>
  );
}