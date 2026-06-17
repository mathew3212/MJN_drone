"""
High-Performance Flight Manager (FlightFM)
============================================
The central high-speed flight intelligence layer between the Decision Engine
and the low-level Controller.

Provides:
1. Dynamic Speed Planner      - continuous speed adaptation
2. Flight Modes               - ECO/NORMAL/CRUISE/SPORT/TURBO/EMERGENCY/PRECISION/LANDING
3. Continuous Trajectory Gen  - Bezier/spline paths
4. Lookahead Controller       - pure pursuit + dynamic lookahead
5. Predictive Obstacle Avoid  - future position prediction
6. Hierarchical Planning      - mission/global/local/trajectory layers
7. Fast Reactive Layer        - emergency collision override
8. Dynamic Path Optimization  - continuous path shortening
9. Energy Optimization        - maximum average speed
10. ETA Optimization           - time-based mission optimization
11. Decision Pipeline Opt      - fast path bypass for AI
12. Parallel Execution         - async background threads
13. Performance Metrics        - comprehensive telemetry
14. Flight Analytics Dashboard - live visualization
15. Intelligent Prioritization - time-risk optimization
"""

from __future__ import annotations

import math
import time
import threading
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from heapq import heappush, heappop
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

from src.core.drone import Drone, FlightMode, default_mode_params


# ============================================================================
# Type Aliases
# ============================================================================
Point = Tuple[float, float]
Path = List[Point]
Trajectory = List[Tuple[float, float, float]]  # (x, y, heading)


# ============================================================================
# Performance Configuration
# ============================================================================
@dataclass
class PerformanceConfig:
    """Global performance tuning knobs."""
    # Control loop
    control_hz: float = 100.0
    planning_hz: float = 10.0
    trajectory_hz: float = 25.0
    perception_hz: float = 30.0

    # Lookahead
    min_lookahead: float = 3.0
    max_lookahead: float = 30.0
    lookahead_time: float = 2.0  # seconds ahead

    # Speed planning
    max_speed_global: float = 20.0
    min_speed: float = 0.5
    speed_smooth_factor: float = 0.85

    # Obstacle prediction
    prediction_horizon: float = 3.0
    collision_time_threshold: float = 2.0
    safety_margin: float = 1.5

    # Path optimization
    max_waypoint_skip: int = 5
    corner_smoothing_radius: float = 2.0

    # ETA
    mission_deadline: Optional[float] = None

    # Energy
    hover_energy_cost: float = 1.0
    cruise_energy_cost: float = 0.3

    # Parallel execution
    async_planning: bool = True
    async_prediction: bool = True


