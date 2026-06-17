"""
Flight Analytics Dashboard
==========================
Live visualization for high-performance flight metrics.
Displays speed, acceleration, throttle, yaw, ETA, mission progress,
risk score, obstacle distance, and all latencies in real-time.
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# Color scheme for the dashboard
class DashboardColors:
    """ANSI color codes for dashboard."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    DIM = "\033[90m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_DIM = "\033[100m"


class FlightDashboard:
    """
    Live flight analytics dashboard.
    Displays real-time performance metrics in a compact terminal layout.
    Can also output structured data for external visualization.
    """

    def __init__(self, max_history: int = 200):
        self.max_history = max_history

        # Metric history for plots
        self.history: Dict[str, deque] = {
            "speed": deque(maxlen=max_history),
            "accel": deque(maxlen=max_history),
            "jerk": deque(maxlen=max_history),
            "target_speed": deque(maxlen=max_history),
            "yaw_rate": deque(maxlen=max_history),
            "planning_latency": deque(maxlen=max_history),
            "controller_latency": deque(maxlen=max_history),
            "risk_score": deque(maxlen=max_history),
            "eta": deque(maxlen=max_history),
            "mission_progress": deque(maxlen=max_history),
        }

        # Timing
        self._last_update: float = 0.0
        self._update_interval: float = 0.1  # 10 Hz refresh
        self._frame_count: int = 0

    def update(self, data: dict) -> None:
        """Update dashboard with new flight data."""
        now = time.time()
        if now - self._last_update < self._update_interval:
            return
        self._last_update = now
        self._frame_count += 1

        # Record history
        if "speed" in data:
            self.history["speed"].append(data["speed"]["current"])
            self.history["target_speed"].append(data["speed"]["target"])
        if "acceleration" in data:
            self.history["accel"].append(data["acceleration"]["current"])
        if "jerk" in data:
            self.history["jerk"].append(data["jerk"])
        if "yaw_rate" in data:
            self.history["yaw_rate"].append(data["yaw_rate"])
        if "latency" in data:
            self.history["planning_latency"].append(data["latency"]["planning"])
            self.history["controller_latency"].append(data["latency"]["controller"])
        if "risk" in data:
            self.history["risk_score"].append(data["risk"]["score"])
        if "eta" in data:
            self.history["eta"].append(data["eta"]["current"])
        if "mission" in data:
            self.history["mission_progress"].append(data["mission"]["progress"])

    def render(self, data: dict) -> str:
        """
        Render the dashboard as a colored terminal string.
        Returns a multi-line string for display.
        """
        lines = []
        C = DashboardColors

        # ── Title ──
        lines.append(f"{C.BOLD}{C.CYAN}{'='*70}{C.RESET}")
        lines.append(f"{C.BOLD}{C.CYAN}   HIGH-PERFORMANCE FLIGHT DASHBOARD{C.RESET}")
        lines.append(f"{C.BOLD}{C.CYAN}{'='*70}{C.RESET}")

        # ── Flight Mode ──
        mode = data.get("flight_mode", "NORMAL")
        mode_color = self._mode_color(mode)
        lines.append(f"  {C.BOLD}Flight Mode: {mode_color}{mode}{C.RESET}  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{C.BOLD}Battery: {C.RESET}{self._battery_bar(data.get('battery', 0))}")

        # ── Speed ──
        speed = data.get("speed", {})
        lines.append(f"  {C.BOLD}Speed:{C.RESET}")
        lines.append(f"    {C.CYAN}Current: {C.BOLD}{speed.get('current', 0):>6.1f} m/s{C.RESET}  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{C.YELLOW}Target: {speed.get('target', 0):>6.1f} m/s{C.RESET}  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{C.GREEN}Average: {speed.get('average', 0):>6.1f} m/s{C.RESET}  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{C.MAGENTA}Max: {speed.get('max', 0):>6.1f} m/s{C.RESET}")
        lines.append(f"    {self._speed_bar(speed.get('current', 0), speed.get('max', 20))}")

        # ── Acceleration & Jerk ──
        accel = data.get("acceleration", {})
        jerk = data.get("jerk", 0)
        lines.append(f"  {C.BOLD}Acceleration: {C.RESET}{accel.get('current', 0):>5.2f} m/s²  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{C.BOLD}Jerk: {C.RESET}{jerk:>6.4f} m/s³  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{C.BOLD}Yaw Rate: {C.RESET}{data.get('yaw_rate', 0):>5.2f} rad/s")

        # ── ETA ──
        eta = data.get("eta", {})
        eta_current = eta.get("current", 0)
        eta_optimal = eta.get("optimal", 0)
        eta_delay = eta.get("delay", 0)
        delay_color = C.GREEN if eta_delay <= 0 else C.YELLOW if eta_delay < 10 else C.RED
        lines.append(f"  {C.BOLD}ETA:{C.RESET}")
        lines.append(f"    {C.CYAN}Current: {C.BOLD}{eta_current:>7.1f}s{C.RESET}  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{C.GREEN}Optimal: {eta_optimal:>7.1f}s{C.RESET}  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{delay_color}Delay: {eta_delay:>+6.1f}s{C.RESET}")

        # ── Mission Progress ──
        mission = data.get("mission", {})
        progress = mission.get("progress", 0)
        dist = mission.get("distance_to_goal", 0)
        lines.append(f"  {C.BOLD}Mission:{C.RESET}")
        lines.append(f"    {C.BLUE}Progress: {self._progress_bar(progress / 100.0)}{C.RESET}  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{C.BOLD}Distance: {dist:>6.1f}m{C.RESET}")

        # ── Risk & Safety ──
        risk = data.get("risk", {})
        risk_score = risk.get("score", 0)
        min_dist = risk.get("min_obstacle_dist", float('inf'))
        confidence = risk.get("confidence", 1.0)
        risk_color = C.GREEN if risk_score < 0.3 else C.YELLOW if risk_score < 0.6 else C.RED
        lines.append(f"  {C.BOLD}Risk:{C.RESET}")
        lines.append(f"    {risk_color}Score: {risk_score:>5.2f}{C.RESET}  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{C.CYAN}Min Obstacle: {min_dist if min_dist == float('inf') else f'{min_dist:>5.1f}m'}{C.RESET}  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{C.BOLD}Confidence: {confidence:>5.2f}{C.RESET}")

        # ── Latency ──
        latency = data.get("latency", {})
        plan_lat = latency.get("planning", 0)
        ctrl_lat = latency.get("controller", 0)
        plan_color = C.GREEN if plan_lat < 5 else C.YELLOW if plan_lat < 20 else C.RED
        ctrl_color = C.GREEN if ctrl_lat < 2 else C.YELLOW if ctrl_lat < 10 else C.RED
        lines.append(f"  {C.BOLD}Latency:{C.RESET}")
        lines.append(f"    {plan_color}Planning: {plan_lat:>6.2f}ms{C.RESET}  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{ctrl_color}Controller: {ctrl_lat:>6.2f}ms{C.RESET}")

        # ── Smoothness & Collisions ──
        smoothness = data.get("smoothness", 1.0)
        coll_rate = data.get("collision_rate", 0)
        smooth_color = C.GREEN if smoothness > 0.8 else C.YELLOW if smoothness > 0.5 else C.RED
        coll_color = C.GREEN if coll_rate < 1 else C.RED
        lines.append(f"  {C.BOLD}Quality:{C.RESET}")
        lines.append(f"    {smooth_color}Smoothness: {smoothness:>5.2f}{C.RESET}  "
                     f"{C.DIM}|{C.RESET}  "
                     f"{coll_color}Collision Rate: {coll_rate:>5.2f}%{C.RESET}")

        # ── Mini Sparkline (ASCII) ──
        if len(self.history["speed"]) >= 2:
            spark = self._sparkline(list(self.history["speed"])[-50:])
            lines.append(f"  {C.DIM}Speed Trend: {spark}{C.RESET}")

        lines.append(f"{C.BOLD}{C.CYAN}{'='*70}{C.RESET}")
        lines.append("")

        return "\n".join(lines)

    def _speed_bar(self, current: float, max_speed: float) -> str:
        """Render a colored speed bar."""
        if max_speed <= 0:
            return ""
        ratio = min(1.0, current / max_speed)
        bar_len = 40
        filled = int(ratio * bar_len)
        empty = bar_len - filled

        # Color changes with speed
        if ratio < 0.3:
            color = DashboardColors.GREEN
        elif ratio < 0.6:
            color = DashboardColors.YELLOW
        elif ratio < 0.85:
            color = DashboardColors.MAGENTA
        else:
            color = DashboardColors.RED

        bar = f"{color}{'█' * filled}{DashboardColors.DIM}{'─' * empty}{DashboardColors.RESET}"
        return f"[{bar}] {current:.1f}/{max_speed:.0f} m/s"

    def _battery_bar(self, percentage: float) -> str:
        """Render a colored battery bar."""
        ratio = min(1.0, max(0.0, percentage / 100.0))
        bar_len = 15
        filled = int(ratio * bar_len)
        empty = bar_len - filled

        if ratio > 0.5:
            color = DashboardColors.GREEN
        elif ratio > 0.2:
            color = DashboardColors.YELLOW
        else:
            color = DashboardColors.RED

        bar = f"{color}{'█' * filled}{DashboardColors.DIM}{'─' * empty}{DashboardColors.RESET}"
        return f"[{bar}] {percentage:.1f}%"

    def _progress_bar(self, ratio: float) -> str:
        """Render a mission progress bar."""
        bar_len = 30
        filled = int(ratio * bar_len)
        empty = bar_len - filled
        bar = f"{DashboardColors.BLUE}{'█' * filled}{DashboardColors.DIM}{'─' * empty}{DashboardColors.RESET}"
        return f"[{bar}] {ratio * 100:.1f}%"

    @staticmethod
    def _mode_color(mode: str) -> str:
        """Get color for flight mode."""
        colors = {
            "ECO": DashboardColors.GREEN,
            "NORMAL": DashboardColors.BLUE,
            "CRUISE": DashboardColors.CYAN,
            "SPORT": DashboardColors.YELLOW,
            "TURBO": DashboardColors.MAGENTA,
            "EMERGENCY": DashboardColors.RED,
            "PRECISION": DashboardColors.WHITE,
            "LANDING": DashboardColors.DIM,
        }
        return colors.get(mode, DashboardColors.WHITE)

    @staticmethod
    def _sparkline(values: List[float], width: int = 40) -> str:
        """Render an ASCII sparkline."""
        if not values:
            return ""
        min_v = min(values)
        max_v = max(values)
        if max_v == min_v:
            return "─" * width

        chars = "▁▂▃▄▅▆▇█"
        steps = len(chars) - 1
        result = ""
        for v in values[-width:]:
            idx = int((v - min_v) / (max_v - min_v) * steps)
            idx = max(0, min(steps, idx))
            result += chars[idx]
        return result

    def get_metric_summary(self) -> dict:
        """Get aggregated metric summary."""
        summary = {}
        for key, hist in self.history.items():
            if hist:
                arr = np.array(hist)
                summary[key] = {
                    "min": float(np.min(arr)),
                    "max": float(np.max(arr)),
                    "mean": float(np.mean(arr)),
                    "std": float(np.std(arr)),
                    "current": float(arr[-1]),
                }
        return summary

    def to_dict(self) -> dict:
        """Export all dashboard data as dict."""
        return {
            "metrics": {k: list(v) for k, v in self.history.items()},
            "summary": self.get_metric_summary(),
        }