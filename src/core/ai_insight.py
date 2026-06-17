"""
AI Insight Engine — Post-Mission Analysis
===========================================
Generates automatic post-mission reports including:
  - Mission summary
  - Flight efficiency
  - Energy usage
  - Obstacle encounters
  - Planning quality
  - Prediction accuracy
  - Confidence trends
  - Lessons learned
  - Improvement suggestions

Explains itself like a senior engineer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .data_recorder import DataRecorder


@dataclass
class InsightReport:
    """A complete post-mission analysis report."""
    mission_id: str = ""
    generated_at: float = 0.0
    summary: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    grade: str = "A"


class AIInsightEngine:
    """
    Generates intelligent post-mission analysis reports.
    """

    def __init__(self, recorder: DataRecorder):
        self.recorder = recorder
        self.reports: List[InsightReport] = []

    def generate_report(self, mission_id: str = "default") -> InsightReport:
        """Generate a complete post-mission analysis."""
        report = InsightReport(
            mission_id=mission_id,
            generated_at=time.time(),
        )

        # Section 1: Mission Summary
        summary = self._analyze_summary()
        report.sections["mission_summary"] = summary["text"]
        report.metrics.update(summary["metrics"])

        # Section 2: Flight Efficiency
        efficiency = self._analyze_efficiency()
        report.sections["flight_efficiency"] = efficiency["text"]
        report.metrics.update(efficiency["metrics"])

        # Section 3: Energy Usage
        energy = self._analyze_energy()
        report.sections["energy_usage"] = energy["text"]
        report.metrics.update(energy["metrics"])

        # Section 4: Planning Quality
        planning = self._analyze_planning()
        report.sections["planning_quality"] = planning["text"]
        report.metrics.update(planning["metrics"])

        # Section 5: AI Decisions
        decisions = self._analyze_decisions()
        report.sections["ai_decisions"] = decisions["text"]
        report.metrics.update(decisions["metrics"])

        # Generate suggestions
        report.suggestions = self._generate_suggestions(report.metrics)

        # Overall grade
        report.grade = self._compute_grade(report.metrics)

        report.summary = (
            f"Mission {mission_id} | Grade: {report.grade} | "
            f"Frames: {report.metrics.get('total_frames', 0)} | "
            f"Suggestions: {len(report.suggestions)}"
        )

        self.reports.append(report)
        return report

    def _analyze_summary(self) -> Dict:
        tel = self.recorder.telemetry
        if not tel:
            return {"text": "No telemetry data available.", "metrics": {}}

        duration = tel[-1].timestamp - tel[0].timestamp
        total_frames = len(tel)

        return {
            "text": (
                f"Mission lasted {duration:.1f}s over {total_frames} frames. "
                f"Drone traveled from ({tel[0].x:.1f},{tel[0].y:.1f}) "
                f"to ({tel[-1].x:.1f},{tel[-1].y:.1f}). "
                f"Final battery: {tel[-1].battery:.1f}%."
            ),
            "metrics": {
                "duration_seconds": duration,
                "total_frames": total_frames,
                "start_x": tel[0].x, "start_y": tel[0].y,
                "end_x": tel[-1].x, "end_y": tel[-1].y,
                "final_battery": tel[-1].battery,
            },
        }

    def _analyze_efficiency(self) -> Dict:
        tel = self.recorder.telemetry
        if len(tel) < 2:
            return {"text": "Insufficient data.", "metrics": {}}

        import math
        # Compute total distance traveled
        total_dist = 0
        for i in range(1, len(tel)):
            dx = tel[i].x - tel[i-1].x
            dy = tel[i].y - tel[i-1].y
            total_dist += math.sqrt(dx*dx + dy*dy)

        # Direct distance
        direct = math.sqrt(
            (tel[-1].x - tel[0].x)**2 + (tel[-1].y - tel[0].y)**2
        )
        efficiency = (direct / max(0.1, total_dist)) * 100

        return {
            "text": (
                f"Total distance: {total_dist:.1f}m | "
                f"Direct distance: {direct:.1f}m | "
                f"Flight efficiency: {efficiency:.1f}% | "
                f"{'Efficient path' if efficiency > 70 else 'Path could be optimized'}"
            ),
            "metrics": {
                "total_distance": total_dist,
                "direct_distance": direct,
                "flight_efficiency_pct": efficiency,
            },
        }

    def _analyze_energy(self) -> Dict:
        tel = self.recorder.telemetry
        if not tel:
            return {"text": "No data.", "metrics": {}}

        battery_used = tel[0].battery - tel[-1].battery
        import math
        total_dist = sum(
            math.sqrt((tel[i].x-tel[i-1].x)**2 + (tel[i].y-tel[i-1].y)**2)
            for i in range(1, len(tel))
        )
        energy_per_meter = battery_used / max(0.1, total_dist)

        return {
            "text": (
                f"Battery used: {battery_used:.1f}% | "
                f"Energy efficiency: {energy_per_meter:.2f}%/m | "
                f"{'Good energy management' if energy_per_meter < 1.0 else 'Consider energy optimization'}"
            ),
            "metrics": {
                "battery_used_pct": battery_used,
                "energy_per_meter": energy_per_meter,
            },
        }

    def _analyze_planning(self) -> Dict:
        planning = self.recorder.planning
        if not planning:
            return {"text": "No planning data.", "metrics": {}}

        replans = sum(1 for p in planning if p.replan_reason)
        avg_path_len = sum(p.path_length for p in planning) / len(planning)

        return {
            "text": (
                f"Planning events: {len(planning)} | "
                f"Replans: {replans} | "
                f"Average path length: {avg_path_len:.0f} | "
                f"{'Stable planning' if replans < len(planning)*0.3 else 'Frequent replanning detected'}"
            ),
            "metrics": {
                "planning_events": len(planning),
                "replan_count": replans,
                "avg_path_length": avg_path_len,
            },
        }

    def _analyze_decisions(self) -> Dict:
        decisions = self.recorder.decisions
        if not decisions:
            return {"text": "No decision data.", "metrics": {}}

        avg_confidence = sum(d.confidence for d in decisions) / len(decisions)
        decision_types = {}
        for d in decisions:
            decision_types[d.decision_type] = decision_types.get(d.decision_type, 0) + 1

        return {
            "text": (
                f"AI decisions made: {len(decisions)} | "
                f"Average confidence: {avg_confidence:.2f} | "
                f"Decision types: {', '.join(decision_types.keys())}"
            ),
            "metrics": {
                "total_decisions": len(decisions),
                "avg_confidence": avg_confidence,
            },
        }

    def _generate_suggestions(self, metrics: Dict) -> List[str]:
        suggestions = []
        eff = metrics.get("flight_efficiency_pct", 100)
        if eff < 60:
            suggestions.append(
                f"Flight efficiency is {eff:.0f}%. Consider using a more direct "
                "path planner or reducing obstacle avoidance radius."
            )
        energy = metrics.get("energy_per_meter", 0)
        if energy > 1.5:
            suggestions.append(
                "High energy consumption per meter. Consider reducing speed "
                "or optimizing flight altitude."
            )
        replans = metrics.get("replan_count", 0)
        total_plans = metrics.get("planning_events", 1)
        if replans > total_plans * 0.4:
            suggestions.append(
                "Frequent replanning detected. Consider improving perception "
                "accuracy or increasing sensor range."
            )
        conf = metrics.get("avg_confidence", 1)
        if conf < 0.7:
            suggestions.append(
                "Low AI confidence. Consider retraining models or "
                "adding more training data."
            )
        battery = metrics.get("final_battery", 100)
        if battery < 20:
            suggestions.append(
                "Low remaining battery. Consider adding a charging "
                "stop to the mission plan."
            )
        if not suggestions:
            suggestions.append("Mission performed well. No critical improvements needed.")

        return suggestions

    def _compute_grade(self, metrics: Dict) -> str:
        score = 100
        eff = metrics.get("flight_efficiency_pct", 50)
        score -= max(0, (70 - eff))
        replans = metrics.get("replan_count", 0)
        total = max(1, metrics.get("planning_events", 1))
        score -= min(20, replans / total * 40)
        conf = metrics.get("avg_confidence", 0.8)
        score -= max(0, (0.8 - conf) * 50)

        if score >= 90: return "A+"
        if score >= 80: return "A"
        if score >= 70: return "B"
        if score >= 60: return "C"
        if score >= 50: return "D"
        return "F"

    def get_all_reports(self) -> List[InsightReport]:
        return self.reports