'use client';

// =============================================================================
// MJN Drone OS - Path Manager
// Efficient path rendering with append-only updates.
// Never redraws the entire polyline - appends efficiently per simulation tick.
// =============================================================================

import L from 'leaflet';
import { DroneEntity, PathInfo } from '@/types/droneEntity';

export type PathType = 'visited' | 'current' | 'planned' | 'returnHome' | 'emergency' | 'predicted';

interface PathLayer {
  type: PathType;
  polyline: L.Polyline;
  lastPointCount: number;
  color: string;
  weight: number;
  dashArray?: string;
  opacity: number;
}

export class PathManager {
  private map: L.Map | null = null;
  private layers: Map<PathType, PathLayer> = new Map();
  private hidden = false;

  constructor() {
    // Initialize all path types
    this.initLayer('visited', '#FF6633', 3, undefined, 0.6);
    this.initLayer('current', '#00D4FF', 4, undefined, 0.9);
    this.initLayer('planned', '#00FF88', 2, '8, 8', 0.5);
    this.initLayer('returnHome', '#9D6CFF', 2, '4, 4', 0.4);
    this.initLayer('emergency', '#FF4D5A', 2, '4, 4', 0.4);
    this.initLayer('predicted', '#FFC857', 1.5, '2, 4', 0.3);
  }

  private initLayer(type: PathType, color: string, weight: number, dashArray?: string, opacity = 0.6) {
    const polyline = L.polyline([], {
      color,
      weight,
      opacity,
      dashArray,
      smoothFactor: 1.5,
      lineCap: 'round',
      lineJoin: 'round',
    });
    this.layers.set(type, { type, polyline, lastPointCount: 0, color, weight, dashArray, opacity });
  }

  attach(map: L.Map) {
    this.map = map;
    // Add all polylines to map
    for (const layer of this.layers.values()) {
      layer.polyline.addTo(map);
    }
  }

  detach() {
    if (this.map) {
      for (const layer of this.layers.values()) {
        this.map.removeLayer(layer.polyline);
      }
    }
    this.map = null;
  }

  show() {
    this.hidden = false;
    for (const layer of this.layers.values()) {
      layer.polyline.setStyle({ opacity: layer.opacity });
    }
  }

  hide() {
    this.hidden = true;
    for (const layer of this.layers.values()) {
      layer.polyline.setStyle({ opacity: 0 });
    }
  }

  isVisible(): boolean {
    return !this.hidden;
  }

  update(path: PathInfo) {
    if (this.hidden) return;

    this.updatePath('visited', path.visited.map(p => [p.latitude, p.longitude] as [number, number]));
    this.updatePath('current', path.current.map(p => [p.latitude, p.longitude] as [number, number]));
    this.updatePath('planned', path.planned.map(p => [p.latitude, p.longitude] as [number, number]));
    this.updatePath('returnHome', path.returnHome.map(p => [p.latitude, p.longitude] as [number, number]));
    this.updatePath('emergency', path.emergency.map(p => [p.latitude, p.longitude] as [number, number]));
    this.updatePath('predicted', path.predicted.map(p => [p.latitude, p.longitude] as [number, number]));
  }

  private updatePath(type: PathType, points: Array<[number, number]>) {
    const layer = this.layers.get(type);
    if (!layer || !this.map) return;

    const currentCount = layer.polyline.getLatLngs().length;

    if (points.length === 0) {
      if (currentCount > 0) {
        layer.polyline.setLatLngs([]);
      }
      layer.lastPointCount = 0;
      return;
    }

    // Efficient append: only add new points since last update
    if (points.length > currentCount) {
      // Add only the new points
      const newPoints = points.slice(currentCount);
      const latlngs = newPoints.map(p => L.latLng(p[0], p[1]));
      latlngs.forEach(ll => layer.polyline.addLatLng(ll));
    } else if (points.length < currentCount) {
      // Replace completely if shorter (shouldn't happen often with visited paths)
      layer.polyline.setLatLngs(points.map(p => L.latLng(p[0], p[1])));
    }
    // If equal length, no update needed (paths haven't changed)

    layer.lastPointCount = points.length;
  }

  setPathVisibility(type: PathType, visible: boolean) {
    const layer = this.layers.get(type);
    if (!layer) return;
    layer.polyline.setStyle({ opacity: visible ? layer.opacity : 0 });
  }

  setPathColor(type: PathType, color: string) {
    const layer = this.layers.get(type);
    if (!layer) return;
    layer.color = color;
    layer.polyline.setStyle({ color });
  }

  clearPath(type: PathType) {
    const layer = this.layers.get(type);
    if (!layer) return;
    layer.polyline.setLatLngs([]);
    layer.lastPointCount = 0;
  }

  clearAll() {
    for (const type of this.layers.keys()) {
      this.clearPath(type);
    }
  }

  destroy() {
    this.detach();
    this.layers.clear();
  }
}