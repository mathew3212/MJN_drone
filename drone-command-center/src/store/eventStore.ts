'use client';

/**
 * Event Store - Structured Event Log for Mission Operations
 * 
 * This is the authoritative record of all significant events during a mission.
 * Every event has a timestamp, severity, source, and suggested action.
 * Events flow from the Drone State and are not duplicated.
 */

import { create } from 'zustand';

export type EventSeverity = 'DEBUG' | 'INFO' | 'WARNING' | 'CRITICAL' | 'EMERGENCY';
export type EventSource = 'MISSION' | 'NAVIGATION' | 'SENSOR' | 'SYSTEM' | 'BATTERY' | 'COMMUNICATION' | 'SAFETY' | 'USER' | 'WEATHER' | 'PREDICTION';

export interface SystemEvent {
  id: string;
  timestamp: number;
  severity: EventSeverity;
  source: EventSource;
  title: string;
  description: string;
  suggestedAction?: string;
  data?: Record<string, unknown>;
  resolved?: boolean;
  resolvedAt?: number;
}

export interface EventStoreState {
  events: SystemEvent[];
  eventCount: number;
  unreadCount: number;
  maxEvents: number;
  
  // Actions
  addEvent: (event: Omit<SystemEvent, 'id' | 'timestamp'>) => void;
  resolveEvent: (eventId: string) => void;
  clearEvents: () => void;
  getEventsBySource: (source: EventSource) => SystemEvent[];
  getEventsBySeverity: (severity: EventSeverity) => SystemEvent[];
  getUnresolvedEvents: () => SystemEvent[];
  markEventsAsRead: () => void;
  setMaxEvents: (max: number) => void;
}

export const useEventStore = create<EventStoreState>((set, get) => ({
  events: [],
  eventCount: 0,
  unreadCount: 0,
  maxEvents: 1000,

  addEvent: (event: Omit<SystemEvent, 'id' | 'timestamp'>) => {
    set((state) => {
      const newEvent: SystemEvent = {
        ...event,
        id: `EVT-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: Date.now(),
      };

      const events = [newEvent, ...state.events].slice(0, state.maxEvents);
      
      return {
        events,
        eventCount: state.eventCount + 1,
        unreadCount: state.unreadCount + 1,
      };
    });
  },

  resolveEvent: (eventId: string) => {
    set((state) => {
      const events = state.events.map((e) =>
        e.id === eventId ? { ...e, resolved: true, resolvedAt: Date.now() } : e
      );
      return { events };
    });
  },

  clearEvents: () => {
    set({ events: [], eventCount: 0, unreadCount: 0 });
  },

  getEventsBySource: (source: EventSource) => {
    const { events } = get();
    return events.filter((e) => e.source === source);
  },

  getEventsBySeverity: (severity: EventSeverity) => {
    const { events } = get();
    return events.filter((e) => e.severity === severity);
  },

  getUnresolvedEvents: () => {
    const { events } = get();
    return events.filter((e) => !e.resolved);
  },

  markEventsAsRead: () => {
    set({ unreadCount: 0 });
  },

  setMaxEvents: (max: number) => {
    set({ maxEvents: max });
  },
}));
