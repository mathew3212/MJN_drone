'use client';

import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Trash2 } from 'lucide-react';
import { useDroneStore } from '@/store/droneStore';

const typeColors: Record<string, string> = {
  info: '#06B6D4',
  warn: '#FFC857',
  error: '#FF4D5A',
  success: '#00FF88',
};

export default function EventConsole() {
  const { events, addEvent } = useDroneStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  const clearEvents = () => {
    // Replace with empty via a hack since we don't have a dispatch action
    window.location.reload();
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-1 flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <Terminal size={10} className="text-[#6B7FA0]" />
          <span className="text-[9px] font-bold uppercase tracking-[0.15em] text-[#6B7FA0] font-mono">
            Event Console
          </span>
          <span className="text-[8px] text-[#4A5A78] font-mono">({events.length})</span>
        </div>
      </div>

      {/* Events List */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-[1px] pr-1"
        style={{ scrollbarWidth: 'thin', scrollbarColor: '#1A1A2E transparent' }}
      >
        <AnimatePresence initial={false}>
          {events.map((event, i) => (
            <motion.div
              key={event.id}
              initial={{ opacity: 0, x: -10, height: 0 }}
              animate={{ opacity: 1, x: 0, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="flex items-start gap-2 py-[2px] px-1 rounded hover:bg-[rgba(26,26,46,0.3)] transition-colors group"
            >
              <span className="text-[9px] text-[#4A5A78] font-mono w-14 flex-shrink-0 tabular-nums">
                {event.time}
              </span>
              <span
                className="w-1.5 h-1.5 rounded-full mt-[3px] flex-shrink-0"
                style={{
                  backgroundColor: typeColors[event.type],
                  boxShadow: `0 0 4px ${typeColors[event.type]}`,
                }}
              />
              <span className="text-[10px] text-[#8A9BB5] font-mono leading-tight">
                {event.message}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}