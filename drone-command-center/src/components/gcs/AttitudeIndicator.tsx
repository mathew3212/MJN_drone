'use client';

// =============================================================================
// MJN Drone OS - Attitude Indicator (Artificial Horizon)
// Displays pitch and roll with a professional aircraft-style instrument.
// =============================================================================

import { useDroneEntityStore } from '@/store/droneEntityStore';
import { useEffect, useRef } from 'react';

export default function AttitudeIndicator() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pitch = useDroneEntityStore((s) => s.drone.pitch);
  const roll = useDroneEntityStore((s) => s.drone.roll);
  const yaw = useDroneEntityStore((s) => s.drone.yaw);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(w, h) / 2 - 4;

    ctx.clearRect(0, 0, w, h);

    // Clip to circle
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.clip();

    // Rotate by roll
    ctx.translate(cx, cy);
    ctx.rotate((roll * Math.PI) / 180);
    ctx.translate(-cx, -cy);

    // Sky (blue)
    const skyGrad = ctx.createLinearGradient(0, 0, 0, cy);
    skyGrad.addColorStop(0, '#1a3a5c');
    skyGrad.addColorStop(1, '#2d6da8');
    ctx.fillStyle = skyGrad;
    ctx.fillRect(0, 0, w, cy + pitch * 2);

    // Ground (brown)
    const groundGrad = ctx.createLinearGradient(0, cy, 0, h);
    groundGrad.addColorStop(0, '#5c3d1a');
    groundGrad.addColorStop(1, '#3d2a10');
    ctx.fillStyle = groundGrad;
    ctx.fillRect(0, cy + pitch * 2, w, h);

    // Horizon line
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx - r + 10, cy + pitch * 2);
    ctx.lineTo(cx + r - 10, cy + pitch * 2);
    ctx.stroke();

    // Pitch lines
    ctx.strokeStyle = 'rgba(255,255,255,0.5)';
    ctx.lineWidth = 1;
    for (let deg = -30; deg <= 30; deg += 10) {
      if (deg === 0) continue;
      const y = cy + pitch * 2 + deg * 3;
      const lineW = deg % 20 === 0 ? 40 : 20;
      ctx.beginPath();
      ctx.moveTo(cx - lineW / 2, y);
      ctx.lineTo(cx + lineW / 2, y);
      ctx.stroke();
      ctx.fillStyle = 'rgba(255,255,255,0.6)';
      ctx.font = '8px monospace';
      ctx.textAlign = 'right';
      ctx.fillText(`${deg}°`, cx - lineW / 2 - 4, y + 3);
      ctx.textAlign = 'left';
      ctx.fillText(`${deg}°`, cx + lineW / 2 + 4, y + 3);
    }

    ctx.restore();

    // Outer ring
    ctx.strokeStyle = 'rgba(255,255,255,0.3)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();

    // Center aircraft symbol
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((roll * Math.PI) / 180);

    // Wings
    ctx.strokeStyle = '#FFC857';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(-20, 0);
    ctx.lineTo(20, 0);
    ctx.stroke();

    // Nose
    ctx.beginPath();
    ctx.moveTo(0, -6);
    ctx.lineTo(0, 12);
    ctx.stroke();

    ctx.restore();

    // Yaw indicator
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    ctx.font = '8px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`${yaw.toFixed(0)}°`, cx, r + 14);
  }, [pitch, roll, yaw]);

  return (
    <div className="flex items-center justify-center">
      <canvas
        ref={canvasRef}
        width={120}
        height={120}
        className="rounded-full"
        style={{ filter: 'drop-shadow(0 2px 8px rgba(0,0,0,0.5))' }}
      />
    </div>
  );
}