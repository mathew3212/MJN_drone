"""
Uncertainty Estimation
=======================

Quantifies uncertainty in beliefs, predictions, and decisions.
Uses multiple methods including ensemble disagreement, variance
estimation, calibration tracking, and information-theoretic measures.

Key Capabilities:
    - Multi-method uncertainty estimation
    - Ensemble-based uncertainty (disagreement)
    - Variance tracking over time
    - Calibration monitoring (are we well-calibrated?)
    - Epistemic vs aleatoric uncertainty separation
    - Uncertainty-aware decision making
"""

import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


class UncertaintyMethod(Enum):
    """Methods for estimating uncertainty."""
    VARIANCE = "variance"
    ENSEMBLE = "ensemble"
    CALIBRATION = "calibration"
    ENTROPY = "entropy"
    CONFIDENCE_INTERVAL = "confidence_interval"
    BAYESIAN = "bayesian"


class UncertaintyType(Enum):
    """Types of uncertainty."""
    EPISTEMIC = "epistemic"      # Due to lack of knowledge (reducible)
    ALEATORIC = "aleatoric"      # Due to inherent noise (irreducible)
    TOTAL = "total"              # Combined uncertainty


@dataclass
class UncertaintyProfile:
    """Complete uncertainty profile for a variable or decision."""
    name: str
    uncertainty_type: UncertaintyType = UncertaintyType.TOTAL
    mean: float = 0.0
    variance: float = 0.0
    std_dev: float = 0.0
    confidence: float = 1.0
    confidence_interval_95: Tuple[float, float] = (0.0, 0.0)
    entropy: float = 0.0
    calibration_error: float = 0.0
    sample_count: int = 0
    method: UncertaintyMethod = UncertaintyMethod.VARIANCE
    timestamp: float = field(default_factory=time.time)
    explanation: str = ""

    @property
    def uncertainty(self) -> float:
        """Overall uncertainty measure (0=certain, 1=very uncertain)."""
        return min(1.0, self.variance * 4.0) if self.variance > 0 else 0.0

    def is_reliable(self, threshold: float = 0.5) -> bool:
        """Check if this estimate is reliable (low enough uncertainty)."""
        return self.uncertainty < threshold


