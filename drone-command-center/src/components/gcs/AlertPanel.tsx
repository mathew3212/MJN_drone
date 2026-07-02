'use client';

// =============================================================================
// MJN Drone OS - Alert Panel
// Displays critical alerts from the event engine.
// Reads from eventEngine (which derives from droneEntityStore).
// =============================================================================

import { useEventEngine } from '@/hooks/useEventEngine';
import { motion, AnimatePresence } from 'framer-motion';

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#FF4D5A',
  ERROR: '#FF6B35',
  WARNING: '#FFC857',
  INFO: '#06B6D4',
};

export default function AlertPanel() {
  const { events, acknowledgeEvent } = useEventEngine();

  // Get unresolved critical/error alerts
  const criticalAlerts = events.filter(
    (e) => !e.acknowledged && (e.severity === 'CRITICAL' || e.severity === 'ERROR')
  );

  if (criticalAlerts.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-14 left-0 right-0 z-50 pointer-events-none">
      <AnimatePresence>
        {criticalAlerts.slice(0, 3).map((alert) => (
          <motion.div
            key={alert.id}
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="pointer-events-auto mx-2 mb-2 p-3 rounded-lg font-mono text-sm font-bold flex items-center justify-between gap-4"
            style={{
              backgroundColor: alert.severity === 'CRITICAL'
                ? 'rgba(255,77,90,0.2)'
                : 'rgba(255,107,53,0.15)',
              borderLeft: `4px solid ${SEVERITY_COLORS[alert.severity]}`,
              boxShadow: `0 0 16px ${SEVERITY_COLORS[alert.severity]}40`,
              backdropFilter: 'blur(12px)',
            }}
          >
            <div className="flex-1">
              <div
                className="text-sm uppercase tracking-wider"
                style={{ color: SEVERITY_COLORS[alert.severity] }}
              >
                {alert.severity}: {alert.message}
              </div>
              <div className="text-xs text-[#8A9BB5] mt-1 font-normal">
                {alert.description}
              </div>
              {alert.suggestedAction && (
                <div className="text-xs text-[#FFC857] mt-1.5 font-normal">
                  → {alert.suggestedAction}
                </div>
              )}
            </div>
            <button
              onClick={() => acknowledgeEvent(alert.id)}
              className="flex-shrink-0 px-3 py-1 rounded bg-[rgba(0,212,255,0.1)] text-[#00D4FF] hover:bg-[rgba(0,212,255,0.2)] transition-colors text-xs uppercase font-mono"
            >
              ACK
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}