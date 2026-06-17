"""
Adaptive Planner
=================

Plans that evolve based on experience, context, and changing conditions.
Combines reactive replanning with deliberative planning, learning from
past plan performance to improve future planning.

Key Features:
    - Multi-strategy planning (reactive, deliberative, hybrid)
    - Plan adaptation based on context changes
    - Performance-based plan refinement
    - Plan quality evaluation
    - Fallback strategies
    - Experience-guided planning
"""

import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


class PlanningStrategy(Enum):
    REACTIVE = "reactive"
    DELIBERATIVE = "deliberative"
    HYBRID = "hybrid"
    EXPERIENCE_GUIDED = "experience_guided"


class PlanStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ADAPTED = "adapted"
    COMPLETED = "completed"
    FAILED = "failed"
    REPLANNING = "replanning"


@dataclass
class PlanStep:
    """A single step in a plan."""
    step_id: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_cost: float = 0.0
    expected_duration: float = 0.0
    preconditions: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, executing, completed, failed
    actual_cost: float = 0.0
    explanation: str = ""

    @property
    def is_done(self) -> bool:
        return self.status in ("completed", "failed")


@dataclass
class Plan:
    """A complete plan consisting of ordered steps."""
    plan_id: str
    name: str
    steps: List[PlanStep] = field(default_factory=list)
    strategy: PlanningStrategy = PlanningStrategy.HYBRID
    status: PlanStatus = PlanStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    current_step: int = 0
    total_cost: float = 0.0
    confidence: float = 1.0
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def active_step(self) -> Optional[PlanStep]:
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    @property
    def progress(self) -> float:
        if not self.steps:
            return 1.0
        completed = sum(1 for s in self.steps if s.status == "completed")
        return completed / len(self.steps)

    @property
    def is_complete(self) -> bool:
        return all(s.is_done for s in self.steps)

    @property
    def remaining_steps(self) -> int:
        return sum(1 for s in self.steps if not s.is_done)

    def advance(self) -> bool:
        """Move to next step. Returns True if plan is complete."""
        if self.current_step < len(self.steps):
            self.steps[self.current_step].status = "completed"
        self.current_step += 1
        return self.current_step >= len(self.steps)


@dataclass
class PlanAdaptation:
    """Record of a plan adaptation."""
    adaptation_id: str
    plan_id: str
    adaptation_type: str  # "replan", "modify_step", "skip_step", "insert_step", "retry_step"
    reason: str
    old_plan_state: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    confidence: float = 0.8
    explanation: str = ""


