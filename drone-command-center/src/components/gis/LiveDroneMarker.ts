'use client';

// =============================================================================
// MJN Drone OS - Live Drone Marker Renderer
// Professional animated drone marker with:
// - Drone silhouette with heading arrow
// - Animated rotation
// - Altitude indicator
// - Shadow
// - Selection highlight
// - Signal ring
// - Battery ring
// - GPS accuracy circle
// - Flight status
// - Speed indicator
// =============================================================================

import { DroneEntity } from '@/types/droneEntity';

export class LiveDroneMarker {
  private ctx: CanvasRenderingContext2D | null = null;
  private animTime = 0;
  private lastRender = 0;
  
  // Smooth interpolation
  private prevX = 0;
  private prevY = 0;
  private currentX = 0;
  private currentY = 0;
  private interpolationSpeed = 0.15; // Lower = smoother but slower
  
  // Heading interpolation
  private prevHeading = 0;
  private currentHeading = 0;

  attach(ctx: CanvasRenderingContext2D) {
    this.ctx = ctx;
  }

  detach() {
    this.ctx = null;
  }

  private normalizeHeading(heading: number): number {
    // Normalize heading to 0-360
    let h = heading % 360;
    if (h < 0) h += 360;
    return h;
  }

  private getShortestHeadingDiff(from: number, to: number): number {
    // Get shortest rotation path
    from = this.normalizeHeading(from);
    to = this.normalizeHeading(to);
    let diff = to - from;
    if (diff > 180) diff -= 360;
    if (diff < -180) diff += 360;
    return diff;
  }

