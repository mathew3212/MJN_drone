"""
Attention Mechanism
====================

Implements cognitive attention - the ability to selectively focus on
relevant information while filtering out noise. Inspired by both
biological attention and transformer attention mechanisms.

Key Capabilities:
    - Multi-factor relevance scoring
    - Spatial attention (focus on nearby/important locations)
    - Task-based attention (filter by current goal)
    - Saliency detection (flag unusual or important stimuli)
    - Attention decay (focus shifts over time)
    - Priority-based information routing
"""

import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set


class AttentionMode(Enum):
    """Different attention allocation modes."""
    BROAD = "broad"          # Scanning, exploratory
    FOCUSED = "focused"      # Narrow, task-oriented
    ALERT = "alert"          # Emergency, high vigilance
    SELECTIVE = "selective"  # Filtering by specific criteria


class AttentionTarget(Enum):
    """What attention can be directed at."""
    OBSTACLE = "obstacle"
    TARGET = "target"
    PATH = "path"
    HAZARD = "hazard"
    BATTERY = "battery"
    TERRAIN = "terrain"
    MOVEMENT = "movement"
    SELF = "self"


@dataclass
class RelevanceScore:
    """Score describing how relevant something is."""
    target_id: str
    target_type: AttentionTarget
    spatial_relevance: float = 0.0     # How spatially relevant (nearby, on path)
    task_relevance: float = 0.0        # How relevant to current task
    urgency_relevance: float = 0.0     # How urgent/time-critical
    novelty_relevance: float = 0.0     # How novel/unexpected
    saliency: float = 0.0             # How salient/eye-catching
    overall: float = 0.0              # Combined relevance
    explanation: str = ""             # Why this score was assigned

    def compute_overall(self, weights: Optional[Dict[str, float]] = None):
        """Compute overall relevance from component scores."""
        w = weights or {
            "spatial": 0.3,
            "task": 0.3,
            "urgency": 0.2,
            "novelty": 0.1,
            "saliency": 0.1,
        }
        self.overall = (
            w.get("spatial", 0.3) * self.spatial_relevance +
            w.get("task", 0.3) * self.task_relevance +
            w.get("urgency", 0.2) * self.urgency_relevance +
            w.get("novelty", 0.1) * self.novelty_relevance +
            w.get("saliency", 0.1) * self.saliency
        )
        return self.overall


@dataclass
class AttentionFocus:
    """Represents the current attentional focus state."""
    mode: AttentionMode = AttentionMode.BROAD
    focus_center: Tuple[float, float] = (0.0, 0.0)
    focus_radius: float = 10.0
    focus_targets: List[str] = field(default_factory=list)
    attention_weights: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0

    @property
    def is_emergency(self) -> bool:
        return self.mode == AttentionMode.ALERT


@dataclass
class AttentionFilter:
    """A filter that determines what gets attention."""
    filter_type: AttentionTarget
    min_relevance: float = 0.3
    max_items: int = 10
    decay_rate: float = 0.95


