"""
Professional Mission Management System
========================================
Supports:
  - Mission queue with priorities
  - Mission dependencies
  - Scheduling and retries
  - Checkpoints and resume
  - Mission rollback
  - Emergency interruption
  - Multiple simultaneous missions
  - Procedural mission generation
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Callable
from enum import Enum, auto

from .event_bus import get_event_bus, Event, EventPriority


class MissionType(Enum):
    PARCEL_DELIVERY = auto()
    INSPECTION = auto()
    MAPPING = auto()
    SEARCH = auto()
    SURVEILLANCE = auto()
    EMERGENCY_RESPONSE = auto()
    WAREHOUSE_LOGISTICS = auto()
    BRIDGE_INSPECTION = auto()
    SOLAR_FARM_INSPECTION = auto()
    PIPELINE_INSPECTION = auto()
    CUSTOM = auto()


class MissionState(Enum):
    QUEUED = auto()
    PLANNING = auto()
    EXECUTING = auto()
    PAUSED = auto()
    CHECKPOINT = auto()
    RETURNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    RETRYING = auto()


@dataclass
class MissionCheckpoint:
    """A saved state point for mission resume."""
    step: int
    drone_position: Tuple[float, float]
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Mission:
    """A complete mission definition."""
    mission_id: str = ""
    name: str = ""
    mission_type: MissionType = MissionType.CUSTOM
    priority: int = 5  # 0=highest, 9=lowest
    state: MissionState = MissionState.QUEUED
    start_pos: Tuple[float, float] = (5, 5)
    target_pos: Tuple[float, float] = (90, 90)
    waypoints: List[Tuple[float, float]] = field(default_factory=list)
    assigned_drone_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    max_retries: int = 3
    retry_count: int = 0
    checkpoints: List[MissionCheckpoint] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    timeout_seconds: float = 300.0

    @property
    def elapsed(self) -> float:
        if self.started_at:
            return time.time() - self.started_at
        return 0.0

    @property
    def is_active(self) -> bool:
        return self.state in (
            MissionState.EXECUTING,
            MissionState.PLANNING,
            MissionState.CHECKPOINT,
            MissionState.RETURNING,
            MissionState.PAUSED,
        )

    def save_checkpoint(self, step: int, position: Tuple[float, float],
                        data: Dict = None):
        cp = MissionCheckpoint(step=step, drone_position=position, data=data or {})
        self.checkpoints.append(cp)

    def get_last_checkpoint(self) -> Optional[MissionCheckpoint]:
        return self.checkpoints[-1] if self.checkpoints else None


class MissionEngine:
    """
    Professional mission management engine.
    
    Handles queuing, scheduling, execution, retries,
    checkpoints, and multi-mission support.
    """

    def __init__(self):
        self.bus = get_event_bus()
        self.missions: Dict[str, Mission] = {}
        self.mission_queue: List[str] = []  # sorted by priority
        self.mission_history: List[Mission] = []
        self.completed_count: int = 0
        self.failed_count: int = 0

    def create_mission(self, name: str, mission_type: MissionType,
                       start: Tuple[float, float], target: Tuple[float, float],
                       priority: int = 5, waypoints: List = None,
                       payload: Dict = None, dependencies: List[str] = None) -> Mission:
        """Create and queue a new mission."""
        mid = str(uuid.uuid4())[:8]
        mission = Mission(
            mission_id=mid, name=name,
            mission_type=mission_type,
            priority=priority,
            start_pos=start, target_pos=target,
            waypoints=waypoints or [],
            payload=payload or {},
            dependencies=dependencies or [],
        )
        self.missions[mid] = mission
        self._enqueue(mid)

        self.bus.publish("mission.created", {
            "mission_id": mid, "name": name,
            "type": mission_type.name, "priority": priority,
        })

        return mission

    def assign_mission(self, mission_id: str, drone_id: str) -> bool:
        """Assign a mission to a drone."""
        mission = self.missions.get(mission_id)
        if not mission or mission.state != MissionState.QUEUED:
            return False

        # Check dependencies
        for dep_id in mission.dependencies:
            dep = self.missions.get(dep_id)
            if dep and dep.state != MissionState.COMPLETED:
                return False

        mission.assigned_drone_id = drone_id
        mission.state = MissionState.PLANNING
        mission.started_at = time.time()

        self.bus.publish("mission.assigned", {
            "mission_id": mission_id,
            "drone_id": drone_id,
        })

        return True

    def start_mission(self, mission_id: str):
        """Start executing a mission."""
        mission = self.missions.get(mission_id)
        if mission and mission.state == MissionState.PLANNING:
            mission.state = MissionState.EXECUTING
            self.bus.publish("mission.started", {
                "mission_id": mission_id,
            })

    def complete_mission(self, mission_id: str, result: Dict = None):
        """Mark a mission as completed."""
        mission = self.missions.get(mission_id)
        if mission:
            mission.state = MissionState.COMPLETED
            mission.completed_at = time.time()
            mission.result = result or {}
            self.completed_count += 1
            if mission_id in self.mission_queue:
                self.mission_queue.remove(mission_id)
            self.mission_history.append(mission)
            self.bus.publish("mission.completed", {
                "mission_id": mission_id,
                "elapsed": mission.elapsed,
            })

    def fail_mission(self, mission_id: str, reason: str = ""):
        """Mark a mission as failed, with retry logic."""
        mission = self.missions.get(mission_id)
        if not mission:
            return

        mission.retry_count += 1
        if mission.retry_count <= mission.max_retries:
            mission.state = MissionState.RETRYING
            self.bus.publish("mission.retry", {
                "mission_id": mission_id,
                "attempt": mission.retry_count,
                "max": mission.max_retries,
            })
            # Re-queue
            mission.state = MissionState.QUEUED
            self._enqueue(mission_id)
        else:
            mission.state = MissionState.FAILED
            mission.result = {"error": reason}
            self.failed_count += 1
            self.mission_history.append(mission)
            self.bus.publish("mission.failed", {
                "mission_id": mission_id,
                "reason": reason,
                "retries": mission.retry_count,
            })

    def cancel_mission(self, mission_id: str):
        """Cancel a mission."""
        mission = self.missions.get(mission_id)
        if mission and mission.is_active:
            mission.state = MissionState.CANCELLED
            if mission_id in self.mission_queue:
                self.mission_queue.remove(mission_id)
            self.bus.publish("mission.cancelled", {
                "mission_id": mission_id,
            })

    def pause_mission(self, mission_id: str):
        """Pause a mission."""
        mission = self.missions.get(mission_id)
        if mission and mission.state == MissionState.EXECUTING:
            mission.state = MissionState.PAUSED
            self.bus.publish("mission.paused", {"mission_id": mission_id})

    def resume_mission(self, mission_id: str):
        """Resume a paused mission."""
        mission = self.missions.get(mission_id)
        if mission and mission.state == MissionState.PAUSED:
            mission.state = MissionState.EXECUTING
            self.bus.publish("mission.resumed", {"mission_id": mission_id})

    def checkpoint(self, mission_id: str, step: int, position: Tuple[float, float]):
        """Save a checkpoint."""
        mission = self.missions.get(mission_id)
        if mission:
            mission.save_checkpoint(step, position)
            self.bus.publish("mission.checkpoint", {
                "mission_id": mission_id, "step": step,
            })

    def rollback(self, mission_id: str) -> bool:
        """Rollback to the last checkpoint."""
        mission = self.missions.get(mission_id)
        if mission and mission.checkpoints:
            cp = mission.get_last_checkpoint()
            mission.state = MissionState.CHECKPOINT
            self.bus.publish("mission.rollback", {
                "mission_id": mission_id,
                "checkpoint_step": cp.step,
            })
            return True
        return False

    def get_next_mission(self) -> Optional[Mission]:
        """Get the highest priority queued mission."""
        for mid in self.mission_queue:
            mission = self.missions.get(mid)
            if mission and mission.state == MissionState.QUEUED:
                # Check dependencies
                deps_met = True
                for dep_id in mission.dependencies:
                    dep = self.missions.get(dep_id)
                    if dep and dep.state != MissionState.COMPLETED:
                        deps_met = False
                        break
                if deps_met:
                    return mission
        return None

    def generate_delivery_mission(self, start: Tuple[float, float],
                                   target: Tuple[float, float]) -> Mission:
        """Generate a procedural delivery mission."""
        return self.create_mission(
            name=f"Delivery to ({target[0]:.0f},{target[1]:.0f})",
            mission_type=MissionType.PARCEL_DELIVERY,
            start=start, target=target,
            priority=5,
            payload={"type": "parcel", "weight": 0.3},
        )

    def generate_inspection_mission(self, target: Tuple[float, float]) -> Mission:
        """Generate a procedural inspection mission."""
        return self.create_mission(
            name=f"Inspection at ({target[0]:.0f},{target[1]:.0f})",
            mission_type=MissionType.INSPECTION,
            start=target, target=target,
            priority=3,
            payload={"inspection_type": "structural"},
        )

    def generate_mapping_mission(self, center: Tuple[float, float],
                                  radius: float = 30) -> Mission:
        """Generate a procedural mapping mission."""
        import math
        wps = []
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            x = center[0] + radius * math.cos(rad)
            y = center[1] + radius * math.sin(rad)
            wps.append((x, y))

        return self.create_mission(
            name=f"Mapping area around ({center[0]:.0f},{center[1]:.0f})",
            mission_type=MissionType.MAPPING,
            start=center, target=center,
            priority=7,
            waypoints=wps,
        )

    def generate_emergency_mission(self, position: Tuple[float, float]) -> Mission:
        """Generate an emergency response mission."""
        return self.create_mission(
            name=f"Emergency at ({position[0]:.0f},{position[1]:.0f})",
            mission_type=MissionType.EMERGENCY_RESPONSE,
            start=(5, 5), target=position,
            priority=0,
            max_retries=0,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get mission statistics."""
        return {
            "total": len(self.missions),
            "queued": sum(1 for m in self.missions.values()
                         if m.state == MissionState.QUEUED),
            "active": sum(1 for m in self.missions.values() if m.is_active),
            "completed": self.completed_count,
            "failed": self.failed_count,
            "queue_length": len(self.mission_queue),
        }

    def _enqueue(self, mission_id: str):
        """Add mission to priority queue."""
        if mission_id not in self.mission_queue:
            self.mission_queue.append(mission_id)
            self.mission_queue.sort(
                key=lambda mid: self.missions[mid].priority
            )