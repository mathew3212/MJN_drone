'use client';

// =============================================================================
// MJN Drone OS - AI Overlay Renderer
// Renders on the tactical canvas:
// - Obstacle detections
// - Restricted Airspace
// - No Fly Zones
// - Weather (wind arrows, visibility)
// - Risk Zones
// - Collision Prediction
// - Safe Landing Areas
// - Geofence
// - Emergency Landing Zones
// - Power Lines
// - Tall Buildings
// - Hospitals
// - Airports
// - Temporary Flight Restrictions
// =============================================================================

import L from 'leaflet';
import { DroneEntity, OverlayInfo } from '@/types/droneEntity';

export class AIOverlayRenderer {
  private ctx: CanvasRenderingContext2D | null = null;
  private mapRef: L.Map | null = null;
  private hidden = false;

  attach(ctx: CanvasRenderingContext2D) {
    this.ctx = ctx;
  }

  setMap(map: L.Map) {
    this.mapRef = map;
  }

  detach() {
    this.ctx = null;
    this.mapRef = null;
  }

  show() { this.hidden = false; }
  hide() { this.hidden = true; }

  render(overlays: OverlayInfo, drone: DroneEntity) {
    if (this.hidden || !this.ctx || !this.mapRef) return;

    const ctx = this.ctx;
    const map = this.mapRef;

    const toPixel = (lat: number, lng: number): [number, number] => {
      const point = map.latLngToContainerPoint([lat, lng]);
      return [point.x, point.y];
    };

    // ── Geofence ──
    if (overlays.geofence.length > 0) {
      ctx.save();
      ctx.globalAlpha = 0.05;
      ctx.fillStyle = '#00D4FF';
      ctx.beginPath();
      overlays.geofence.forEach((v, i) => {
        const [px, py] = toPixel(v.latitude, v.longitude);
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      });
      ctx.closePath();
      ctx.fill();
      ctx.globalAlpha = 0.3;
      ctx.strokeStyle = '#00D4FF';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.restore();
    }

    // ── No-Fly Zones ──
    for (const nfz of overlays.noFlyZones) {
      ctx.save();
      ctx.globalAlpha = 0.1;
      ctx.fillStyle = nfz.color || '#FF4D5A';
      ctx.beginPath();
      nfz.vertices.forEach((v, i) => {
        const [px, py] = toPixel(v.latitude, v.longitude);
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      });
      ctx.closePath();
      ctx.fill();
      ctx.globalAlpha = 0.5;
      ctx.strokeStyle = nfz.color || '#FF4D5A';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 3]);
      ctx.stroke();
      // Label
      const center = nfz.vertices.reduce(
        (acc, v) => ({ lat: acc.lat + v.latitude / nfz.vertices.length, lng: acc.lng + v.longitude / nfz.vertices.length }),
        { lat: 0, lng: 0 }
      );
      const [cx, cy] = toPixel(center.lat, center.lng);
      ctx.globalAlpha = 0.6;
      ctx.fillStyle = nfz.color || '#FF4D5A';
      ctx.font = '7px monospace';
      ctx.fillText('NO FLY ZONE', cx - 20, cy - 8);
      ctx.fillText(nfz.name, cx - 20, cy + 2);
      ctx.restore();
    }

    // ── Restricted Airspace ──
    for (const zone of overlays.restrictedAirspace) {
      ctx.save();
      ctx.globalAlpha = 0.08;
      ctx.fillStyle = zone.color || '#FFC857';
      ctx.beginPath();
      zone.vertices.forEach((v, i) => {
        const [px, py] = toPixel(v.latitude, v.longitude);
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      });
      ctx.closePath();
      ctx.fill();
      ctx.globalAlpha = 0.4;
      ctx.strokeStyle = zone.color || '#FFC857';
      ctx.lineWidth = 1;
      ctx.setLineDash([8, 4]);
      ctx.stroke();
      const center = zone.vertices.reduce(
        (acc, v) => ({ lat: acc.lat + v.latitude / zone.vertices.length, lng: acc.lng + v.longitude / zone.vertices.length }),
        { lat: 0, lng: 0 }
      );
      const [cx, cy] = toPixel(center.lat, center.lng);
      ctx.fillStyle = zone.color || '#FFC857';
      ctx.font = '7px monospace';
      ctx.fillText(zone.name, cx - 15, cy);
      ctx.restore();
    }

    // ── Obstacles ──
    for (const obs of overlays.obstacles) {
      const [ox, oy] = toPixel(obs.latitude, obs.longitude);
      ctx.save();
      ctx.globalAlpha = 0.3 + obs.risk * 0.5;
      ctx.fillStyle = obs.risk > 0.7 ? '#FF4D5A' : obs.risk > 0.4 ? '#FFC857' : '#00D4FF';
      ctx.beginPath();
      ctx.arc(ox, oy, Math.max(3, obs.radius * 0.5), 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = obs.risk > 0.7 ? '#FF4D5A' : '#FFC857';
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.fillStyle = '#FF4D5A';
      ctx.font = '6px monospace';
      ctx.fillText(obs.type, ox + 5, oy - 3);
      ctx.restore();
    }

    // ── Risk Zones ──
    for (const rz of overlays.riskZones) {
      const [rx, ry] = toPixel(rz.latitude, rz.longitude);
      ctx.save();
      ctx.globalAlpha = 0.15 * rz.risk;
      ctx.fillStyle = '#FF4D5A';
      ctx.beginPath();
      ctx.arc(rx, ry, Math.max(5, rz.radius * 0.3), 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 0.4 * rz.risk;
      ctx.strokeStyle = '#FF4D5A';
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.stroke();
      ctx.restore();
    }

    // ── Collision Predictions ──
    for (const cp of overlays.collisionPredictions) {
      const [cx, cy] = toPixel(cp.latitude, cp.longitude);
      ctx.save();
      ctx.globalAlpha = cp.probability;
      ctx.fillStyle = '#FF4D5A';
      ctx.beginPath();
      ctx.arc(cx, cy, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#FF4D5A';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, 8, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = '#FF4D5A';
      ctx.font = '6px monospace';
      ctx.fillText(`T-${cp.timeToImpact.toFixed(0)}s`, cx + 8, cy + 3);
      ctx.restore();
    }

    // ── Safe Landing Zones ──
    for (const slz of overlays.safeLandingZones) {
      const [sx, sy] = toPixel(slz.latitude, slz.longitude);
      ctx.save();
      ctx.globalAlpha = 0.2;
      ctx.fillStyle = '#00FF88';
      ctx.beginPath();
      ctx.arc(sx, sy, Math.max(4, slz.radius * 0.3), 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 0.5;
      ctx.strokeStyle = '#00FF88';
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.stroke();
      ctx.fillStyle = '#00FF88';
      ctx.font = '6px monospace';
      ctx.fillText('LAND', sx - 8, sy - 6);
      ctx.restore();
    }

    // ── Emergency Landing Zones ──
    for (const elz of overlays.emergencyLandingZones) {
      const [ex, ey] = toPixel(elz.latitude, elz.longitude);
      ctx.save();
      ctx.globalAlpha = 0.3;
      ctx.fillStyle = '#FFC857';
      ctx.beginPath();
      ctx.arc(ex, ey, Math.max(4, elz.radius * 0.3), 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 0.6;
      ctx.strokeStyle = '#FFC857';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 2]);
      ctx.stroke();
      ctx.fillStyle = '#FFC857';
      ctx.font = '6px monospace';
      ctx.fillText('EMERG LAND', ex - 12, ey - 6);
      ctx.restore();
    }

    // ── Power Lines ──
    for (const pl of overlays.powerLines) {
      const [px1, py1] = toPixel(pl.start.latitude, pl.start.longitude);
      const [px2, py2] = toPixel(pl.end.latitude, pl.end.longitude);
      ctx.save();
      ctx.globalAlpha = 0.3;
      ctx.strokeStyle = '#FFC857';
      ctx.lineWidth = 0.5;
      ctx.setLineDash([2, 4]);
      ctx.beginPath();
      ctx.moveTo(px1, py1);
      ctx.lineTo(px2, py2);
      ctx.stroke();
      ctx.restore();
    }

    // ── Weather: Wind Arrows ──
    const [wx, wy] = toPixel(drone.latitude, drone.longitude);
    ctx.save();
    ctx.globalAlpha = 0.4;
    ctx.strokeStyle = '#6B7FA0';
    ctx.lineWidth = 1;
    const windLen = 20;
    const windRad = overlays.weather.windDirection * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(wx + 30, wy - 30);
    ctx.lineTo(wx + 30 + Math.cos(windRad) * windLen, wy - 30 + Math.sin(windRad) * windLen);
    ctx.stroke();
    ctx.fillStyle = '#6B7FA0';
    ctx.font = '6px monospace';
    ctx.fillText(`${overlays.weather.windSpeed.toFixed(1)}m/s`, wx + 30, wy - 33);
    ctx.fillText(`${overlays.weather.windDirection.toFixed(0)}°`, wx + 30, wy - 26);
    ctx.restore();
  }
}