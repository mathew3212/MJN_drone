'use client';

import { useMemo } from 'react';
import { motion } from 'framer-motion';

interface ChartDataPoint {
  time: number;
  value: number;
}

interface PremiumLineChartProps {
  data: ChartDataPoint[];
  title?: string;
  unit?: string;
  color?: string;
  gradientFrom?: string;
  gradientTo?: string;
  min?: number;
  max?: number;
  showGrid?: boolean;
  height?: number;
  live?: boolean;
  strokeWidth?: number;
  areaOpacity?: number;
}

export default function PremiumLineChart({
  data,
  title,
  unit = '',
  color = '#00D4FF',
  gradientFrom = 'rgba(0, 212, 255, 0.3)',
  gradientTo = 'rgba(0, 212, 255, 0.0)',
  min,
  max,
  showGrid = true,
  height = 120,
  live = false,
  strokeWidth = 1.5,
  areaOpacity = 0.3,
}: PremiumLineChartProps) {
  const svgWidth = 400;
  const padding = { top: 20, right: 15, bottom: 20, left: 35 };
  const chartW = svgWidth - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const { points, yMin, yMax, path, areaPath, gridLines, yLabels } = useMemo(() => {
    if (!data || data.length < 2) {
      return { points: [], yMin: 0, yMax: 100, path: '', areaPath: '', gridLines: [], yLabels: [] };
    }

    const values = data.map(d => d.value);
    const yMinVal = min ?? Math.min(...values) * 0.95;
    const yMaxVal = max ?? Math.max(...values) * 1.05;
    const range = yMaxVal - yMinVal || 1;

    // Scale function
    const scaleX = (i: number) => padding.left + (i / (data.length - 1)) * chartW;
    const scaleY = (v: number) => padding.top + chartH - ((v - yMinVal) / range) * chartH;

    const pts = data.map((d, i) => ({
      x: scaleX(i),
      y: scaleY(d.value),
      value: d.value,
      time: d.time,
    }));

    // Build SVG path
    const pathD = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    
    // Build area path
    const bottomY = padding.top + chartH;
    const areaD = `${pathD} L${pts[pts.length - 1].x.toFixed(1)},${bottomY} L${pts[0].x.toFixed(1)},${bottomY} Z`;

    // Grid lines (5 horizontal)
    const gridYLabels = Array.from({ length: 5 }, (_, i) => {
      const val = yMinVal + (range * (4 - i)) / 4;
      const yPos = padding.top + (chartH * i) / 4;
      return { y: yPos, label: val.toFixed(1) };
    });

    // Vertical grid lines
    const vGrid = Array.from({ length: 5 }, (_, i) => ({
      x: padding.left + (chartW * i) / 4,
    }));

    return {
      points: pts,
      yMin: yMinVal,
      yMax: yMaxVal,
      path: pathD,
      areaPath: areaD,
      gridLines: vGrid,
      yLabels: gridYLabels,
    };
  }, [data, min, max, chartW, chartH]);

  const currentValue = data.length > 0 ? data[data.length - 1].value : 0;

  return (
    <div className="relative h-full w-full">
      {/* Title row */}
      {(title || unit) && (
        <div className="flex items-baseline justify-between mb-0.5">
          <span className="text-[9px] font-semibold uppercase tracking-[0.1em] text-[#6B7FA0] font-mono">
            {title}
          </span>
          <div className="flex items-baseline gap-1">
            <motion.span
              key={currentValue.toFixed(1)}
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-xs font-bold font-mono"
              style={{ color }}
            >
              {currentValue.toFixed(1)}
            </motion.span>
            {unit && (
              <span className="text-[9px] text-[#4A5A78] font-mono">{unit}</span>
            )}
          </div>
        </div>
      )}

      {/* SVG Chart */}
      <svg
        width="100%"
        height={height - 20}
        viewBox={`0 0 ${svgWidth} ${height}`}
        preserveAspectRatio="none"
        className="overflow-visible"
      >
        {/* Grid */}
        {showGrid && gridLines.map((g, i) => (
          <line
            key={`vg-${i}`}
            x1={g.x}
            y1={padding.top}
            x2={g.x}
            y2={padding.top + chartH}
            stroke="rgba(26, 26, 46, 0.5)"
            strokeWidth={0.5}
          />
        ))}
        {showGrid && yLabels.map((l, i) => (
          <g key={`hl-${i}`}>
            <line
              x1={padding.left}
              y1={l.y}
              x2={padding.left + chartW}
              y2={l.y}
              stroke="rgba(26, 26, 46, 0.4)"
              strokeWidth={0.5}
              strokeDasharray="2,2"
            />
            <text
              x={padding.left - 4}
              y={l.y + 2}
              textAnchor="end"
              fill="#4A5A78"
              fontSize={7}
              fontFamily="monospace"
            >
              {l.label}
            </text>
          </g>
        ))}

        {/* Area fill */}
        {areaPath && (
          <motion.path
            d={areaPath}
            fill={`url(#gradient-${title?.replace(/\s/g, '')})`}
            opacity={areaOpacity}
            initial={{ opacity: 0 }}
            animate={{ opacity: areaOpacity }}
          />
        )}

        {/* Line */}
        {path && (
          <motion.path
            d={path}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        )}

        {/* Glow line (behind) */}
        {path && (
          <path
            d={path}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth * 3}
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity={0.15}
          />
        )}

        {/* Live point */}
        {live && points.length > 0 && (
          <motion.circle
            cx={points[points.length - 1].x}
            cy={points[points.length - 1].y}
            r={3}
            fill={color}
            initial={{ r: 0 }}
            animate={{ r: 3, opacity: [1, 0.5, 1] }}
            transition={{ duration: 0.3, opacity: { duration: 1.5, repeat: Infinity } }}
          />
        )}

        {/* Gradient definition */}
        <defs>
          <linearGradient id={`gradient-${title?.replace(/\s/g, '')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={gradientFrom} />
            <stop offset="100%" stopColor={gradientTo} />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}