'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Radio, Satellite, Signal, Clock, Play, Pause, FastForward,
  Monitor, Sun, LayoutGrid, CircleDot
} from 'lucide-react';
import { useDroneStore } from '@/store/droneStore';
import { ThemeMode } from '@/types';

const THEME_CYCLE: ThemeMode[] = ['dark', 'midnight', 'blueprint', 'graphite', 'operator'];
const THEME_ICONS: Record<ThemeMode, string> = {
  dark: '#00D4FF',
  midnight: '#38BDF8',
  blueprint: '#64B5F6',
  graphite: '#888888',
  operator: '#FF6600',
};

export default function StatusBar() {
  const { telemetry, mission, theme, setTheme, isPaused, togglePause, timeAcceleration, setTimeAcceleration, fps } = useDroneStore();
  const [currentTime, setCurrentTime] = useState('');

  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString('en-US', { hour12: false }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const cycleTheme = () => {
    const idx = THEME_CYCLE.indexOf(theme);
    const next = THEME_CYCLE[(idx + 1) % THEME_CYCLE.length];
    setTheme(next);
  };

  const cycleSpeed = () => {
    const speeds = [1, 2, 5, 10];
    const idx = speeds.indexOf(timeAcceleration);
    const next = speeds[(idx + 1) % speeds.length];
    setTimeAcceleration(next);
  };

  return (
    <div
      className="h-10 px-4 flex items-center justify-between border-b border-[rgba(26,26,46,0.6)]"
      style={{
        background: 'rgba(5, 5, 5, 0.8)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
      }}
    >
      {/* Left: System Identity */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <motion.div
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          >
            <CircleDot size={12} className="text-[#00D4FF]" />
          </motion.div>
          <span className="text-xs font-bold tracking-[0.2em] text-[#6B7FA0] font-mono">
            MJN COMMAND
          </span>
        </div>
        <div className="h-3 w-px bg-[rgba(26,26,46,0.6)]" />
        <div className="flex items-center gap-2 text-[10px] text-[#4A5A78] font-mono">
          <Radio size={10} className="text-[#00FF88]" />
          <span className="text-[#00FF88]">{telemetry.id}</span>
        </div>
        <div className="flex items-center gap-1">
          <Satellite size={9} className="text-[#06B6D4]" />
          <span className="text-[10px] text-[#06B6D4] font-mono">GPS</span>
        </div>
        <div className="flex items-center gap-1">
          <Signal size={9} className="text-[#00FF88]" />
          <span className="text-[10px] text-[#00FF88] font-mono">{telemetry.signal_strength}%</span>
        </div>
      </div>

      {/* Center: Mission Info */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Clock size={9} className="text-[#6B7FA0]" />
          <span className="text-[10px] text-[#6B7FA0] font-mono">{formatTime(mission.elapsed)}</span>
        </div>
        <div className="text-[10px] text-[#4A5A78] font-mono">
          M {mission.progress.toFixed(1)}%
        </div>
        <div className="text-[10px] text-[#4A5A78] font-mono">
          {telemetry.speed.toFixed(1)} m/s
        </div>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-3">
        <div className="text-[10px] text-[#4A5A78] font-mono">
          {fps} FPS
        </div>
        <div className="h-3 w-px bg-[rgba(26,26,46,0.6)]" />

        {/* Speed control */}
        <button
          onClick={cycleSpeed}
          className="flex items-center gap-1 text-[10px] text-[#6B7FA0] hover:text-[#00D4FF] font-mono transition-colors"
        >
          <FastForward size={9} />
          {timeAcceleration}x
        </button>

        {/* Pause/Play */}
        <button
          onClick={togglePause}
          className="text-[#6B7FA0] hover:text-[#00FF88] transition-colors"
        >
          {isPaused ? <Play size={10} /> : <Pause size={10} />}
        </button>

        {/* Theme */}
        <button
          onClick={cycleTheme}
          className="flex items-center gap-1 text-[10px] font-mono text-[#6B7FA0] hover:text-white transition-colors"
        >
          <LayoutGrid size={9} style={{ color: THEME_ICONS[theme] }} />
        </button>

        <div className="text-[10px] text-[#4A5A78] font-mono">
          {currentTime} UTC
        </div>
      </div>
    </div>
  );
}