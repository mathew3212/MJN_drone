'use client';

// =============================================================================
// MJN Drone OS - Map Engine (Leaflet + Canvas Overlay)
// Full integration with DroneEntity, SimulationBridge, and all sub-systems.
// Single RAF loop renders: Drone Marker, Paths, Waypoints, AI Overlays, Telemetry.
// =============================================================================

import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useMapStore } from './MapStore';
import { useDroneEntityStore } from '@/store/droneEntityStore';
import { tileProvider, TileSource, TILE_PROVIDERS } from './TileProvider';
import { LiveDroneMarker } from './LiveDroneMarker';
import { PathManager } from './PathManager';
import { WaypointRenderer } from './WaypointRenderer';
import { MapFollowController, FollowMode } from './MapFollowController';
import { AIOverlayRenderer } from './AIOverlayRenderer';

const BANGALORE_CENTER: [number, number] = [12.9716, 77.5946];

export type MapEngineStatus = 'loading' | 'ready' | 'fallback' | 'error' | 'offline' | 'warning';

export interface MapEngineConfig {
  container: HTMLDivElement;
  onStatusChange?: (status: MapEngineStatus, msg: string) => void;
  onTileError?: (err: string) => void;
}

export class MapEngine {
  private container: HTMLDivElement | null = null;
  private map: L.Map | null = null;
  private tileLayer: L.TileLayer | null = null;
  private pathManager: PathManager | null = null;
  private waypointRenderer: WaypointRenderer | null = null;
  private followController: MapFollowController | null = null;
  private liveDroneMarker: LiveDroneMarker | null = null;
  private aiOverlayRenderer: AIOverlayRenderer | null = null;
  private droneLeafletMarker: L.Marker | null = null;
  private canvasEl: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private renderId = 0;
  private status: MapEngineStatus = 'loading';
  private providerIndex = 0;
  private resizeObserver: ResizeObserver | null = null;
  private onStatus: ((status: MapEngineStatus, msg: string) => void) | null = null;
  private onTileError: ((err: string) => void) | null = null;
  private animCheckInterval: ReturnType<typeof setInterval> | null = null;
  private mapReady = false;
  private destroyed = false;
  private lastZoom = 15;
  private sizeDirty = true;
  private unsubDroneStore: (() => void) | null = null;
  private lastDroneUpdate = 0;
  private selectedDroneId = 'MJN-01';

