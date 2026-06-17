"""
Event Bus — Asynchronous Event-Driven Architecture
====================================================
Central publish/subscribe system enabling loose coupling between
all subsystems. Supports:

  - Topic-based publish/subscribe
  - Typed events with metadata
  - Event history and replay
  - Wildcard subscriptions
  - Priority queues
  - Event filtering

No subsystem directly depends on another — all communication
flows through the event bus.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict
from enum import Enum, auto
import threading


class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """A system event with metadata."""
    topic: str
    data: Any = None
    source: str = ""
    priority: EventPriority = EventPriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    event_id: int = 0

    _next_id: int = 0

    def __post_init__(self):
        Event._next_id += 1
        self.event_id = Event._next_id


class EventBus:
    """
    Central event bus for the autonomous system.
    
    Usage:
        bus = EventBus()
        bus.subscribe("drone.battery.low", my_handler)
        bus.publish("drone.battery.low", {"drone_id": 1, "level": 15})
    """

    def __init__(self, max_history: int = 10000):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._wildcard_subscribers: List[Callable] = []
        self._event_history: List[Event] = []
        self._max_history = max_history
        self._event_counter: int = 0
        self._lock = threading.Lock()
        self._enabled: bool = True

    def subscribe(self, topic: str, callback: Callable[[Event], None]):
        """Subscribe to a topic. Use '#' for wildcard."""
        if topic == '#':
            self._wildcard_subscribers.append(callback)
        else:
            self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable):
        """Remove a subscription."""
        if topic == '#':
            self._wildcard_subscribers = [
                c for c in self._wildcard_subscribers if c != callback
            ]
        elif topic in self._subscribers:
            self._subscribers[topic] = [
                c for c in self._subscribers[topic] if c != callback
            ]

    def publish(self, topic: str, data: Any = None, source: str = "",
                priority: EventPriority = EventPriority.NORMAL):
        """Publish an event to all subscribers of the topic."""
        if not self._enabled:
            return

        self._event_counter += 1
        event = Event(
            topic=topic, data=data, source=source,
            priority=priority, event_id=self._event_counter,
        )

        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]

        # Notify topic-specific subscribers
        callbacks = list(self._subscribers.get(topic, []))
        # Notify wildcard subscribers
        callbacks.extend(self._wildcard_subscribers)

        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                pass  # Silently handle subscriber errors

    def get_history(self, topic_filter: Optional[str] = None,
                    limit: int = 100) -> List[Event]:
        """Get recent events, optionally filtered by topic."""
        with self._lock:
            if topic_filter:
                return [
                    e for e in self._event_history
                    if e.topic.startswith(topic_filter)
                ][-limit:]
            return list(self._event_history[-limit:])

    def clear_history(self):
        """Clear event history."""
        with self._lock:
            self._event_history.clear()

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    @property
    def event_count(self) -> int:
        return self._event_counter

    @property
    def subscriber_count(self) -> int:
        total = len(self._wildcard_subscribers)
        for subs in self._subscribers.values():
            total += len(subs)
        return total


# ── Global singleton ─────────────────────────────────────────────────────────
_global_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus singleton."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus