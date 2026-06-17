"""
Hierarchical Memory System
===========================

Four-layer memory architecture inspired by cognitive science:

1. **Working Memory**: Current active context (limited capacity, fast access).
   Holds the immediate situation, current goals, and active calculations.

2. **Episodic Memory**: Past experiences stored as sequences of events.
   Enables learning from history and recognizing similar situations.

3. **Semantic Memory**: General knowledge about the world (facts, relationships).
   Static knowledge that persists across episodes.

4. **Procedural Memory**: Action patterns and skills (how to do things).
   Compiled behavioral routines that can be triggered automatically.

Each layer has its own storage, retrieval, and consolidation mechanisms.
Memory consolidation moves information between layers over time.
"""

import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from collections import OrderedDict


class MemoryType(Enum):
    """Types of memory entries."""
    SENSORY = "sensory"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    EMOTIONAL = "emotional"  # urgency / risk level
    PROCEDURAL = "procedural"
    DECLARATIVE = "declarative"


class MemoryPriority(Enum):
    """Priority levels for memory retention."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    MINIMAL = 1


@dataclass
class MemoryEntry:
    """A single entry in any memory layer."""
    content: Any
    memory_type: MemoryType
    priority: MemoryPriority = MemoryPriority.MEDIUM
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    confidence: float = 1.0
    source: str = "sensor"
    tags: Set[str] = field(default_factory=set)
    associations: List[str] = field(default_factory=list)

    def access(self):
        """Record an access to this memory (strengthens it)."""
        self.access_count += 1
        self.last_accessed = time.time()

    def recency_score(self, half_life: float = 300.0) -> float:
        """Compute recency score using exponential decay."""
        age = time.time() - self.last_accessed
        return math.exp(-age / half_life)

    def strength(self) -> float:
        """Overall memory strength combining frequency, recency, and priority."""
        freq = min(1.0, self.access_count / 10.0)
        recency = self.recency_score()
        priority_weight = self.priority.value / 5.0
        return (0.3 * freq + 0.4 * recency + 0.3 * priority_weight) * self.confidence


# ==========================================
# Working Memory
# ==========================================

class WorkingMemory:
    """
    Limited-capacity working memory for active processing.
    
    Implements a capacity-limited buffer where lower-priority items
    are evicted when full. Items can be promoted to higher priority
    through repeated access.
    """

    def __init__(self, capacity: int = 7):
        self.capacity = capacity  # Miller's number ± 2
        self._items: OrderedDict[str, MemoryEntry] = OrderedDict()
        self._context_stack: List[Dict[str, Any]] = []

    def store(self, key: str, content: Any,
              memory_type: MemoryType = MemoryType.SENSORY,
              priority: MemoryPriority = MemoryPriority.MEDIUM,
              **kwargs) -> bool:
        """Store an item in working memory. Returns False if evicted."""
        if key in self._items:
            self._items[key].content = content
            self._items[key].access()
            self._items.move_to_end(key)
            return True

        if len(self._items) >= self.capacity:
            # Evict weakest item
            weakest_key = min(
                self._items.keys(),
                key=lambda k: self._items[k].strength()
            )
            evicted = self._items.pop(weakest_key)
            self._on_eviction(weakest_key, evicted)

        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            priority=priority,
            source=kwargs.get("source", "working"),
            tags=kwargs.get("tags", set()),
            confidence=kwargs.get("confidence", 1.0),
        )
        self._items[key] = entry
        return True

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve an item from working memory."""
        if key in self._items:
            self._items[key].access()
            self._items.move_to_end(key)
            return self._items[key].content
        return None

    def contains(self, key: str) -> bool:
        return key in self._items

    def remove(self, key: str) -> Optional[MemoryEntry]:
        return self._items.pop(key, None)

    def get_all(self) -> Dict[str, Any]:
        """Get all items as key-content dict."""
        return {k: v.content for k, v in self._items.items()}

    def get_entries(self) -> OrderedDict[str, MemoryEntry]:
        """Get all entries with metadata."""
        return OrderedDict(self._items)

    @property
    def utilization(self) -> float:
        return len(self._items) / self.capacity if self.capacity > 0 else 0.0

    def push_context(self, context: Dict[str, Any]):
        """Push a context frame onto the stack."""
        self._context_stack.append(context)
        if len(self._context_stack) > 10:
            self._context_stack.pop(0)

    def pop_context(self) -> Optional[Dict[str, Any]]:
        return self._context_stack.pop() if self._context_stack else None

    def get_current_context(self) -> Dict[str, Any]:
        return self._context_stack[-1] if self._context_stack else {}

    def clear(self):
        self._items.clear()
        self._context_stack.clear()

    def _on_eviction(self, key: str, entry: MemoryEntry):
        """Hook for when an item is evicted from working memory."""
        pass