  async initialize(config: MapEngineConfig): Promise<boolean> {
    this.container = config.container;
    this.onStatus = config.onStatusChange || null;
    this.onTileError = config.onTileError || null;

    if (!this.container) {
      this.setStatus('error', 'Container is null');
      return false;
    }

    this.setStatus('loading', 'Initializing map engine...');

    await this.waitForDimensions();
    if (!this.container || this.destroyed) return false;

    // Create Leaflet map with smooth animations
    this.map = L.map(this.container, {
      center: BANGALORE_CENTER,
      zoom: 15,
      zoomControl: false,
      attributionControl: false,
      fadeAnimation: true,
      zoomAnimation: true,
      markerZoomAnimation: true,
      preferCanvas: false,
      inertia: true,
      inertiaDeceleration: 3000,
      inertiaMaxSpeed: 1500,
      easeLinearity: 0.25,
      worldCopyJump: true,
    });

    // Add first tile provider
    this.addTileLayer(TILE_PROVIDERS[0]);

    // Create canvas overlay for tactical rendering
    this.canvasEl = L.DomUtil.create('canvas', 'leaflet-tactical-canvas') as HTMLCanvasElement;
    this.canvasEl.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100% !important;pointer-events:none;z-index:10000;';
    this.container.appendChild(this.canvasEl);
    this.ctx = this.canvasEl.getContext('2d');
    this.syncCanvasSize();

    // ── Initialize sub-systems ──
    // Live Drone Marker
    this.liveDroneMarker = new LiveDroneMarker();
    if (this.ctx) this.liveDroneMarker.attach(this.ctx);

    // Path Manager (Leaflet polylines)
    this.pathManager = new PathManager();
    this.pathManager.attach(this.map);

    // Waypoint Renderer (Leaflet markers)
    this.waypointRenderer = new WaypointRenderer();
    this.waypointRenderer.attach(this.map);

    // Map Follow Controller
    this.followController = new MapFollowController();
    this.followController.attach(this.map);

    // AI Overlay Renderer (canvas)
    this.aiOverlayRenderer = new AIOverlayRenderer();
    if (this.ctx) this.aiOverlayRenderer.attach(this.ctx);
    this.aiOverlayRenderer.setMap(this.map);

    // ── Subscribe to DroneEntity Store ──
    this.unsubDroneStore = useDroneEntityStore.subscribe((state) => {
      if (this.destroyed) return;
      this.onDroneEntityUpdate(state.drone);
    });

    // Smooth render on every map move/zoom
    this.map.on('movestart move zoomstart zoom', () => {
      this.scheduleRender();
    });
    this.map.on('moveend zoomend', () => {
      this.syncCanvasSize();
      this.scheduleRender();
    });

    // Resize handling with debounce
    let resizeTimer: ReturnType<typeof setTimeout> | null = null;
    this.resizeObserver = new ResizeObserver(() => {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        this.syncCanvasSize();
        this.scheduleRender();
        this.map?.invalidateSize();
        useMapStore.getState().setDebug({ resizeCount: useMapStore.getState().debug.resizeCount + 1 });
      }, 50);
    });
    this.resizeObserver.observe(this.container);

    // Start smooth render loop
    this.startRenderLoop();

    // Health checks
    this.animCheckInterval = setInterval(() => this.healthCheck(), 5000);

    this.mapReady = true;
    useMapStore.getState().setMapReady(true);
    useMapStore.getState().setDebug({
      mapLoaded: true,
      provider: TILE_PROVIDERS[0].name,
      providerIndex: 0,
      webglVersion: 'leaflet-canvas2d',
      gpu: 'Leaflet',
    });
    this.setStatus('ready', `${TILE_PROVIDERS[0].name} loaded`);

    // Initial jump to drone
    const drone = useDroneEntityStore.getState().drone;
    this.followController?.jumpToDrone(drone);

    return true;
  }

  private addTileLayer(source: TileSource) {
    if (!this.map) return;
    if (this.tileLayer) this.map.removeLayer(this.tileLayer);

    this.tileLayer = L.tileLayer(source.url, {
      maxZoom: source.maxZoom,
      minZoom: source.minZoom,
      tileSize: source.tileSize,
      attribution: source.attribution,
      crossOrigin: 'anonymous',
      keepBuffer: 4,
      updateWhenIdle: true,
      updateWhenZooming: true,
    });

    this.tileLayer.on('tileerror', (err: L.TileErrorEvent) => {
      const errMsg = err?.tile?.src || 'Tile load failed';
      this.onTileError?.(errMsg);
      useMapStore.getState().incrementTileErrors();
    });

    this.tileLayer.addTo(this.map);
  }

  private syncCanvasSize() {
    if (!this.canvasEl || !this.container) return;
    const rect = this.container.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(1, Math.round(rect.width));
    const h = Math.max(1, Math.round(rect.height));
    this.canvasEl.width = w * dpr;
    this.canvasEl.height = h * dpr;
    this.canvasEl.style.width = `${w}px`;
    this.canvasEl.style.height = `${h}px`;
    this.sizeDirty = true;
  }

  private scheduledRender = false;

  private scheduleRender() {
    if (!this.scheduledRender) {
      this.scheduledRender = true;
      requestAnimationFrame(() => {
        this.scheduledRender = false;
        this.renderTactical();
      });
    }
  }

  private startRenderLoop() {
    const loop = () => {
      if (this.destroyed) return;
      this.renderTactical();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  private onDroneEntityUpdate(drone: import('@/types/droneEntity').DroneEntity) {
    if (this.destroyed || !this.map) return;

    const now = Date.now();
    this.lastDroneUpdate = now;

    // Update path polylines (efficient append)
    this.pathManager?.update(drone.path);

    // Update waypoint markers
    this.waypointRenderer?.update(drone.waypoints, drone.currentWaypointIndex);

    // Update follow controller
    this.followController?.update(drone);

    // Update map store debug
    useMapStore.getState().updateFromDroneEntity(drone);
    useMapStore.getState().setDebug({
      updateRate: useDroneEntityStore.getState().updateRate,
      latency: useDroneEntityStore.getState().latency,
    });

    // Canvas will be updated in render loop
    this.scheduleRender();
  }

  private renderTactical() {
    if (this.destroyed || !this.map || !this.ctx) return;

    try {
      const center = this.map.getCenter();
      const zoom = this.map.getZoom();
      const bounds = this.map.getBounds();
      const dpr = window.devicePixelRatio || 1;
      const w = this.canvasEl!.width / dpr;
      const h = this.canvasEl!.height / dpr;

      if (w <= 5 || h <= 5) return;

      // Reset transform to prevent compounding, then apply DPR
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Clear canvas with transparent
      this.ctx.clearRect(0, 0, w, h);

      const mapStore = useMapStore.getState();
      const drone = useDroneEntityStore.getState().drone;

      // ── Render AI Overlays (geofences, no-fly zones, obstacles, etc.) ──
      if (mapStore.showGeofences || mapStore.showNoFlyZones || mapStore.showObstacles || mapStore.showRiskZones) {
        this.aiOverlayRenderer?.render(drone.overlays, drone);
      }

      // ── Render Live Drone Marker ──
      const [dx, dy] = this.latLngToPixel(drone.latitude, drone.longitude);
      const isSelected = drone.id === this.selectedDroneId;
      this.liveDroneMarker?.render(dx, dy, drone, isSelected, 1);

      // ── Home marker ──
      const homeWp = drone.waypoints.find(w => w.type === 'home');
      if (homeWp) {
        const [hx, hy] = this.latLngToPixel(homeWp.latitude, homeWp.longitude);
        this.ctx.save();
        this.ctx.strokeStyle = '#00FF88';
        this.ctx.lineWidth = 1.5;
        this.ctx.beginPath();
        this.ctx.moveTo(hx - 6, hy);
        this.ctx.lineTo(hx + 6, hy);
        this.ctx.moveTo(hx, hy - 6);
        this.ctx.lineTo(hx, hy + 6);
        this.ctx.stroke();
        if (mapStore.showLabels) {
          this.ctx.fillStyle = '#00FF88';
          this.ctx.font = '7px monospace';
          this.ctx.fillText('HOME', hx + 8, hy + 3);
        }
        this.ctx.restore();
      }

      // ── Scale bar ──
      if (mapStore.showScale) {
        const y = h - 15;
        const centerLat = this.map.getCenter().lat;
        const metersPerPixel = 40075016.686 * Math.abs(Math.cos(centerLat * Math.PI / 180)) / Math.pow(2, this.map.getZoom() + 8);
        const scaleWidth = 50;
        const scaleDist = metersPerPixel * scaleWidth;
        this.ctx.save();
        this.ctx.strokeStyle = '#4A5A78';
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.moveTo(10, y);
        this.ctx.lineTo(10 + scaleWidth, y);
        this.ctx.stroke();
        this.ctx.fillStyle = '#4A5A78';
        this.ctx.font = '7px monospace';
        this.ctx.fillText(scaleDist < 1000 ? `~${scaleDist.toFixed(0)}m` : `~${(scaleDist / 1000).toFixed(1)}km`, 15, y - 3);
        this.ctx.restore();
      }

      // ── Compass ──
      if (mapStore.showCompass) {
        this.ctx.save();
        this.ctx.strokeStyle = 'rgba(26, 26, 46, 0.6)';
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.arc(30, 35, 14, 0, Math.PI * 2);
        this.ctx.stroke();
        this.ctx.fillStyle = '#4A5A78';
        this.ctx.font = '6px monospace';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('N', 30, 19);
        this.ctx.fillText('S', 30, 55);
        this.ctx.fillText('E', 48, 37);
        this.ctx.fillText('W', 12, 37);
        this.ctx.restore();
      }

      // Update debug
      useMapStore.getState().setDebug({
        centerLat: center.lat,
        centerLng: center.lng,
        zoom,
        bearing: 0,
        pitch: 0,
      });

      this.sizeDirty = false;
    } catch {
      // Never crash render loop
    }
  }

  private latLngToPixel(lat: number, lng: number): [number, number] {
    if (!this.map) return [0, 0];
    const point = this.map.latLngToContainerPoint([lat, lng]);
    return [point.x, point.y];
  }

  private async waitForDimensions(maxWait = 5000): Promise<void> {
    const start = Date.now();
    while (Date.now() - start < maxWait) {
      if (!this.container || this.destroyed) return;
      const rect = this.container.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) return;
      await new Promise(r => requestAnimationFrame(r));
    }
  }

  private setStatus(status: MapEngineStatus, msg: string) {
    this.status = status;
    this.onStatus?.(status, msg);
    useMapStore.getState().setDebug({ lastError: status === 'error' || status === 'offline' ? msg : null });
  }

  private healthCheck() {
    if (this.destroyed || !this.map) return;
    const store = useMapStore.getState();
    store.setDebug({ fps: 60, tileErrors: 0 });
  }

  async tryFallback(error: string) {
    this.providerIndex++;
    if (this.providerIndex >= TILE_PROVIDERS.length) {
      this.setStatus('offline', 'All tile providers failed - tactical mode');
      useMapStore.getState().setOfflineMode(true);
      return;
    }
    const source = TILE_PROVIDERS[this.providerIndex];
    this.addTileLayer(source);
    useMapStore.getState().setDebug({ provider: source.name, providerIndex: this.providerIndex });
    this.setStatus('fallback', `Falling back to ${source.name}`);
  }

  setView(lat: number, lng: number, zoom: number) {
    if (this.map) this.map.setView([lat, lng], zoom, { animate: true, duration: 0.3 });
  }

  setFollowMode(mode: FollowMode) {
    this.followController?.setMode(mode);
    useMapStore.getState().setFollowMode(mode);
  }

  getFollowMode(): FollowMode {
    return this.followController?.getMode() || 'free';
  }

  jumpToDrone() {
    const drone = useDroneEntityStore.getState().drone;
    this.followController?.jumpToDrone(drone);
  }

  forceRender() {
    this.scheduleRender();
  }

  getMap(): L.Map | null {
    return this.map;
  }

  destroy() {
    this.destroyed = true;
    this.unsubDroneStore?.();
    if (this.animCheckInterval) clearInterval(this.animCheckInterval);
    this.resizeObserver?.disconnect();
    if (this.canvasEl && this.canvasEl.parentElement) {
      this.canvasEl.parentElement.removeChild(this.canvasEl);
    }

    this.pathManager?.destroy();
    this.waypointRenderer?.destroy();
    this.followController?.detach();
    this.liveDroneMarker?.detach();
    this.aiOverlayRenderer?.detach();

    if (this.map) {
      this.map.remove();
      this.map = null;
    }

    this.container = null;
    this.tileLayer = null;
    this.canvasEl = null;
    this.ctx = null;
    this.pathManager = null;
    this.waypointRenderer = null;
    this.followController = null;
    this.liveDroneMarker = null;
    this.aiOverlayRenderer = null;
    useMapStore.getState().setMapReady(false);
  }
}