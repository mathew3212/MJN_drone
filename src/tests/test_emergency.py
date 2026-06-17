"""Unit tests for EmergencyManager."""

from src.autonomy.emergency_manager import EmergencyManager
from src.autonomy.battery_manager import BatteryManager
from src.core.drone import Drone


class MockBattery:
    def __init__(self, low=False, critical=False):
        self._low = low
        self._critical = critical

    def is_low(self):
        return self._low

    def is_critical(self):
        return self._critical


class TestEmergencyManager:
    """Test suite for EmergencyManager."""

    def test_normal_state(self):
        em = EmergencyManager()
        drone = Drone((5, 5))
        bat = MockBattery(low=False, critical=False)
        result = em.evaluate(drone, bat, path=[(5, 5), (6, 5)], sensor_ok=True)
        assert result == em.NORMAL

    def test_critical_battery(self):
        em = EmergencyManager()
        drone = Drone((5, 5))
        bat = MockBattery(low=True, critical=True)
        result = em.evaluate(drone, bat, path=[], sensor_ok=True)
        assert result == em.CRITICAL_BATTERY

    def test_low_battery(self):
        em = EmergencyManager()
        drone = Drone((5, 5))
        bat = MockBattery(low=True, critical=False)
        result = em.evaluate(drone, bat, path=[], sensor_ok=True)
        assert result == em.LOW_BATTERY

    def test_no_path(self):
        em = EmergencyManager()
        drone = Drone((5, 5))
        bat = MockBattery(low=False, critical=False)
        result = em.evaluate(drone, bat, path=None, sensor_ok=True)
        assert result == em.NO_PATH

    def test_sensor_failure(self):
        em = EmergencyManager()
        drone = Drone((5, 5))
        bat = MockBattery(low=False, critical=False)
        result = em.evaluate(drone, bat, path=[], sensor_ok=False)
        assert result == em.SENSOR_FAILURE

    def test_stuck_detection(self):
        em = EmergencyManager()
        drone = Drone((5, 5))
        bat = MockBattery(low=False, critical=False)
        # Stuck detection is now handled by local_planner and main loop,
        # not by EmergencyManager.evaluate(). Verify it returns NORMAL.
        for _ in range(25):
            result = em.evaluate(drone, bat, path=[(5, 5)], sensor_ok=True)
            em.last_position = (5, 5)
        assert result == em.NORMAL