  render(
    x: number,
    y: number,
    drone: DroneEntity,
    selected: boolean,
    scale: number = 1,
  ) {
    const ctx = this.ctx;
    if (!ctx) return;

    const now = performance.now();
    const dt = Math.min(now - this.lastRender, 16); // Cap at 60 FPS
    this.lastRender = now;
    this.animTime += dt * 0.001;

    // First frame initialization
    if (this.prevX === 0 && this.prevY === 0) {
      this.prevX = x;
      this.prevY = y;
      this.currentX = x;
      this.currentY = y;
      this.prevHeading = drone.heading;
      this.currentHeading = drone.heading;
    }

    // Update target position
    this.prevX = this.currentX;
    this.prevY = this.currentY;
    this.currentX = x;
    this.currentY = y;

    // Update heading with shortest path
    this.prevHeading = this.normalizeHeading(this.currentHeading);
    const headingDiff = this.getShortestHeadingDiff(this.prevHeading, drone.heading);
    this.currentHeading = this.prevHeading + headingDiff;

    // Smooth interpolation
    const interpX = this.prevX + (this.currentX - this.prevX) * this.interpolationSpeed;
    const interpY = this.prevY + (this.currentY - this.prevY) * this.interpolationSpeed;
    const interpHeading = this.prevHeading + headingDiff * this.interpolationSpeed;

    const s = scale;
    const pulse = 0.8 + Math.sin(this.animTime * 3) * 0.2;
    const signalPulse = 0.6 + Math.sin(this.animTime * 2) * 0.4;
    const rotatePulse = 1 + Math.sin(this.animTime * 4) * 0.05; // Subtle scaling pulse

    // ── Shadow ──
    ctx.save();
    ctx.translate(interpX + 2 * s, interpY + 2 * s);
    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.beginPath();
    ctx.ellipse(0, 0, 14 * s * rotatePulse, 6 * s * rotatePulse, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // ── GPS Accuracy Circle ──
    const gpsRadius = 8 * s + drone.gps.accuracy * 5 * s;
    ctx.save();
    ctx.strokeStyle = drone.gps.fixType === 'RTK_FIXED' ? 'rgba(0, 255, 136, 0.15)'
      : drone.gps.fixType === 'RTK_FLOAT' ? 'rgba(0, 212, 255, 0.15)'
      : 'rgba(255, 200, 87, 0.15)';
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 3]);
    ctx.beginPath();
    ctx.arc(interpX, interpY, gpsRadius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();

    // ── Signal Ring ──
    const signalRadius = 18 * s * signalPulse;
    ctx.save();
    const signalGrad = ctx.createRadialGradient(interpX, interpY, signalRadius - 4 * s, interpX, interpY, signalRadius);
    signalGrad.addColorStop(0, `rgba(0, 212, 255, ${0.15 * (drone.signal.strength / 100)})`);
    signalGrad.addColorStop(1, 'rgba(0, 212, 255, 0)');
    ctx.fillStyle = signalGrad;
    ctx.beginPath();
    ctx.arc(interpX, interpY, signalRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = `rgba(0, 212, 255, ${0.2 * (drone.signal.strength / 100)})`;
    ctx.lineWidth = 0.5;
    ctx.stroke();
    ctx.restore();

    // ── Selection Highlight ──
    if (selected) {
      ctx.save();
      ctx.strokeStyle = 'rgba(0, 212, 255, 0.4)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.arc(interpX, interpY, 22 * s * pulse, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }

    // ── Battery Ring ──
    const batteryAngle = (drone.battery.percentage / 100) * Math.PI * 2;
    const batteryColor = drone.battery.percentage > 50 ? '#00FF88'
      : drone.battery.percentage > 20 ? '#FFC857'
      : '#FF4D5A';
    ctx.save();
    ctx.strokeStyle = 'rgba(74, 90, 120, 0.3)';
    ctx.lineWidth = 2 * s;
    ctx.beginPath();
    ctx.arc(interpX, interpY, 16 * s, -Math.PI / 2, Math.PI * 1.5);
    ctx.stroke();
    ctx.strokeStyle = batteryColor;
    ctx.lineWidth = 2 * s;
    ctx.beginPath();
    ctx.arc(interpX, interpY, 16 * s, -Math.PI / 2, -Math.PI / 2 + batteryAngle);
    ctx.stroke();
    ctx.restore();

    // ── Drone Body ──
    ctx.save();
    ctx.translate(interpX, interpY);
    ctx.rotate((interpHeading * Math.PI) / 180);

    // Glow
    const glowGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, 20 * s);
    glowGrad.addColorStop(0, `rgba(0, 212, 255, ${0.2 * pulse})`);
    glowGrad.addColorStop(1, 'rgba(0, 212, 255, 0)');
    ctx.fillStyle = glowGrad;
    ctx.beginPath();
    ctx.arc(0, 0, 20 * s * rotatePulse, 0, Math.PI * 2);
    ctx.fill();

    // Drone silhouette (X-frame quadcopter)
    ctx.strokeStyle = '#00D4FF';
    ctx.lineWidth = 2 * s;
    ctx.globalAlpha = 0.9;

    // Arms (X pattern)
    ctx.beginPath();
    ctx.moveTo(-10 * s, -10 * s);
    ctx.lineTo(10 * s, 10 * s);
    ctx.moveTo(10 * s, -10 * s);
    ctx.lineTo(-10 * s, 10 * s);
    ctx.stroke();

    // Motor housings (small circles at arm ends)
    ctx.fillStyle = '#00D4FF';
    ctx.globalAlpha = 0.7;
    [
      [-10 * s, -10 * s],
      [10 * s, 10 * s],
      [10 * s, -10 * s],
      [-10 * s, 10 * s],
    ].forEach(([mx, my]) => {
      ctx.beginPath();
      ctx.arc(mx, my, 2.5 * s, 0, Math.PI * 2);
      ctx.fill();
    });

    // Center body
    ctx.fillStyle = '#00D4FF';
    ctx.globalAlpha = 0.6;
    ctx.beginPath();
    ctx.arc(0, 0, 5 * s, 0, Math.PI * 2);
    ctx.fill();

    // Center dot
    ctx.fillStyle = '#FFFFFF';
    ctx.globalAlpha = 0.9;
    ctx.beginPath();
    ctx.arc(0, 0, 2 * s, 0, Math.PI * 2);
    ctx.fill();

    // ── Heading Arrow (nose) ──
    ctx.fillStyle = '#FF6600';
    ctx.globalAlpha = 0.95;
    ctx.beginPath();
    ctx.moveTo(0, -14 * s);
    ctx.lineTo(-5 * s, -6 * s);
    ctx.lineTo(5 * s, -6 * s);
    ctx.closePath();
    ctx.fill();

    // Arrow outline
    ctx.strokeStyle = '#FF8844';
    ctx.lineWidth = 0.5 * s;
    ctx.globalAlpha = 0.5;
    ctx.stroke();

    // ── Crosshairs ──
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.3)';
    ctx.lineWidth = 1 * s;
    ctx.globalAlpha = 0.4;
    ctx.beginPath();
    ctx.moveTo(-8 * s, -8 * s);
    ctx.lineTo(8 * s, 8 * s);
    ctx.moveTo(8 * s, -8 * s);
    ctx.lineTo(-8 * s, 8 * s);
    ctx.stroke();

    // ── Range rings ──
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.1)';
    ctx.lineWidth = 0.5 * s;
    ctx.globalAlpha = 0.3;
    ctx.beginPath();
    ctx.arc(0, 0, 12 * s, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(0, 0, 15 * s, 0, Math.PI * 2);
    ctx.stroke();

    ctx.restore();

    // ── Altitude Indicator (left side) ──
    ctx.save();
    ctx.fillStyle = 'rgba(5, 5, 5, 0.6)';
    const altBarX = interpX - 24 * s;
    const altBarY = interpY - 10 * s;
    const altBarW = 3 * s;
    const altBarH = 20 * s;
    ctx.fillRect(altBarX, altBarY, altBarW, altBarH);

    const altFill = Math.min(1, Math.max(0, (drone.altitude - 900) / 200));
    ctx.fillStyle = '#00D4FF';
    ctx.fillRect(altBarX, altBarY + altBarH * (1 - altFill), altBarW, altBarH * altFill);

    ctx.fillStyle = '#6B7FA0';
    ctx.font = `${6 * s}px monospace`;
    ctx.fillText(`${drone.altitude.toFixed(0)}m`, altBarX - 2 * s, altBarY - 3 * s);
    ctx.restore();

    // ── Speed Indicator (right side) ──
    ctx.save();
    ctx.fillStyle = 'rgba(5, 5, 5, 0.6)';
    const spdX = interpX + 20 * s;
    const spdY = interpY - 10 * s;
    ctx.fillRect(spdX, spdY, 3 * s, 20 * s);

    const spdFill = Math.min(1, drone.velocity / 30);
    ctx.fillStyle = '#FFC857';
    ctx.fillRect(spdX, spdY + 20 * s * (1 - spdFill), 3 * s, 20 * s * spdFill);

    ctx.fillStyle = '#6B7FA0';
    ctx.font = `${6 * s}px monospace`;
    ctx.fillText(`${drone.velocity.toFixed(1)}m/s`, spdX - 2 * s, spdY - 3 * s);
    ctx.restore();

    // ── Flight Status Label ──
    ctx.save();
    const statusColor = drone.status === 'EMERGENCY' ? '#FF4D5A'
      : drone.status === 'RETURN_HOME' ? '#FFC857'
      : drone.status === 'COMPLETE' ? '#00FF88'
      : '#00D4FF';
    ctx.fillStyle = 'rgba(5, 5, 5, 0.7)';
    const statusText = `${drone.status}`;
    ctx.font = `bold ${7 * s}px monospace`;
    const statusW = ctx.measureText(statusText).width;
    ctx.fillRect(interpX - statusW / 2 - 4 * s, interpY + 18 * s, statusW + 8 * s, 12 * s);
    ctx.fillStyle = statusColor;
    ctx.textAlign = 'center';
    ctx.fillText(statusText, interpX, interpY + 27 * s);
    ctx.restore();
  }
}