"""Unit tests for behavior tree and drone behaviors."""

from src.autonomy.behavior_tree import Selector, Sequence, Condition, Action
from src.autonomy.drone_behaviors import DroneBehaviors
from src.core.drone import Drone
from src.core.world import World
from src.autonomy.battery_manager import BatteryManager
from src.autonomy.emergency_manager import EmergencyManager


class TestBehaviorTree:
    """Test the behavior tree nodes."""

    def test_selector_runs_until_success(self):
        results = []

        def a():
            results.append("a")
            return False

        def b():
            results.append("b")
            return True

        def c():
            results.append("c")
            return True

        selector = Selector([
            Condition(a),
            Condition(b),
            Condition(c),
        ])
        assert selector.run() is True
        assert results == ["a", "b"]

    def test_selector_fails_all(self):
        def fail():
            return False

        selector = Selector([
            Condition(fail),
            Condition(fail),
        ])
        assert selector.run() is False

    def test_sequence_fails_on_first_false(self):
        results = []

        def a():
            results.append("a")
            return True

        def b():
            results.append("b")
            return False

        def c():
            results.append("c")
            return True

        seq = Sequence([Condition(a), Condition(b), Condition(c)])
        assert seq.run() is False
        assert results == ["a", "b"]

    def test_sequence_succeeds(self):
        def ok():
            return True

        seq = Sequence([Condition(ok), Condition(ok)])
        assert seq.run() is True

    def test_action_always_returns_true(self):
        side_effects = []

        def act():
            side_effects.append("executed")

        action = Action(act)
        assert action.run() is True
        assert side_effects == ["executed"]


class TestDroneBehaviors:
    """Test DroneBehaviors integration."""

    def test_low_battery_condition(self):
        drone = Drone((10, 10))
        world = World(100, 100, 10)
        bat = BatteryManager(capacity=100.0, reserve_level=20.0)
        bat.level = 15.0  # Below reserve
        behaviors = DroneBehaviors(drone, world, battery=bat)
        assert behaviors.low_battery() is True

    def test_not_low_battery(self):
        drone = Drone((10, 10))
        world = World(100, 100, 10)
        bat = BatteryManager()
        behaviors = DroneBehaviors(drone, world, battery=bat)
        assert behaviors.low_battery() is False

    def test_collision_risk_near_obstacle(self):
        drone = Drone((10, 10))
        world = World(100, 100, 10)
        # Place obstacle very close
        world.obstacles.add((11, 10))
        behaviors = DroneBehaviors(drone, world)
        assert behaviors.collision_risk() is True

    def test_no_collision_risk(self):
        drone = Drone((10, 10))
        world = World(100, 100, 10)
        world.obstacles = [(50, 50)]  # Far away
        behaviors = DroneBehaviors(drone, world)
        assert behaviors.collision_risk() is False

    def test_return_home_action(self):
        drone = Drone((10, 10))
        behaviors = DroneBehaviors(drone, World(100, 100, 10))
        behaviors.return_home()
        assert behaviors.state == "RETURN_HOME"