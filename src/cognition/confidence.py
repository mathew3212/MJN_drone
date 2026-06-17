"""
Confidence Estimation
======================

Estimates confidence levels for all decisions, predictions, and
actions. Provides confidence scoring that accounts for evidence
quality, uncertainty, and historical accuracy.

Key Features:
    - Multi-factor confidence scoring
    - Evidence-based confidence
    - Historical accuracy calibration
    - Confidence decay over time
    - Risk-adjusted confidence levels
"""

import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


class ConfidenceLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"

    @classmethod
    def from_value(cls, value: float) -> 'ConfidenceLevel':
        if value >= 0.9:
            return cls.VERY_HIGH
        elif value >= 0.7:
            return cls.HIGH
        elif value >= 0.5:
            return cls.MODERATE
        elif value >= 0.3:
            return cls.LOW
        return cls.VERY_LOW


@dataclass
class ConfidenceReport:
    """Detailed confidence report for a decision or action."""
    target: str
    overall_confidence: float
    level: ConfidenceLevel
    factors: Dict[str, float]
    evidence_quality: float
    historical_accuracy: float
    uncertainty_contribution: float
    timestamp: float = field(default_factory=time.time)
    explanation: str = ""

    @property
    def is_acceptable(self) -> bool:
        return self.overall_confidence >= 0.5


@dataclass
class ConfidenceFactor:
    """A factor contributing to confidence."""
    name: str
    value: float
    weight: float
    description: str = ""

    @property
    def contribution(self) -> float:
        return self.value * self.weight


class ConfidenceEstimator:
    """
    Estimates confidence for decisions, predictions, and actions
    by combining multiple factors.
    """

    def __init__(self):
        # Default factor weights
        self._factor_weights = {
            "evidence_quality": 0.25,
            "historical_accuracy": 0.25,
            "model_confidence": 0.20,
            "data_freshness": 0.15,
            "consistency": 0.15,
        }

        # Historical accuracy tracking
        self._accuracy_history: Dict[str, List[float]] = {}
        self._confidence_reports: List[ConfidenceReport] = []

        # Calibration data
        self._calibration_points: Dict[str, List[Tuple[float, bool]]] = {}

    def estimate_confidence(self, target: str,
                             evidence: Dict[str, float],
                             model_confidence: float = 0.8,
                             data_age: float = 0.0,
                             consistency: float = 0.8) -> ConfidenceReport:
        """
        Estimate overall confidence for a target (decision, prediction, etc.).
        
        Args:
            target: What we're estimating confidence for
            evidence: Dict of evidence_name -> quality_score [0, 1]
            model_confidence: Confidence in the model itself [0, 1]
            data_age: Age of data in seconds (older = less confident)
            consistency: How consistent are recent predictions [0, 1]
        """
        # 1. Evidence quality
        if evidence:
            evidence_quality = sum(evidence.values()) / len(evidence)
        else:
            evidence_quality = 0.3  # Low confidence without evidence

        # 2. Historical accuracy
        historical_accuracy = self._get_historical_accuracy(target)

        # 3. Data freshness (exponential decay)
        data_freshness = math.exp(-data_age / 300.0)  # 5-min half-life

        # 4. Compute weighted confidence
        factors = {
            "evidence_quality": evidence_quality * self._factor_weights["evidence_quality"],
            "historical_accuracy": historical_accuracy * self._factor_weights["historical_accuracy"],
            "model_confidence": model_confidence * self._factor_weights["model_confidence"],
            "data_freshness": data_freshness * self._factor_weights["data_freshness"],
            "consistency": consistency * self._factor_weights["consistency"],
        }

        overall = sum(factors.values())
        overall = max(0.0, min(1.0, overall))

        # Uncertainty contribution (how much uncertainty reduces confidence)
        uncertainty_contribution = 1.0 - overall

        level = ConfidenceLevel.from_value(overall)

        explanation = (
            f"Confidence in '{target}': {overall:.1%} ({level.value}). "
            f"Evidence quality: {evidence_quality:.2f}, "
            f"Historical accuracy: {historical_accuracy:.2f}, "
            f"Model confidence: {model_confidence:.2f}"
        )

        report = ConfidenceReport(
            target=target,
            overall_confidence=overall,
            level=level,
            factors=factors,
            evidence_quality=evidence_quality,
            historical_accuracy=historical_accuracy,
            uncertainty_contribution=uncertainty_contribution,
            explanation=explanation,
        )

        self._confidence_reports.append(report)
        if len(self._confidence_reports) > 500:
            self._confidence_reports.pop(0)

        return report

    def record_outcome(self, target: str, confidence: float,
                       was_correct: bool):
        """Record whether a confident prediction/decision was correct."""
        if target not in self._accuracy_history:
            self._accuracy_history[target] = []
        self._accuracy_history[target].append(1.0 if was_correct else 0.0)
        if len(self._accuracy_history[target]) > 100:
            self._accuracy_history[target].pop(0)

        # Update calibration data
        if target not in self._calibration_points:
            self._calibration_points[target] = []
        self._calibration_points[target].append((confidence, was_correct))
        if len(self._calibration_points[target]) > 200:
            self._calibration_points[target].pop(0)

    def _get_historical_accuracy(self, target: str) -> float:
        history = self._accuracy_history.get(target, [])
        if not history:
            return 0.5  # Default: uncertain
        recent = history[-20:]
        return sum(recent) / len(recent)

    def compute_brier_score(self, target: str) -> Optional[float]:
        """Compute Brier score for calibration (lower is better)."""
        points = self._calibration_points.get(target, [])
        if not points:
            return None
        score = sum((conf - (1.0 if correct else 0.0)) ** 2
                    for conf, correct in points) / len(points)
        return score

    def is_well_calibrated(self, target: str,
                            max_brier: float = 0.25) -> bool:
        brier = self.compute_brier_score(target)
        return brier is not None and brier <= max_brier

    def adjust_confidence_for_risk(self, confidence: float,
                                    risk_level: float) -> float:
        """Adjust confidence based on risk level."""
        risk_penalty = risk_level * 0.3
        return max(0.0, confidence - risk_penalty)

    def get_confidence_trend(self, target: str,
                              window: int = 10) -> str:
        """Determine if confidence is trending up or down."""
        reports = [r for r in self._confidence_reports if r.target == target]
        if len(reports) < window:
            return "insufficient_data"
        recent = reports[-window:]
        first_half = sum(r.overall_confidence for r in recent[:window // 2]) / (window // 2)
        second_half = sum(r.overall_confidence for r in recent[window // 2:]) / (window // 2)
        diff = second_half - first_half
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        return "stable"

    def get_recent_reports(self, n: int = 10) -> List[ConfidenceReport]:
        return self._confidence_reports[-n:]

    def get_statistics(self) -> Dict[str, Any]:
        if not self._confidence_reports:
            return {"total_reports": 0}
        avg_conf = sum(r.overall_confidence for r in self._confidence_reports) / len(self._confidence_reports)
        return {
            "total_reports": len(self._confidence_reports),
            "avg_confidence": avg_conf,
            "targets_tracked": len(self._accuracy_history),
            "well_calibrated_count": sum(
                1 for t in self._calibration_points if self.is_well_calibrated(t)
            ),
        }

    def __repr__(self) -> str:
        n = len(self._confidence_reports)
        return f"ConfidenceEstimator(reports={n})"