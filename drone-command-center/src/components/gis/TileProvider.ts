'use client';

// =============================================================================
// MJN Drone OS - Tile Provider with Automatic Fallback
// Priority chain: MapLibre+OSM → PMTiles Offline → Local → OpenTopoMap → Esri → Carto
// =============================================================================

// MapLibre GL style object type
interface MapLibreStyle {
  version: number;
  name: string;
  sources: Record<string, {
    type: string;
    tiles?: string[];
    tileSize?: number;
    attribution?: string;
    maxzoom?: number;
    minzoom?: number;
    url?: string;
  }>;
  layers: Array<{
    id: string;
    type: string;
    source?: string;
    minzoom?: number;
    maxzoom?: number;
    paint?: Record<string, string | number | boolean>;
  }>;
}

// import { offlineCache } from './OfflineCache';

export interface TileSource {
  id: string;
  name: string;
  type: 'raster' | 'vector' | 'pmtiles';
  url: string;
  attribution: string;
  maxZoom: number;
  minZoom: number;
  tileSize: number;
}

// Provider priority order for automatic fallback
// All use proper raster tile URLs for Leaflet compatibility
export const TILE_PROVIDERS: TileSource[] = [
  {
    id: 'osm',
    name: 'OpenStreetMap',
    type: 'raster',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
    maxZoom: 19,
    minZoom: 1,
    tileSize: 256,
  },
  {
    id: 'opentopomap',
    name: 'OpenTopoMap',
    type: 'raster',
    url: 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://opentopomap.org">OpenTopoMap</a> contributors',
    maxZoom: 17,
    minZoom: 1,
    tileSize: 256,
  },
  {
    id: 'esri-satellite',
    name: 'Esri Satellite',
    type: 'raster',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri, Maxar, Earthstar Geographics',
    maxZoom: 19,
    minZoom: 1,
    tileSize: 256,
  },
  {
    id: 'carto-dark',
    name: 'Carto Dark',
    type: 'raster',
    url: 'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://carto.com">CARTO</a>',
    maxZoom: 19,
    minZoom: 1,
    tileSize: 256,
  },
  {
    id: 'carto-light',
    name: 'Carto Light',
    type: 'raster',
    url: 'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://carto.com">CARTO</a>',
    maxZoom: 19,
    minZoom: 1,
    tileSize: 256,
  },
  {
    id: 'stamen-terrain',
    name: 'Stamen Terrain',
    type: 'raster',
    url: 'https://tile.stamen.com/terrain/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://stamen.com">Stamen Design</a>',
    maxZoom: 18,
    minZoom: 1,
    tileSize: 256,
  },
];

export interface ProviderStatus {
  currentIndex: number;
  currentId: string;
  currentName: string;
  fallbacksTried: string[];
  isOffline: boolean;
  lastError: string | null;
}

export class TileProviderManager {
  private providers = TILE_PROVIDERS;
  private currentIndex = 0;
  private fallbacksTried: string[] = [];
  private isOffline = false;
  private lastError: string | null = null;
  private onFallback: ((status: ProviderStatus) => void) | null = null;
  private onAllFailed: (() => void) | null = null;

  getCurrent(): TileSource {
    return this.providers[this.currentIndex] || this.providers[0];
  }

  getStatus(): ProviderStatus {
    return {
      currentIndex: this.currentIndex,
      currentId: this.getCurrent()?.id || 'none',
      currentName: this.getCurrent()?.name || 'none',
      fallbacksTried: [...this.fallbacksTried],
      isOffline: this.isOffline,
      lastError: this.lastError,
    };
  }

  setOnFallback(cb: (status: ProviderStatus) => void) {
    this.onFallback = cb;
  }

  setOnAllFailed(cb: () => void) {
    this.onAllFailed = cb;
  }

  async tryFallback(error: string): Promise<boolean> {
    this.lastError = error;
    this.fallbacksTried.push(this.providers[this.currentIndex]?.id || 'unknown');
    this.currentIndex++;

    if (this.currentIndex >= this.providers.length) {
      this.isOffline = true;
      this.onAllFailed?.();
      return false;
    }

    const status = this.getStatus();
    this.onFallback?.(status);
    return true;
  }

  reset() {
    this.currentIndex = 0;
    this.fallbacksTried = [];
    this.isOffline = false;
    this.lastError = null;
  }

  // MapLibre GL style object for a raster provider
  getRasterStyle(source: TileSource): MapLibreStyle {
    return {
      version: 8,
      name: source.name,
      sources: {
        'raster-tiles': {
          type: 'raster' as const,
          tiles: [source.url],
          tileSize: source.tileSize,
          attribution: source.attribution,
          maxzoom: source.maxZoom,
          minzoom: source.minZoom,
        },
      },
      layers: [
        {
          id: 'base-map',
          type: 'raster' as const,
          source: 'raster-tiles',
          minzoom: source.minZoom,
          maxzoom: source.maxZoom,
        },
      ],
    };
  }

  // MapLibre GL style for dark tactical night mode
  getTacticalNightStyle(): MapLibreStyle {
    return {
      version: 8,
      name: 'Tactical Night',
      sources: {},
      layers: [
        {
          id: 'background',
          type: 'background' as const,
          paint: { 'background-color': '#0A0A1A' },
        },
        {
          id: 'tactical-grid',
          type: 'line' as const,
          paint: {
            'line-color': 'rgba(26, 26, 46, 0.4)',
            'line-width': 0.5,
          },
        },
      ],
    };
  }
}

// Singleton
export const tileProvider = new TileProviderManager();
