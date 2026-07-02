'use client';

import { useRef, useEffect, useState } from 'react';
import { useEventStore, EventSeverity, EventSource } from '@/store/eventStore';
import { motion, AnimatePresence } from 'framer-motion';

const SEVERITY_COLORS: Record<EventSeverity, string> = {
  DEBUG: '#4A5A78',
  INFO: '#06B6D4',
  WARNING: '#FFC857',
  CRITICAL: '#FF6B35',
  EMERGENCY: '#FF0044',
};

const SEVERITY_BG: Record<EventSeverity, string> = {
  DEBUG: 'rgba(74,90,120,0.05)',
  INFO: 'rgba(6,182,212,0.08)',
  WARNING: 'rgba(255,200,87,0.08)',
  CRITICAL: 'rgba(255,107,53,0.12)',
  EMERGENCY: 'rgba(255,0,68,0.15)',
};

type FilterType = 'all' | EventSeverity;
type SourceFilter = 'all' | EventSource;

export default function EventConsole() {
  const events = useEventStore((s) => s.events);
  const resolveEvent = useEventStore((s) => s.resolveEvent);
  const [severityFilter, setSeverityFilter] = useState<FilterType>('all');
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  const filtered = events.filter((e) => {
    const typeMatch = severityFilter === 'all' || e.severity === severityFilter;
    const sourceMatch = sourceFilter === 'all' || e.source === sourceFilter;
    const searchMatch = !searchQuery || 
      e.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
      e.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.source.toLowerCase().includes(searchQuery.toLowerCase());
    return typeMatch && sourceMatch && searchMatch;
  });

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filtered.length]);

  const severities: FilterType[] = ['all', 'DEBUG', 'INFO', 'WARNING', 'CRITICAL', 'EMERGENCY'];
  const sources: SourceFilter[] = [
    'all', 'MISSION', 'NAVIGATION', 'SENSOR', 'SYSTEM', 'BATTERY', 
    'COMMUNICATION', 'SAFETY', 'USER', 'WEATHER', 'PREDICTION'
  ];

  return (
    <div className="h-full flex flex-col font-mono select-none">
      {/* Controls */}
      <div className="flex flex-col gap-1 mb-1 flex-shrink-0 p-1 border-b border-[rgba(26,26,46,0.4)]">
        {/* Severity Filter */}
        <div className="flex items-center gap-0.5 overflow-x-auto pb-0.5">
          {severities.map((f) => (
            <button 
              key={f} 
              onClick={() => setSeverityFilter(f)}
              className={`px-1.5 py-0.5 text-[7px] font-mono uppercase rounded whitespace-nowrap transition-all ${
                severityFilter === f
                  ? 'bg-[rgba(0,212,255,0.15)] text-[#00D4FF] border border-[rgba(0,212,255,0.3)]'
                  : 'text-[#4A5A78] hover:text-[#6B7FA0]'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* Source & Search */}
        <div className="flex items-center gap-1">
          <select 
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value as SourceFilter)}
            className="px-1.5 py-0.5 text-[7px] font-mono bg-[rgba(26,26,46,0.3)] border border-[rgba(26,26,46,0.6)] rounded text-[#8A9BB5] outline-none"
          >
            {sources.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search..."
            className="flex-1 px-1.5 py-0.5 text-[7px] font-mono bg-[rgba(26,26,46,0.3)] border border-[rgba(26,26,46,0.6)] rounded text-[#8A9BB5] placeholder-[#4A5A78] outline-none"
          />
          <span className="text-[7px] text-[#4A5A78] whitespace-nowrap">({filtered.length}/{events.length})</span>
        </div>
      </div>

      {/* Events List */}
      <div 
        ref={scrollRef} 
        className="flex-1 overflow-y-auto space-y-[1px]" 
        style={{ scrollbarWidth: 'thin', scrollbarColor: '#1A1A2E transparent' }}
      >
        <AnimatePresence initial={false}>
          {filtered.length === 0 ? (
            <div className="flex items-center justify-center h-full text-[#4A5A78] text-[8px]">
              No events matching filter
            </div>
          ) : (
            filtered.map((event) => (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: -10, height: 0 }}
                animate={{ opacity: event.resolved ? 0.4 : 1, x: 0, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.15 }}
                onClick={() => {
                  if (!event.resolved) {
                    resolveEvent(event.id);
                  }
                }}
                className="flex flex-col gap-0.5 py-1 px-1 rounded cursor-pointer hover:bg-[rgba(26,26,46,0.3)] transition-colors group"
                style={{ 
                  background: event.resolved ? 'transparent' : SEVERITY_BG[event.severity] || 'transparent',
                  opacity: event.resolved ? 0.5 : 1,
                }}
              >
                {/* Title row */}
                <div className="flex items-center gap-1">
                  <span className="text-[7px] text-[#4A5A78] whitespace-nowrap">
                    {new Date(event.timestamp).toLocaleTimeString('en-US', { hour12: false })}
                  </span>
                  <span 
                    className="w-1 h-1 rounded-full flex-shrink-0"
                    style={{ 
                      backgroundColor: SEVERITY_COLORS[event.severity],
                      boxShadow: `0 0 4px ${SEVERITY_COLORS[event.severity]}`
                    }} 
                  />
                  <span className="text-[7px] font-bold uppercase tracking-wider text-[#6B7FA0] w-16 flex-shrink-0">
                    {event.severity}
                  </span>
                  <span className="text-[7px] font-mono text-[#4A5A78] w-12 flex-shrink-0">
                    {event.source}
                  </span>
                  <span className="text-[8px] font-mono font-bold" style={{ color: SEVERITY_COLORS[event.severity] }}>
                    {event.title}
                  </span>
                  {event.resolved && (
                    <span className="text-[6px] text-[#4A5A78] ml-auto">✓ RESOLVED</span>
                  )}
                </div>

                {/* Description */}
                <div className="flex items-start gap-1 pl-1">
                  <span className="text-[6px] text-[#8A9BB5] leading-tight flex-1">
                    {event.description}
                  </span>
                </div>

                {/* Suggested Action */}
                {event.suggestedAction && (
                  <div className="flex items-start gap-1 pl-1">
                    <span className="text-[6px] text-[#FFC857] leading-tight">
                      → {event.suggestedAction}
                    </span>
                  </div>
                )}
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      {/* Summary Footer */}
      <div className="border-t border-[rgba(26,26,46,0.4)] px-1 py-0.5 text-[7px] text-[#4A5A78] flex justify-between">
        <span>Total Events: {events.length}</span>
        <span>Unresolved: {events.filter(e => !e.resolved).length}</span>
      </div>
    </div>
  );
}