class UncertaintyEstimator:
    """
    Estimates uncertainty in beliefs and predictions using
    multiple methods.
    """

    def __init__(self, history_size: int = 100):
        self.history_size = history_size

        # Prediction tracking
        self._predictions: Dict[str, List[Tuple[float, float]]] = {}
        # name -> [(predicted, actual), ...]

        # Ensemble predictions
        self._ensemble_predictions: Dict[str, List[float]] = {}
        # name -> [pred_1, pred_2, ..., pred_n]

        # Calibration tracking
        self._calibration_data: Dict[str, List[Tuple[float, bool]]] = {}
        # name -> [(predicted_prob, was_correct), ...]

        # Running statistics
        self._running_stats: Dict[str, Dict[str, float]] = {}

        # Uncertainty profiles
        self._profiles: Dict[str, UncertaintyProfile] = {}

    # ==========================================
    # Variance-Based Estimation
    # ==========================================

    def estimate_from_variance(self, name: str,
                                values: List[float]) -> UncertaintyProfile:
        """Estimate uncertainty from variance of observed values."""
        if len(values) < 2:
            return UncertaintyProfile(
                name=name,
                method=UncertaintyMethod.VARIANCE,
                sample_count=len(values),
                explanation="Insufficient data for variance estimation",
            )

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        std_dev = math.sqrt(variance)

        # 95% confidence interval (using t-distribution approximation)
        t_value = 1.96  # Approximate for large n
        if len(values) < 30:
            # Approximate t-value for small samples
            t_value = 2.0 + (30 - len(values)) * 0.05
        margin = t_value * std_dev / math.sqrt(len(values))
        ci_95 = (mean - margin, mean + margin)

        # Entropy estimate (for Gaussian approximation)
        entropy = 0.5 * math.log(2 * math.pi * math.e * variance) if variance > 0 else 0.0

        profile = UncertaintyProfile(
            name=name,
            uncertainty_type=UncertaintyType.ALEATORIC,
            mean=mean,
            variance=variance,
            std_dev=std_dev,
            confidence=max(0.0, 1.0 - min(1.0, variance * 2)),
            confidence_interval_95=ci_95,
            entropy=max(0.0, min(1.0, entropy / 5.0)),
            sample_count=len(values),
            method=UncertaintyMethod.VARIANCE,
        )

        profile.explanation = (
            f"Variance-based estimate from {len(values)} samples: "
            f"mean={mean:.3f}, σ²={variance:.4f}, "
            f"95% CI=[{ci_95[0]:.3f}, {ci_95[1]:.3f}]"
        )

        self._profiles[name] = profile
        return profile

    # ==========================================
    # Ensemble-Based Estimation
    # ==========================================

    def add_ensemble_prediction(self, name: str, prediction: float):
        """Add a prediction from an ensemble member."""
        if name not in self._ensemble_predictions:
            self._ensemble_predictions[name] = []
        self._ensemble_predictions[name].append(prediction)
        # Keep limited history
        if len(self._ensemble_predictions[name]) > 50:
            self._ensemble_predictions[name].pop(0)

    def estimate_from_ensemble(self, name: str) -> UncertaintyProfile:
        """Estimate uncertainty from ensemble disagreement."""
        preds = self._ensemble_predictions.get(name, [])

        if len(preds) < 2:
            return UncertaintyProfile(
                name=name,
                method=UncertaintyMethod.ENSEMBLE,
                sample_count=len(preds),
                explanation="Insufficient ensemble members",
            )

        mean = sum(preds) / len(preds)
        variance = sum((p - mean) ** 2 for p in preds) / len(preds)
        std_dev = math.sqrt(variance)

        # Ensemble disagreement normalized
        disagreement = std_dev / max(abs(mean), 1e-6)

        profile = UncertaintyProfile(
            name=name,
            uncertainty_type=UncertaintyType.EPISTEMIC,
            mean=mean,
            variance=variance,
            std_dev=std_dev,
            confidence=max(0.0, 1.0 - min(1.0, disagreement * 2)),
            sample_count=len(preds),
            method=UncertaintyMethod.ENSEMBLE,
        )

        # 95% CI from ensemble
        sorted_preds = sorted(preds)
        lower_idx = max(0, int(0.025 * len(sorted_preds)))
        upper_idx = min(len(sorted_preds) - 1, int(0.975 * len(sorted_preds)))
        profile.confidence_interval_95 = (sorted_preds[lower_idx], sorted_preds[upper_idx])

        profile.explanation = (
            f"Ensemble estimate from {len(preds)} members: "
            f"mean={mean:.3f}, disagreement={disagreement:.3f}, "
            f"confidence={profile.confidence:.3f}"
        )

        self._profiles[name] = profile
        return profile

    # ==========================================
    # Prediction Error Tracking
    # ==========================================

    def record_prediction(self, name: str,
                           predicted: float, actual: float):
        """Record a prediction vs actual for calibration."""
        if name not in self._predictions:
            self._predictions[name] = []
        self._predictions[name].append((predicted, actual))
        if len(self._predictions[name]) > self.history_size:
            self._predictions[name].pop(0)

        # Update running statistics
        error = abs(predicted - actual)
        if name not in self._running_stats:
            self._running_stats[name] = {
                "sum_error": 0, "sum_sq_error": 0, "count": 0,
                "max_error": 0,
            }
        stats = self._running_stats[name]
        stats["sum_error"] += error
        stats["sum_sq_error"] += error ** 2
        stats["count"] += 1
        stats["max_error"] = max(stats["max_error"], error)

    def get_prediction_stats(self, name: str) -> Dict[str, float]:
        """Get prediction error statistics."""
        stats = self._running_stats.get(name, {})
        count = stats.get("count", 0)
        if count == 0:
            return {"mae": 0, "rmse": 0, "max_error": 0, "count": 0}

        mae = stats["sum_error"] / count
        rmse = math.sqrt(stats["sum_sq_error"] / count)
        return {
            "mae": mae,
            "rmse": rmse,
            "max_error": stats["max_error"],
            "count": count,
        }

    def estimate_from_errors(self, name: str) -> UncertaintyProfile:
        """Estimate uncertainty from historical prediction errors."""
        predictions = self._predictions.get(name, [])
        if len(predictions) < 2:
            return UncertaintyProfile(
                name=name,
                method=UncertaintyMethod.VARIANCE,
                sample_count=len(predictions),
                explanation="Not enough prediction history",
            )

        errors = [abs(p - a) for p, a in predictions]
        return self.estimate_from_variance(f"{name}_errors", errors)

    # ==========================================
    # Calibration
    # ==========================================

    def record_calibration(self, name: str,
                           predicted_prob: float, was_correct: bool):
        """Record a calibration data point."""
        if name not in self._calibration_data:
            self._calibration_data[name] = []
        self._calibration_data[name].append((predicted_prob, was_correct))
        if len(self._calibration_data[name]) > self.history_size:
            self._calibration_data[name].pop(0)

    def compute_calibration_error(self, name: str,
                                   n_bins: int = 10) -> float:
        """
        Compute Expected Calibration Error (ECE).
        Lower is better (0 = perfectly calibrated).
        """
        data = self._calibration_data.get(name, [])
        if len(data) < n_bins:
            return 1.0  # Max uncertainty when not enough data

        bins = [[] for _ in range(n_bins)]
        for prob, correct in data:
            bin_idx = min(int(prob * n_bins), n_bins - 1)
            bins[bin_idx].append(correct)

        total_error = 0.0
        total_samples = len(data)
        for i, bin_data in enumerate(bins):
            if not bin_data:
                continue
            bin_confidence = (i + 0.5) / n_bins  # Midpoint of bin
            bin_accuracy = sum(bin_data) / len(bin_data)
            bin_weight = len(bin_data) / total_samples
            total_error += bin_weight * abs(bin_accuracy - bin_confidence)

        return total_error

    def is_well_calibrated(self, name: str,
                            max_ece: float = 0.1) -> bool:
        """Check if predictions are well-calibrated."""
        ece = self.compute_calibration_error(name)
        return ece <= max_ece

    # ==========================================
    # Combined Estimation
    # ==========================================

    def estimate_combined(self, name: str,
                          values: Optional[List[float]] = None,
                          ensemble_preds: Optional[List[float]] = None,
                          prediction_errors: Optional[List[Tuple[float, float]]] = None
                          ) -> UncertaintyProfile:
        """
        Combined uncertainty estimation using multiple methods.
        Separates epistemic and aleatoric uncertainty.
        """
        profiles = []

        if values and len(values) >= 2:
            profiles.append(self.estimate_from_variance(f"{name}_var", values))

        if ensemble_preds and len(ensemble_preds) >= 2:
            for p in ensemble_preds:
                self.add_ensemble_prediction(f"{name}_ens", p)
            profiles.append(self.estimate_from_ensemble(f"{name}_ens"))

        if prediction_errors:
            for pred, actual in prediction_errors:
                self.record_prediction(f"{name}_err", pred, actual)
            profiles.append(self.estimate_from_errors(f"{name}_err"))

        if not profiles:
            return UncertaintyProfile(
                name=name,
                method=UncertaintyMethod.VARIANCE,
                explanation="No data available for uncertainty estimation",
            )

        # Combine: take the maximum uncertainty across methods
        combined = max(profiles, key=lambda p: p.uncertainty)

        # Try to separate epistemic from aleatoric
        epistemic = [p for p in profiles
                     if p.uncertainty_type == UncertaintyType.EPISTEMIC]
        aleatoric = [p for p in profiles
                     if p.uncertainty_type == UncertaintyType.ALEATORIC]

        result = UncertaintyProfile(
            name=name,
            uncertainty_type=UncertaintyType.TOTAL,
            mean=combined.mean,
            variance=combined.variance,
            std_dev=combined.std_dev,
            confidence=combined.confidence,
            confidence_interval_95=combined.confidence_interval_95,
            entropy=combined.entropy,
            sample_count=combined.sample_count,
            method=combined.method,
        )

        epistemic_str = f"{epistemic[0].uncertainty:.3f}" if epistemic else "N/A"
        aleatoric_str = f"{aleatoric[0].uncertainty:.3f}" if aleatoric else "N/A"

        result.explanation = (
            f"Combined uncertainty for '{name}': "
            f"total={result.uncertainty:.3f}, "
            f"epistemic={epistemic_str}, "
            f"aleatoric={aleatoric_str}, "
            f"confidence={result.confidence:.3f}"
        )

        self._profiles[name] = result
        return result

    # ==========================================
    # Uncertainty-Aware Decisions
    # ==========================================

    def should_act_under_uncertainty(self, uncertainty: float,
                                      risk_tolerance: float = 0.5,
                                      value_of_information: float = 0.0
                                      ) -> Tuple[bool, str]:
        """
        Decide whether to act given uncertainty level.
        
        Args:
            uncertainty: Current uncertainty level [0, 1]
            risk_tolerance: How much risk is acceptable [0, 1]
            value_of_information: Expected value of gathering more info
        
        Returns:
            (should_act, explanation)
        """
        if uncertainty < 0.2:
            return True, "Low uncertainty - confident to act"
        elif uncertainty < risk_tolerance:
            return True, (f"Moderate uncertainty ({uncertainty:.2f}) "
                          f"within risk tolerance ({risk_tolerance:.2f})")
        elif value_of_information > uncertainty:
            return False, (f"High uncertainty ({uncertainty:.2f}), "
                           f"information gathering more valuable "
                           f"(VoI={value_of_information:.2f})")
        else:
            return True, (f"Acting despite high uncertainty ({uncertainty:.2f}) "
                          f"- no better option available")

    def recommend_action(self, options: List[str],
                          option_uncertainties: Dict[str, float],
                          option_values: Dict[str, float],
                          risk_tolerance: float = 0.5
                          ) -> Tuple[str, str]:
        """
        Recommend the best action considering both value and uncertainty.
        Uses a simple risk-adjusted scoring: score = value - risk_tolerance * uncertainty
        """
        best_option = None
        best_score = -float('inf')
        scores = {}

        for option in options:
            unc = option_uncertainties.get(option, 0.5)
            val = option_values.get(option, 0.0)
            score = val - risk_tolerance * unc
            scores[option] = score
            if score > best_score:
                best_score = score
                best_option = option

        if best_option is None:
            return options[0] if options else "none", "No options available"

        explanation = (
            f"Recommended '{best_option}' with risk-adjusted score "
            f"{best_score:.3f} (value={option_values.get(best_option, 0):.2f}, "
            f"uncertainty={option_uncertainties.get(best_option, 0):.3f}). "
            f"All scores: {', '.join(f'{k}={v:.3f}' for k, v in sorted(scores.items(), key=lambda x: -x[1]))}"
        )

        return best_option, explanation

    # ==========================================
    # Queries & State
    # ==========================================

    def get_profile(self, name: str) -> Optional[UncertaintyProfile]:
        return self._profiles.get(name)

    def get_all_profiles(self) -> Dict[str, UncertaintyProfile]:
        return dict(self._profiles)

    def get_overall_uncertainty(self) -> float:
        """Average uncertainty across all tracked profiles."""
        profiles = list(self._profiles.values())
        if not profiles:
            return 0.5  # Default moderate uncertainty
        return sum(p.uncertainty for p in profiles) / len(profiles)

    def get_uncertainty_summary(self) -> Dict[str, Any]:
        profiles = list(self._profiles.values())
        return {
            "total_profiles": len(profiles),
            "avg_uncertainty": self.get_overall_uncertainty(),
            "high_uncertainty_count": sum(
                1 for p in profiles if p.uncertainty > 0.7
            ),
            "well_calibrated_count": sum(
                1 for n in self._calibration_data
                if self.is_well_calibrated(n)
            ),
            "predictions_tracked": len(self._predictions),
        }

    def reset(self):
        self._predictions.clear()
        self._ensemble_predictions.clear()
        self._calibration_data.clear()
        self._running_stats.clear()
        self._profiles.clear()

    def __repr__(self) -> str:
        n = len(self._profiles)
        avg = self.get_overall_uncertainty()
        return f"UncertaintyEstimator(profiles={n}, avg_uncertainty={avg:.3f})"