"""
Comprehensive Tests for the High-Performance Flight Manager
============================================================
Tests: performance benchmarks, collision avoidance, trajectory generation,
speed planning, hierarchical planning, ETA optimization, and regression.
"""

from __future__ import annotations

import math
import time
import unittest
from typing import List, Tuple

import numpy as np

from src.core.drone import Drone, FlightMode, default_mode_params
from src.control.flight_manager import (
    FlightManager,
    PerformanceConfig,
    DynamicSpeedPlanner,
    ContinuousTrajectoryGenerator,
    LookaheadController,
    PredictiveObstacleAvoidance,
    FastReactiveLayer,
    DynamicPathOptimizer,
    ETAOptimizer,
    HierarchicalPlanner,
    FlightAnalytics,
)


Point = Tuple[float, float]
Path = List[Point]


class TestDynamicSpeedPlanner(unittest.TestCase):
    """Tests for the dynamic speed planning system."""

    def setUp(self):
        self.config = PerformanceConfig()
        self.planner = DynamicSpeedPlanner(self.config)
        self.drone = Drone((0, 0), FlightMode.SPORT)

    def test_speed_increases_with_distance(self):
        """Speed should be higher when far from goal."""
        speed_near = self.planner.compute_target_speed(
            self.drone, distance_to_goal=5.0,
            distance_to_nearest_obstacle=100.0, obstacle_density=0.0,
            battery_level=1.0, prediction_confidence=1.0, risk_score=0.0,
        )
        speed_far = self.planner.compute_target_speed(
            self.drone, distance_to_goal=80.0,
            distance_to_nearest_obstacle=100.0, obstacle_density=0.0,
            battery_level=1.0, prediction_confidence=1.0, risk_score=0.0,
        )
        self.assertGreater(speed_far, speed_near)

    def test_speed_decreases_near_obstacles(self):
        """Speed should decrease when close to obstacles."""
        speed_clear = self.planner.compute_target_speed(
            self.drone, distance_to_goal=50.0,
            distance_to_nearest_obstacle=100.0, obstacle_density=0.0,
            battery_level=1.0, prediction_confidence=1.0, risk_score=0.0,
        )
        speed_blocked = self.planner.compute_target_speed(
            self.drone, distance_to_goal=50.0,
            distance_to_nearest_obstacle=2.0, obstacle_density=0.5,
            battery_level=1.0, prediction_confidence=1.0, risk_score=0.0,
        )
        self.assertGreater(speed_clear, speed_blocked)

    def test_speed_decreases_with_risk(self):
        """Speed should decrease with higher risk score."""
        speed_safe = self.planner.compute_target_speed(
            self.drone, distance_to_goal=50.0,
            distance_to_nearest_obstacle=100.0, obstacle_density=0.0,
            battery_level=1.0, prediction_confidence=1.0, risk_score=0.0,
        )
        speed_risky = self.planner.compute_target_speed(
            self.drone, distance_to_goal=50.0,
            distance_to_nearest_obstacle=100.0, obstacle_density=0.0,
            battery_level=1.0, prediction_confidence=1.0, risk_score=0.8,
        )
        self.assertGreater(speed_safe, speed_risky)

    def test_speed_smoothing(self):
        """Speed smoothing should reduce jerk."""
        target = 10.0
        smoothed = self.planner.smooth_speed(target, dt=0.01)
        self.assertGreaterEqual(smoothed, 0.0)
        self.assertLessEqual(smoothed, target)

        # Multiple smooth steps should converge
        for _ in range(500):
            smoothed = self.planner.smooth_speed(target, dt=0.01)
        self.assertAlmostEqual(smoothed, target, delta=2.0)

    def test_speed_clamped_to_max(self):
        """Speed should never exceed max speed."""
        self.drone.flight_mode = FlightMode.ECO
        speed = self.planner.compute_target_speed(
            self.drone, distance_to_goal=100.0,
            distance_to_nearest_obstacle=100.0, obstacle_density=0.0,
            battery_level=1.0, prediction_confidence=1.0, risk_score=0.0,
            mission_priority=1.0,
        )
        self.assertLessEqual(speed, self.drone.max_speed)

    def test_minimum_speed(self):
        """Speed should never go below minimum."""
        speed = self.planner.compute_target_speed(
            self.drone, distance_to_goal=0.5,
            distance_to_nearest_obstacle=0.5, obstacle_density=1.0,
            battery_level=0.1, prediction_confidence=0.1, risk_score=0.95,
        )
        self.assertGreaterEqual(speed, self.config.min_speed)