class AttentionMechanism:
    """
    Cognitive attention system that selectively processes information
    based on relevance to current goals, spatial proximity, urgency,
    and novelty.
    """

    def __init__(self, attention_range: float = 20.0,
                 max_focus_items: int = 5):
        self.attention_range = attention_range
        self.max_focus_items = max_focus_items

        # Current attention state
        self._current_focus = AttentionFocus()
        self._relevance_history: Dict[str, List[float]] = {}
        self._attention_log: List[Tuple[float, str, float]] = []

        # Novelty detection (tracks what's been seen before)
        self._seen_items: Dict[str, int] = {}
        self._novelty_threshold: int = 3

        # Attention weights (can be learned)
        self._weights = {
            "spatial": 0.30,
            "task": 0.30,
            "urgency": 0.20,
            "novelty": 0.10,
            "saliency": 0.10,
        }

        # Filters
        self._filters: List[AttentionFilter] = []

        # Habituation (reduce attention to repeated stimuli)
        self._habituation: Dict[str, float] = {}

        # Alert triggers
        self._alert_conditions: Dict[str, callable] = {}

    # ==========================================
    # Core Attention Scoring
    # ==========================================

    def score_relevance(self, item_id: str,
                        item_type: AttentionTarget,
                        item_position: Tuple[float, float],
                        current_position: Tuple[float, float],
                        current_goal: Optional[Tuple[float, float]] = None,
                        urgency: float = 0.0,
                        item_properties: Optional[Dict[str, Any]] = None
                        ) -> RelevanceScore:
        """
        Compute the relevance of an item to current attention.
        
        Args:
            item_id: Unique identifier for the item
            item_type: Category of the item
            item_position: (x, y) position of the item
            current_position: Drone's current (x, y)
            current_goal: Current navigation goal (x, y)
            urgency: Urgency level [0, 1]
            item_properties: Additional properties for scoring
        
        Returns:
            RelevanceScore with all components computed
        """
        props = item_properties or {}
        score = RelevanceScore(
            target_id=item_id,
            target_type=item_type,
        )

        # 1. Spatial relevance (closer = more relevant, path-relevant = bonus)
        dist = math.sqrt(
            (item_position[0] - current_position[0]) ** 2 +
            (item_position[1] - current_position[1]) ** 2
        )
        proximity = max(0.0, 1.0 - dist / self.attention_range)

        # Bonus if item is near the path to goal
        path_bonus = 0.0
        if current_goal:
            path_dist = self._point_to_line_distance(
                item_position, current_position, current_goal
            )
            path_bonus = max(0.0, 0.3 * (1.0 - path_dist / 5.0))

        score.spatial_relevance = min(1.0, proximity + path_bonus)

        # 2. Task relevance (does it affect the current goal?)
        task_relevance_map = {
            AttentionTarget.OBSTACLE: 0.8,
            AttentionTarget.TARGET: 1.0 if current_goal else 0.3,
            AttentionTarget.PATH: 0.7,
            AttentionTarget.HAZARD: 0.9,
            AttentionTarget.BATTERY: 0.6,
            AttentionTarget.TERRAIN: 0.4,
            AttentionTarget.MOVEMENT: 0.7,
            AttentionTarget.SELF: 0.5,
        }
        score.task_relevance = task_relevance_map.get(item_type, 0.5)

        # Adjust task relevance based on distance to goal
        if current_goal and item_type == AttentionTarget.OBSTACLE:
            goal_dist = math.sqrt(
                (current_position[0] - current_goal[0]) ** 2 +
                (current_position[1] - current_goal[1]) ** 2
            )
            item_goal_dist = math.sqrt(
                (item_position[0] - current_goal[0]) ** 2 +
                (item_position[1] - current_goal[1]) ** 2
            )
            if item_goal_dist < goal_dist * 0.3:
                score.task_relevance = 1.0  # Obstacle between here and goal

        # 3. Urgency
        score.urgency_relevance = min(1.0, urgency)

        # Boost urgency for certain types
        if item_type == AttentionTarget.HAZARD:
            score.urgency_relevance = max(score.urgency_relevance, 0.8)
        elif item_type == AttentionTarget.BATTERY:
            bat_level = props.get("battery_level", 1.0)
            if bat_level < 0.3:
                score.urgency_relevance = max(score.urgency_relevance, 0.9)

        # 4. Novelty (unfamiliar items get more attention)
        seen_count = self._seen_items.get(item_id, 0)
        self._seen_items[item_id] = seen_count + 1
        if seen_count < self._novelty_threshold:
            score.novelty_relevance = 1.0 - (seen_count / self._novelty_threshold)
        else:
            score.novelty_relevance = 0.1

        # 5. Saliency (unexpected or unusual items)
        saliency = 0.0
        if props.get("unexpected", False):
            saliency += 0.5
        if props.get("moving", False) and item_type == AttentionTarget.OBSTACLE:
            saliency += 0.3
        if props.get("size", 1.0) > 2.0:
            saliency += 0.2
        score.saliency = min(1.0, saliency)

        # Apply habituation (reduce attention to repeatedly seen items)
        habit = self._habituation.get(item_id, 1.0)
        score.compute_overall(self._weights)
        score.overall *= habit

        # Generate explanation
        score.explanation = (
            f"{item_type.value} '{item_id}': "
            f"spatial={score.spatial_relevance:.2f}, "
            f"task={score.task_relevance:.2f}, "
            f"urgency={score.urgency_relevance:.2f}, "
            f"novelty={score.novelty_relevance:.2f}, "
            f"overall={score.overall:.2f}"
        )

        # Update habituation (frequent exposure reduces attention)
        self._habituation[item_id] = max(0.1, habit * 0.98)

        return score

    def rank_items(self, scores: List[RelevanceScore]) -> List[RelevanceScore]:
        """Rank items by overall relevance."""
        return sorted(scores, key=lambda s: s.overall, reverse=True)

    def get_top_focus(self, scores: List[RelevanceScore],
                      n: Optional[int] = None) -> List[RelevanceScore]:
        """Get the top n most relevant items."""
        n = n or self.max_focus_items
        ranked = self.rank_items(scores)
        return ranked[:n]

    # ==========================================
    # Attention Mode Control
    # ==========================================

    def set_mode(self, mode: AttentionMode,
                 center: Optional[Tuple[float, float]] = None,
                 radius: Optional[float] = None):
        """Change the attention mode."""
        self._current_focus.mode = mode
        if center is not None:
            self._current_focus.focus_center = center
        if radius is not None:
            self._current_focus.focus_radius = radius
        self._current_focus.timestamp = time.time()

        # Adjust weights based on mode
        if mode == AttentionMode.BROAD:
            self._weights = {
                "spatial": 0.25, "task": 0.25, "urgency": 0.15,
                "novelty": 0.20, "saliency": 0.15,
            }
        elif mode == AttentionMode.FOCUSED:
            self._weights = {
                "spatial": 0.35, "task": 0.40, "urgency": 0.10,
                "novelty": 0.05, "saliency": 0.10,
            }
        elif mode == AttentionMode.ALERT:
            self._weights = {
                "spatial": 0.20, "task": 0.15, "urgency": 0.40,
                "novelty": 0.10, "saliency": 0.15,
            }
        elif mode == AttentionMode.SELECTIVE:
            self._weights = {
                "spatial": 0.15, "task": 0.45, "urgency": 0.20,
                "novelty": 0.10, "saliency": 0.10,
            }

    def check_alerts(self, conditions: Dict[str, float]) -> bool:
        """
        Check if any alert conditions are triggered.
        Returns True if mode should switch to ALERT.
        """
        for name, value in conditions.items():
            trigger = self._alert_conditions.get(name)
            if trigger and trigger(value):
                self.set_mode(AttentionMode.ALERT)
                return True
        return False

    def register_alert(self, name: str, condition_fn):
        """Register an alert condition function."""
        self._alert_conditions[name] = condition_fn

    # ==========================================
    # Attention Filtering
    # ==========================================

    def add_filter(self, filter_obj: AttentionFilter):
        """Add an attention filter."""
        self._filters.append(filter_obj)

    def apply_filters(self, scores: List[RelevanceScore]) -> List[RelevanceScore]:
        """Apply all active filters to relevance scores."""
        result = list(scores)
        for f in self._filters:
            result = [
                s for s in result
                if s.target_type == f.filter_type or s.overall >= f.min_relevance
            ]
            result = result[:f.max_items]
        return result

    # ==========================================
    # Spatial Attention Map
    # ==========================================

    def compute_attention_map(self, items: List[Tuple[str, Tuple[float, float], AttentionTarget, float]],
                               grid_width: int = 50,
                               grid_height: int = 50) -> List[List[float]]:
        """
        Compute a 2D attention heatmap over the grid.
        
        items: list of (id, (x, y), type, urgency)
        Returns: 2D grid of attention values [0, 1]
        """
        attn_map = [[0.0] * grid_width for _ in range(grid_height)]

        for item_id, (ix, iy), item_type, urgency in items:
            for gy in range(grid_height):
                for gx in range(grid_width):
                    dist = math.sqrt((gx - ix) ** 2 + (gy - iy) ** 2)
                    if dist < self.attention_range:
                        # Gaussian falloff
                        sigma = self._current_focus.focus_radius / 3.0
                        attention = math.exp(-0.5 * (dist / max(sigma, 0.1)) ** 2)
                        attention *= urgency
                        attn_map[gy][gx] = min(1.0, attn_map[gy][gx] + attention)

        return attn_map

    # ==========================================
    # Attention History & Diagnostics
    # ==========================================

    def get_attention_history(self, last_n: int = 20) -> List[Tuple[float, str, float]]:
        """Get recent attention log entries."""
        return self._attention_log[-last_n:]

    def log_attention(self, item_id: str, relevance: float):
        """Log an attention event."""
        self._attention_log.append((time.time(), item_id, relevance))
        if len(self._attention_log) > 200:
            self._attention_log.pop(0)

    def get_current_focus(self) -> AttentionFocus:
        """Get current attention focus state."""
        return self._current_focus

    def get_attention_summary(self) -> Dict[str, Any]:
        """Get summary of attention state."""
        focus = self._current_focus
        return {
            "mode": focus.mode.value,
            "center": focus.focus_center,
            "radius": focus.focus_radius,
            "focus_count": len(focus.focus_targets),
            "weights": dict(self._weights),
            "seen_items": len(self._seen_items),
            "log_size": len(self._attention_log),
        }

    def reset(self):
        """Reset attention state."""
        self._current_focus = AttentionFocus()
        self._seen_items.clear()
        self._habituation.clear()
        self._attention_log.clear()

    # ==========================================
    # Internal Helpers
    # ==========================================

    @staticmethod
    def _point_to_line_distance(point: Tuple[float, float],
                                 line_start: Tuple[float, float],
                                 line_end: Tuple[float, float]) -> float:
        """Distance from point to line segment."""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end

        dx = x2 - x1
        dy = y2 - y1
        len_sq = dx * dx + dy * dy

        if len_sq == 0:
            return math.sqrt((x0 - x1) ** 2 + (y0 - y1) ** 2)

        t = max(0.0, min(1.0, ((x0 - x1) * dx + (y0 - y1) * dy) / len_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy

        return math.sqrt((x0 - proj_x) ** 2 + (y0 - proj_y) ** 2)

    def __repr__(self) -> str:
        mode = self._current_focus.mode.value
        seen = len(self._seen_items)
        return f"AttentionMechanism(mode={mode}, seen={seen})"