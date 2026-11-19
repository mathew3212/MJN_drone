'use client';

// =============================================================================
// MJN Drone OS - Map Follow Controller v2
// Google Maps-style camera tracking.
// Drone stays at 35-40% from bottom so operator sees route ahead.
// =============================================================================

import L from 'leaflet';
import { DroneEntity } from '@/types/droneEntity';

export type FollowMode = 'follow' | 'north-up' | 'heading-up' | 'overview' | 'free';

export class MapFollowController {
  private map: L.Map | null = null;
  private mode: FollowMode = 'free';
  private targetLat = 0;
  private targetLng = 0;
  private targetZoom = 15;
  private targetBearing = 0;
  private animating = false;
  private missionBounds: L.LatLngBounds | null = null;

  attach(map: L.Map) {
    this.map = map;
    this.targetZoom = map.getZoom();
    const c = map.getCenter();
    this.targetLat = c.lat;
    this.targetLng = c.lng;
  }

  detach() {
    this.map = null;
  }

  setMode(m: FollowMode) {
    this.mode = m;
  }

  getMode(): FollowMode {
    return this.mode;
  }

  setMissionBounds(b: L.LatLngBounds) {
    this.missionBounds = b;
  }

  recenter(drone: DroneEntity) {
    if (!this.map) return;
    this.targetLat = drone.latitude;
    this.targetLng = drone.longitude;
    this.map.setView([drone.latitude, drone.longitude], this.map.getZoom(), {
      animate: true, duration: 0.3,
    });
  }

  private headingFromBearing(bearing: number): number {
    return ((bearing % 360) + 360) % 360;
  }

  update(drone: DroneEntity) {
    if (!this.map) return;

    // Always update values for smooth interpolation
    if (this.mode !== 'overview' && this.mode !== 'free') {
      this.targetLat = drone.latitude;
      this.targetLng = drone.longitude;
      this.targetZoom = this.map.getZoom();
      this.targetBearing = drone.heading;
    }

    if (this.mode === 'free') return;

    if (this.mode === 'overview') {
      if (this.missionBounds && this.missionBounds.isValid()) {
        this.map.fitBounds(this.missionBounds, { padding: [40, 40], maxZoom: 15, animate: true, duration: 0.4 });
      }
      return;
    }

    // Animate camera smoothly toward target
    const current = this.map.getCenter();
    const dLat = this.targetLat - current.lat;
    const dLng = this.targetLng - current.lng;
    const dist = Math.sqrt(dLat * dLat + dLng * dLng);

    if (dist > 0.000001) {
      const zoom = this.map.getZoom();
      this.targetZoom = zoom;

      // Keep the drone below centre, leaving more map visible in the direction
      // of travel. Convert the desired screen point back to a geographic point
      // so this is one smooth camera movement rather than competing pans.
      const mapSize = this.map.getSize();
      const targetPoint = this.map.project([this.targetLat, this.targetLng], zoom)
        .subtract(L.point(0, Math.round(mapSize.y * 0.15)));
      const cameraCenter = this.map.unproject(targetPoint, zoom);
      this.map.panTo(cameraCenter, {
        animate: true,
        duration: 0.12,
        easeLinearity: 0.2,
      });
    }
  }

  jumpToDrone(drone: DroneEntity) {
    if (!this.map) return;
    this.targetLat = drone.latitude;
    this.targetLng = drone.longitude;
    this.map.setView([drone.latitude, drone.longitude], 16, {
      animate: true, duration: 0.3,
    });
  }
}