# ============================================================================
# FlightAnalytics - Live Dashboard Data
# ============================================================================
@dataclass
class FlightAnalytics:
    """Live flight analytics for dashboard."""
    # Timestamps
    timestamp: float = 0.0
    mission_start: float = 0.0

    # Speed
    current_speed: float = 0.0
    target_speed: float = 0.0
    average_speed: float = 0.0
    max_speed_achieved: float = 0.0

    # Acceleration
    current_acceleration: float = 0.0
    average_acceleration: float = 0.0

    # Jerk
    current_jerk: float = 0.0

    # Throttle / Yaw
    throttle: float = 0.0
    yaw_rate: float = 0.0

    # ETA
    distance_to_goal: float = 0.0
    eta_seconds: float = 0.0
    optimal_eta: float = 0.0
    eta_delay: float = 0.0
    mission_progress: float = 0.0

    # Risk
    risk_score: float = 0.0
    min_obstacle_distance: float = float('inf')
    prediction_confidence: float = 1.0

    # Latency
    planning_latency: float = 0.0
    controller_latency: float = 0.0
    decision_latency: float = 0.0

    # Battery / Energy
    battery_level: float = 1.0
    energy_efficiency: float = 1.0

    # Flight mode
    flight_mode: str = "NORMAL"

    # Metrics history
    speed_history: List[float] = field(default_factory=list)
    accel_history: List[float] = field(default_factory=list)
    jerk_history: List[float] = field(default_factory=list)
    planning_time_history: List[float] = field(default_factory=list)
    collision_free_steps: int = 0
    total_steps: int = 0

    def update_speed(self, speed: float) -> None:
        self.current_speed = speed
        self.max_speed_achieved = max(self.max_speed_achieved, speed)
        self.speed_history.append(speed)
        if len(self.speed_history) > 1000:
            self.speed_history = self.speed_history[-500:]

    def update_acceleration(self, accel: float) -> None:
        self.current_acceleration = accel
        self.accel_history.append(accel)
        if len(self.accel_history) > 1000:
            self.accel_history = self.accel_history[-500:]

    def update_jerk(self, jerk: float) -> None:
        self.current_jerk = jerk
        self.jerk_history.append(jerk)
        if len(self.jerk_history) > 1000:
            self.jerk_history = self.jerk_history[-500:]

    @property
    def average_speed_computed(self) -> float:
        if not self.speed_history:
            return 0.0
        return sum(self.speed_history[-100:]) / min(len(self.speed_history[-100:]), 100)

    @property
    def flight_smoothness(self) -> float:
        """Compute flight smoothness as 1 / (1 + mean jerk)."""
        if not self.jerk_history:
            return 1.0
        recent = self.jerk_history[-50:]
        mean_jerk = sum(recent) / len(recent)
        return 1.0 / (1.0 + mean_jerk)

    @property
    def collision_rate(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return 1.0 - (self.collision_free_steps / self.total_steps)


# ============================================================================
# Dynamic Speed Planner
# ============================================================================
class DynamicSpeedPlanner:
    """
    Continuously adapts speed based on:
    - Distance to goal
    - Distance to nearest obstacle
    - Obstacle density
    - Mission priority
    - Battery level
    - Prediction confidence
    - Risk score
    - Mission deadline
    - Current flight mode limits
    """

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self._current_target_speed: float = config.min_speed * 2.0  # Start with reasonable speed
        self._smoothed_speed: float = config.min_speed * 2.0
        self._braking: bool = False
        self._acceleration_phase: bool = True

    def compute_target_speed(
        self,
        drone: Drone,
        distance_to_goal: float,
        distance_to_nearest_obstacle: float,
        obstacle_density: float,
        battery_level: float,
        prediction_confidence: float,
        risk_score: float,
        mission_deadline_remaining: Optional[float] = None,
        mission_priority: float = 0.5,
    ) -> float:
        """
        Compute the optimal target speed using all available signals.
        Returns a float 0..max_speed.
        """
        max_speed = drone.max_speed

        # 1. Base speed from flight mode
        base_speed = max_speed * 0.9

        # 2. Distance-to-goal modulation
        # Speed up when far, slow down when close
        goal_factor = min(1.0, distance_to_goal / 50.0)
        goal_factor = max(0.2, goal_factor)

        target = base_speed * goal_factor

        # 3. Obstacle distance modulation
        if distance_to_nearest_obstacle < float('inf'):
            min_clearance = drone.min_obstacle_clearance
            if distance_to_nearest_obstacle < min_clearance * 2.0:
                # Exponential slowdown near obstacles
                obstacle_factor = (distance_to_nearest_obstacle / (min_clearance * 2.0)) ** 1.5
                obstacle_factor = max(0.1, min(1.0, obstacle_factor))
                target *= obstacle_factor

        # 4. Obstacle density modulation
        if obstacle_density > 0.05:
            density_factor = max(0.3, 1.0 - obstacle_density * 3.0)
            target *= density_factor

        # 5. Battery modulation
        battery_factor = 0.5 + 0.5 * battery_level  # 0.5..1.0
        target *= battery_factor

        # 6. Prediction confidence modulation
        confidence_factor = max(0.3, prediction_confidence)
        target *= confidence_factor

        # 7. Risk score modulation
        risk_factor = max(0.2, 1.0 - risk_score * 2.0)
        target *= risk_factor

        # 8. Mission deadline pressure
        if mission_deadline_remaining is not None and mission_deadline_remaining > 0:
            required_speed = distance_to_goal / mission_deadline_remaining
            # If we need to go faster, push speed up
            if required_speed > target:
                deadline_factor = min(1.5, required_speed / max(target, 0.1))
                target = min(target * deadline_factor, max_speed)

        # 9. Mission priority boost
        priority_boost = 1.0 + 0.3 * mission_priority  # 1.0..1.3
        target *= priority_boost

        # Safety clamp: never exceed max speed
        target = min(target, max_speed)
        target = max(self.config.min_speed, target)

        self._current_target_speed = target
        return target

    def smooth_speed(self, target: float, dt: float = 0.01) -> float:
        """
        Smooth speed transitions to avoid jerk.
        Implements exponential smoothing with time-awareness.
        """
        alpha = 1.0 - (self.config.speed_smooth_factor ** dt)
        self._smoothed_speed = self._smoothed_speed + alpha * (target - self._smoothed_speed)
        return self._smoothed_speed

    def compute_deceleration_profile(
        self,
        drone: Drone,
        distance_to_stop: float,
        dt: float = 0.01,
    ) -> float:
        """
        Compute required deceleration to stop at target.
        Returns safe approach speed.
        """
        current_speed = drone.velocity_magnitude
        if distance_to_stop < 1.0:
            return 0.0

        # v^2 = u^2 + 2*a*s => u = sqrt(2*a*s)
        max_decel = drone.max_acceleration * 0.8
        theoretical_speed = math.sqrt(2.0 * max_decel * distance_to_stop)
        safe_speed = min(current_speed, theoretical_speed)
        return max(0.0, safe_speed)


# ============================================================================
# Continuous Trajectory Generator
# ============================================================================
class ContinuousTrajectoryGenerator:
    """
    Generates smooth continuous trajectories using cubic Bezier curves and
    spline interpolation. Eliminates stop-turn-go behavior.
    """

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self._current_trajectory: Trajectory = []
        self._trajectory_index: int = 0
        self._cache: Dict[Tuple, Trajectory] = {}

    def generate_bezier_path(
        self,
        path: Path,
        heading_start: float = 0.0,
        heading_end: float = 0.0,
        num_samples: int = 50,
    ) -> Trajectory:
        """
        Convert a waypoint path into a smooth Bezier curve trajectory
        with continuous heading.
        """
        if not path or len(path) < 2:
            return [(p[0], p[1], 0.0) for p in path] if path else []

        # Cache key
        cache_key = (tuple(path), heading_start, heading_end, num_samples)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Generate smooth control points
        points = np.array(path, dtype=np.float64)
        n = len(points)

        if n <= 2:
            trajectory = self._generate_segment(points, heading_start, heading_end, num_samples)
        else:
            trajectory = self._generate_multi_segment(points, heading_start, heading_end, num_samples)

        self._cache[cache_key] = trajectory
        # Limit cache size
        if len(self._cache) > 200:
            self._cache.clear()

        self._current_trajectory = trajectory
        self._trajectory_index = 0
        return trajectory

    def _generate_segment(
        self,
        points: np.ndarray,
        heading_start: float,
        heading_end: float,
        num_samples: int,
    ) -> Trajectory:
        """Generate a single Bezier curve segment."""
        p0 = points[0]
        p3 = points[-1]

        # Control points for smooth curve
        dist = np.linalg.norm(p3 - p0) * 0.3
        angle_start = heading_start
        angle_end = heading_end

        p1 = p0 + np.array([math.cos(angle_start), math.sin(angle_start)]) * dist
        p2 = p3 - np.array([math.cos(angle_end), math.sin(angle_end)]) * dist

        trajectory = []
        for i in range(num_samples):
            t = i / (num_samples - 1)
            # Cubic Bezier
            x = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0]
            y = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1]
            heading = math.atan2(p3[1] - p0[1], p3[0] - p0[0])
            trajectory.append((float(x), float(y), heading))

        return trajectory

    def _generate_multi_segment(
        self,
        points: np.ndarray,
        heading_start: float,
        heading_end: float,
        num_samples: int,
    ) -> Trajectory:
        """Generate smooth multi-segment Catmull-Rom-like spline."""
        trajectory = []
        n = len(points)
        samples_per_segment = max(5, num_samples // (n - 1))

        for i in range(n - 1):
            p0 = points[max(0, i - 1)]
            p1 = points[i]
            p2 = points[min(n - 1, i + 1)]
            p3 = points[min(n - 1, i + 2)]

            seg = self._catmull_rom_segment(p0, p1, p2, p3, samples_per_segment)
            # Skip first point if not first segment (avoid duplicates)
            start_idx = 1 if i > 0 else 0
            for j in range(start_idx, len(seg)):
                x, y = seg[j]
                # Compute heading
                if j < len(seg) - 1:
                    heading = math.atan2(seg[j + 1][1] - y, seg[j + 1][0] - x)
                else:
                    heading = heading_end if i == n - 2 else math.atan2(points[i + 1][1] - points[i][1], points[i + 1][0] - points[i][0])
                trajectory.append((float(x), float(y), heading))

        return trajectory

    @staticmethod
    def _catmull_rom_segment(
        p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray,
        num_samples: int,
    ) -> List[Tuple[float, float]]:
        """Compute a Catmull-Rom spline segment."""
        points = []
        for i in range(num_samples):
            t = i / max(num_samples - 1, 1)
            tt = t * t
            ttt = tt * t

            # Catmull-Rom basis matrix
            q0 = -ttt + 2.0 * tt - t
            q1 = 3.0 * ttt - 5.0 * tt + 2.0
            q2 = -3.0 * ttt + 4.0 * tt + t
            q3 = ttt - tt

            x = 0.5 * (q0 * p0[0] + q1 * p1[0] + q2 * p2[0] + q3 * p3[0])
            y = 0.5 * (q0 * p0[1] + q1 * p1[1] + q2 * p2[1] + q3 * p3[1])
            points.append((float(x), float(y)))

        return points

    def get_trajectory_point(self, index: int) -> Optional[Tuple[float, float, float]]:
        """Get a point from the current trajectory by index."""
        if not self._current_trajectory or index >= len(self._current_trajectory):
            return None
        return self._current_trajectory[index]

    def get_lookahead_point(self, lookahead_distance: float, current_pos: Point) -> Optional[Tuple[float, float, float]]:
        """Get the lookahead point along the trajectory."""
        if not self._current_trajectory:
            return None

        best_idx = 0
        best_dist = float('inf')
        for i, (tx, ty, _) in enumerate(self._current_trajectory):
            d = math.sqrt((tx - current_pos[0]) ** 2 + (ty - current_pos[1]) ** 2)
            if d < best_dist:
                best_dist = d
                best_idx = i

        # Look ahead
        target_idx = best_idx + max(1, int(lookahead_distance / 1.0))
        target_idx = min(target_idx, len(self._current_trajectory) - 1)
        return self._current_trajectory[target_idx]

    def invalidate_cache(self) -> None:
        """Clear trajectory cache (call when environment changes)."""
        self._cache.clear()


# ============================================================================
# Lookahead Controller (Pure Pursuit + Stanley)
# ============================================================================
class LookaheadController:
    """
    Advanced lookahead controller combining Pure Pursuit and Stanley methods.
    Dynamically adjusts lookahead distance based on speed.
    """

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self._lookahead_gain: float = 1.0
        self._steering_gain: float = 2.0
        self._cross_track_gain: float = 1.5
        self._last_target: Optional[Point] = None
        self._cross_track_error: float = 0.0

    def compute_lookahead_distance(self, speed: float) -> float:
        """Dynamic lookahead: farther at higher speeds."""
        base = self.config.min_lookahead
        speed_factor = speed * self.config.lookahead_time
        lookahead = base + speed_factor
        return min(self.config.max_lookahead, lookahead)

    def compute_control(
        self,
        drone: Drone,
        target: Point,
        lookahead_distance: float,
        dt: float = 0.01,
    ) -> Tuple[float, float, float]:
        """
        Compute velocity (vx, vy) and heading control.
        Returns (target_vx, target_vy, heading_correction).
        """
        dx = target[0] - drone.x
        dy = target[1] - drone.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 0.1:
            return (0.0, 0.0, 0.0)

        # Pure pursuit: head directly towards target
        desired_heading = math.atan2(dy, dx)

        # Heading error
        heading_error = desired_heading - drone.heading
        while heading_error > math.pi:
            heading_error -= 2 * math.pi
        while heading_error < -math.pi:
            heading_error += 2 * math.pi

        # Cross-track error (Stanley-like correction)
        if self._last_target is not None:
            # Distance from drone to line between last_target and current target
            ax = target[0] - self._last_target[0]
            ay = target[1] - self._last_target[1]
            path_length = math.sqrt(ax * ax + ay * ay)
            if path_length > 0.01:
                # Project drone onto path segment
                bx = drone.x - self._last_target[0]
                by = drone.y - self._last_target[1]
                t = max(0.0, min(1.0, (ax * bx + ay * by) / (path_length * path_length)))
                proj_x = self._last_target[0] + t * ax
                proj_y = self._last_target[1] + t * ay
                self._cross_track_error = math.sqrt((drone.x - proj_x) ** 2 + (drone.y - proj_y) ** 2)

                # Cross-track sign (which side of path)
                cross_sign = math.copysign(1.0, ax * (drone.y - self._last_target[1]) - ay * (drone.x - self._last_target[0]))
                cte_term = math.atan2(self._cross_track_gain * self._cross_track_error * cross_sign, max(1.0, drone.velocity_magnitude + 0.1))
                heading_error += cte_term
                heading_error = max(-math.pi / 4, min(math.pi / 4, heading_error))

        self._last_target = target

        # Speed towards target
        speed = min(drone.max_speed, distance / max(dt, 0.001))

        # Target velocity
        target_vx = math.cos(desired_heading) * speed
        target_vy = math.sin(desired_heading) * speed

        return (target_vx, target_vy, heading_error)

    def reset(self) -> None:
        """Reset controller state."""
        self._last_target = None
        self._cross_track_error = 0.0


# ============================================================================
# Predictive Obstacle Avoidance
# ============================================================================
@dataclass
class ObstaclePrediction:
    """Predicted state of an obstacle."""
    position: Point
    velocity: Point
    future_positions: List[Point]
    confidence: float
    time_to_collision: float = float('inf')
    collision_probability: float = 0.0


class PredictiveObstacleAvoidance:
    """
    Predicts future obstacle positions and computes collision probabilities
    and escape trajectories before obstacles get close.
    """

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self._predictions: Dict[int, ObstaclePrediction] = {}
        self._next_id: int = 0
        self._collision_warning: bool = False
        self._escape_trajectory: Optional[Tuple[float, float]] = None

    def update_predictions(
        self,
        drone: Drone,
        visible_obstacles: List[Point],
        dynamic_obstacles: List[Tuple[Point, Point]],  # (position, velocity)
        dt: float = 0.01,
    ) -> None:
        """
        Update obstacle predictions with current sensor data.
        dynamic_obstacles: list of (position, velocity) tuples.
        """
        horizon = self.config.prediction_horizon
        steps = int(horizon / max(dt, 0.01))
        step_size = horizon / max(steps, 1)

        # Process static obstacles
        for i, obs_pos in enumerate(visible_obstacles):
            pred = ObstaclePrediction(
                position=obs_pos,
                velocity=(0.0, 0.0),
                future_positions=[obs_pos] * min(steps, 5),
                confidence=0.8,
            )
            self._predictions[self._next_id] = pred
            self._next_id += 1

        # Process dynamic obstacles with velocity
        for obs_pos, obs_vel in dynamic_obstacles:
            vx, vy = obs_vel
            future_positions = []
            for s in range(min(steps, 10)):
                t = s * step_size
                fx = obs_pos[0] + vx * t
                fy = obs_pos[1] + vy * t
                future_positions.append((fx, fy))

            pred = ObstaclePrediction(
                position=obs_pos,
                velocity=obs_vel,
                future_positions=future_positions,
                confidence=0.6 + 0.2 * (len(future_positions) > 0),
            )
            self._predictions[self._next_id] = pred
            self._next_id += 1

        # Limit predictions size
        if len(self._predictions) > 500:
            # Keep only most recent
            keys = list(self._predictions.keys())[-300:]
            self._predictions = {k: self._predictions[k] for k in keys}

    def compute_collision_risk(
        self,
        drone: Drone,
        trajectory: Trajectory,
        dt: float = 0.01,
    ) -> float:
        """
        Compute collision risk score (0..1) and populate predictions with
        time-to-collision data. Also computes best escape trajectory.
        """
        if not self._predictions:
            self._collision_warning = False
            return 0.0

        min_distance = float('inf')
        time_to_collision = float('inf')
        collision_prob = 0.0
        escape_dir = 0.0

        drone_pos = np.array([drone.x, drone.y])
        drone_speed = drone.velocity_magnitude

        # Check predicted obstacle positions against drone trajectory
        for pred_id, pred in self._predictions.items():
            for future_pos in pred.future_positions:
                obs = np.array(future_pos)
                dist = np.linalg.norm(obs - drone_pos)

                if dist < min_distance:
                    min_distance = dist

                # Time to collision
                if drone_speed > 0.1:
                    closing_speed = drone_speed
                    ttc = dist / closing_speed
                    if ttc < time_to_collision:
                        time_to_collision = ttc

                # Collision probability
                if dist < self.config.safety_margin * 2.0:
                    prob = max(0.0, 1.0 - dist / (self.config.safety_margin * 2.0))
                    collision_prob = max(collision_prob, prob)

                    # Compute escape direction (perpendicular to obstacle)
                    escape_angle = math.atan2(future_pos[1] - drone.y, future_pos[0] - drone.x)
                    escape_dir = escape_angle + math.pi / 2  # 90 degrees

        # Update stored data
        for pred_id in self._predictions:
            self._predictions[pred_id].time_to_collision = time_to_collision
            self._predictions[pred_id].collision_probability = collision_prob

        self._collision_warning = collision_prob > 0.3 or min_distance < self.config.safety_margin

        # Compute escape trajectory
        if self._collision_warning:
            # Escape to the side of the nearest threat
            escape_vx = math.cos(escape_dir) * drone.max_speed * 0.8
            escape_vy = math.sin(escape_dir) * drone.max_speed * 0.8
            self._escape_trajectory = (escape_vx, escape_vy)
        else:
            self._escape_trajectory = None

        return collision_prob

    @property
    def has_collision_warning(self) -> bool:
        return self._collision_warning

    @property
    def escape_vector(self) -> Optional[Tuple[float, float]]:
        return self._escape_trajectory

    @property
    def min_obstacle_distance(self) -> float:
        if not self._predictions:
            return float('inf')
        min_d = float('inf')
        drone_pos = (0.0, 0.0)  # Will be set externally
        for pred in self._predictions.values():
            for fp in pred.future_positions:
                d = math.sqrt((fp[0] - drone_pos[0]) ** 2 + (fp[1] - drone_pos[1]) ** 2)
                if d < min_d:
                    min_d = d
        return min_d


# ============================================================================
# Fast Reactive Layer (Emergency Controller)
# ============================================================================
class FastReactiveLayer:
    """
    Emergency collision override.
    Bypasses AI/cognitive layers when imminent collision is detected.
    Implements direct evasive maneuvers.
    """

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self._active: bool = False
        self._override_velocity: Tuple[float, float] = (0.0, 0.0)
        self._override_count: int = 0
        self._last_trigger_time: float = 0.0

    def evaluate(
        self,
        drone: Drone,
        nearest_obstacle_distance: float,
        nearest_obstacle_angle: float,
        collision_probability: float,
        time_to_collision: float,
        current_time: float,
    ) -> Tuple[bool, Optional[Tuple[float, float]]]:
        """
        Evaluate if reactive override is needed.
        Returns (is_active, override_velocity_vector).
        """
        # Immediate danger: too close or imminent collision
        if nearest_obstacle_distance < drone.min_obstacle_clearance * 0.6:
            # Emergency brake and steer away
            self._active = True
            self._override_count += 1
            self._last_trigger_time = current_time

            # Steer away from obstacle
            escape_angle = nearest_obstacle_angle + math.pi / 2
            escape_speed = drone.max_speed * 0.6

            override_vx = math.cos(escape_angle) * escape_speed
            override_vy = math.sin(escape_angle) * escape_speed

            self._override_velocity = (override_vx, override_vy)
            return (True, self._override_velocity)

        if collision_probability > 0.6 and time_to_collision < self.config.collision_time_threshold:
            # High collision probability with imminent threat
            self._active = True
            self._override_count += 1
            self._last_trigger_time = current_time

            escape_angle = nearest_obstacle_angle + math.pi / 2
            escape_speed = drone.max_speed * 0.7
            override_vx = math.cos(escape_angle) * escape_speed
            override_vy = math.sin(escape_angle) * escape_speed
            self._override_velocity = (override_vx, override_vy)
            return (True, self._override_velocity)

        # Deactivate override if safe
        if self._active and nearest_obstacle_distance > drone.min_obstacle_clearance * 2.0:
            self._active = False
            self._override_velocity = (0.0, 0.0)

        return (self._active, self._override_velocity if self._active else None)

    @property
    def is_active(self) -> bool:
        return self._active

    def reset(self) -> None:
        self._active = False
        self._override_velocity = (0.0, 0.0)


# ============================================================================
# Dynamic Path Optimizer
# ============================================================================
class DynamicPathOptimizer:
    """
    Continuously optimizes the global path:
    - Shortens path by removing unnecessary waypoints
    - Merges collinear waypoints
    - Smooths corners
    - Reduces travel time
    - Avoids oscillations
    """

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self._last_optimized_path: Optional[Path] = None

    def optimize(self, path: Path, drone_position: Point) -> Path:
        """Optimize the given path for speed."""
        if not path or len(path) < 3:
            return path

        # 1. Remove waypoints behind drone
        path = self._prune_behind(path, drone_position)

        # 2. Remove collinear intermediate points
        path = self._remove_collinear(path)

        # 3. Simplify using Ramer-Douglas-Peucker
        path = self._simplify_path(path)

        # 4. Smooth corners
        path = self._smooth_corners(path)

        self._last_optimized_path = path
        return path

    @staticmethod
    def _prune_behind(path: Path, drone_position: Point) -> Path:
        """Remove waypoints that are behind the drone."""
        if not path:
            return path

        best_idx = 0
        best_dist = float('inf')
        for i, wp in enumerate(path):
            d = (wp[0] - drone_position[0]) ** 2 + (wp[1] - drone_position[1]) ** 2
            if d < best_dist:
                best_dist = d
                best_idx = i

        return path[best_idx:]

    @staticmethod
    def _remove_collinear(path: Path, angle_threshold: float = 0.15) -> Path:
        """Remove waypoints that are nearly collinear with neighbors."""
        if len(path) < 3:
            return path

        result = [path[0]]
        for i in range(1, len(path) - 1):
            v1 = (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
            v2 = (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])

            v1_len = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
            v2_len = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

            if v1_len > 0 and v2_len > 0:
                dot = (v1[0] * v2[0] + v1[1] * v2[1]) / (v1_len * v2_len)
                angle = abs(math.acos(max(-1.0, min(1.0, dot))))
                if angle > angle_threshold:
                    result.append(path[i])
            else:
                result.append(path[i])

        result.append(path[-1])
        return result

    @staticmethod
    def _simplify_path(path: Path, epsilon: float = 1.0) -> Path:
        """Ramer-Douglas-Peucker simplification."""
        if len(path) < 3:
            return path

        def point_line_distance(p: Point, a: Point, b: Point) -> float:
            if a == b:
                return math.sqrt((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
            num = abs((b[0] - a[0]) * (a[1] - p[1]) - (a[0] - p[0]) * (b[1] - a[1]))
            den = math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)
            return num / den

        def rdp_recursive(points: Path, eps: float) -> Path:
            if len(points) <= 2:
                return points

            dmax = 0.0
            idx = 0
            for i in range(1, len(points) - 1):
                d = point_line_distance(points[i], points[0], points[-1])
                if d > dmax:
                    dmax = d
                    idx = i

            if dmax > eps:
                left = rdp_recursive(points[:idx + 1], eps)
                right = rdp_recursive(points[idx:], eps)
                return left[:-1] + right
            else:
                return [points[0], points[-1]]

        return rdp_recursive(path, epsilon)

    @staticmethod
    def _smooth_corners(path: Path, radius: float = 2.0) -> Path:
        """Round sharp corners in the path."""
        if len(path) < 3:
            return path

        result = [path[0]]
        for i in range(1, len(path) - 1):
            prev = path[i - 1]
            curr = path[i]
            next_ = path[i + 1]

            v1 = (curr[0] - prev[0], curr[1] - prev[1])
            v2 = (next_[0] - curr[0], next_[1] - curr[1])
            v1_len = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
            v2_len = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

            if v1_len > 0 and v2_len > 0:
                angle = math.acos(
                    max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (v1_len * v2_len)))
                )
                if angle < 2.8:  # Sharp corner ( > ~160 degrees external)
                    # Insert intermediate points for smoother corner
                    t = radius / v1_len
                    p1 = (curr[0] - t * v1[0], curr[1] - t * v1[1])
                    t = radius / v2_len
                    p2 = (curr[0] + t * v2[0], curr[1] + t * v2[1])
                    result.append(p1)
                    result.append(p2)
                else:
                    result.append(curr)
            else:
                result.append(curr)

        result.append(path[-1])
        return result


