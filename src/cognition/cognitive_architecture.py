"""
Cognitive Architecture - Main Orchestrator
============================================

Central orchestrator that integrates all cognitive subsystems into
a unified architecture. Every decision passes through this architecture,
is explained, logged, and can be traced back to its root causes.

This is the entry point for all cognitive processing in the drone
navigation system. It coordinates:

    - World modeling and simulation
    - Hierarchical memory (working/episodic/semantic/procedural)
    - Attention mechanisms
    - Uncertainty estimation
    - Probabilistic reasoning
    - Bayesian belief updates
    - RL interface
    - Mission context understanding
    - Explainable AI decision logging
    - Adaptive planning
    - Self-evaluation and confidence estimation
    - Continuous learning
"""

import math
import time
from typing import Dict, List, Optional, Tuple, Any, Set

from src.cognition.world_model import WorldModel
from src.cognition.hierarchical_memory import (
    HierarchicalMemory, MemoryType, MemoryPriority,
)
from src.cognition.attention import (
    AttentionMechanism, AttentionMode, AttentionTarget,
)
from src.cognition.uncertainty import UncertaintyEstimator
from src.cognition.probabilistic import ProbabilisticReasoner
from src.cognition.bayesian import BayesianBeliefNetwork
from src.cognition.rl_interface import ReinforcementLearningInterface
from src.cognition.mission_context import (
    MissionContextManager, MissionGoal, MissionPhase,
)
from src.cognition.explainability import (
    ExplainableAILogger, DecisionCategory, ExplanationLevel,
)
from src.cognition.adaptive_planner import AdaptivePlanner, PlanStep
from src.cognition.self_evaluation import SelfEvaluator, MetricType
from src.cognition.confidence import ConfidenceEstimator
from src.cognition.learning import ContinuousLearningHooks