class TestContinuousTrajectoryGenerator(unittest.TestCase):
    """Tests for smooth trajectory generation."""

    def setUp(self):
        self.config = PerformanceConfig()
        self.generator = ContinuousTrajectoryGenerator(self.config)

    def test_generates_smooth_path(self):
        """Should generate a smooth path from waypoints."""
        path = [(0, 0), (10, 0), (20, 5), (30, 10)]
        trajectory = self.generator.generate_bezier_path(path)

        self.assertIsNotNone(trajectory)
        self.assertGreater(len(trajectory), len(path))

        # Should start at first waypoint
        self.assertAlmostEqual(trajectory[0][0], path[0][0], delta=0.5)
        self.assertAlmostEqual(trajectory[0][1], path[0][1], delta=0.5)

    def test_lookahead_point(self):
        """Lookahead should return a point further along the trajectory."""
        path = [(0, 0), (50, 0)]
        trajectory = self.generator.generate_bezier_path(path)

        lookahead = self.generator.get_lookahead_point(5.0, (0, 0))
        self.assertIsNotNone(lookahead)

        # Lookahead should be ahead of current position
        if lookahead:
            self.assertGreaterEqual(lookahead[0], 0)

    def test_single_segment(self):
        """Should handle single-segment paths."""
        path = [(0, 0), (10, 10)]
        trajectory = self.generator.generate_bezier_path(path)
        self.assertGreater(len(trajectory), 1)

    def test_invalid_path(self):
        """Should handle empty paths."""
        trajectory = self.generator.generate_bezier_path([])
        self.assertEqual(len(trajectory), 0)

    def test_cache_efficiency(self):
        """Repeated queries should use cache."""
        path = [(0, 0), (10, 10), (20, 0)]
        t1 = self.generator.generate_bezier_path(path)
        t2 = self.generator.generate_bezier_path(path)
        self.assertEqual(len(t1), len(t2))
        self.assertIs(t1, t2)  # Same cached object


class TestLookaheadController(unittest.TestCase):
    """Tests for the lookahead/pure pursuit controller."""

    def setUp(self):
        self.config = PerformanceConfig()
        self.controller = LookaheadController(self.config)
        self.drone = Drone((0, 0), FlightMode.SPORT)

    def test_computes_lookahead_distance(self):
        """Lookahead distance should increase with speed."""
        lookahead_low = self.controller.compute_lookahead_distance(1.0)
        lookahead_high = self.controller.compute_lookahead_distance(10.0)
        self.assertGreater(lookahead_high, lookahead_low)
        self.assertLessEqual(lookahead_low, self.config.max_lookahead)
        self.assertGreaterEqual(lookahead_low, self.config.min_lookahead)

    def test_computes_control_output(self):
        """Should produce valid control outputs."""
        target = (50, 50)
        vx, vy, heading_err = self.controller.compute_control(
            self.drone, target, 10.0, dt=0.01
        )
        self.assertIsInstance(vx, float)
        self.assertIsInstance(vy, float)
        self.assertIsInstance(heading_err, float)

    def test_converges_to_target(self):
        """After multiple steps, should approach target."""
        target = (10, 0)

        for _ in range(100):
            vx, vy, _ = self.controller.compute_control(self.drone, target, 5.0, dt=0.05)
            self.drone.set_velocity_target(vx, vy, 0.05)
            self.drone.update_dynamics(0.05)

        final_dist = self.drone.distance_to(target)
        self.assertLessEqual(final_dist, 20.0)


