"""
Continuous Learning Hooks
==========================

Mechanisms for ongoing adaptation and learning from experience.
Provides hooks that can be called throughout the system to enable
incremental learning and policy updates.

Key Features:
    - Event-driven learning triggers
    - Multiple learning strategies
    - Performance-based adaptation rate
    - Knowledge extraction from episodes
    - Transfer learning support
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable


class LearningStrategy(Enum):
    INCREMENTAL = "incremental"
    BATCH = "batch"
    REINFORCEMENT = "reinforcement"
    IMITATION = "imitation"
    TRANSFER = "transfer"


class AdaptationResult(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    NO_CHANGE = "no_change"
    FAILURE = "failure"


@dataclass
class LearningEvent:
    """A learning event that triggers adaptation."""
    event_id: str
    event_type: str  # success, failure, surprise, near_miss, novelty
    context: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    priority: float = 0.5
    processed: bool = False


@dataclass
class LearningRule:
    """A rule that determines when to trigger learning."""
    rule_id: str
    condition: str
    action: str
    learning_rate: float = 0.01
    min_events: int = 1
    max_events: int = 100
    events_processed: int = 0
    success_count: int = 0


class ContinuousLearningHooks:
    """
    Manages continuous learning through hooks that are called
    throughout the cognitive architecture.
    """

    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}
        self._learning_events: Dict[int, LearningEvent] = {}
        self._event_counter = 0
        self._learning_rules: Dict[str, LearningRule] = {}

        # Strategy performance tracking
        self._strategy_stats: Dict[str, Dict[str, int]] = {
            "incremental": {"success": 0, "failure": 0},
            "batch": {"success": 0, "failure": 0},
            "reinforcement": {"success": 0, "failure": 0},
            "imitation": {"success": 0, "failure": 0},
            "transfer": {"success": 0, "failure": 0},
        }

        # Active learning strategies
        self._active_strategies: List[LearningStrategy] = [
            LearningStrategy.INCREMENTAL,
        ]

        # Knowledge extraction
        self._extracted_knowledge: Dict[str, Any] = {}

        # Adaptation history
        self._adaptation_history: List[Tuple[float, AdaptationResult, str]] = []

        # Learning rate adaptation
        self._base_learning_rate = 0.01
        self._current_learning_rate = 0.01
        self._learning_rate_adaptation = 0.001

    # ==========================================
    # Hook Management
    # ==========================================

    def register_hook(self, hook_name: str, callback: Callable):
        """Register a callback for a hook point."""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)

    def trigger_hooks(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Trigger all callbacks registered for a hook point."""
        results = []
        for callback in self._hooks.get(hook_name, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                results.append(None)
        return results

    def get_hook_names(self) -> List[str]:
        return list(self._hooks.keys())

    # ==========================================
    # Learning Events
    # ==========================================

    def record_event(self, event_type: str,
                     context: Optional[Dict[str, Any]] = None,
                     priority: float = 0.5) -> int:
        """Record a learning event."""
        self._event_counter += 1
        event = LearningEvent(
            event_id=f"le_{self._event_counter}",
            event_type=event_type,
            context=context or {},
            priority=priority,
        )
        self._learning_events[self._event_counter] = event
        self.trigger_hooks("on_learning_event", event)
        return self._event_counter

    def record_success(self, context: Optional[Dict[str, Any]] = None):
        """Record a successful outcome."""
        return self.record_event("success", context, priority=0.6)

    def record_failure(self, context: Optional[Dict[str, Any]] = None):
        """Record a failure outcome."""
        return self.record_event("failure", context, priority=0.8)

    def record_surprise(self, context: Optional[Dict[str, Any]] = None):
        """Record a surprising/unexpected outcome."""
        return self.record_event("surprise", context, priority=0.9)

    def record_near_miss(self, context: Optional[Dict[str, Any]] = None):
        """Record a near-miss event."""
        return self.record_event("near_miss", context, priority=0.7)

    def get_unprocessed_events(self) -> List[LearningEvent]:
        return [e for e in self._learning_events.values() if not e.processed]

    def process_events(self) -> int:
        """Process all unprocessed learning events. Returns count processed."""
        events = self.get_unprocessed_events()
        processed = 0

        for event in sorted(events, key=lambda e: -e.priority):
            for strategy in self._active_strategies:
                result = self._apply_strategy(strategy, event)
                if result == AdaptationResult.SUCCESS:
                    self._strategy_stats[strategy.value]["success"] += 1
                else:
                    self._strategy_stats[strategy.value]["failure"] += 1
            event.processed = True
            processed += 1

            # Adapt learning rate
            self._adapt_learning_rate(event)

        return processed

    def _apply_strategy(self, strategy: LearningStrategy,
                        event: LearningEvent) -> AdaptationResult:
        """Apply a learning strategy to an event."""
        if strategy == LearningStrategy.INCREMENTAL:
            return self._incremental_learn(event)
        elif strategy == LearningStrategy.REINFORCEMENT:
            return self._reinforcement_learn(event)
        elif strategy == LearningStrategy.IMITATION:
            return self._imitation_learn(event)
        return AdaptationResult.NO_CHANGE

    def _incremental_learn(self, event: LearningEvent) -> AdaptationResult:
        """Incrementally update knowledge based on event."""
        key = f"pattern_{event.event_type}"
        if key not in self._extracted_knowledge:
            self._extracted_knowledge[key] = {"count": 0, "avg_priority": 0.0}
        knowledge = self._extracted_knowledge[key]
        n = knowledge["count"]
        knowledge["avg_priority"] = (
            (knowledge["avg_priority"] * n + event.priority) / (n + 1)
        )
        knowledge["count"] = n + 1
        return AdaptationResult.SUCCESS

    def _reinforcement_learn(self, event: LearningEvent) -> AdaptationResult:
        """Learn through reinforcement signal."""
        reward = 1.0 if event.event_type == "success" else -1.0
        if event.event_type == "surprise":
            reward = 0.5
        key = "reinforcement_value"
        current = self._extracted_knowledge.get(key, 0.0)
        self._extracted_knowledge[key] = current + self._current_learning_rate * reward
        return AdaptationResult.SUCCESS

    def _imitation_learn(self, event: LearningEvent) -> AdaptationResult:
        """Learn by observing expert behavior."""
        expert_action = event.context.get("expert_action")
        if expert_action:
            key = f"imitation_{expert_action}"
            count = self._extracted_knowledge.get(key, 0) + 1
            self._extracted_knowledge[key] = count
            return AdaptationResult.SUCCESS
        return AdaptationResult.NO_CHANGE

    # ==========================================
    # Learning Rules
    # ==========================================

    def add_rule(self, rule: LearningRule):
        self._learning_rules[rule.rule_id] = rule

    def evaluate_rules(self) -> List[str]:
        """Evaluate learning rules and return triggered rule actions."""
        triggered = []
        unprocessed = len(self.get_unprocessed_events())
        for rule in self._learning_rules.values():
            if unprocessed >= rule.min_events:
                triggered.append(rule.action)
                rule.events_processed += 1
        return triggered

    # ==========================================
    # Learning Rate Adaptation
    # ==========================================

    def _adapt_learning_rate(self, event: LearningEvent):
        """Adapt learning rate based on recent outcomes."""
        if event.event_type == "success":
            self._current_learning_rate = max(
                0.001,
                self._current_learning_rate - self._learning_rate_adaptation,
            )
        elif event.event_type == "failure":
            self._current_learning_rate = min(
                0.1,
                self._current_learning_rate + self._learning_rate_adaptation,
            )

    # ==========================================
    # Knowledge Management
    # ==========================================

    def extract_knowledge(self, source: str,
                           data: Dict[str, Any]) -> str:
        """Extract and store knowledge from data."""
        key = f"knowledge_{source}_{len(self._extracted_knowledge)}"
        self._extracted_knowledge[key] = data
        self.trigger_hooks("on_knowledge_extracted", key, data)
        return key

    def get_knowledge(self, key: str) -> Optional[Any]:
        return self._extracted_knowledge.get(key)

    def transfer_knowledge(self, source_domain: str,
                            target_domain: str) -> AdaptationResult:
        """Transfer knowledge between domains."""
        source_key = f"knowledge_{source_domain}"
        knowledge = self._extracted_knowledge.get(source_key)
        if knowledge:
            target_key = f"knowledge_{target_domain}"
            self._extracted_knowledge[target_key] = knowledge
            self._adaptation_history.append(
                (time.time(), AdaptationResult.SUCCESS,
                 f"Transferred from {source_domain} to {target_domain}")
            )
            return AdaptationResult.SUCCESS
        return AdaptationResult.NO_CHANGE

    # ==========================================
    # Queries
    # ==========================================

    def add_active_strategy(self, strategy: LearningStrategy):
        if strategy not in self._active_strategies:
            self._active_strategies.append(strategy)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_events": len(self._learning_events),
            "unprocessed": len(self.get_unprocessed_events()),
            "active_strategies": [s.value for s in self._active_strategies],
            "strategy_stats": dict(self._strategy_stats),
            "learning_rate": self._current_learning_rate,
            "knowledge_items": len(self._extracted_knowledge),
            "total_adaptations": len(self._adaptation_history),
        }

    def __repr__(self) -> str:
        n = len(self._learning_events)
        lr = self._current_learning_rate
        return f"ContinuousLearningHooks(events={n}, lr={lr:.4f})"