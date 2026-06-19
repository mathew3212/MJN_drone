'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { X, Minus, Maximize2 } from 'lucide-react';

interface GlassPanelProps {
  children: React.ReactNode;
  title?: string;
  icon?: React.ReactNode;
  status?: 'online' | 'offline' | 'warning' | 'error' | 'idle';
  statusColor?: string;
  isFocused?: boolean;
  onFocus?: () => void;
  onDoubleClick?: () => void;
  onClose?: () => void;
  className?: string;
  style?: React.CSSProperties;
}

const statusDotColors: Record<string, string> = {
  online: '#00FF88',
  offline: '#4A5A78',
  warning: '#FFC857',
  error: '#FF4D5A',
  idle: '#06B6D4',
};

export default function GlassPanel({
  children,
  title,
  icon,
  status = 'online',
  statusColor,
  isFocused = false,
  onFocus,
  onDoubleClick,
  onClose,
  className = '',
  style,
}: GlassPanelProps) {
  const [isHovered, setIsHovered] = useState(false);
  const dotColor = statusColor || statusDotColors[status];

  return (
    <motion.div
      className={`relative rounded-xl overflow-hidden flex flex-col ${className}`}
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{
        opacity: 1,
        y: 0,
        scale: 1,
        boxShadow: isFocused
          ? '0 0 30px rgba(0, 212, 255, 0.15), 0 8px 32px rgba(0, 0, 0, 0.4)'
          : isHovered
          ? '0 8px 32px rgba(0, 0, 0, 0.3)'
          : '0 4px 16px rgba(0, 0, 0, 0.2)',
      }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      onClick={onFocus}
      onDoubleClick={onDoubleClick}
      style={{
        ...style,
        background: 'rgba(10, 10, 15, 0.6)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        border: isFocused
          ? '1px solid rgba(0, 212, 255, 0.6)'
          : '1px solid rgba(26, 26, 46, 0.8)',
      }}
    >
      {/* Animated glow border on focus */}
      {isFocused && (
        <motion.div
          className="absolute inset-0 rounded-xl pointer-events-none"
          animate={{
            boxShadow: [
              '0 0 20px rgba(0, 212, 255, 0.0), inset 0 0 20px rgba(0, 212, 255, 0.0)',
              '0 0 20px rgba(0, 212, 255, 0.1), inset 0 0 20px rgba(0, 212, 255, 0.05)',
              '0 0 20px rgba(0, 212, 255, 0.0), inset 0 0 20px rgba(0, 212, 255, 0.0)',
            ],
          }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        />
      )}

      {/* Title Bar */}
      {title && (
        <div className="flex items-center justify-between px-3 py-2 border-b border-[rgba(26,26,46,0.6)]">
          <div className="flex items-center gap-2">
            {icon && <span className="text-[#6B7FA0] w-3.5 h-3.5">{icon}</span>}
            <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-[#6B7FA0] font-mono">
              {title}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {/* Status dot */}
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{
                backgroundColor: dotColor,
                boxShadow: `0 0 6px ${dotColor}`,
              }}
            />
            {/* Controls */}
            {onDoubleClick && (
              <button
                onClick={(e) => { e.stopPropagation(); onDoubleClick(); }}
                className="text-[#4A5A78] hover:text-[#6B7FA0] transition-colors"
              >
                <Maximize2 size={10} />
              </button>
            )}
            {onClose && (
              <button
                onClick={(e) => { e.stopPropagation(); onClose(); }}
                className="text-[#4A5A78] hover:text-[#FF4D5A] transition-colors"
              >
                <X size={10} />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Content - flex fill remaining space */}
      <div className="p-3 flex-1 min-h-0 overflow-hidden">
        {children}
      </div>
    </motion.div>
  );
}