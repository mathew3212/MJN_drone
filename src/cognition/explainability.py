"""
Explainable AI Decision Logging
================================

Every decision made by the system is recorded with a full explanation
of WHY it was chosen, WHAT evidence supported it, and HOW confident
the system was. This module provides transparent, traceable decision
logging for accountability and debugging.

Key Features:
    - Full decision traceability with timestamps
    - Multi-level explanations (summary, detailed, technical)
    - Evidence tracking for each decision
    - Confidence and uncertainty records
    - Decision tree reconstruction
    - Queryable decision history
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set


class DecisionCategory(Enum):
    """Categories of decisions made by the system."""
    NAVIGATION = "navigation"
    PATH_PLANNING = "path_planning"
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"
    MISSION_CONTROL = "mission_control"
    EMERGENCY = "emergency"
    EXPLORATION = "exploration"
    RESOURCE_MANAGEMENT = "resource_management"
    SENSOR_PROCESSING = "sensor_processing"
    BELIEF_UPDATE = "belief_update"
    ADAPTATION = "adaptation"
    LEARNING = "learning"


class ExplanationLevel(Enum):
    """Levels of explanation detail."""
    SUMMARY = "summary"          # One-line summary
    DETAILED = "detailed"        # Human-readable explanation
    TECHNICAL = "technical"      # Full technical details
    TRACE = "trace"              # Complete trace with all inputs


@dataclass
class Explanation:
    """A structured explanation for a decision."""
    level: ExplanationLevel
    content: str
    evidence: List[str] = field(default_factory=list)
    reasoning_chain: List[str] = field(default_factory=list)
    confidence: float = 1.0
    alternatives_considered: List[str] = field(default_factory=list)
    rejection_reasons: Dict[str, str] = field(default_factory=dict)

    def to_text(self) -> str:
        parts = [self.content]
        if self.evidence:
            parts.append(f"Evidence: {'; '.join(self.evidence)}")
        if self.reasoning_chain:
            parts.append(f"Reasoning: {' -> '.join(self.reasoning_chain)}")
        parts.append(f"Confidence: {self.confidence:.1%}")
        if self.rejection_reasons:
            rejected = "; ".join(f"{k}: {v}" for k, v in self.rejection_reasons.items())
            parts.append(f"Rejected alternatives: {rejected}")
        return " | ".join(parts)


@dataclass
class DecisionRecord:
    """Complete record of a single decision."""
    decision_id: str
    timestamp: float
    category: DecisionCategory
    decision: str
    explanation: Explanation
    inputs: Dict[str, Any] = field(default_factory=dict)
    output: Any = None
    subsystem: str = "cognitive"
    parent_decision_id: Optional[str] = None
    child_decisions: List[str] = field(default_factory=list)
    outcome: Optional[str] = None  # Set after execution
    outcome_timestamp: Optional[float] = None

    def get_age(self) -> float:
        return time.time() - self.timestamp

    def record_outcome(self, outcome: str):
        self.outcome = outcome
        self.outcome_timestamp = time.time()

    def was_successful(self) -> Optional[bool]:
        if self.outcome is None:
            return None
        return self.outcome in ("success", "completed", "achieved")


class ExplainableAILogger:
    """
    Comprehensive decision logging system that ensures every
    decision is traceable with full explanation.
    """

    def __init__(self, max_records: int = 5000):
        self.max_records = max_records
        self._decisions: Dict[str, DecisionRecord] = {}
        self._decision_counter = 0
        self._decision_tree: Dict[str, List[str]] = {}
        self._category_counts: Dict[str, int] = {}
        self._recent_outcomes: List[Tuple[str, bool]] = []

    # ==========================================
    # Decision Logging
    # ==========================================

    def log_decision(self, category: DecisionCategory,
                     decision: str,
                     explanation: str,
                     evidence: Optional[List[str]] = None,
                     reasoning_chain: Optional[List[str]] = None,
                     confidence: float = 1.0,
                     alternatives: Optional[List[str]] = None,
                     rejection_reasons: Optional[Dict[str, str]] = None,
                     inputs: Optional[Dict[str, Any]] = None,
                     output: Any = None,
                     subsystem: str = "cognitive",
                     parent_decision_id: Optional[str] = None,
                     level: ExplanationLevel = ExplanationLevel.DETAILED
                     ) -> str:
        """
        Log a decision with full explanation.
        Returns the decision_id for tracking.
        """
        self._decision_counter += 1
        decision_id = f"dec_{self._decision_counter}_{int(time.time() * 1000) % 10000}"

        explanation_obj = Explanation(
            level=level,
            content=explanation,
            evidence=evidence or [],
            reasoning_chain=reasoning_chain or [],
            confidence=confidence,
            alternatives_considered=alternatives or [],
            rejection_reasons=rejection_reasons or {},
        )

        record = DecisionRecord(
            decision_id=decision_id,
            timestamp=time.time(),
            category=category,
            decision=decision,
            explanation=explanation_obj,
            inputs=inputs or {},
            output=output,
            subsystem=subsystem,
            parent_decision_id=parent_decision_id,
        )

        self._decisions[decision_id] = record

        # Track parent-child relationship
        if parent_decision_id and parent_decision_id in self._decision_tree:
            self._decision_tree[parent_decision_id].append(decision_id)
        self._decision_tree[decision_id] = []

        # Track category counts
        cat_key = category.value
        self._category_counts[cat_key] = self._category_counts.get(cat_key, 0) + 1

        # Enforce capacity
        if len(self._decisions) > self.max_records:
            self._prune_old_records()

        return decision_id

    def log_navigation_decision(self, action: str, reason: str,
                                 confidence: float,
                                 position: Tuple[float, float],
                                 goal: Optional[Tuple[float, float]] = None,
                                 **kwargs) -> str:
        """Convenience: log a navigation decision."""
        evidence = [
            f"Position: {position}",
            f"Goal: {goal}" if goal else "No active goal",
        ]
        evidence.extend(kwargs.get("evidence", []))

        return self.log_decision(
            category=DecisionCategory.NAVIGATION,
            decision=action,
            explanation=reason,
            confidence=confidence,
            evidence=evidence,
            reasoning_chain=kwargs.get("chain", ["sensed_environment", "evaluated_options", "selected_action"]),
            inputs={"position": position, "goal": goal, **kwargs.get("inputs", {})},
            level=kwargs.get("level", ExplanationLevel.DETAILED),
        )

    def log_emergency_decision(self, action: str, threat: str,
                                urgency: float, **kwargs) -> str:
        """Convenience: log an emergency decision."""
        return self.log_decision(
            category=DecisionCategory.EMERGENCY,
            decision=action,
            explanation=f"Emergency action '{action}' due to {threat}",
            confidence=max(0.5, 1.0 - urgency * 0.5),
            evidence=[f"Threat: {threat}", f"Urgency: {urgency:.2f}"],
            reasoning_chain=["detected_emergency", "assessed_threat", "selected_emergency_response"],
            level=ExplanationLevel.DETAILED,
            **kwargs,
        )

    def log_belief_update(self, variable: str, prior: float,
                           posterior: float, evidence_source: str,
                           **kwargs) -> str:
        """Convenience: log a belief update."""
        change = posterior - prior
        direction = "increased" if change > 0 else "decreased"
        return self.log_decision(
            category=DecisionCategory.BELIEF_UPDATE,
            decision=f"Update {variable}: {prior:.3f} -> {posterior:.3f}",
            explanation=(
                f"Belief in '{variable}' {direction} by {abs(change):.3f} "
                f"based on evidence from '{evidence_source}'"
            ),
            confidence=1.0 - abs(change),
            evidence=[f"Prior: {prior:.3f}", f"Source: {evidence_source}"],
            reasoning_chain=["received_evidence", "applied_bayesian_update", "propagated_beliefs"],
            inputs={"variable": variable, "prior": prior, "posterior": posterior, "source": evidence_source},
            level=ExplanationLevel.DETAILED,
            **kwargs,
        )

    def log_adaptation(self, adaptation_type: str, reason: str,
                        old_plan: str, new_plan: str,
                        confidence: float = 0.8, **kwargs) -> str:
        """Convenience: log a plan adaptation."""
        return self.log_decision(
            category=DecisionCategory.ADAPTATION,
            decision=f"Adapt: {old_plan} -> {new_plan}",
            explanation=f"Plan adapted ({adaptation_type}): {reason}",
            confidence=confidence,
            evidence=[f"Old plan: {old_plan}", f"New plan: {new_plan}"],
            reasoning_chain=["detected_need_for_adaptation", "evaluated_alternatives", "applied_adaptation"],
            level=ExplanationLevel.DETAILED,
            **kwargs,
        )

    # ==========================================
    # Decision Tracking
    # ==========================================

    def record_outcome(self, decision_id: str, outcome: str):
        """Record the outcome of a decision."""
        if decision_id in self._decisions:
            self._decisions[decision_id].record_outcome(outcome)
            self._recent_outcomes.append(
                (decision_id, outcome in ("success", "completed", "achieved"))
            )
            if len(self._recent_outcomes) > 200:
                self._recent_outcomes.pop(0)

    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        return self._decisions.get(decision_id)

    def get_recent_decisions(self, n: int = 10,
                              category: Optional[DecisionCategory] = None
                              ) -> List[DecisionRecord]:
        records = list(self._decisions.values())
        if category:
            records = [r for r in records if r.category == category]
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:n]

    def get_decision_children(self, decision_id: str) -> List[DecisionRecord]:
        child_ids = self._decision_tree.get(decision_id, [])
        return [self._decisions[cid] for cid in child_ids if cid in self._decisions]

    def get_decision_trail(self, decision_id: str) -> List[DecisionRecord]:
        """Get the full chain of decisions leading to this one."""
        trail = []
        current_id = decision_id
        while current_id and current_id in self._decisions:
            trail.append(self._decisions[current_id])
            current_id = self._decisions[current_id].parent_decision_id
        trail.reverse()
        return trail

    # ==========================================
    # Explanation Generation
    # ==========================================

    def explain_recent(self, n: int = 5,
                        level: ExplanationLevel = ExplanationLevel.DETAILED
                        ) -> List[str]:
        """Generate explanations for recent decisions."""
        recent = self.get_recent_decisions(n)
        explanations = []
        for record in recent:
            if level == ExplanationLevel.SUMMARY:
                explanations.append(
                    f"[{record.category.value}] {record.decision} "
                    f"(confidence: {record.explanation.confidence:.0%})"
                )
            elif level == ExplanationLevel.DETAILED:
                explanations.append(record.explanation.to_text())
            else:
                explanations.append(
                    f"#{record.decision_id} [{record.category.value}] "
                    f"{record.explanation.to_text()}"
                )
        return explanations

    def explain_decision(self, decision_id: str,
                          level: ExplanationLevel = ExplanationLevel.TECHNICAL
                          ) -> Optional[str]:
        """Get full explanation for a specific decision."""
        record = self._decisions.get(decision_id)
        if record is None:
            return None

        parts = [
            f"Decision: {record.decision}",
            f"Category: {record.category.value}",
            f"Time: {record.timestamp}",
            f"Subsystem: {record.subsystem}",
            f"Explanation: {record.explanation.to_text()}",
        ]
        if record.outcome:
            parts.append(f"Outcome: {record.outcome}")
        if record.child_decisions:
            parts.append(f"Child decisions: {len(record.child_decisions)}")
        if level == ExplanationLevel.TRACE:
            parts.append(f"Inputs: {record.inputs}")
            parts.append(f"Output: {record.output}")

        return "\n".join(parts)

    # ==========================================
    # Analytics
    # ==========================================

    def get_success_rate(self) -> float:
        outcomes = [(did, ok) for did, ok in self._recent_outcomes]
        if not outcomes:
            return 0.5
        successes = sum(1 for _, ok in outcomes if ok)
        return successes / len(outcomes)

    def get_statistics(self) -> Dict[str, Any]:
        records = list(self._decisions.values())
        outcomes = [r for r in records if r.outcome is not None]
        successes = [r for r in outcomes if r.was_successful()]

        return {
            "total_decisions": len(records),
            "category_counts": dict(self._category_counts),
            "total_with_outcomes": len(outcomes),
            "success_rate": len(successes) / max(1, len(outcomes)),
            "avg_confidence": (
                sum(r.explanation.confidence for r in records) / max(1, len(records))
            ),
            "recent_outcomes": len(self._recent_outcomes),
        }

    def _prune_old_records(self):
        records = sorted(self._decisions.values(), key=lambda r: r.timestamp)
        to_remove = len(records) - self.max_records // 2
        for record in records[:to_remove]:
            del self._decisions[record.decision_id]
            self._decision_tree.pop(record.decision_id, None)

    def __repr__(self) -> str:
        return (f"ExplainableAILogger(decisions={len(self._decisions)}, "
                f"success_rate={self.get_success_rate():.0%})")