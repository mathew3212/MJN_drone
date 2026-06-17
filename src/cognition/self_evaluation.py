"""
Self-Evaluation System
=======================

Continuous self-assessment of performance, capability estimation,
and confidence scoring for all decisions and actions.

Key Features:
    - Performance metric tracking across episodes
    - Capability assessment (what can the system do well/poorly)
    - Strength and weakness identification
    - Self-improvement tracking over time
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


class MetricType(Enum):
    SUCCESS_RATE = "success_rate"
    EFFICIENCY = "efficiency"
    SAFETY = "safety"
    ACCURACY = "accuracy"
    RESPONSE_TIME = "response_time"
    RESOURCE_USAGE = "resource_usage"


class CapabilityLevel(Enum):
    NOVICE = 1
    DEVELOPING = 2
    COMPETENT = 3
    PROFICIENT = 4
    EXPERT = 5


@dataclass
class PerformanceMetric:
    """A single performance measurement."""
    metric_type: MetricType
    value: float
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0

    @property
    def is_good(self) -> bool:
        return self.value > 0.7


@dataclass
class CapabilityAssessment:
    """Assessment of a specific capability."""
    capability: str
    level: CapabilityLevel
    confidence: float
    evidence_count: int
    recent_trend: str = "stable"  # improving, declining, stable
    last_assessed: float = field(default_factory=time.time)

    @property
    def score(self) -> float:
        return self.level.value / 5.0


@dataclass
class EvaluationReport:
    """Comprehensive evaluation report."""
    timestamp: float
    overall_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    metric_averages: Dict[str, float]
    capabilities: Dict[str, str]
    explanation: str = ""


class SelfEvaluator:
    """
    Continuously evaluates system performance, identifies strengths
    and weaknesses, and recommends improvements.
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._metrics: Dict[str, List[PerformanceMetric]] = {}
        self._capabilities: Dict[str, CapabilityAssessment] = {}
        self._evaluation_history: List[EvaluationReport] = []
        self._episode_count = 0
        self._total_scores: List[float] = []

    def record_metric(self, metric_type: MetricType, value: float,
                      context: Optional[Dict[str, Any]] = None):
        """Record a performance metric."""
        key = metric_type.value
        if key not in self._metrics:
            self._metrics[key] = []
        self._metrics[key].append(PerformanceMetric(
            metric_type=metric_type, value=value, context=context or {},
        ))
        if len(self._metrics[key]) > self.window_size:
            self._metrics[key].pop(0)

    def record_episode_outcome(self, success: bool, duration: float,
                               energy_used: float, distance_covered: float,
                               collisions: int = 0):
        """Record the outcome of an episode for evaluation."""
        self._episode_count += 1
        self.record_metric(MetricType.SUCCESS_RATE, 1.0 if success else 0.0)
        efficiency = min(1.0, distance_covered / max(energy_used, 0.01))
        self.record_metric(MetricType.EFFICIENCY, efficiency)
        safety = max(0.0, 1.0 - collisions * 0.3)
        self.record_metric(MetricType.SAFETY, safety)
        if duration > 0:
            response = max(0.0, 1.0 - min(1.0, duration / 300.0))
            self.record_metric(MetricType.RESPONSE_TIME, response)

        score = (0.4 * (1.0 if success else 0.0) + 0.3 * efficiency + 0.3 * safety)
        self._total_scores.append(score)

    def assess_capability(self, capability: str, success: bool):
        """Assess a specific capability based on an outcome."""
        if capability not in self._capabilities:
            self._capabilities[capability] = CapabilityAssessment(
                capability=capability, level=CapabilityLevel.DEVELOPING,
                confidence=0.3, evidence_count=0,
            )
        cap = self._capabilities[capability]
        cap.evidence_count += 1
        cap.last_assessed = time.time()

        # Update level based on success rate
        if cap.evidence_count >= 3:
            recent_successes = min(cap.evidence_count, 5)
            success_rate = 1.0 if success else 0.0

            if success_rate > 0.8 and cap.level.value < 5:
                new_level = CapabilityLevel(min(5, cap.level.value + 1))
                cap.recent_trend = "improving"
            elif success_rate < 0.3 and cap.level.value > 1:
                new_level = CapabilityLevel(max(1, cap.level.value - 1))
                cap.recent_trend = "declining"
            else:
                new_level = cap.level
                cap.recent_trend = "stable"

            cap.level = new_level
            cap.confidence = min(1.0, cap.evidence_count / 20.0)

    def evaluate(self) -> EvaluationReport:
        """Generate a comprehensive evaluation report."""
        metric_avgs = {}
        for key, metrics in self._metrics.items():
            if metrics:
                metric_avgs[key] = sum(m.value for m in metrics) / len(metrics)

        strengths = []
        weaknesses = []
        recommendations = []

        for key, avg in metric_avgs.items():
            if avg > 0.7:
                strengths.append(f"Strong {key} ({avg:.1%})")
            elif avg < 0.4:
                weaknesses.append(f"Weak {key} ({avg:.1%})")
                recommendations.append(f"Focus on improving {key}")

        for cap in self._capabilities.values():
            if cap.level.value >= 4:
                strengths.append(f"Expert-level {cap.capability}")
            elif cap.level.value <= 2:
                weaknesses.append(f"Developing {cap.capability}")
                recommendations.append(f"Practice {cap.capability} more")

        overall = sum(self._total_scores[-self.window_size:]) / max(1, len(self._total_scores[-self.window_size:]))

        report = EvaluationReport(
            timestamp=time.time(),
            overall_score=overall,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            metric_averages=metric_avgs,
            capabilities={c.capability: c.level.name for c in self._capabilities.values()},
            explanation=f"Overall score: {overall:.2f}. {len(strengths)} strengths, {len(weaknesses)} weaknesses identified.",
        )
        self._evaluation_history.append(report)
        return report

    def get_overall_score(self) -> float:
        if not self._total_scores:
            return 0.5
        recent = self._total_scores[-self.window_size:]
        return sum(recent) / len(recent)

    def get_capability(self, name: str) -> Optional[CapabilityAssessment]:
        return self._capabilities.get(name)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "episode_count": self._episode_count,
            "overall_score": self.get_overall_score(),
            "metrics_tracked": len(self._metrics),
            "capabilities": len(self._capabilities),
            "evaluations": len(self._evaluation_history),
        }

    def __repr__(self) -> str:
        return f"SelfEvaluator(episodes={self._episode_count}, score={self.get_overall_score():.2f})"