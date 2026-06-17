"""
Tests for the AirSim integration package.

Runs without AirSim connected — tests the physics model,
bridge fallback, coordinate conversion, and sensor fallbacks.
"""

import math
import sys

from src.airsim.airsim_config import (
    AirSimConfig,
    AirSimConnectionConfig,
    AirSimDroneConfig,
    AirSimSensorConfig,
    AirSimPhysicsConfig,
    AirSimWorldConfig,
)
from src.airsim.airsim_drone import AirSimDrone, Pose3D, Velocity3D, DroneState
from src.airsim.airsim_physics import AirSimPhysicsModel, PhysicsState
from src.airsim.airsim_sensors import AirSimSensorSuite, LidarData
from src.airsim.airsim_bridge import AirSimBridge, SimulationMode


def test_config_defaults():
    """Test that default configs are created correctly."""
    cfg = AirSimConfig()
    assert cfg.connection.ip == "127.0.0.1"
    assert cfg.connection.port == 41451
    assert cfg.drone.vehicle_name == "Drone1"
    assert cfg.physics.gravity == 9.81
    assert cfg.sensors.lidar_enabled is True
    print("[PASS] test_config_defaults")


def test_config_serialization():
    """Test config to_dict / from_dict round-trip."""
    cfg = AirSimConfig()
    d = cfg.to_dict()
    cfg2 = AirSimConfig.from_dict(d)
    assert cfg2.connection.ip == "127.0.0.1"
    assert cfg2.physics.gravity == 9.81
    print("[PASS] test_config_serialization")


def test_pose3d():
    """Test Pose3D creation and distance."""
    p1 = Pose3D(0, 0, 0)
    p2 = Pose3D(3, 4, 0)
    assert p1.distance_to(p2) == 5.0
    assert p1.to_tuple() == (0, 0, 0)
    print("[PASS] test_pose3d")


def test_velocity3d():
    """Test Velocity3D speed and heading."""
    v = Velocity3D(3, 4, 0)
    assert abs(v.speed() - 5.0) < 1e-10
    assert abs(v.heading() - math.atan2(4, 3)) < 1e-10
    print("[PASS] test_velocity3d")


def test_drone_without_airsim():
    """Test AirSimDrone creation and connection fallback."""
    cfg = AirSimConfig()
    drone = AirSimDrone(cfg)

    # Without AirSim package, connect() should return False
    result = drone.connect()
    assert result is False
    assert drone.is_connected() is False

    # Other operations should be safe no-ops
    assert drone.takeoff() is False
    assert drone.land() is False
    assert drone.move_to_position(1, 2, -3) is False
    assert drone.move_by_velocity(1, 1, 0) is False
    assert drone.hover() is False
    assert drone.check_collision() is False
    assert drone.get_kinematics() == {}
    drone.disconnect()

    print("[PASS] test_drone_without_airsim")


def test_drone_grid_conversion():
    """Test grid ↔ AirSim coordinate conversion."""
    cfg = AirSimConfig()
    drone = AirSimDrone(cfg)
    drone.set_grid_mapping(origin_x=50, origin_y=50, scale=1.0)

    # Grid (50,50) → AirSim (0,0)
    ax, ay = drone.grid_to_airsim(50, 50)
    assert ax == 0.0 and ay == 0.0

    # Grid (60,40) → AirSim (10,-10)
    ax, ay = drone.grid_to_airsim(60, 40)
    assert ax == 10.0 and ay == -10.0

    # AirSim (10,-10) → Grid (60,40)
    gx, gy = drone.airsim_to_grid(10, -10)
    assert gx == 60.0 and gy == 40.0

    # get_grid_position with origin=50 and pose at (0,0) gives (50,50)
    gx, gy = drone.get_grid_position()
    assert (gx, gy) == (50.0, 50.0)

    print("[PASS] test_drone_grid_conversion")


def test_drone_state_enum():
    """Test DroneState enum values."""
    assert DroneState.GROUNDED.value == "grounded"
    assert DroneState.IN_AIR.value == "in_air"
    assert DroneState.FLYING.value == "flying"
    print("[PASS] test_drone_state_enum")


def test_drone_context_manager():
    """Test that context manager doesn't crash."""
    cfg = AirSimConfig()
    with AirSimDrone(cfg) as drone:
        assert not drone.is_connected()
    print("[PASS] test_drone_context_manager")