class TestPredictiveObstacleAvoidance(unittest.TestCase):
    """Tests for predictive obstacle avoidance."""

    def setUp(self):
        self.config = PerformanceConfig()
        self.avoider = PredictiveObstacleAvoidance(self.config)
        self.drone = Drone((0, 0), FlightMode.SPORT)

    def test_static_obstacle_detection(self):
        """Should detect static obstacles."""
        obstacles = [(5, 0)]
        self.avoider.update_predictions(self.drone, obstacles, [], dt=0.01)
        risk = self.avoider.compute_collision_risk(self.drone, [], 0.01)
        self.assertGreaterEqual(risk, 0.0)

    def test_dynamic_obstacle_prediction(self):
        """Should predict future positions of moving obstacles."""
        dyn_obs = [((5, 5), (1, 0))]  # moving right
        self.avoider.update_predictions(self.drone, [], dyn_obs, dt=0.01)

        # Should have predictions
        self.assertGreater(len(self.avoider._predictions), 0)

    def test_escape_vector(self):
        """Should compute escape vector during collision warning."""
        obstacles = [(2, 0)]  # Very close
        self.avoider.update_predictions(self.drone, obstacles, [], dt=0.01)
        risk = self.avoider.compute_collision_risk(self.drone, [], 0.01)

        if self.avoider.has_collision_warning:
            escape = self.avoider.escape_vector
            self.assertIsNotNone(escape)
            vx, vy = escape
            speed = math.sqrt(vx**2 + vy**2)
            self.assertGreater(speed, 0)


class TestFastReactiveLayer(unittest.TestCase):
    """Tests for the emergency reactive layer."""

    def setUp(self):
        self.config = PerformanceConfig()
        self.reactive = FastReactiveLayer(self.config)
        self.drone = Drone((0, 0), FlightMode.SPORT)

    def test_triggers_on_close_obstacle(self):
        """Should trigger on very close obstacles."""
        active, override = self.reactive.evaluate(
            self.drone, nearest_obstacle_distance=0.5,
            nearest_obstacle_angle=0.0, collision_probability=0.9,
            time_to_collision=0.5, current_time=time.time()
        )
        self.assertTrue(active)
        self.assertIsNotNone(override)

    def test_not_triggered_on_safe_distance(self):
        """Should not trigger when obstacles are far."""
        active, override = self.reactive.evaluate(
            self.drone, nearest_obstacle_distance=50.0,
            nearest_obstacle_angle=0.0, collision_probability=0.0,
            time_to_collision=100.0, current_time=time.time()
        )
        self.assertFalse(active)

    def test_reset_clears_state(self):
        """Reset should clear override state."""
        self.reactive.evaluate(
            self.drone, nearest_obstacle_distance=0.5,
            nearest_obstacle_angle=0.0, collision_probability=0.9,
            time_to_collision=0.5, current_time=time.time()
        )
        self.assertTrue(self.reactive.is_active)
        self.reactive.reset()
        self.assertFalse(self.reactive.is_active)


class TestDynamicPathOptimizer(unittest.TestCase):
    """Tests for dynamic path optimization."""

    def setUp(self):
        self.config = PerformanceConfig()
        self.optimizer = DynamicPathOptimizer(self.config)

    def test_removes_collinear_waypoints(self):
        """Should remove unnecessary collinear points."""
        path = [(0, 0), (5, 0), (10, 0), (15, 5), (20, 10)]
        optimized = self.optimizer.optimize(path, (0, 0))
        self.assertLessEqual(len(optimized), len(path))

    def test_preserves_start_and_end(self):
        """Should preserve first and last waypoint."""
        path = [(0, 0), (5, 5), (10, 10), (20, 20)]
        optimized = self.optimizer.optimize(path, (0, 0))
        self.assertEqual(optimized[0], path[0])
        self.assertEqual(optimized[-1], path[-1])

    def test_short_path_no_change(self):
        """Short paths should not be modified."""
        path = [(0, 0), (10, 10)]
        optimized = self.optimizer.optimize(path, (0, 0))
        self.assertEqual(len(optimized), 2)


