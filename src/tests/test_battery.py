"""Unit tests for BatteryManager."""

from src.autonomy.battery_manager import BatteryManager


class TestBatteryManager:
    """Test suite for BatteryManager."""

    def test_init(self):
        bat = BatteryManager()
        assert bat.level == 100.0
        assert bat.percentage() == 100.0

    def test_update_drains_battery(self):
        bat = BatteryManager()
        bat.update(distance_travelled=1, obstacle_count=0)
        assert bat.level < 100.0

    def test_is_low(self):
        bat = BatteryManager(capacity=100.0, reserve_level=20.0)
        # Drain to below reserve
        while bat.level > bat.reserve_level:
            bat.update(distance_travelled=10, obstacle_count=0)
        assert bat.is_low()

    def test_is_critical(self):
        bat = BatteryManager(capacity=100.0, critical_level=10.0)
        while bat.level > bat.critical_level:
            bat.update(distance_travelled=10, obstacle_count=0)
        assert bat.is_critical()

    def test_is_empty(self):
        bat = BatteryManager()
        bat.level = 0
        assert bat.is_empty()

    def test_percentage(self):
        bat = BatteryManager(capacity=50.0)
        bat.level = 25.0
        assert bat.percentage() == 50.0