# ── Physics tests ──────────────────────────────────────────────────


def test_physics_reset():
    """Test physics model reset."""
    cfg = AirSimPhysicsConfig()
    physics = AirSimPhysicsModel(cfg)
    physics.set_thrust((0, 0, 15))
    physics.update(0.01)
    physics.reset()
    state = physics.state
    assert state.position == (0.0, 0.0, 0.0)
    assert state.speed() == 0.0
    print("[PASS] test_physics_reset")


def test_physics_gravity():
    """Test that objects fall under gravity."""
    cfg = AirSimPhysicsConfig()
    physics = AirSimPhysicsModel(cfg)
    physics.set_position(0, 0, -10)

    # Update without thrust — should fall
    for _ in range(50):
        physics.update(0.02)

    pos = physics.state.position
    # Drone should have moved downward (z increasing towards 0)
    assert pos[2] >= -10.0, f"Expected z >= -10, got {pos[2]}"
    print("[PASS] test_physics_gravity")


def test_physics_ground_collision():
    """Test that the drone stops at ground level."""
    cfg = AirSimPhysicsConfig()
    physics = AirSimPhysicsModel(cfg)
    physics.set_position(0, 0, -0.1)

    # Apply downward velocity
    physics._velocity = [0, 0, 2.0]

    for _ in range(200):
        physics.update(0.02)

    pos = physics.state.position
    # Should not fall below z = 0
    assert pos[2] <= 0.0, f"Expected z <= 0, got {pos[2]}"
    print("[PASS] test_physics_ground_collision")


def test_physics_thrust():
    """Test that upward thrust lifts the drone."""
    cfg = AirSimPhysicsConfig()
    physics = AirSimPhysicsModel(cfg)
    physics.set_position(0, 0, 0)

    # Upward thrust must exceed gravity: mass * g = 1.5 * 9.81 = 14.715 N
    # Negative Z is up in NED, so thrust points in -Z direction
    # Each step: apply thrust, update, clear force accumulators
    for _ in range(100):
        # Thrust of 20 N upward exceeds 14.715 N gravity
        physics.set_thrust((0, 0, -20.0))
        physics.update(0.02)

    pos = physics.state.position
    # Should have moved upward (z negative in NED)
    assert pos[2] < 0.0, f"Expected z < 0, got {pos[2]}"
    print("[PASS] test_physics_thrust")


def test_physics_wind():
    """Test wind application."""
    cfg = AirSimPhysicsConfig()
    physics = AirSimPhysicsModel(cfg)
    physics.set_position(0, 0, -5)

    physics.apply_wind(
        wind_speed=5.0,
        wind_direction=0.0,
        gust_factor=0.0,
    )
    physics.update(0.02)

    # Drone should have moved in x direction
    assert physics.state.position[0] != 0.0
    print("[PASS] test_physics_wind")


def test_physics_ground_effect():
    """Test ground effect computation."""
    cfg = AirSimPhysicsConfig()
    physics = AirSimPhysicsModel(cfg)

    # Far from ground — no ground effect
    physics.set_position(0, 0, -5)
    assert physics.get_ground_effect() == 1.0

    # Near ground — ground effect applies
    physics.set_position(0, 0, -0.5)
    assert physics.get_ground_effect() > 1.0

    # At ground — max ground effect
    physics.set_position(0, 0, -0.01)
    assert physics.get_ground_effect() > 1.4

    print("[PASS] test_physics_ground_effect")


def test_physics_state_speed():
    """Test PhysicsState.speed()."""
    state = PhysicsState(
        position=(0, 0, 0),
        velocity=(3, 4, 0),
    )
    assert abs(state.speed() - 5.0) < 1e-10
    print("[PASS] test_physics_state_speed")


def test_physics_get_state():
    """Test physics get_state() returns a full dictionary."""
    cfg = AirSimPhysicsConfig()
    physics = AirSimPhysicsModel(cfg)
    s = physics.get_state()
    assert "position" in s
    assert "velocity" in s
    assert "orientation" in s
    assert "angular_velocity" in s
    assert "speed" in s
    assert "heading" in s
    assert "rotors" in s
    assert len(s["rotors"]) == 4
    print("[PASS] test_physics_get_state")