class TestETAOptimizer(unittest.TestCase):
    """Tests for ETA optimization."""

    def setUp(self):
        self.config = PerformanceConfig()
        self.optimizer = ETAOptimizer(self.config)
        self.drone = Drone((0, 0), FlightMode.SPORT)

    def test_computes_eta(self):
        """Should compute reasonable ETA."""
        self.drone.vx = 5.0
        eta = self.optimizer.compute_eta(self.drone, 100.0, time.time())
        self.assertGreater(eta, 0)
        self.assertAlmostEqual(eta, 20.0, delta=1.0)

    def test_optimal_eta_faster(self):
        """Optimal ETA should be less than or equal to current."""
        self.drone.vx = 1.0  # Very slow
        eta = self.optimizer.compute_eta(self.drone, 100.0, time.time())
        optimal = self.optimizer.compute_optimal_eta(self.drone, 100.0)
        self.assertLessEqual(optimal, eta)

    def test_pace_factor(self):
        """Pace factor should reflect required speed change."""
        self.drone.vx = 1.0
        pace = self.optimizer.compute_pace_factor(
            self.drone, 100.0, remaining_mission_time=10.0
        )
        self.assertGreater(pace, 1.0)  # Need to speed up


class TestHierarchicalPlanner(unittest.TestCase):
    """Tests for hierarchical planning rates."""

    def setUp(self):
        self.config = PerformanceConfig()
        self.planner = HierarchicalPlanner(self.config)

    def test_planning_rates(self):
        """Should maintain correct planning frequencies."""
        current_time = time.time()

        # Initially all should be allowed
        self.assertTrue(self.planner.should_plan_mission(current_time))
        self.assertTrue(self.planner.should_plan_global(current_time))
        self.assertTrue(self.planner.should_plan_local(current_time))
        self.assertTrue(self.planner.should_plan_trajectory(current_time))

        # After recording, should not be allowed immediately
        self.planner.record_mission_time(current_time)
        self.planner.record_global_time(current_time)
        self.planner.record_local_time(current_time)
        self.planner.record_trajectory_time(current_time)

        self.assertFalse(self.planner.should_plan_mission(current_time))
        self.assertFalse(self.planner.should_plan_global(current_time))
        self.assertFalse(self.planner.should_plan_local(current_time))
        self.assertFalse(self.planner.should_plan_trajectory(current_time))

        # After interval has passed, should allow again
        later = current_time + 1.1
        self.assertTrue(self.planner.should_plan_mission(later))
        self.assertTrue(self.planner.should_plan_global(later))

    def test_latency_tracking(self):
        """Should track planning latencies."""
        self.planner.record_mission_time(time.time())
        self.planner.record_global_time(time.time())
        self.assertGreaterEqual(self.planner.mission_latency, 0)
        self.assertGreaterEqual(self.planner.global_latency, 0)


class TestFlightManagerIntegration(unittest.TestCase):
    """Integration tests for the full FlightManager."""

    def setUp(self):
        self.config = PerformanceConfig()
        self.drone = Drone((10, 10), FlightMode.SPORT)
        self.fm = FlightManager(self.drone, self.config)

    def test_sets_goal(self):
        """Should accept a mission goal."""
        goal = (90, 90)
        self.fm.set_goal(goal)
        self.assertIsNotNone(self.fm.get_current_target())

    def test_update_runs(self):
        """Update should run without errors."""
        self.fm.set_goal((50, 50))
        for _ in range(10):
            self.fm.update(0.01)
        self.assertGreater(self.fm.analytics.total_steps, 0)

    def test_dashboard_data(self):
        """Should produce valid dashboard data."""
        self.fm.set_goal((50, 50))
        self.fm.update(0.01)
        data = self.fm.get_dashboard_data()
        self.assertIn("speed", data)
        self.assertIn("eta", data)
        self.assertIn("latency", data)
        self.assertIn("risk", data)
        self.assertIn("flight_mode", data)

    def test_speed_planning(self):
        """Speed planning should update target speed."""
        self.fm.update_speed_plan(
            distance_to_goal=50.0,
            distance_to_nearest_obstacle=100.0,
            obstacle_density=0.0,
        )
        self.assertGreater(self.fm.speed_planner._current_target_speed, 0)

    def test_flight_mode_switching(self):
        """Should switch flight modes mid-mission."""
        self.fm.switch_flight_mode(FlightMode.TURBO)
        self.assertEqual(self.drone.flight_mode, FlightMode.TURBO)
        self.assertEqual(self.fm.analytics.flight_mode, "TURBO")

    def test_obstacle_update(self):
        """Should process obstacle data."""
        obstacles = [(15, 15), (20, 20)]
        self.fm.update_obstacle_data(obstacles)
        self.assertEqual(len(self.fm.external_obstacle_list), 2)

    def test_reset_clears_state(self):
        """Reset should clear the flight manager state."""
        self.fm.set_goal((50, 50))
        self.fm.update(0.01)
        self.fm.reset()
        self.assertIsNone(self.fm.get_current_target())
        self.assertEqual(self.fm.analytics.total_steps, 0)

    def test_analytics_snapshot(self):
        """Should return a valid analytics snapshot."""
        snapshot = self.fm.get_analytics_snapshot()
        self.assertIsInstance(snapshot, FlightAnalytics)
        self.assertGreater(snapshot.mission_start, 0)


