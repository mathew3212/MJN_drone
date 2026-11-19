'use client';

import { create } from 'zustand';
import { FollowMode } from './MapFollowController';
import { DroneEntity } from '@/types/droneEntity';

export interface MapStoreState {
  showDebug: boolean;
  showGeofences: boolean;
  showNoFlyZones: boolean;
  showObstacles: boolean;
  showRiskZones: boolean;
  showLabels: boolean;
  showScale: boolean;
  showCompass: boolean;
  followMode: FollowMode;
  offlineMode: boolean;
  mapReady: boolean;
  autoZoom: boolean;
  autoCenter: boolean;
  debug: {
    fps: number;
    tileErrors: number;
    resizeCount: number;
    mapLoaded: boolean;
    provider: string;
    providerIndex: number;
    webglVersion: string;
    gpu: string;
    lastError: string | null;
    updateRate: number;
    latency: number;
    centerLat: number;
    centerLng: number;
    zoom: number;
    bearing: number;
    pitch: number;
  };
  setShowDebug: (v: boolean) => void;
  setShowGeofences: (v: boolean) => void;
  setShowNoFlyZones: (v: boolean) => void;
  setShowObstacles: (v: boolean) => void;
  setShowRiskZones: (v: boolean) => void;
  setShowLabels: (v: boolean) => void;
  setShowScale: (v: boolean) => void;
  setShowCompass: (v: boolean) => void;
  setFollowMode: (m: FollowMode) => void;
  setOfflineMode: (v: boolean) => void;
  setMapReady: (v: boolean) => void;
  setAutoZoom: (v: boolean) => void;
  setAutoCenter: (v: boolean) => void;
  setDebug: (p: Partial<MapStoreState['debug']>) => void;
  incrementTileErrors: () => void;
  updateFromDroneEntity: (drone: DroneEntity) => void;
}

export const useMapStore = create<MapStoreState>((set) => ({
  showDebug: false,
  showGeofences: true,
  showNoFlyZones: true,
  showObstacles: true,
  showRiskZones: true,
  showLabels: true,
  showScale: true,
  showCompass: true,
  followMode: 'follow',
  offlineMode: false,
  mapReady: false,
  autoZoom: false,
  autoCenter: false,
  debug: {
    fps: 0,
    tileErrors: 0,
    resizeCount: 0,
    mapLoaded: false,
    provider: '',
    providerIndex: 0,
    webglVersion: 'leaflet',
    gpu: 'CPU',
    lastError: null,
    updateRate: 0,
    latency: 0,
    centerLat: 12.9716,
    centerLng: 77.5946,
    zoom: 15,
    bearing: 0,
    pitch: 0,
  },
  setShowDebug: (v) => set({ showDebug: v }),
  setShowGeofences: (v) => set({ showGeofences: v }),
  setShowNoFlyZones: (v) => set({ showNoFlyZones: v }),
  setShowObstacles: (v) => set({ showObstacles: v }),
  setShowRiskZones: (v) => set({ showRiskZones: v }),
  setShowLabels: (v) => set({ showLabels: v }),
  setShowScale: (v) => set({ showScale: v }),
  setShowCompass: (v) => set({ showCompass: v }),
  setFollowMode: (m) => set({ followMode: m }),
  setOfflineMode: (v) => set({ offlineMode: v }),
  setMapReady: (v) => set({ mapReady: v }),
  setAutoZoom: (v: boolean) => set({ autoZoom: v }),
  setAutoCenter: (v: boolean) => set({ autoCenter: v }),
  setDebug: (p) => set((s) => ({ debug: { ...s.debug, ...p } })),
  incrementTileErrors: () => set((s) => ({ debug: { ...s.debug, tileErrors: s.debug.tileErrors + 1 } })),
  updateFromDroneEntity: () => {},
}));
