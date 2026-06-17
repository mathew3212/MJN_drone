"""
Mission Context Understanding
==============================

Deep understanding of mission goals, constraints, and situational
awareness. Maintains a rich model of the mission that enables
intelligent decision-making aligned with objectives.
"""

import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set


class MissionPhase(Enum):
    INITIALIZATION = "initialization"
    NAVIGATION = "navigation"
    INSPECTION = "inspection"
    RETURN_HOME = "return_home"
    EMERGENCY = "emergency"
    EXPLORATION = "exploration"
    COMPLETE = "complete"


class ThreatLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MissionGoal:
    """A specific mission objective."""
    goal_id: str
    description: str
    target_position: Tuple[float, float]
    priority: int = 1
    status: str = "pending"  # pending, active, completed, failed
    deadline: Optional[float] = None
    constraints: List[str] = field(default_factory=list)
    progress: float = 0.0

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def is_complete(self) -> bool:
        return self.status == "completed"


@dataclass
class MissionConstraint:
    """A constraint on mission execution."""
    constraint_id: str
    name: str
    description: str
    constraint_type: str  # "battery", "time", "geofence", "payload", "weather"
    value: float
    current_value: float = 0.0
    active: bool = True

    @property
    def is_satisfied(self) -> bool:
        if self.constraint_type == "battery":
            return self.current_value > self.value
        return self.current_value <= self.value

    @property
    def margin(self) -> float:
        return abs(self.current_value - self.value) / max(abs(self.value), 0.01)


@dataclass
class SituationalAssessment:
    """Assessment of current situation."""
    threat_level: ThreatLevel
    terrain_risk: float
    weather_risk: float
    battery_risk: float
    time_pressure: float
    mission_proximity: float
    overall_risk: float
    recommended_phase: MissionPhase
    explanation: str = ""

    def compute_overall(self):
        self.overall_risk = (
            0.3 * self.terrain_risk +
            0.1 * self.weather_risk +
            0.3 * self.battery_risk +
            0.2 * self.time_pressure +
            0.1 * (1.0 - self.mission_proximity)
        )


class MissionContextManager:
    """
    Maintains deep understanding of the mission context including
    goals, constraints, situational awareness, and progress tracking.
    """

    def __init__(self):
        self._goals: Dict[str, MissionGoal] = {}
        self._constraints: Dict[str, MissionConstraint] = {}
        self._phase = MissionPhase.INITIALIZATION
        self._phase_history: List[Tuple[MissionPhase, float]] = []
        self._assessment: Optional[SituationalAssessment] = None
        self._context_data: Dict[str, Any] = {}
        self._event_log: List[Tuple[float, str, Dict]] = []

    def add_goal(self, goal: MissionGoal):
        self._goals[goal.goal_id] = goal

    def add_constraint(self, constraint: MissionConstraint):
        self._constraints[constraint.constraint_id] = constraint

    def set_phase(self, phase: MissionPhase):
        if phase != self._phase:
            self._phase_history.append((self._phase, time.time()))
            self._phase = phase

    def assess_situation(self, drone_position: Tuple[float, float],
                         target_position: Tuple[float, float],
                         battery_level: float,
                         obstacles_nearby: int,
                         mission_elapsed: float) -> SituationalAssessment:
        dist_to_target = math.sqrt(
            (drone_position[0] - target_position[0]) ** 2 +
            (drone_position[1] - target_position[1]) ** 2
        )

        terrain_risk = min(1.0, obstacles_nearby * 0.15)
        weather_risk = self._context_data.get("weather_risk", 0.0)
        battery_risk = max(0.0, 1.0 - battery_level)
        time_pressure = min(1.0, mission_elapsed / 300.0)
        mission_proximity = max(0.0, 1.0 - dist_to_target / 50.0)

        if battery_level < 0.15:
            threat = ThreatLevel.CRITICAL
            recommended = MissionPhase.EMERGENCY
        elif battery_level < 0.3 or obstacles_nearby > 5:
            threat = ThreatLevel.HIGH
            recommended = MissionPhase.RETURN_HOME
        elif dist_to_target < 1.5:
            threat = ThreatLevel.NONE
            recommended = MissionPhase.INSPECTION
        else:
            threat = ThreatLevel.LOW
            recommended = MissionPhase.NAVIGATION

        assessment = SituationalAssessment(
            threat_level=threat, terrain_risk=terrain_risk,
            weather_risk=weather_risk, battery_risk=battery_risk,
            time_pressure=time_pressure, mission_proximity=mission_proximity,
            overall_risk=0.0, recommended_phase=recommended,
        )
        assessment.compute_overall()

        explanation_parts = []
        if battery_risk > 0.5:
            explanation_parts.append(f"Battery critical ({battery_level:.0%})")
        if terrain_risk > 0.5:
            explanation_parts.append(f"High obstacle density ({obstacles_nearby})")
        if mission_proximity > 0.8:
            explanation_parts.append("Near target")
        assessment.explanation = "; ".join(explanation_parts) if explanation_parts else "Normal operations"

        self._assessment = assessment
        return assessment

    def get_next_goal(self) -> Optional[MissionGoal]:
        active = [g for g in self._goals.values() if g.is_active]
        if active:
            return max(active, key=lambda g: g.priority)
        pending = [g for g in self._goals.values() if g.status == "pending"]
        if pending:
            return max(pending, key=lambda g: g.priority)
        return None

    def update_progress(self, drone_position: Tuple[float, float]):
        for goal in self._goals.values():
            if goal.status == "active":
                dist = math.sqrt(
                    (drone_position[0] - goal.target_position[0]) ** 2 +
                    (drone_position[1] - goal.target_position[1]) ** 2
                )
                goal.progress = max(0, 1.0 - dist / 50.0)
                if dist < 1.5:
                    goal.status = "completed"

    def check_constraints(self) -> List[MissionConstraint]:
        return [c for c in self._constraints.values() if c.active and not c.is_satisfied]

    def update_constraint(self, constraint_id: str, current_value: float):
        if constraint_id in self._constraints:
            self._constraints[constraint_id].current_value = current_value

    def log_event(self, event_type: str, data: Optional[Dict] = None):
        self._event_log.append((time.time(), event_type, data or {}))
        if len(self._event_log) > 200:
            self._event_log.pop(0)

    def set_context(self, key: str, value: Any):
        self._context_data[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self._context_data.get(key, default)

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "phase": self._phase.value,
            "goals": {gid: {"status": g.status, "progress": g.progress}
                     for gid, g in self._goals.items()},
            "violated_constraints": [c.name for c in self.check_constraints()],
            "threat_level": self._assessment.threat_level.value if self._assessment else "unknown",
            "overall_risk": self._assessment.overall_risk if self._assessment else 0,
        }

    def __repr__(self) -> str:
        return f"MissionContextManager(phase={self._phase.value}, goals={len(self._goals)})"