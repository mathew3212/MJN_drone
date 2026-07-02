'use client';

// =============================================================================
// MJN Drone OS - Waypoint Renderer
// Uses Leaflet markers for interactive waypoints with labels:
// - Start, Current, Completed, Upcoming, Landing, Home
// - Hover labels with ETA, Altitude, Mission step
// =============================================================================

import L from 'leaflet';
import { WaypointInfo, DroneEntity } from '@/types/droneEntity';

interface WaypointLayer {
  marker: L.Marker;
  label: L.Tooltip | null;
  lastReached: boolean;
}

export class WaypointRenderer {
  private map: L.Map | null = null;
  private layers: Map<string, WaypointLayer> = new Map();
  private hidden = false;
  private currentWpIndex = -1;

  attach(map: L.Map) {
    this.map = map;
  }

  detach() {
    this.removeAll();
    this.map = null;
  }

  show() { this.hidden = false; }
  hide() { this.hidden = true; this.removeAll(); }

  update(waypoints: WaypointInfo[], currentWaypointIndex: number) {
    if (this.hidden || !this.map) return;

    this.currentWpIndex = currentWaypointIndex;

    const processedIds = new Set<string>();

    for (let i = 0; i < waypoints.length; i++) {
      const wp = waypoints[i];
      processedIds.add(wp.id);

      const isCurrent = i === currentWaypointIndex;
      const isCompleted = wp.reached && !isCurrent;
      const isUpcoming = !wp.reached && !isCurrent;

      // Determine icon based on type
      const color = wp.type === 'home' ? '#A855F7'
        : wp.type === 'land' || wp.type === 'landing-zone' ? '#EF4444'
        : isCurrent ? '#00D4FF'
        : isCompleted ? '#4A5A78'
        : '#6B7FA0';

      const size = wp.type === 'home' || wp.type === 'land' || wp.type === 'landing-zone' ? 14
        : isCurrent ? 10 : 8;

      // Create SVG icon
      const svgIcon = this.createWaypointIcon(wp, color, size, isCurrent, isCompleted);

      const existing = this.layers.get(wp.id);
      if (existing) {
        // Update existing marker
        existing.marker.setLatLng([wp.latitude, wp.longitude]);
        existing.marker.setIcon(svgIcon);
        if (existing.label) {
          existing.label.setContent(this.createLabelContent(wp, i, isCurrent));
        }
        existing.lastReached = wp.reached;
      } else {
        // Create new marker
        const marker = L.marker([wp.latitude, wp.longitude], {
          icon: svgIcon,
          interactive: true,
          zIndexOffset: isCurrent ? 1000 : 0,
        });

        const label = L.tooltip({
          permanent: true,
          direction: 'top',
          offset: L.point(0, -size - 4),
          className: 'waypoint-tooltip',
          opacity: isCurrent ? 1 : 0.7,
        });
        label.setContent(this.createLabelContent(wp, i, isCurrent));
        marker.bindTooltip(label);

        marker.addTo(this.map);
        this.layers.set(wp.id, { marker, label, lastReached: wp.reached });
      }
    }

    // Remove stale waypoints
    for (const [id, layer] of this.layers) {
      if (!processedIds.has(id)) {
        this.map.removeLayer(layer.marker);
        this.layers.delete(id);
      }
    }
  }

  private createWaypointIcon(wp: WaypointInfo, color: string, size: number, isCurrent: boolean, isCompleted: boolean): L.DivIcon {
    const svg = `<svg width="${size * 2 + 4}" height="${size * 2 + 10}" viewBox="0 0 ${size * 2 + 4} ${size * 2 + 10}" xmlns="http://www.w3.org/2000/svg">
      ${wp.type === 'home' ? this.homeIconSVG(color)
      : wp.type === 'land' || wp.type === 'landing-zone' ? this.landIconSVG(color)
      : isCurrent ? this.currentIconSVG(color)
      : isCompleted ? this.completedIconSVG(color)
      : this.waypointIconSVG(color, size)}
    </svg>`;

    return L.divIcon({
      html: svg,
      className: 'waypoint-marker',
      iconSize: [size * 2 + 4, size * 2 + 10],
      iconAnchor: [size + 2, size + 10],
      tooltipAnchor: [0, -size - 10],
    });
  }

  private waypointIconSVG(color: string, size: number): string {
    return `<circle cx="${size + 2}" cy="${size + 2}" r="${size}" fill="none" stroke="${color}" stroke-width="1.5" opacity="0.8"/>
      <circle cx="${size + 2}" cy="${size + 2}" r="${size * 0.4}" fill="${color}" opacity="0.6"/>`;
  }

  private currentIconSVG(color: string): string {
    return `<circle cx="8" cy="8" r="7" fill="none" stroke="${color}" stroke-width="2" opacity="1"/>
      <circle cx="8" cy="8" r="3" fill="${color}" opacity="0.9"/>
      <circle cx="8" cy="8" r="10" fill="none" stroke="${color}" stroke-width="0.5" opacity="0.5"/>`;
  }

  private completedIconSVG(color: string): string {
    return `<circle cx="7" cy="7" r="5" fill="${color}" opacity="0.3"/>
      <polyline points="4,7 6,9 10,5" fill="none" stroke="${color}" stroke-width="1.5" opacity="0.6"/>`;
  }

  private homeIconSVG(color: string): string {
    return `<polygon points="8,2 16,12 12,12 12,18 4,18 4,12 0,12" fill="${color}" opacity="0.8"/>`;
  }

  private landIconSVG(color: string): string {
    return `<rect x="3" y="6" width="10" height="10" rx="1" fill="none" stroke="${color}" stroke-width="1.5" opacity="0.8"/>
      <line x1="5" y1="12" x2="11" y2="12" stroke="${color}" stroke-width="1" opacity="0.6"/>
      <polygon points="6,10 8,8 10,10" fill="${color}" opacity="0.6"/>`;
  }

  private createLabelContent(wp: WaypointInfo, index: number, isCurrent: boolean): string {
    const typeLabel = wp.type.toUpperCase();
    const etaLabel = wp.eta > 0 ? `${Math.floor(wp.eta / 60)}:${String(Math.round(wp.eta % 60)).padStart(2, '0')}` : '--:--';
    return `<div style="
      background: ${isCurrent ? 'rgba(0, 212, 255, 0.15)' : 'rgba(5, 5, 5, 0.75)'};
      border: 1px solid ${isCurrent ? 'rgba(0, 212, 255, 0.5)' : 'rgba(74, 90, 120, 0.4)'};
      border-radius: 2px;
      padding: 2px 6px;
      font-family: monospace;
      font-size: 7px;
      color: ${isCurrent ? '#00D4FF' : '#6B7FA0'};
      pointer-events: none;
      white-space: nowrap;
    ">
      <div style="font-weight: bold; font-size: 8px; color: ${isCurrent ? '#FFFFFF' : '#8A9BB5'}">${wp.label}</div>
      <div style="display: flex; gap: 6px; margin-top: 1px;">
        <span>WP#${index}</span>
        <span>${wp.altitude.toFixed(0)}m</span>
        <span>ETA ${etaLabel}</span>
      </div>
    </div>`;
  }

  private removeAll() {
    if (this.map) {
      for (const layer of this.layers.values()) {
        this.map.removeLayer(layer.marker);
      }
    }
    this.layers.clear();
  }

  destroy() {
    this.removeAll();
    this.map = null;
  }
}