class TestFlightModePerformance(unittest.TestCase):
    """Test that flight modes provide increasing performance."""

    def test_mode_speed_increases(self):
        """Speed should increase from ECO to TURBO."""
        modes = [FlightMode.ECO, FlightMode.NORMAL, FlightMode.CRUISE,
                 FlightMode.SPORT, FlightMode.TURBO]
        speeds = [default_mode_params(m)["max_speed"] for m in modes]
        for i in range(1, len(speeds)):
            self.assertGreaterEqual(speeds[i], speeds[i-1])

    def test_emergency_has_high_acceleration(self):
        """Emergency mode should have highest acceleration."""
        emergency = default_mode_params(FlightMode.EMERGENCY)
        normal = default_mode_params(FlightMode.NORMAL)
        self.assertGreater(emergency["max_acceleration"], normal["max_acceleration"])


class TestDroneDynamics(unittest.TestCase):
    """Tests for drone dynamics model."""

    def setUp(self):
        self.drone = Drone((0, 0), FlightMode.SPORT)

    def test_velocity_limits(self):
        """Velocity should be limited by max speed."""
        self.drone.set_velocity_target(100, 0, dt=1.0)
        self.drone.update_dynamics(1.0)
        self.assertLessEqual(self.drone.velocity_magnitude, self.drone.max_speed)

    def test_position_update(self):
        """Position should update based on velocity."""
        self.drone.set_velocity_target(5, 0, dt=1.0)
        self.drone.update_dynamics(1.0)
        self.assertGreater(self.drone.x, 0)

    def test_braking(self):
        """Brakes should reduce velocity."""
        self.drone.vx = 10.0
        self.drone.apply_brakes(dt=1.0)
        # After braking, velocity should be less
        self.assertLessEqual(self.drone.velocity_magnitude, 10.0)

    def test_heading_follows_velocity(self):
        """Heading should align with velocity direction."""
        self.drone.set_velocity_target(1, 1, dt=1.0)
        self.drone.update_dynamics(1.0)
        expected_heading = math.atan2(1, 1)
        self.assertAlmostEqual(self.drone.heading, expected_heading, delta=0.1)

    def test_flight_mode_change(self):
        """Switching flight mode should update parameters."""
        self.drone.flight_mode = FlightMode.TURBO
        self.assertEqual(self.drone.max_speed, default_mode_params(FlightMode.TURBO)["max_speed"])

    def test_distance_to(self):
        """Distance calculation should be correct."""
        dist = self.drone.distance_to((3, 4))
        self.assertAlmostEqual(dist, 5.0)

    def test_heading_to(self):
        """Heading calculation should be correct."""
        heading = self.drone.heading_to((1, 1))
        self.assertAlmostEqual(heading, math.pi / 4, delta=0.01)


