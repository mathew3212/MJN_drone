"""
Configuration
=============
Central configuration dataclass for all simulation parameters.
Single source of truth for every configurable value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class SimulationConfig:
    """Master configuration for the autonomous drone simulation."""

    # ── World ────────────────────────────────────────────────────────
    world_width: int = 100
    world_height: int = 100
    world_resolution: float = 1.0
    random_seed: int = 42

    # ── Obstacles ────────────────────────────────────────────────────
    num_static_obstacles: int = 100
    num_dynamic_obstacles: int = 10
    obstacle_radius: float = 0.5

    # ── Drone ────────────────────────────────────────────────────────
    drone_start_x: float = 10.0
    drone_start_y: float = 10.0
    drone_start_heading: float = 0.0
    drone_max_speed: float = 2.0
    drone_max_turn_rate: float = 1.0

    # ── Target ───────────────────────────────────────────────────────
    target_x: float = 90.0
    target_y: float = 90.0

    # ── Sensors ──────────────────────────────────────────────────────
    scan_radius: float = 8.0
    lidar_rays: int = 64
    lidar_max_range: float = 15.0
    gps_noise_std: float = 1.5
    imu_drift_rate: float = 0.01

    # ── Simulation ───────────────────────────────────────────────────
    dt: float = 0.1
    realtime_factor: float = 1.0
    max_steps: int = 5000

    # ── Planning ─────────────────────────────────────────────────────
    plan_hysteresis: float = 0.5
    replan_cooldown: int = 30
    stuck_threshold: float = 0.5
    stuck_frames: int = 20

    # ── Control ──────────────────────────────────────────────────────
    pid_kp: float = 1.5
    pid_ki: float = 0.01
    pid_kd: float = 0.3
    waypoint_tolerance: float = 3.0

    # ── Battery ──────────────────────────────────────────────────────
    battery_capacity: float = 100.0
    battery_reserve: float = 20.0
    battery_critical: float = 10.0
    battery_consumption_rate: float = 0.05

    # ── Memory ───────────────────────────────────────────────────────
    memory_decay_rate: float = 0.995
    memory_forget_threshold: float = 0.05

    # ── Prediction ───────────────────────────────────────────────────
    prediction_horizon: int = 15
    risk_steps: int = 10

    # ── Visualization ────────────────────────────────────────────────
    dashboard_enabled: bool = True
    frame_delay: float = 0.02

    # ── Home ─────────────────────────────────────────────────────────
    @property
    def home_position(self) -> Tuple[float, float]:
        return (self.drone_start_x, self.drone_start_y)

    @property
    def target_position(self) -> Tuple[float, float]:
        return (self.target_x, self.target_y)