# ==========================================
# Episodic Memory
# ==========================================

@dataclass
class MemoryEpisode:
    """A complete episode (sequence of events)."""
    episode_id: str
    start_time: float
    end_time: float = 0.0
    events: List[Dict[str, Any]] = field(default_factory=list)
    outcome: str = "unknown"
    location: Tuple[float, float] = (0.0, 0.0)
    context: Dict[str, Any] = field(default_factory=dict)
    emotional_valence: float = 0.0  # -1 (bad) to +1 (good)
    importance: float = 0.5
    tags: Set[str] = field(default_factory=set)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time > 0 else 0.0

    def similarity(self, other: 'MemoryEpisode') -> float:
        """Compute similarity between two episodes based on context and location."""
        loc_dist = math.sqrt(
            (self.location[0] - other.location[0]) ** 2 +
            (self.location[1] - other.location[1]) ** 2
        )
        loc_sim = 1.0 / (1.0 + loc_dist)

        # Context similarity (Jaccard on tags)
        if self.tags or other.tags:
            intersection = len(self.tags & other.tags)
            union = len(self.tags | other.tags)
            tag_sim = intersection / union if union > 0 else 0.0
        else:
            tag_sim = 0.5

        # Outcome similarity
        outcome_sim = 1.0 if self.outcome == other.outcome else 0.0

        return 0.4 * loc_sim + 0.3 * tag_sim + 0.3 * outcome_sim