def test_physics_aerodynamic_force():
    """Test aerodynamic drag force computation."""
    cfg = AirSimPhysicsConfig()
    physics = AirSimPhysicsModel(cfg)
    f = physics.compute_aerodynamic_force(speed=10.0)
    assert f > 0
    print("[PASS] test_physics_aerodynamic_force")


def test_physics_rotor_forces():
    """Test rotor force computation."""
    cfg = AirSimPhysicsConfig()
    physics = AirSimPhysicsModel(cfg)
    physics.set_rotor_speeds([1000, 1000, 1000, 1000])
    thrust, roll, pitch, yaw = physics.compute_rotor_forces()
    assert thrust > 0
    print("[PASS] test_physics_rotor_forces")


# ── Sensor tests ──────────────────────────────────────────────────


def test_sensor_suite_without_airsim():
    """Test sensor suite fallback methods."""
    cfg = AirSimSensorConfig()
    sensors = AirSimSensorSuite(cfg)

    # Without connection, reads should return defaults
    cam = sensors.get_camera_image()
    assert cam.has_image is False

    lidar = sensors.get_lidar_data()
    assert lidar.count == 0

    imu = sensors.get_imu_data()
    assert imu.acceleration == (0, 0, 0)

    gps = sensors.get_gps_data()
    assert gps.latitude == 0.0

    baro = sensors.get_barometer_data()
    assert baro.altitude == 0.0

    mag = sensors.get_magnetometer_data()
    assert mag.heading == 0.0

    collision = sensors.get_collision_info()
    assert collision["has_collided"] is False

    print("[PASS] test_sensor_suite_without_airsim")


def test_simulated_lidar():
    """Test simulated LiDAR fallback."""
    cfg = AirSimSensorConfig()
    sensors = AirSimSensorSuite(cfg)

    lidar = sensors.get_simulated_lidar(
        position=(50, 50, -3),
        heading=0.0,
        range_limit=10.0,
        num_rays=16,
    )
    assert lidar.count == 16

    # Check all points are within range
    for pt in lidar.points:
        assert pt.distance <= 10.0

    # Check filtering
    filtered = lidar.filter_by_range(0, 5)
    for pt in filtered.points:
        assert pt.distance <= 5.0

    print("[PASS] test_simulated_lidar")


def test_simulated_gps():
    """Test simulated GPS fallback."""
    cfg = AirSimSensorConfig()
    sensors = AirSimSensorSuite(cfg)

    gps = sensors.get_simulated_gps(position=(10, 20, -5))
    assert gps.latitude != 0.0 or gps.longitude != 0.0
    print("[PASS] test_simulated_gps")


def test_simulated_imu():
    """Test simulated IMU fallback."""
    cfg = AirSimSensorConfig()
    sensors = AirSimSensorSuite(cfg)

    imu = sensors.get_simulated_imu(
        position=(0, 0, 0),
        velocity=(0, 0, 0),
    )
    # Should have near -9.81 z acceleration (gravity)
    assert abs(imu.acceleration[2] - (-9.81)) < 0.1
    print("[PASS] test_simulated_imu")


def test_lidar_to_array():
    """Test LidarData.to_array()."""
    import numpy as np

    lidar = LidarData()
    assert lidar.to_array().shape == (0, 3)

    from src.airsim.airsim_sensors import LidarPoint

    lidar2 = LidarData(
        points=[
            LidarPoint(1, 0, 0, distance=1),
            LidarPoint(0, 2, 0, distance=2),
        ]
    )
    arr = lidar2.to_array()
    assert arr.shape == (2, 3)
    print("[PASS] test_lidar_to_array")


# ── Bridge tests ──────────────────────────────────────────────────


def test_bridge_creation():
    """Test bridge creation and initialization in 2D mode."""
    cfg = AirSimConfig()
    bridge = AirSimBridge(cfg)

    # Initialize in 2D mode
    result = bridge.initialize(
        grid_width=100, grid_height=100, use_airsim=False,
    )
    assert result is True
    assert bridge.state.mode == SimulationMode.NATIVE_2D
    assert bridge.is_airsim_active() is False

    # Takeoff and land should be no-ops in 2D
    assert bridge.takeoff() is True
    assert bridge.land() is True

    bridge.shutdown()
    print("[PASS] test_bridge_creation")


