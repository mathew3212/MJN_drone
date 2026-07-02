'use client';

// =============================================================================
// MJN Drone OS - Event Engine React Hook
// =============================================================================

import { useState, useEffect, useCallback } from 'react';
import { eventEngine, EventEngineState, DroneEvent } from '@/store/eventEngine';

export function useEventEngine() {
  const [state, setState] = useState<EventEngineState>(eventEngine.getState());

  useEffect(() => {
    const unsubscribe = eventEngine.subscribe(() => {
      setState({ ...eventEngine.getState() });
    });
    return unsubscribe;
  }, []);

  const acknowledgeEvent = useCallback((eventId: string) => {
    eventEngine.acknowledgeEvent(eventId);
  }, []);

  const acknowledgeAll = useCallback(() => {
    eventEngine.acknowledgeAll();
  }, []);

  const clearEvents = useCallback(() => {
    eventEngine.clearEvents();
  }, []);

  return {
    events: state.events,
    unreadCount: state.unreadCount,
    acknowledgeEvent,
    acknowledgeAll,
    clearEvents,
  };
}