class EpisodicMemory:
    """
    Stores and retrieves past experiences as episodes.
    Supports similarity-based retrieval and pattern recognition.
    """

    def __init__(self, max_episodes: int = 500):
        self.max_episodes = max_episodes
        self._episodes: Dict[str, MemoryEpisode] = {}
        self._current_episode: Optional[MemoryEpisode] = None
        self._episode_counter = 0

    def start_episode(self, location: Tuple[float, float],
                      context: Optional[Dict[str, Any]] = None) -> str:
        """Start recording a new episode."""
        if self._current_episode is not None:
            self.end_episode("interrupted")

        self._episode_counter += 1
        episode_id = f"ep_{self._episode_counter}"
        self._current_episode = MemoryEpisode(
            episode_id=episode_id,
            start_time=time.time(),
            location=location,
            context=context or {},
        )
        return episode_id

    def add_event(self, event: Dict[str, Any]):
        """Add an event to the current episode."""
        if self._current_episode is not None:
            event["timestamp"] = time.time()
            self._current_episode.events.append(event)

    def end_episode(self, outcome: str = "completed",
                    importance: float = 0.5):
        """End the current episode and store it."""
        if self._current_episode is None:
            return

        self._current_episode.end_time = time.time()
        self._current_episode.outcome = outcome
        self._current_episode.importance = importance

        # Determine emotional valence from outcome
        if outcome in ("success", "completed", "goal_reached"):
            self._current_episode.emotional_valence = 0.8
        elif outcome in ("failure", "collision", "timeout"):
            self._current_episode.emotional_valence = -0.8
        elif outcome == "interrupted":
            self._current_episode.emotional_valence = -0.3

        self._episodes[self._current_episode.episode_id] = self._current_episode
        self._enforce_capacity()
        self._current_episode = None

    def find_similar(self, context: Dict[str, Any],
                     location: Tuple[float, float],
                     k: int = 5) -> List[Tuple[MemoryEpisode, float]]:
        """Find k most similar past episodes."""
        query = MemoryEpisode(
            episode_id="query",
            start_time=time.time(),
            location=location,
            context=context,
            tags=set(context.get("tags", [])),
        )

        scored = []
        for ep in self._episodes.values():
            sim = ep.similarity(query)
            scored.append((ep, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def find_by_outcome(self, outcome: str) -> List[MemoryEpisode]:
        """Find all episodes with a specific outcome."""
        return [ep for ep in self._episodes.values() if ep.outcome == outcome]

    def find_by_tag(self, tag: str) -> List[MemoryEpisode]:
        """Find all episodes with a specific tag."""
        return [ep for ep in self._episodes.values() if tag in ep.tags]

    def get_recent(self, n: int = 10) -> List[MemoryEpisode]:
        """Get the n most recent episodes."""
        sorted_eps = sorted(
            self._episodes.values(),
            key=lambda e: e.start_time,
            reverse=True
        )
        return sorted_eps[:n]

    def get_successful_episodes(self) -> List[MemoryEpisode]:
        return self.find_by_outcome("success") + self.find_by_outcome("completed")

    def get_failed_episodes(self) -> List[MemoryEpisode]:
        return self.find_by_outcome("failure") + self.find_by_outcome("collision")

    def get_statistics(self) -> Dict[str, Any]:
        """Get summary statistics of episodic memory."""
        episodes = list(self._episodes.values())
        if not episodes:
            return {"total": 0}

        outcomes = {}
        for ep in episodes:
            outcomes[ep.outcome] = outcomes.get(ep.outcome, 0) + 1

        avg_importance = sum(e.importance for e in episodes) / len(episodes)
        avg_valence = sum(e.emotional_valence for e in episodes) / len(episodes)

        return {
            "total": len(episodes),
            "outcomes": outcomes,
            "avg_importance": avg_importance,
            "avg_valence": avg_valence,
        }

    def _enforce_capacity(self):
        if len(self._episodes) > self.max_episodes:
            # Remove least important episodes
            sorted_eps = sorted(
                self._episodes.values(),
                key=lambda e: (e.importance, e.start_time)
            )
            to_remove = len(self._episodes) - self.max_episodes
            for ep in sorted_eps[:to_remove]:
                del self._episodes[ep.episode_id]


# ==========================================
# Semantic Memory
# ==========================================

@dataclass
class SemanticFact:
    """A piece of general knowledge."""
    fact_id: str
    subject: str
    predicate: str
    obj: str
    confidence: float = 1.0
    source: str = "learned"
    times_observed: int = 1
    first_observed: float = field(default_factory=time.time)
    tags: Set[str] = field(default_factory=set)

    def __hash__(self):
        return hash((self.subject, self.predicate, self.obj))

    def __eq__(self, other):
        return (self.subject == other.subject and
                self.predicate == other.predicate and
                self.obj == other.obj)


class SemanticMemory:
    """
    Stores general world knowledge as (subject, predicate, object) triples.
    Supports querying, reasoning, and knowledge accumulation.
    """

    def __init__(self):
        self._facts: Dict[str, SemanticFact] = {}
        self._fact_counter = 0
        self._knowledge_graph: Dict[str, List[str]] = {}  # subject -> [fact_ids]

    def add_fact(self, subject: str, predicate: str, obj: str,
                 confidence: float = 1.0, source: str = "observed",
                 tags: Optional[Set[str]] = None) -> str:
        """Add a fact to semantic memory. Returns fact_id."""
        # Check for duplicates
        for fid, fact in self._facts.items():
            if (fact.subject == subject and
                fact.predicate == predicate and
                fact.obj == obj):
                fact.times_observed += 1
                fact.confidence = min(1.0, fact.confidence + 0.05)
                return fid

        self._fact_counter += 1
        fact_id = f"fact_{self._fact_counter}"
        fact = SemanticFact(
            fact_id=fact_id,
            subject=subject,
            predicate=predicate,
            obj=obj,
            confidence=confidence,
            source=source,
            tags=tags or set(),
        )
        self._facts[fact_id] = fact

        # Update knowledge graph
        if subject not in self._knowledge_graph:
            self._knowledge_graph[subject] = []
        self._knowledge_graph[subject].append(fact_id)

        return fact_id

    def query(self, subject: Optional[str] = None,
              predicate: Optional[str] = None,
              obj: Optional[str] = None) -> List[SemanticFact]:
        """Query facts matching the given criteria."""
        results = []
        for fact in self._facts.values():
            if subject and fact.subject != subject:
                continue
            if predicate and fact.predicate != predicate:
                continue
            if obj and fact.obj != obj:
                continue
            results.append(fact)
        return results

    def get_facts_about(self, subject: str) -> List[SemanticFact]:
        """Get all facts about a subject."""
        fact_ids = self._knowledge_graph.get(subject, [])
        return [self._facts[fid] for fid in fact_ids if fid in self._facts]

    def get_related(self, subject: str,
                    predicate: str) -> List[str]:
        """Get all objects related to a subject via a predicate."""
        facts = self.query(subject=subject, predicate=predicate)
        return [f.obj for f in facts]

    def strengthen(self, fact_id: str, amount: float = 0.1):
        """Strengthen a fact's confidence."""
        if fact_id in self._facts:
            f = self._facts[fact_id]
            f.confidence = min(1.0, f.confidence + amount)
            f.times_observed += 1

    def weaken(self, fact_id: str, amount: float = 0.1):
        """Weaken a fact's confidence."""
        if fact_id in self._facts:
            self._facts[fact_id].confidence = max(
                0.0, self._facts[fact_id].confidence - amount
            )

    def get_high_confidence_facts(self,
                                   threshold: float = 0.7) -> List[SemanticFact]:
        return [f for f in self._facts.values() if f.confidence >= threshold]

    def get_statistics(self) -> Dict[str, Any]:
        facts = list(self._facts.values())
        if not facts:
            return {"total_facts": 0}
        return {
            "total_facts": len(facts),
            "avg_confidence": sum(f.confidence for f in facts) / len(facts),
            "subjects": len(self._knowledge_graph),
            "total_observations": sum(f.times_observed for f in facts),
        }


# ==========================================
# Procedural Memory
# ==========================================

@dataclass
class ProceduralRule:
    """An if-then rule for behavior."""
    rule_id: str
    name: str
    condition: str  # Human-readable condition description
    action: str  # Action to take
    priority: int = 1
    success_rate: float = 1.0
    times_triggered: int = 0
    times_succeeded: int = 0
    confidence: float = 1.0
    context_tags: Set[str] = field(default_factory=set)
    cooldown: float = 0.0  # Minimum seconds between triggers
    last_triggered: float = 0.0

    @property
    def effectiveness(self) -> float:
        if self.times_triggered == 0:
            return 0.5
        return self.times_succeeded / self.times_triggered

    def can_trigger(self) -> bool:
        """Check if cooldown has elapsed."""
        if self.cooldown <= 0:
            return True
        return (time.time() - self.last_triggered) >= self.cooldown

    def record_outcome(self, success: bool):
        self.times_triggered += 1
        self.last_triggered = time.time()
        if success:
            self.times_succeeded += 1
        # Update success rate with exponential moving average
        alpha = 0.1
        self.success_rate = (
            (1 - alpha) * self.success_rate + alpha * (1.0 if success else 0.0)
        )


class ProceduralMemory:
    """
    Stores action patterns and behavioral rules.
    Rules are matched against the current situation to suggest actions.
    """

    def __init__(self):
        self._rules: Dict[str, ProceduralRule] = {}
        self._rule_counter = 0
        self._action_history: List[Tuple[str, bool, float]] = []

    def add_rule(self, name: str, condition: str, action: str,
                 priority: int = 1, context_tags: Optional[Set[str]] = None,
                 cooldown: float = 0.0) -> str:
        """Add a procedural rule."""
        self._rule_counter += 1
        rule_id = f"rule_{self._rule_counter}"
        self._rules[rule_id] = ProceduralRule(
            rule_id=rule_id,
            name=name,
            condition=condition,
            action=action,
            priority=priority,
            context_tags=context_tags or set(),
            cooldown=cooldown,
        )
        return rule_id

    def get_matching_rules(self, situation_tags: Set[str]) -> List[ProceduralRule]:
        """Get rules whose context tags match the situation."""
        matching = []
        for rule in self._rules.values():
            if not rule.context_tags:
                matching.append(rule)
                continue
            overlap = len(rule.context_tags & situation_tags)
            if overlap > 0:
                matching.append(rule)
        matching.sort(key=lambda r: (r.priority, r.effectiveness), reverse=True)
        return matching

    def suggest_action(self, situation_tags: Set[str]) -> Optional[str]:
        """Suggest the best action for a situation."""
        rules = self.get_matching_rules(situation_tags)
        for rule in rules:
            if rule.can_trigger() and rule.confidence > 0.3:
                return rule.action
        return None

    def record_action(self, rule_id: str, success: bool):
        """Record the outcome of an action."""
        if rule_id in self._rules:
            self._rules[rule_id].record_outcome(success)
        self._action_history.append((rule_id, success, time.time()))
        if len(self._action_history) > 1000:
            self._action_history.pop(0)

    def get_rule(self, rule_id: str) -> Optional[ProceduralRule]:
        return self._rules.get(rule_id)

    def get_all_rules(self) -> List[ProceduralRule]:
        return list(self._rules.values())

    def get_statistics(self) -> Dict[str, Any]:
        rules = list(self._rules.values())
        if not rules:
            return {"total_rules": 0}
        return {
            "total_rules": len(rules),
            "avg_success_rate": sum(r.success_rate for r in rules) / len(rules),
            "total_actions": len(self._action_history),
            "recent_success_rate": self._recent_success_rate(),
        }

    def _recent_success_rate(self, window: int = 50) -> float:
        recent = self._action_history[-window:]
        if not recent:
            return 0.5
        successes = sum(1 for _, s, _ in recent if s)
        return successes / len(recent)


# ==========================================
# Hierarchical Memory (Orchestrator)
# ==========================================

class HierarchicalMemory:
    """
    Unified interface to all four memory layers.
    Manages consolidation between layers and provides
    a single API for memory operations.
    """

    def __init__(self, working_capacity: int = 7,
                 max_episodes: int = 500):
        self.working = WorkingMemory(capacity=working_capacity)
        self.episodic = EpisodicMemory(max_episodes=max_episodes)
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()

        # Consolidation tracking
        self._consolidation_count = 0
        self._last_consolidation = time.time()

    def perceive(self, key: str, content: Any,
                 memory_type: MemoryType = MemoryType.SENSORY,
                 priority: MemoryPriority = MemoryPriority.MEDIUM,
                 **kwargs):
        """Store a new perception in working memory."""
        self.working.store(key, content, memory_type, priority, **kwargs)

    def remember(self, key: str) -> Optional[Any]:
        """Retrieve something from memory (checks working first)."""
        result = self.working.retrieve(key)
        if result is not None:
            return result
        return None

    def learn_fact(self, subject: str, predicate: str, obj: str,
                   confidence: float = 1.0):
        """Learn a new fact about the world."""
        self.semantic.add_fact(subject, predicate, obj, confidence)
        # Also put in working memory for immediate use
        self.working.store(
            f"fact_{subject}_{predicate}",
            {"subject": subject, "predicate": predicate, "object": obj},
            MemoryType.DECLARATIVE,
            MemoryPriority.MEDIUM,
        )

    def record_episode_event(self, event: Dict[str, Any]):
        """Add event to current episode."""
        self.episodic.add_event(event)

    def get_suggested_action(self, situation_tags: Set[str]) -> Optional[str]:
        """Get an action suggestion from procedural memory."""
        return self.procedural.suggest_action(situation_tags)

    def consolidate(self):
        """
        Consolidate memories between layers.
        - Working memory -> Episodic (when context ends)
        - Episodic -> Semantic (pattern extraction)
        - Weak memories get pruned
        """
        self._consolidation_count += 1
        self._last_consolidation = time.time()

        # Prune low-strength working memory entries
        entries = self.working.get_entries()
        to_remove = []
        for key, entry in entries.items():
            if entry.strength() < 0.2:
                to_remove.append(key)
        for key in to_remove:
            self.working.remove(key)

    def get_memory_state(self) -> Dict[str, Any]:
        """Get comprehensive memory state."""
        return {
            "working": {
                "utilization": self.working.utilization,
                "items": len(self.working.get_all()),
                "capacity": self.working.capacity,
            },
            "episodic": self.episodic.get_statistics(),
            "semantic": self.semantic.get_statistics(),
            "procedural": self.procedural.get_statistics(),
            "consolidations": self._consolidation_count,
        }

    def __repr__(self) -> str:
        ws = self.working.utilization
        ep = len(self.episodic._episodes)
        sf = len(self.semantic._facts)
        pr = len(self.procedural._rules)
        return (
            f"HierarchicalMemory(working={ws:.0%}, "
            f"episodes={ep}, facts={sf}, rules={pr})"
        )