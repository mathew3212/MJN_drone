"""
Data Recording System
======================
Automatically records:
  - Mission telemetry
  - AI decisions
  - Cognitive state
  - Planning history
  - Controller outputs
  - Performance metrics
  - Sensor data

Supports instant replay and analysis.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

from .event_bus import get_event_bus


@dataclass
class TelemetryRecord:
    """A single telemetry data point."""
    timestamp: float
    frame: int
    drone_id: str
    x: float
    y: float
    altitude: float
    heading: float
    speed: float
    battery: float
    status: str
    mission_state: str
    behavior_state: str


@dataclass
class DecisionRecord:
    """An AI decision record."""
    timestamp: float
    frame: int
    drone_id: str
    decision_type: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    confidence: float


@dataclass
class PlanningRecord:
    """A planning history record."""
    timestamp: float
    frame: int
    drone_id: str
    planner: str
    path_length: int
    path_cost: float
    replan_reason: str


class DataRecorder:
    """
    Records all simulation data for replay and analysis.
    """

    def __init__(self, max_records: int = 50000):
        self.bus = get_event_bus()
        self.max_records = max_records

        self.telemetry: List[TelemetryRecord] = []
        self.decisions: List[DecisionRecord] = []
        self.planning: List[PlanningRecord] = []
        self.events: List[Dict] = []

        self._frame: int = 0
        self._start_time: float = time.time()

        # Subscribe to events
        self.bus.subscribe("#", self._on_event)

    def _on_event(self, event):
        """Capture all events."""
        self.events.append({
            "timestamp": event.timestamp,
            "topic": event.topic,
            "source": event.source,
            "data": event.data,
        })
        if len(self.events) > self.max_records:
            self.events = self.events[-self.max_records:]

    def record_telemetry(self, drone_id: str, x: float, y: float,
                          altitude: float, heading: float, speed: float,
                          battery: float, status: str,
                          mission_state: str, behavior_state: str):
        """Record telemetry data."""
        record = TelemetryRecord(
            timestamp=time.time() - self._start_time,
            frame=self._frame, drone_id=drone_id,
            x=x, y=y, altitude=altitude,
            heading=heading, speed=speed,
            battery=battery, status=status,
            mission_state=mission_state,
            behavior_state=behavior_state,
        )
        self.telemetry.append(record)
        if len(self.telemetry) > self.max_records:
            self.telemetry = self.telemetry[-self.max_records:]

    def record_decision(self, drone_id: str, decision_type: str,
                         input_data: Dict, output_data: Dict,
                         confidence: float = 1.0):
        """Record an AI decision."""
        record = DecisionRecord(
            timestamp=time.time() - self._start_time,
            frame=self._frame, drone_id=drone_id,
            decision_type=decision_type,
            input_data=input_data, output_data=output_data,
            confidence=confidence,
        )
        self.decisions.append(record)
        if len(self.decisions) > self.max_records:
            self.decisions = self.decisions[-self.max_records:]

    def record_planning(self, drone_id: str, planner: str,
                         path_length: int, path_cost: float,
                         replan_reason: str = ""):
        """Record a planning event."""
        record = PlanningRecord(
            timestamp=time.time() - self._start_time,
            frame=self._frame, drone_id=drone_id,
            planner=planner, path_length=path_length,
            path_cost=path_cost, replan_reason=replan_reason,
        )
        self.planning.append(record)
        if len(self.planning) > self.max_records:
            self.planning = self.planning[-self.max_records:]

    def advance_frame(self):
        """Advance the frame counter."""
        self._frame += 1

    def get_replay_window(self, start_frame: int, end_frame: int) -> Dict:
        """Get data for a replay window."""
        return {
            "telemetry": [
                t for t in self.telemetry
                if start_frame <= t.frame <= end_frame
            ],
            "decisions": [
                d for d in self.decisions
                if start_frame <= d.frame <= end_frame
            ],
            "planning": [
                p for p in self.planning
                if start_frame <= p.frame <= end_frame
            ],
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get recording summary."""
        duration = time.time() - self._start_time
        return {
            "duration_seconds": duration,
            "total_frames": self._frame,
            "telemetry_records": len(self.telemetry),
            "decision_records": len(self.decisions),
            "planning_records": len(self.planning),
            "event_records": len(self.events),
            "fps": self._frame / max(0.1, duration),
        }

    def clear(self):
        """Clear all recorded data."""
        self.telemetry.clear()
        self.decisions.clear()
        self.planning.clear()
        self.events.clear()
        self._frame = 0
        self._start_time = time.time()