# ============================================================================
# ETA Optimizer
# ============================================================================
class ETAOptimizer:
    """
    Continuously monitors and optimizes estimated time of arrival.
    Tracks current vs optimal ETA and adjusts speed to meet deadlines.
    """

    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.mission_start_time: float = 0.0
        self._last_eta: float = 0.0
        self._last_optimal_eta: float = 0.0

    def compute_eta(
        self,
        drone: Drone,
        distance_to_goal: float,
        current_time: float,
    ) -> float:
        """Compute ETA in seconds based on current speed."""
        speed = max(drone.velocity_magnitude, 0.1)
        eta = distance_to_goal / speed
        self._last_eta = eta
        return eta

    def compute_optimal_eta(
        self,
        drone: Drone,
        distance_to_goal: float,
    ) -> float:
        """Compute optimal ETA at max speed."""
        optimal_speed = drone.max_speed * 0.95
        optimal_eta = distance_to_goal / max(optimal_speed, 0.1)
        self._last_optimal_eta = optimal_eta
        return optimal_eta

    def compute_pace_factor(
        self,
        drone: Drone,
        distance_to_goal: float,
        remaining_mission_time: Optional[float],
    ) -> float:
        """
        Compute pace factor (0..2) indicating if we need to speed up or slow down.
        >1 means speed up, <1 means we have time.
        """
        if remaining_mission_time is None or remaining_mission_time <= 0:
            return 1.0

        required_speed = distance_to_goal / max(remaining_mission_time, 0.1)
        current_speed = max(drone.velocity_magnitude, 0.1)
        pace = required_speed / current_speed

        return max(0.3, min(2.0, pace))


