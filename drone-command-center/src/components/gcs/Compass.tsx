'use client';

// =============================================================================
// MJN Drone OS - Compass
// Professional heading indicator with cardinal directions.
// =============================================================================

import { useDroneEntityStore } from '@/store/droneEntityStore';
import { useEffect, useRef } from 'react';

export default function Compass() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const heading = useDroneEntityStore((s) => s.drone.heading);

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

    // Background
    ctx.fillStyle = 'rgba(0,0,0,0.4)';
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();

    // Outer ring
    ctx.strokeStyle = 'rgba(255,255,255,0.2)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();

    // Tick marks (every 10 degrees)
    ctx.save();
    for (let deg = 0; deg < 360; deg += 10) {
      const rad = ((deg - heading) * Math.PI) / 180;
      const isCardinal = deg % 90 === 0;
      const isMajor = deg % 30 === 0;
      const tickLen = isCardinal ? 12 : isMajor ? 8 : 4;
      const innerR = r - tickLen;

      ctx.strokeStyle = isCardinal ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.3)';
      ctx.lineWidth = isCardinal ? 2 : 1;
      ctx.beginPath();
      ctx.moveTo(cx + (r - 2) * Math.sin(rad), cy - (r - 2) * Math.cos(rad));
      ctx.lineTo(cx + innerR * Math.sin(rad), cy - innerR * Math.cos(rad));
      ctx.stroke();

      // Cardinal labels
      if (isCardinal) {
        const labels: Record<number, string> = { 0: 'N', 90: 'E', 180: 'S', 270: 'W' };
        const labelR = r - 16;
        ctx.fillStyle = deg === 0 ? '#FF4D5A' : 'rgba(255,255,255,0.7)';
        ctx.font = 'bold 9px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(
          labels[deg] || '',
          cx + labelR * Math.sin(rad),
          cy - labelR * Math.cos(rad)
        );
      }
    }
    ctx.restore();

    // Center heading indicator
    ctx.fillStyle = '#FF4D5A';
    ctx.beginPath();
    ctx.moveTo(cx, cy - r + 2);
    ctx.lineTo(cx - 5, cy - r + 12);
    ctx.lineTo(cx + 5, cy - r + 12);
    ctx.closePath();
    ctx.fill();

    // Heading text
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 10px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${Math.round(heading)}°`, cx, cy);

    // Center dot
    ctx.fillStyle = 'rgba(255,255,255,0.5)';
    ctx.beginPath();
    ctx.arc(cx, cy, 2, 0, Math.PI * 2);
    ctx.fill();
  }, [heading]);

  return (
    <div className="flex items-center justify-center">
      <canvas
        ref={canvasRef}
        width={100}
        height={100}
        className="rounded-full"
        style={{ filter: 'drop-shadow(0 2px 8px rgba(0,0,0,0.5))' }}
      />
    </div>
  );
}