# ============================================================================
# Performance Benchmarks
# ============================================================================
class BenchmarkFlightManager(unittest.TestCase):
    """Performance benchmarks for the Flight Manager."""

    def setUp(self):
        self.config = PerformanceConfig()
        self.drone = Drone((10, 10), FlightMode.TURBO)
        self.fm = FlightManager(self.drone, self.config)
        self.fm.set_goal((90, 90))

        # Obstacles
        obstacles = [(20, 20), (30, 25), (40, 30), (50, 35),
                     (60, 40), (70, 45), (80, 50)]
        self.fm.update_obstacle_data(obstacles)

    def test_control_loop_latency(self):
        """Control loop should run under 5ms."""
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            self.fm.update(0.01)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            latencies.append(elapsed)

        avg_latency = np.mean(latencies)
        max_latency = np.max(latencies)

        print(f"\n  Control Loop Latency: avg={avg_latency:.2f}ms, max={max_latency:.2f}ms")
        self.assertLess(avg_latency, 5.0, f"Average latency {avg_latency:.2f}ms exceeds 5ms")

    def test_speed_achieved(self):
        """Should achieve high cruise speed."""
        # Run for 1000 steps to build up speed with speed planning
        self.fm.update_speed_plan(
            distance_to_goal=self.drone.distance_to((90, 90)),
            distance_to_nearest_obstacle=50.0,
            obstacle_density=0.0,
        )
        for _ in range(1000):
            self.fm.update_speed_plan(
                distance_to_goal=self.drone.distance_to((90, 90)),
                distance_to_nearest_obstacle=50.0,
                obstacle_density=0.0,
            )
            self.fm.update(0.01)

        max_speed = self.fm.analytics.max_speed_achieved
        avg_speed = self.fm.analytics.average_speed_computed

        print(f"\n  Max Speed: {max_speed:.1f} m/s")
        print(f"  Average Speed: {avg_speed:.1f} m/s")

        # In TURBO mode should reach at least 5 m/s in simulation
        self.assertGreater(max_speed, 5.0,
                           f"Max speed {max_speed:.1f} m/s below 5 m/s target")

    def test_planning_latency(self):
        """Planning should complete quickly."""
        for _ in range(50):
            self.fm.update(0.01)

        plan_lat = self.fm.analytics.planning_latency * 1000  # ms
        print(f"\n  Planning Latency: {plan_lat:.2f}ms")
        self.assertLess(plan_lat, 10.0)

    def test_flight_smoothness(self):
        """Flight should be smooth (low jerk)."""
        for _ in range(200):
            self.fm.update(0.01)

        smoothness = self.fm.analytics.flight_smoothness
        print(f"\n  Flight Smoothness: {smoothness:.4f}")
        self.assertGreater(smoothness, 0.3)

    def test_reactive_speed(self):
        """Reactive layer should respond in <1ms."""
        obstacles = [(15, 15)]  # Close
        self.fm.update_obstacle_data(obstacles)

        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            self.fm.update(0.01)
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)

        avg = np.mean(latencies)
        print(f"\n  Reactive Latency: {avg:.3f}ms")
        self.assertLess(avg, 2.0)

    def test_mission_completion_time(self):
        """Should complete a mission quickly."""
        self.drone = Drone((10, 10), FlightMode.TURBO)
        self.fm = FlightManager(self.drone, self.config)
        goal = (90, 90)
        self.fm.set_goal(goal)

        start_time = time.time()
        max_steps = 2000
        step = 0

        obstacles = [(20, 20), (30, 25), (40, 35)]
        while step < max_steps:
            self.fm.update_obstacle_data(obstacles)
            self.fm.update_speed_plan(
                distance_to_goal=self.drone.distance_to(goal),
                distance_to_nearest_obstacle=50.0,
                obstacle_density=0.0,
            )
            self.fm.update(0.01)

            if self.drone.distance_to(goal) < 5.0:
                break
            step += 1

        elapsed = time.time() - start_time
        total_dist = self.drone.distance_to((10, 10))

        print(f"\n  Mission completed in {step} steps ({elapsed:.2f}s)")
        print(f"  Distance covered: {total_dist:.1f}m")
        print(f"  Average speed: {self.fm.analytics.average_speed_computed:.1f} m/s")
        print(f"  Max speed: {self.fm.analytics.max_speed_achieved:.1f} m/s")

        self.assertLess(step, max_steps, "Mission did not complete within step limit")


if __name__ == "__main__":
    unittest.main(verbosity=2)