# ============================================================================
# Hierarchical Planner
# ============================================================================
class HierarchicalPlanner:
    """
    Multi-layer planning system:
    - Mission Planner: 1 Hz - high-level mission decisions
    - Global Planner: 2 Hz - path finding
    - Local Planner: 10 Hz - local path adjustment
    - Trajectory Planner: 25 Hz - smooth trajectory generation
    """

    def __init__(self, config: PerformanceConfig):
        self.config = config

        # Timing for each layer
        self.mission_interval: float = 1.0
        self.global_interval: float = 0.5
        self.local_interval: float = 0.1
        self.trajectory_interval: float = 0.04

        self._last_mission_time: float = 0.0
        self._last_global_time: float = 0.0
        self._last_local_time: float = 0.0
        self._last_trajectory_time: float = 0.0

        # Planning latencies
        self.mission_latency: float = 0.0
        self.global_latency: float = 0.0
        self.local_latency: float = 0.0
        self.trajectory_latency: float = 0.0

    def should_plan_mission(self, current_time: float) -> bool:
        return current_time - self._last_mission_time >= self.mission_interval

    def should_plan_global(self, current_time: float) -> bool:
        return current_time - self._last_global_time >= self.global_interval

    def should_plan_local(self, current_time: float) -> bool:
        return current_time - self._last_local_time >= self.local_interval

    def should_plan_trajectory(self, current_time: float) -> bool:
        return current_time - self._last_trajectory_time >= self.trajectory_interval

    def record_mission_time(self, current_time: float) -> None:
        self.mission_latency = current_time - max(self._last_mission_time, current_time - 0.1)
        self._last_mission_time = current_time

    def record_global_time(self, current_time: float) -> None:
        self.global_latency = current_time - max(self._last_global_time, current_time - 0.1)
        self._last_global_time = current_time

    def record_local_time(self, current_time: float) -> None:
        self.local_latency = current_time - max(self._last_local_time, current_time - 0.1)
        self._last_local_time = current_time

    def record_trajectory_time(self, current_time: float) -> None:
        self.trajectory_latency = current_time - max(self._last_trajectory_time, current_time - 0.1)
        self._last_trajectory_time = current_time


