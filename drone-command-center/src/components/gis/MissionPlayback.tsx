'use client';

// =============================================================================
// MJN Drone OS - Mission Playback
// Replay completed flights with:
// - Timeline scrubber
// - Pause/Resume
// - Speed control (2x, 5x, 10x)
// - Jump to waypoint
// =============================================================================

import { useState, useEffect, useCallback, useRef } from 'react';
import { useDroneEntityStore } from '@/store/droneEntityStore';

type PlaybackSpeed = 1 | 2 | 5 | 10;

export default function MissionPlayback() {
  const drone = useDroneEntityStore((s) => s.drone);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<PlaybackSpeed>(1);
  const [progress, setProgress] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const animRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);

  const visitedPoints = drone.path.visited;
  const totalPoints = visitedPoints.length;

  const togglePlayback = useCallback(() => {
    if (totalPoints === 0) return;
    if (!isPlaying) {
      startTimeRef.current = Date.now();
      setIsPlaying(true);
    } else {
      setIsPlaying(false);
      if (animRef.current) cancelAnimationFrame(animRef.current);
    }
  }, [isPlaying, totalPoints]);

  const jumpToWaypoint = useCallback((index: number) => {
    if (index < 0 || index >= totalPoints) return;
    setProgress((index / Math.max(totalPoints - 1, 1)) * 100);
  }, [totalPoints]);

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return m + ':' + s.toString().padStart(2, '0');
  };

  useEffect(() => {
    if (!isPlaying || totalPoints === 0) return;

    const totalDuration = totalPoints * (1000 / 20);
    const speedMs = totalDuration / speed;

    const animate = () => {
      const elapsed = Date.now() - startTimeRef.current;
      const newProgress = Math.min(100, (elapsed / speedMs) * 100);
      setProgress(newProgress);

      if (newProgress >= 100) {
        setIsPlaying(false);
        return;
      }
      animRef.current = requestAnimationFrame(animate);
    };
    animRef.current = requestAnimationFrame(animate);

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [isPlaying, speed, totalPoints]);

  if (!isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        className="absolute bottom-2 right-2 z-30 bg-[rgba(5,5,5,0.85)] border border-[rgba(26,26,46,0.6)] rounded px-2 py-1 text-[8px] font-mono text-[#6B7FA0] hover:text-[#00D4FF] transition-colors"
      >
        PLAYBACK
      </button>
    );
  }

  return (
    <div className="absolute bottom-2 left-2 right-2 z-30 bg-[rgba(5,5,5,0.92)] border border-[rgba(26,26,46,0.8)] rounded p-2 font-mono text-[8px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <span className="text-[#FFC857] font-bold text-[9px] uppercase tracking-wider">Mission Playback</span>
        <button
          onClick={() => { setIsVisible(false); setIsPlaying(false); }}
          className="text-[#4A5A78] hover:text-[#FF4D5A]"
        >
          X
        </button>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 mb-1">
        <button
          onClick={togglePlayback}
          disabled={totalPoints === 0}
          className={'px-2 py-0.5 rounded text-[8px] font-mono transition-all ' + (
            isPlaying
              ? 'bg-[#FFC857] text-[#050505]'
              : 'bg-[rgba(0,212,255,0.15)] text-[#00D4FF] hover:bg-[rgba(0,212,255,0.25)]'
          ) + ' disabled:opacity-30'}
        >
          {isPlaying ? 'PAUSE' : 'PLAY'}
        </button>

        {/* Speed buttons */}
        {([1, 2, 5, 10] as PlaybackSpeed[]).map((s) => (
          <button
            key={s}
            onClick={() => setSpeed(s)}
            className={'px-1.5 py-0.5 rounded text-[7px] font-mono transition-all ' + (
              speed === s
                ? 'bg-[#00D4FF] text-[#050505]'
                : 'bg-[rgba(26,26,46,0.6)] text-[#4A5A78] hover:text-[#00D4FF]'
            )}
          >
            {s}x
          </button>
        ))}

        <span className="text-[#4A5A78] ml-auto">
          {formatTime((progress / 100) * totalPoints * 0.05)} / {formatTime(totalPoints * 0.05)}
        </span>
      </div>

      {/* Timeline Scrubber */}
      <div className="relative h-4 flex items-center">
        <input
          type="range"
          min={0}
          max={100}
          value={progress}
          onChange={(e) => {
            const val = parseFloat(e.target.value);
            setProgress(val);
            const pointIndex = Math.floor((val / 100) * (totalPoints - 1));
            if (pointIndex >= 0 && pointIndex < totalPoints) {
              const pt = visitedPoints[pointIndex];
              window.dispatchEvent(new CustomEvent('mission-playback-seek', {
                detail: { latitude: pt.latitude, longitude: pt.longitude, altitude: pt.altitude, index: pointIndex },
              }));
            }
          }}
          className="w-full h-1 appearance-none bg-[rgba(26,26,46,0.6)] rounded outline-none cursor-pointer"
          style={{
            background: 'linear-gradient(to right, #00D4FF ' + progress + '%, rgba(26,26,46,0.6) ' + progress + '%)',
          }}
        />
      </div>

      {/* Waypoint jump markers on timeline */}
      <div className="flex items-center gap-1 mt-1 flex-wrap">
        {drone.waypoints.map((wp, i) => (
          <button
            key={wp.id}
            onClick={() => jumpToWaypoint(i)}
            className={'px-1 py-0.5 rounded text-[6px] font-mono transition-all ' + (
              i === drone.currentWaypointIndex
                ? 'bg-[#00D4FF] text-[#050505]'
                : wp.reached
                  ? 'bg-[rgba(0,255,136,0.15)] text-[#00FF88]'
                  : 'bg-[rgba(74,90,120,0.3)] text-[#4A5A78]'
            )}
          >
            {'WP' + i + ' ' + wp.label}
          </button>
        ))}
      </div>

      {/* Stats */}
      <div className="flex items-center gap-3 mt-1 text-[#4A5A78]">
        <span>{'Points: ' + totalPoints}</span>
        <span>{'Speed: ' + speed + 'x'}</span>
        <span>{'Progress: ' + progress.toFixed(1) + '%'}</span>
      </div>
    </div>
  );
}