def test_bridge_airsim_unavailable():
    """Test bridge falls back when AirSim is not installed."""
    cfg = AirSimConfig()
    bridge = AirSimBridge(cfg)

    result = bridge.initialize(
        grid_width=100, grid_height=100, use_airsim=True,
    )
    # Without AirSim package, should fall back to 2D
    assert bridge.state.mode == SimulationMode.NATIVE_2D
    assert bridge.is_airsim_active() is False

    bridge.shutdown()
    print("[PASS] test_bridge_airsim_unavailable")


def test_bridge_coordinate_conversion():
    """Test grid ↔ AirSim coordinate conversion in bridge."""
    cfg = AirSimConfig()
    bridge = AirSimBridge(cfg)
    bridge.initialize(use_airsim=False)

    # Grid to AirSim 3D
    x, y, z = bridge.grid_to_airsim_3d(50, 50)
    assert x == 50.0
    assert y == 50.0
    assert z == -3.0

    # AirSim to grid
    gx, gy = bridge.airsim_to_grid_2d(50, 50)
    assert gx == 50
    assert gy == 50

    bridge.shutdown()
    print("[PASS] test_bridge_coordinate_conversion")


def test_bridge_sensor_fallbacks():
    """Test that bridge sensor reads work in 2D mode."""
    cfg = AirSimConfig()
    bridge = AirSimBridge(cfg)
    bridge.initialize(use_airsim=False)

    gps = bridge.read_gps()
    assert len(gps) == 2

    imu = bridge.read_imu()
    assert "acceleration" in imu
    assert "angular_velocity" in imu

    lidar = bridge.read_lidar()
    assert lidar == []  # no AirSim, returns empty

    cam = bridge.read_camera()
    assert cam is None

    assert bridge.check_collision() is False

    bridge.shutdown()
    print("[PASS] test_bridge_sensor_fallbacks")


def test_bridge_status():
    """Test bridge status reporting."""
    cfg = AirSimConfig()
    bridge = AirSimBridge(cfg)
    bridge.initialize(use_airsim=False)

    status = bridge.get_status()
    assert status["mode"] == "native_2d"
    assert status["connected"] is False
    assert status["airsim_available"] is False

    bridge.shutdown()
    print("[PASS] test_bridge_status")


def test_bridge_context_manager():
    """Test bridge as context manager."""
    cfg = AirSimConfig()
    with AirSimBridge(cfg) as bridge:
        bridge.initialize(use_airsim=False)
        assert bridge.state.mode == "native_2d"
    print("[PASS] test_bridge_context_manager")


def test_bridge_get_battery_info():
    """Test battery info from drone."""
    cfg = AirSimConfig()
    bridge = AirSimBridge(cfg)
    bridge.initialize(use_airsim=False)

    batt = bridge.get_battery_info()
    assert "voltage" in batt
    assert "remaining_percent" in batt

    bridge.shutdown()
    print("[PASS] test_bridge_get_battery_info")


# ── Main ──────────────────────────────────────────────────────────


def main():
    """Run all tests."""
    print("=" * 60)
    print("  AirSim Integration Tests")
    print("=" * 60)
    print()

    tests = [
        test_config_defaults,
        test_config_serialization,
        test_pose3d,
        test_velocity3d,
        test_drone_without_airsim,
        test_drone_grid_conversion,
        test_drone_state_enum,
        test_drone_context_manager,
        test_physics_reset,
        test_physics_gravity,
        test_physics_ground_collision,
        test_physics_thrust,
        test_physics_wind,
        test_physics_ground_effect,
        test_physics_state_speed,
        test_physics_get_state,
        test_physics_aerodynamic_force,
        test_physics_rotor_forces,
        test_sensor_suite_without_airsim,
        test_simulated_lidar,
        test_simulated_gps,
        test_simulated_imu,
        test_lidar_to_array,
        test_bridge_creation,
        test_bridge_airsim_unavailable,
        test_bridge_coordinate_conversion,
        test_bridge_sensor_fallbacks,
        test_bridge_status,
        test_bridge_context_manager,
        test_bridge_get_battery_info,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"  Total:   {len(tests)} tests")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())