# ============================================================================
# Main Flight Manager
# ============================================================================
class FlightManager:
    """
    The central high-performance flight intelligence system.

    Designed as the intermediary between cognitive AI and low-level control.
    Converts AI decisions into the fastest possible safe flight.
    """

    def __init__(
        self,
        drone: Drone,
        config: Optional[PerformanceConfig] = None,
    ):
        self.drone = drone
        self.config = config or PerformanceConfig()

        # Subsystems
        self.speed_planner = DynamicSpeedPlanner(self.config)
        self.trajectory_generator = ContinuousTrajectoryGenerator(self.config)
        self.lookahead_controller = LookaheadController(self.config)
        self.obstacle_avoider = PredictiveObstacleAvoidance(self.config)
        self.reactive_layer = FastReactiveLayer(self.config)
        self.path_optimizer = DynamicPathOptimizer(self.config)
        self.eta_optimizer = ETAOptimizer(self.config)
        self.hierarchical_planner = HierarchicalPlanner(self.config)

        # Analytics
        self.analytics = FlightAnalytics()
        self.analytics.mission_start = time.time()

        # Internal state
        self._active: bool = True
        self._current_target: Optional[Point] = None
        self._global_path: Optional[Path] = None
        self._locked_obstacle_path: Optional[Path] = None
        self._dt: float = 0.01
        self._control_accumulator: float = 0.0
        self._step_counter: int = 0

        # Async workers
        self._async_threads: List[threading.Thread] = []
        self._async_lock = threading.Lock()
        self._async_results: Dict[str, Any] = {}

        # External references (set by integrator)
        self.external_planner: Any = None
        self.external_obstacle_list: List[Point] = []
        self.external_dynamic_obstacles: List[Tuple[Point, Point]] = []
        self.external_battery_level: float = 1.0
        self.external_prediction_confidence: float = 1.0
        self.external_risk_score: float = 0.0
        self.external_mission_priority: float = 0.5
        self.external_mission_deadline: Optional[float] = None
        self.external_mission_progress: float = 0.0

        # Data for telemetry
        self._last_planning_time: float = 0.0
        self._last_control_time: float = 0.0

    # ========================================================================
    # Core Update Loop (Call at 100 Hz)
    # ========================================================================
    def update(self, dt: float = 0.01) -> None:
        """
        Main flight update loop. Call at ~100 Hz from the simulation.

        Fast path:
        1. Reactive layer check (sub-millisecond)
        2. Lookahead control (sub-millisecond)
        3. Drone dynamics update

        Background (async or cooldown):
        4. Trajectory generation (25 Hz)
        5. Local planning (10 Hz)
        6. Global planning (2 Hz)
        7. Mission planning (1 Hz)
        8. Path optimization
        """
        if not self._active:
            return

        self._dt = dt
        self._step_counter += 1
        current_time = time.time()

        # ====================================================================
        # FAST REACTIVE LAYER (Highest Priority)
        # ====================================================================
        control_start = time.time()

        # Find nearest obstacle
        nearest_obs_dist = float('inf')
        nearest_obs_angle = 0.0
        for obs in self.external_obstacle_list:
            dx = obs[0] - self.drone.x
            dy = obs[1] - self.drone.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < nearest_obs_dist:
                nearest_obs_dist = dist
                nearest_obs_angle = math.atan2(dy, dx)

        # Predictive collision risk
        collision_prob = self.obstacle_avoider.compute_collision_risk(
            self.drone, self.trajectory_generator._current_trajectory, dt
        )

        # Fast reactive override
        reactive_active, override_vel = self.reactive_layer.evaluate(
            self.drone,
            nearest_obs_dist,
            nearest_obs_angle,
            collision_prob,
            self.obstacle_avoider._predictions.get(-1, None) is not None and 0.5,
            current_time,
        )

        if reactive_active and override_vel is not None:
            # FAST PATH: bypass everything, direct override
            override_vx, override_vy = override_vel
            self.drone.set_velocity_target(override_vx, override_vy, dt)
            self.drone.update_dynamics(dt)

            self._last_control_time = time.time() - control_start
            self.analytics.controller_latency = self._last_control_time
            self.analytics.total_steps += 1
            return

        # ====================================================================
        # LOOKAHEAD CONTROL (Fast path, ~1-2 ms)
        # ====================================================================
        if self._current_target is not None:
            lookahead_dist = self.lookahead_controller.compute_lookahead_distance(
                self.drone.velocity_magnitude
            )

            target_vx, target_vy, heading_error = self.lookahead_controller.compute_control(
                self.drone, self._current_target, lookahead_dist, dt
            )

            # Apply speed from dynamic speed planner
            # Use max of smoothed speed and basic velocity to ensure startup acceleration
            current_speed = self.speed_planner.smooth_speed(
                self.speed_planner._current_target_speed, dt
            )
            speed_mag = math.sqrt(target_vx ** 2 + target_vy ** 2)
            if speed_mag > 0.01:
                # Use the larger of the smoothed speed and the raw controller speed
                # to ensure the drone accelerates from standstill
                effective_speed = max(current_speed, speed_mag * 0.3)
                scale = effective_speed / speed_mag
                target_vx *= scale
                target_vy *= scale

            self.drone.set_velocity_target(target_vx, target_vy, dt)
            self.drone.update_dynamics(dt)

            # Update analytics
            self.analytics.update_speed(self.drone.velocity_magnitude)
            self.analytics.update_acceleration(self.drone.acceleration_magnitude)
            self.analytics.update_jerk(self.drone.jerk_magnitude)

        self._last_control_time = time.time() - control_start
        self.analytics.controller_latency = self._last_control_time

        # Track collision-free steps
        if nearest_obs_dist > self.drone.min_obstacle_clearance:
            self.analytics.collision_free_steps += 1

        # ====================================================================
        # HIERARCHICAL PLANNING (Background / Conditional)
        # ====================================================================
        # Trajectory planning (25 Hz)
        if self.hierarchical_planner.should_plan_trajectory(current_time):
            self._plan_trajectory(current_time)

        # Local planning (10 Hz)
        if self.hierarchical_planner.should_plan_local(current_time):
            self._plan_local(current_time)

        # Global planning (2 Hz)
        if self.hierarchical_planner.should_plan_global(current_time):
            self._plan_global()

        # Mission planning (1 Hz)
        if self.hierarchical_planner.should_plan_mission(current_time):
            self._plan_mission(current_time)

        # Path optimization (runs when path changes)
        if self._global_path and self._step_counter % 20 == 0:
            self._global_path = self.path_optimizer.optimize(
                self._global_path, (self.drone.x, self.drone.y)
            )

        # ====================================================================
        # ANALYTICS UPDATE
        # ====================================================================
        self._update_analytics(current_time)
        self.analytics.total_steps += 1

    def _plan_trajectory(self, current_time: float) -> None:
        """Generate smooth trajectory from current global path."""
        start_time = time.time()
        self.hierarchical_planner.record_trajectory_time(current_time)

        if self._global_path and len(self._global_path) >= 2:
            trajectory = self.trajectory_generator.generate_bezier_path(
                self._global_path,
                self.drone.heading,
                math.atan2(
                    self._global_path[-1][1] - self._global_path[-2][1],
                    self._global_path[-1][0] - self._global_path[-2][0],
                ) if len(self._global_path) >= 2 else self.drone.heading,
            )

            # Update current target from trajectory lookahead
            if trajectory:
                lookahead_dist = self.lookahead_controller.compute_lookahead_distance(
                    self.drone.velocity_magnitude
                )
                lookahead_point = self.trajectory_generator.get_lookahead_point(
                    lookahead_dist, (self.drone.x, self.drone.y)
                )
                if lookahead_point:
                    self._current_target = (lookahead_point[0], lookahead_point[1])

        self._last_planning_time = time.time() - start_time
        self.analytics.planning_latency = self._last_planning_time
        self.analytics.planning_time_history.append(self._last_planning_time)

    def _plan_local(self, current_time: float) -> None:
        """Local path adjustment - avoid local obstacles."""
        self.hierarchical_planner.record_local_time(current_time)

        # Check if we need to deviate for close obstacles
        if self.external_obstacle_list and self._global_path:
            nearest_dist = float('inf')
            for obs in self.external_obstacle_list:
                d = self.drone.distance_to(obs)
                if d < nearest_dist:
                    nearest_dist = d

            if nearest_dist < self.drone.min_obstacle_clearance * 1.5:
                # Need local replan
                if self.external_planner:
                    self._global_path = self.external_planner.find_path(
                        (self.drone.x, self.drone.y),
                        self._global_path[-1] if self._global_path else (0, 0)
                    )

    def _plan_global(self) -> None:
        """Global path planning."""
        start_time = time.time()

        if self.external_planner and self._current_target:
            goal = self._global_path[-1] if self._global_path else self._current_target
            path = self.external_planner.find_path(
                (self.drone.x, self.drone.y), goal
            )
            if path:
                self._global_path = path
                self._global_path = self.path_optimizer.optimize(
                    self._global_path, (self.drone.x, self.drone.y)
                )

        self.hierarchical_planner.record_global_time(time.time())
        self.external_mission_progress = 0.0

    def _plan_mission(self, current_time: float) -> None:
        """High-level mission planning."""
        self.hierarchical_planner.record_mission_time(current_time)
        # Mission planning is delegated to MissionManager externally

    def _update_analytics(self, current_time: float) -> None:
        """Update flight analytics data."""
        elapsed = current_time - self.analytics.mission_start
        dist_to_goal = 0.0
        if self._global_path and len(self._global_path) > 0:
            dist_to_goal = self.drone.distance_to(self._global_path[-1])

        self.analytics.timestamp = current_time
        self.analytics.distance_to_goal = dist_to_goal
        self.analytics.eta_seconds = self.eta_optimizer.compute_eta(
            self.drone, dist_to_goal, current_time
        )
        self.analytics.optimal_eta = self.eta_optimizer.compute_optimal_eta(
            self.drone, dist_to_goal
        )
        self.analytics.eta_delay = self.analytics.eta_seconds - self.analytics.optimal_eta
        self.analytics.flight_mode = self.drone.flight_mode.value
        self.analytics.battery_level = self.external_battery_level
        self.analytics.risk_score = self.external_risk_score
        self.analytics.prediction_confidence = self.external_prediction_confidence
        self.analytics.yaw_rate = self.drone.yaw_rate

        # Mission progress
        if self.external_mission_progress > 0:
            self.analytics.mission_progress = self.external_mission_progress

    # ========================================================================
    # PUBLIC API
    # ========================================================================
    def set_goal(self, goal: Point, path: Optional[Path] = None) -> None:
        """Set mission goal and optionally a precomputed path."""
        self._current_target = goal
        if path is not None:
            self._global_path = list(path)
        else:
            # Generate a simple straight-line path to the goal
            self._global_path = [(self.drone.x, self.drone.y), goal]

        if self._global_path and len(self._global_path) >= 2:
            self._global_path = self.path_optimizer.optimize(
                self._global_path, (self.drone.x, self.drone.y)
            )
            # Generate initial trajectory
            trajectory = self.trajectory_generator.generate_bezier_path(
                self._global_path, self.drone.heading, math.atan2(
                    goal[1] - self.drone.y, goal[0] - self.drone.x
                )
            )
            # Set initial target from trajectory
            if trajectory:
                lookahead_dist = self.lookahead_controller.compute_lookahead_distance(
                    1.0  # Initial slow lookahead
                )
                lp = self.trajectory_generator.get_lookahead_point(
                    lookahead_dist, (self.drone.x, self.drone.y)
                )
                if lp:
                    self._current_target = (lp[0], lp[1])
                else:
                    self._current_target = goal
            else:
                self._current_target = goal
        else:
            self._global_path = None
            self._current_target = goal

    def set_speed_override(self, speed: float) -> None:
        """Override current speed target."""
        self.speed_planner._current_target_speed = max(self.config.min_speed, min(speed, self.drone.max_speed))

    def update_speed_plan(
        self,
        distance_to_goal: float,
        distance_to_nearest_obstacle: float = float('inf'),
        obstacle_density: float = 0.0,
        mission_deadline_remaining: Optional[float] = None,
    ) -> None:
        """Update speed plan based on current conditions."""
        target_speed = self.speed_planner.compute_target_speed(
            self.drone,
            distance_to_goal,
            distance_to_nearest_obstacle,
            obstacle_density,
            self.external_battery_level,
            self.external_prediction_confidence,
            self.external_risk_score,
            mission_deadline_remaining,
            self.external_mission_priority,
        )
        self.speed_planner._current_target_speed = target_speed
        self.analytics.target_speed = target_speed

    def update_obstacle_data(
        self,
        obstacles: List[Point],
        dynamic_obstacles: Optional[List[Tuple[Point, Point]]] = None,
    ) -> None:
        """Update obstacle data for predictive avoidance."""
        self.external_obstacle_list = obstacles
        if dynamic_obstacles:
            self.external_dynamic_obstacles = dynamic_obstacles
        self.obstacle_avoider.update_predictions(
            self.drone, obstacles, self.external_dynamic_obstacles, self._dt
        )

    def switch_flight_mode(self, mode: FlightMode) -> None:
        """Switch flight mode mid-mission."""
        self.drone.flight_mode = mode
        self.analytics.flight_mode = mode.value

    def get_current_target(self) -> Optional[Point]:
        """Get the current lookahead target."""
        return self._current_target

    def get_global_path(self) -> Optional[Path]:
        """Get the current global path."""
        return self._global_path

    def get_analytics_snapshot(self) -> FlightAnalytics:
        """Get a snapshot of current analytics."""
        return self.analytics

    def get_dashboard_data(self) -> dict:
        """Get formatted data for the flight dashboard."""
        a = self.analytics
        return {
            "speed": {
                "current": round(a.current_speed, 2),
                "target": round(a.target_speed, 2),
                "average": round(a.average_speed_computed, 2),
                "max": round(a.max_speed_achieved, 2),
            },
            "acceleration": {
                "current": round(a.current_acceleration, 2),
                "average": round(a.average_acceleration, 2),
            },
            "jerk": round(a.current_jerk, 4),
            "yaw_rate": round(a.yaw_rate, 2),
            "eta": {
                "current": round(a.eta_seconds, 1),
                "optimal": round(a.optimal_eta, 1),
                "delay": round(a.eta_delay, 1),
            },
            "mission": {
                "progress": round(a.mission_progress * 100, 1),
                "distance_to_goal": round(a.distance_to_goal, 1),
            },
            "risk": {
                "score": round(a.risk_score, 2),
                "min_obstacle_dist": round(a.min_obstacle_distance, 1),
                "confidence": round(a.prediction_confidence, 2),
            },
            "latency": {
                "planning": round(a.planning_latency * 1000, 2),
                "controller": round(a.controller_latency * 1000, 2),
            },
            "flight_mode": a.flight_mode,
            "battery": round(a.battery_level * 100, 1),
            "smoothness": round(a.flight_smoothness, 2),
            "collision_rate": round(a.collision_rate * 100, 1),
        }

    def reset(self) -> None:
        """Reset the flight manager state."""
        self._current_target = None
        self._global_path = None
        self.trajectory_generator.invalidate_cache()
        self.lookahead_controller.reset()
        self.reactive_layer.reset()
        self.analytics = FlightAnalytics()
        self.analytics.mission_start = time.time()
        self._step_counter = 0

    def shutdown(self) -> None:
        """Shutdown flight manager and stop background threads."""
        self._active = False
        for thread in self._async_threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
        self._async_threads.clear()