class CognitiveArchitecture:
    """
    Main cognitive architecture that orchestrates all cognitive
    subsystems. Every decision made by the drone passes through
    this architecture and is fully explained and logged.
    """

    def __init__(self, grid_width: int = 100, grid_height: int = 100):
        # Initialize all subsystems
        self.world_model = WorldModel(grid_width, grid_height)
        self.memory = HierarchicalMemory()
        self.attention = AttentionMechanism()
        self.uncertainty = UncertaintyEstimator()
        self.probabilistic = ProbabilisticReasoner()
        self.bayesian = BayesianBeliefNetwork()
        self.rl = ReinforcementLearningInterface()
        self.mission = MissionContextManager()
        self.explainer = ExplainableAILogger()
        self.planner = AdaptivePlanner()
        self.self_eval = SelfEvaluator()
        self.confidence = ConfidenceEstimator()
        self.learning = ContinuousLearningHooks()

        # State
        self._step_count = 0
        self._decision_chain: List[str] = []
        self._cognitive_state: Dict[str, Any] = {
            "attention_mode": "broad",
            "overall_confidence": 0.5,
            "overall_uncertainty": 0.5,
            "risk_level": 0.0,
        }

        # Initialize default belief network
        self._initialize_beliefs()

    def _initialize_beliefs(self):
        """Set up initial beliefs for common variables."""
        self.bayesian.add_belief("safe_to_navigate", prior=0.8, variance=0.15)
        self.bayesian.add_belief("target_reachable", prior=0.7, variance=0.2)
        self.bayesian.add_belief("battery_sufficient", prior=0.9, variance=0.1)
        self.bayesian.add_belief("path_clear", prior=0.6, variance=0.25)
        self.bayesian.add_belief("mission_on_track", prior=0.5, variance=0.25)

    # ==========================================
    # Main Cognitive Cycle
    # ==========================================

    def cognitive_step(self, drone_position: Tuple[float, float],
                       drone_heading: float, drone_speed: float,
                       visible_obstacles: List[Tuple[float, float]],
                       target_position: Tuple[float, float],
                       battery_level: float,
                       mission_phase: str = "NAVIGATION") -> Dict[str, Any]:
        """
        Execute one complete cognitive processing cycle.
        Returns a decision dict with action, explanation, and confidence.
        """
        self._step_count += 1
        decision_chain = []

        # 1. PERCEIVE: Update world model with sensor data
        self.world_model.update_from_sensors(
            drone_position=drone_position,
            drone_heading=drone_heading,
            drone_speed=drone_speed,
            visible_obstacles=visible_obstacles,
            battery_level=battery_level,
            mission_phase=mission_phase,
        )

        # 2. ATTEND: Focus attention on relevant items
        attention_focus = self._compute_attention(
            drone_position, target_position, visible_obstacles, battery_level
        )
        decision_chain.append("attention")

        # 3. REMEMBER: Store perceptions in memory
        self._update_memory(drone_position, target_position, battery_level)
        decision_chain.append("memory")

        # 4. REASON: Update beliefs and estimate uncertainty
        reasoning_result = self._reason(
            drone_position, target_position, battery_level, visible_obstacles
        )
        decision_chain.append("reasoning")

        # 5. DECIDE: Choose an action
        decision = self._decide(
            drone_position, drone_heading, drone_speed,
            target_position, battery_level, visible_obstacles,
            attention_focus, reasoning_result,
        )
        decision_chain.append("decision")

        # 6. EXPLAIN: Log the decision with full explanation
        explanation_id = self._explain_decision(
            decision, drone_position, target_position,
            battery_level, reasoning_result,
        )
        decision_chain.append("explanation")

        # 7. LEARN: Record learning events
        self._learn_from_step(decision, reasoning_result)

        # 8. EVALUATE: Update self-evaluation
        self._self_evaluate(decision, reasoning_result)

        # Update cognitive state
        self._cognitive_state["overall_confidence"] = decision["confidence"]
        self._cognitive_state["overall_uncertainty"] = reasoning_result.get("uncertainty", 0.5)

        return {
            "action": decision["action"],
            "action_params": decision.get("params", {}),
            "confidence": decision["confidence"],
            "explanation": decision["explanation"],
            "explanation_id": explanation_id,
            "decision_chain": decision_chain,
            "attention_mode": attention_focus,
            "uncertainty": reasoning_result.get("uncertainty", 0.5),
            "beliefs": reasoning_result.get("beliefs", {}),
            "should_replan": decision.get("should_replan", False),
        }

    # ==========================================
    # Perception
    # ==========================================

    def initialize_mission(self, home_position: Tuple[float, float],
                           target_position: Tuple[float, float],
                           obstacles: List[Tuple[int, int]]):
        """Initialize the cognitive architecture for a mission."""
        self.world_model.initialize(
            drone_position=home_position,
            target_position=target_position,
            obstacles=obstacles,
        )
        self.mission.add_goal(MissionGoal(
            goal_id="primary_target",
            description="Navigate to target and inspect",
            target_position=target_position,
            priority=1,
            status="active",
        ))
        self.mission.add_goal(MissionGoal(
            goal_id="return_home",
            description="Return to home position after inspection",
            target_position=home_position,
            priority=2,
            status="pending",
        ))
        self.mission.set_phase(MissionPhase.NAVIGATION)

        # Start episodic memory episode
        self.memory.episodic.start_episode(
            location=home_position,
            context={"mission_start": True, "target": target_position},
        )

        self.explainer.log_decision(
            category=DecisionCategory.MISSION_CONTROL,
            decision="Mission initialized",
            explanation=(
                f"Mission started: navigate from {home_position} to "
                f"{target_position} with {len(obstacles)} known obstacles"
            ),
            confidence=0.9,
            evidence=[f"Home: {home_position}", f"Target: {target_position}", f"Obstacles: {len(obstacles)}"],
        )

    # ==========================================
    # Attention Processing
    # ==========================================

    def _compute_attention(self, position, target, obstacles, battery):
        """Score and rank attention targets."""
        scores = []

        # Score target
        scores.append(self.attention.score_relevance(
            item_id="target", item_type=AttentionTarget.TARGET,
            item_position=target, current_position=position,
            current_goal=target,
        ))

        # Score obstacles
        for i, (ox, oy) in enumerate(obstacles):
            scores.append(self.attention.score_relevance(
                item_id=f"obstacle_{i}", item_type=AttentionTarget.OBSTACLE,
                item_position=(float(ox), float(oy)),
                current_position=position, current_goal=target,
            ))

        # Score battery
        battery_urgency = max(0.0, 1.0 - battery)
        scores.append(self.attention.score_relevance(
            item_id="battery", item_type=AttentionTarget.BATTERY,
            item_position=position, current_position=position,
            urgency=battery_urgency,
            item_properties={"battery_level": battery},
        ))

        # Get top focus
        top = self.attention.get_top_focus(scores, n=5)
        self._cognitive_state["attention_mode"] = self.attention._current_focus.mode.value

        if battery < 0.3:
            self.attention.set_mode(AttentionMode.ALERT, center=position, radius=15.0)
        elif len(obstacles) > 5:
            self.attention.set_mode(AttentionMode.FOCUSED, center=target, radius=10.0)
        else:
            self.attention.set_mode(AttentionMode.BROAD, center=position, radius=20.0)

        return self.attention._current_focus.mode.value

    # ==========================================
    # Memory Processing
    # ==========================================

    def _update_memory(self, position, target, battery):
        """Update all memory layers."""
        self.memory.perceive("drone_position", position, MemoryType.SPATIAL, MemoryPriority.HIGH)
        self.memory.perceive("target_position", target, MemoryType.SPATIAL, MemoryPriority.HIGH)
        self.memory.perceive("battery_level", battery, MemoryType.SENSORY, MemoryPriority.HIGH)

        # Record episodic event
        self.memory.record_episode_event({
            "type": "position_update",
            "position": position,
            "battery": battery,
        })

    # ==========================================
    # Reasoning
    # ==========================================

    def _reason(self, position, target, battery, obstacles):
        """Perform probabilistic reasoning and Bayesian updates."""
        dist_to_target = math.sqrt(
            (position[0] - target[0]) ** 2 + (position[1] - target[1]) ** 2
        )

        # Bayesian updates
        self.bayesian.observe("battery_sufficient", battery,
                              reliability=0.95, source="battery_sensor")
        self.bayesian.observe("path_clear", 1.0 - min(1.0, len(obstacles) * 0.1),
                              reliability=0.8, source="obstacle_detection")
        self.bayesian.observe("target_reachable", max(0, 1.0 - dist_to_target / 100.0),
                              reliability=0.7, source="distance_estimate")

        beliefs = {}
        for var in ["safe_to_navigate", "target_reachable", "battery_sufficient", "path_clear"]:
            b = self.bayesian.query(var)
            beliefs[var] = b.posterior if b else 0.5

        # Uncertainty estimation
        self.uncertainty.estimate_combined(
            "navigation",
            values=[position[0], position[1]],
        )

        overall_uncertainty = self.uncertainty.get_overall_uncertainty()

        # Store reasoning in working memory
        self.memory.perceive("reasoning_result", {
            "beliefs": beliefs,
            "uncertainty": overall_uncertainty,
            "dist_to_target": dist_to_target,
        })

        return {
            "beliefs": beliefs,
            "uncertainty": overall_uncertainty,
            "dist_to_target": dist_to_target,
            "belief_safe": beliefs.get("safe_to_navigate", 0.5),
        }

    # ==========================================
    # Decision Making
    # ==========================================

    def _decide(self, position, heading, speed, target, battery,
                obstacles, attention_mode, reasoning):
        """Make a decision based on all cognitive inputs."""
        beliefs = reasoning["beliefs"]
        uncertainty = reasoning["uncertainty"]
        dist = reasoning["dist_to_target"]

        # Check if emergency
        if battery < 0.15:
            return self._emergency_decision(position, target, battery, "critical_battery")

        # Check if should replan
        should_replan = self.planner.should_replan(
            "current", uncertainty, beliefs.get("safe_to_navigate", 0.5)
        )[0]

        # Determine action based on beliefs and context
        if dist < 1.5:
            action = "arrived_at_target"
            explanation = f"Reached target (distance={dist:.2f}). Ready for inspection."
            confidence = 0.95
        elif not beliefs.get("path_clear", 0.5) > 0.4:
            action = "avoid_obstacle"
            explanation = f"Path not clear (belief={beliefs.get('path_clear', 0):.2f}). Avoiding obstacles."
            confidence = 0.8
        else:
            action = "navigate_toward_target"
            angle = math.atan2(target[1] - position[1], target[0] - position[0])
            explanation = (
                f"Navigating toward target at distance {dist:.2f}. "
                f"Heading angle: {math.degrees(angle):.1f} degrees. "
                f"Beliefs: safe={beliefs.get('safe_to_navigate', 0):.2f}, "
                f"reachable={beliefs.get('target_reachable', 0):.2f}"
            )
            confidence = max(0.3, 1.0 - uncertainty)

        return {
            "action": action,
            "params": {"target": target, "heading": math.atan2(target[1] - position[1], target[0] - position[0])},
            "confidence": confidence,
            "explanation": explanation,
            "should_replan": should_replan,
        }

    def _emergency_decision(self, position, target, battery, threat):
        """Handle emergency decisions."""
        action = "return_home"
        explanation = f"EMERGENCY: {threat} (battery={battery:.0%}). Returning home immediately."
        confidence = 0.95

        self.mission.set_phase(MissionPhase.EMERGENCY)

        self.explainer.log_emergency_decision(
            action=action, threat=threat, urgency=1.0 - battery,
            inputs={"position": position, "battery": battery},
        )

        self.learning.record_failure({"threat": threat, "battery": battery})

        return {
            "action": action,
            "params": {"target": (0, 0)},
            "confidence": confidence,
            "explanation": explanation,
            "should_replan": True,
        }

    # ==========================================
    # Explanation Logging
    # ==========================================

    def _explain_decision(self, decision, position, target, battery, reasoning):
        """Log the decision with full explanation."""
        evidence = [
            f"Position: {position}",
            f"Target: {target}",
            f"Battery: {battery:.0%}",
            f"Beliefs: {reasoning['beliefs']}",
            f"Uncertainty: {reasoning['uncertainty']:.3f}",
        ]

        chain = [
            "perceived_environment",
            "updated_world_model",
            "computed_attention",
            "updated_memory",
            "reasoned_with_beliefs",
            "estimated_uncertainty",
            "selected_action",
        ]

        alternatives = ["navigate_toward_target", "avoid_obstacle", "return_home", "hover", "explore"]

        return self.explainer.log_decision(
            category=DecisionCategory.NAVIGATION,
            decision=decision["action"],
            explanation=decision["explanation"],
            confidence=decision["confidence"],
            evidence=evidence,
            reasoning_chain=chain,
            alternatives=alternatives,
            inputs={
                "position": position,
                "target": target,
                "battery": battery,
                "uncertainty": reasoning["uncertainty"],
            },
        )

    # ==========================================
    # Learning
    # ==========================================

    def _learn_from_step(self, decision, reasoning):
        """Process learning events from this step."""
        if decision["action"] == "arrived_at_target":
            self.learning.record_success({
                "action": decision["action"],
                "confidence": decision["confidence"],
            })
        elif decision["action"] == "avoid_obstacle":
            self.learning.record_near_miss({
                "uncertainty": reasoning["uncertainty"],
            })

        self.learning.process_events()

    # ==========================================
    # Self-Evaluation
    # ==========================================

    def _self_evaluate(self, decision, reasoning):
        """Update self-evaluation metrics."""
        self.self_eval.record_metric(
            MetricType.ACCURACY, decision["confidence"],
        )
        self.self_eval.record_metric(
            MetricType.ACCURACY, 1.0 - reasoning["uncertainty"],
        )

    # ==========================================
    # Mission Completion
    # ==========================================

    def complete_mission(self, success: bool = True):
        """Mark mission as complete and record outcome."""
        outcome = "success" if success else "failure"
        self.memory.episodic.end_episode(outcome=outcome, importance=0.8)
        self.mission.set_phase(MissionPhase.COMPLETE)

        self.self_eval.record_episode_outcome(
            success=success,
            duration=self._step_count * 0.1,
            energy_used=1.0 - self.world_model._current_state.battery_level if self.world_model._current_state else 0.5,
            distance_covered=self._step_count * 0.5,
        )

        self.explainer.log_decision(
            category=DecisionCategory.MISSION_CONTROL,
            decision=f"Mission {outcome}",
            explanation=f"Mission completed with outcome: {outcome} after {self._step_count} steps",
            confidence=0.95 if success else 0.3,
        )

        self.planner.record_plan_outcome("current", success)

    # ==========================================
    # Status & Diagnostics
    # ==========================================

    def get_cognitive_state(self) -> Dict[str, Any]:
        """Get the complete cognitive state."""
        return {
            "step_count": self._step_count,
            "cognitive_state": dict(self._cognitive_state),
            "world_model": {
                "confidence": self.world_model.model_confidence,
                "entities": len(self.world_model._entities),
            },
            "memory": self.memory.get_memory_state(),
            "attention": self.attention.get_attention_summary(),
            "uncertainty": self.uncertainty.get_uncertainty_summary(),
            "beliefs": {
                name: belief.posterior
                for name, belief in self.bayesian.get_all_beliefs().items()
            },
            "mission": self.mission.get_status_summary(),
            "explanations": self.explainer.get_statistics(),
            "planner": self.planner.get_statistics(),
            "self_evaluation": self.self_eval.get_statistics(),
            "confidence": self.confidence.get_statistics(),
            "learning": self.learning.get_statistics(),
            "rl": self.rl.get_performance_summary(),
        }

    def explain_last_decisions(self, n: int = 5) -> List[str]:
        """Get human-readable explanations of recent decisions."""
        return self.explainer.explain_recent(n)

    def get_decision_trace(self, decision_id: str) -> List[str]:
        """Get the full trace of a decision."""
        trail = self.explainer.get_decision_trail(decision_id)
        return [self.explainer.explain_decision(d.decision_id) for d in trail]

    def __repr__(self) -> str:
        return (
            f"CognitiveArchitecture(step={self._step_count}, "
            f"confidence={self._cognitive_state['overall_confidence']:.2f}, "
            f"uncertainty={self._cognitive_state['overall_uncertainty']:.2f})"
        )