class AdaptivePlanner:
    """
    Planner that adapts plans based on experience, context changes,
    and performance feedback.
    """

    def __init__(self):
        self._plans: Dict[str, Plan] = {}
        self._plan_history: List[Plan] = []
        self._adaptations: List[PlanAdaptation] = []
        self._strategy = PlanningStrategy.HYBRID

        # Performance tracking per strategy
        self._strategy_performance: Dict[str, Dict[str, float]] = {
            "reactive": {"success": 0, "failure": 0, "avg_cost": 0},
            "deliberative": {"success": 0, "failure": 0, "avg_cost": 0},
            "hybrid": {"success": 0, "failure": 0, "avg_cost": 0},
            "experience_guided": {"success": 0, "failure": 0, "avg_cost": 0},
        }

        # Plan templates learned from experience
        self._templates: Dict[str, List[str]] = {
            "navigate_to_target": ["plan_path", "avoid_obstacles", "reach_target"],
            "return_home": ["plan_path_home", "navigate_home", "land"],
            "inspect_area": ["approach", "scan", "record", "retreat"],
        }

        # Fallback chains
        self._fallbacks: Dict[str, List[str]] = {
            "navigate_to_target": ["replan_with_detour", "explore_alternative", "return_home"],
            "avoid_obstacle": ["go_around", "go_over", "wait_for_clear"],
        }

    # ==========================================
    # Plan Creation
    # ==========================================

    def create_plan(self, name: str, steps: List[PlanStep],
                    strategy: Optional[PlanningStrategy] = None,
                    context: Optional[Dict[str, Any]] = None) -> str:
        """Create a new plan."""
        plan_id = f"plan_{len(self._plans) + len(self._plan_history) + 1}"
        plan = Plan(
            plan_id=plan_id,
            name=name,
            steps=steps,
            strategy=strategy or self._strategy,
            context=context or {},
        )
        self._plans[plan_id] = plan
        return plan_id

    def create_from_template(self, template_name: str,
                              context: Optional[Dict[str, Any]] = None
                              ) -> Optional[str]:
        """Create a plan from a learned template."""
        template = self._templates.get(template_name)
        if not template:
            return None

        steps = [
            PlanStep(
                step_id=f"step_{i}",
                action=action,
                explanation=f"Template step: {action}",
            )
            for i, action in enumerate(template)
        ]
        return self.create_plan(template_name, steps, context=context)

    # ==========================================
    # Plan Execution
    # ==========================================

    def get_current_action(self, plan_id: str) -> Optional[PlanStep]:
        plan = self._plans.get(plan_id)
        if plan and plan.status == PlanStatus.ACTIVE:
            return plan.active_step
        return None

    def complete_step(self, plan_id: str, success: bool = True,
                      actual_cost: float = 0.0) -> bool:
        """Mark current step as completed. Returns True if plan is done."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return True

        step = plan.active_step
        if step:
            step.status = "completed" if success else "failed"
            step.actual_cost = actual_cost
            plan.total_cost += actual_cost

            if not success:
                plan.status = PlanStatus.ADAPTED
                return False

        return plan.advance()

    # ==========================================
    # Plan Adaptation
    # ==========================================

    def adapt_plan(self, plan_id: str, reason: str,
                   adaptation_type: str = "modify_step",
                   new_steps: Optional[List[PlanStep]] = None
                   ) -> Optional[str]:
        """Adapt a plan due to changing conditions."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        old_state = {
            "current_step": plan.current_step,
            "progress": plan.progress,
            "remaining": plan.remaining_steps,
        }

        plan.status = PlanStatus.ADAPTED

        if adaptation_type == "skip_step" and plan.active_step:
            plan.advance()
        elif adaptation_type == "retry_step":
            if plan.active_step:
                plan.active_step.status = "pending"
        elif adaptation_type == "insert_step" and new_steps:
            idx = plan.current_step + 1
            for step in reversed(new_steps):
                plan.steps.insert(idx, step)
        elif adaptation_type == "replan":
            if new_steps:
                plan.steps = new_steps
                plan.current_step = 0
                plan.total_cost = 0.0
            plan.status = PlanStatus.ACTIVE

        adaptation = PlanAdaptation(
            adaptation_id=f"adapt_{len(self._adaptations) + 1}",
            plan_id=plan_id,
            adaptation_type=adaptation_type,
            reason=reason,
            old_plan_state=old_state,
            explanation=f"Plan adapted ({adaptation_type}): {reason}",
        )
        self._adaptations.append(adaptation)

        if adaptation_type == "replan":
            plan.status = PlanStatus.REPLANNING

        return adaptation.adaptation_id

    def should_replan(self, plan_id: str,
                      current_uncertainty: float = 0.5,
                      plan_confidence: float = 0.8,
                      progress: float = 0.0) -> Tuple[bool, str]:
        """Determine if replanning is needed."""
        if current_uncertainty > 0.7:
            return True, f"High uncertainty ({current_uncertainty:.2f}) degrades plan quality"

        if plan_confidence < 0.4:
            return True, f"Low plan confidence ({plan_confidence:.2f})"

        # Check if plan has too many failures
        plan = self._plans.get(plan_id)
        if plan:
            failures = sum(1 for s in plan.steps if s.status == "failed")
            if failures > len(plan.steps) * 0.3:
                return True, f"Too many step failures ({failures}/{len(plan.steps)})"

        return False, "Plan is viable"

    # ==========================================
    # Experience Learning
    # ==========================================

    def record_plan_outcome(self, plan_id: str, success: bool):
        """Record the outcome of a completed plan for learning."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return

        strat = plan.strategy.value
        if strat in self._strategy_performance:
            if success:
                self._strategy_performance[strat]["success"] += 1
            else:
                self._strategy_performance[strat]["failure"] += 1
            total = (self._strategy_performance[strat]["success"] +
                     self._strategy_performance[strat]["failure"])
            if total > 0:
                self._strategy_performance[strat]["avg_cost"] = (
                    (self._strategy_performance[strat]["avg_cost"] * (total - 1) + plan.total_cost) / total
                )

        # Move to history
        if plan_id in self._plans:
            del self._plans[plan_id]
        self._plan_history.append(plan)

        # Learn template from successful plans
        if success and len(plan.steps) > 0:
            template_key = f"{plan.name}_learned"
            actions = [s.action for s in plan.steps]
            self._templates[template_key] = actions

    def select_strategy(self) -> PlanningStrategy:
        """Select the best strategy based on performance."""
        best_strat = PlanningStrategy.HYBRID
        best_score = -1

        for strat_name, perf in self._strategy_performance.items():
            total = perf["success"] + perf["failure"]
            if total == 0:
                score = 0.5  # Default for untried
            else:
                success_rate = perf["success"] / total
                score = success_rate - perf["avg_cost"] * 0.01
            if score > best_score:
                best_score = score
                best_strat = PlanningStrategy(strat_name)

        self._strategy = best_strat
        return best_strat

    def get_fallback(self, plan_id: str, failed_action: str) -> Optional[str]:
        """Get a fallback action for a failed action."""
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        for template_name, fallbacks in self._fallbacks.items():
            if any(s.action == failed_action for s in plan.steps):
                if template_name in self._templates:
                    return fallbacks[0] if fallbacks else None

        return None

    # ==========================================
    # Queries
    # ==========================================

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self._plans.get(plan_id)

    def get_active_plan(self) -> Optional[Plan]:
        for plan in self._plans.values():
            if plan.status in (PlanStatus.ACTIVE, PlanStatus.ADAPTED):
                return plan
        return None

    def get_recent_adaptations(self, n: int = 10) -> List[PlanAdaptation]:
        return self._adaptations[-n:]

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "active_plans": len(self._plans),
            "historical_plans": len(self._plan_history),
            "total_adaptations": len(self._adaptations),
            "strategy_performance": dict(self._strategy_performance),
            "templates": len(self._templates),
            "current_strategy": self._strategy.value,
        }

    def __repr__(self) -> str:
        active = sum(1 for p in self._plans.values() if p.status == PlanStatus.ACTIVE)
        return f"AdaptivePlanner(active={active}, strategy={self._strategy.value})"