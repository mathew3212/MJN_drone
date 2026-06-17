"""
AirSim Integration Package
===========================
Bridges the MJN drone simulation to Microsoft AirSim for realistic 3D physics,
sensor simulation, and environment rendering.

Provides:
- 3D drone control via the AirSim Python API
- Sensor adapters (LiDAR, camera, GPS, IMU, barometer)
- Physics simulation delegation to AirSim
- Integration with existing navigation, planning, and autonomy subsystems
- Fallback mode when AirSim is not available (graceful degradation)

Usage:
    from src.airsim import AirSimBridge, AirSimConfig

    # With AirSim running:
    config = AirSimConfig()
    bridge = AirSimBridge(config)
    bridge.initialize()
    bridge.takeoff()
    bridge.move_grid_waypoint(50, 50)
    bridge.land()

    # Without AirSim (graceful fallback):
    bridge = AirSimBridge(config)
    bridge.initialize(use_airsim=False)  # falls back to 2D
"""

from src.airsim.airsim_config import AirSimConfig
from src.airsim.airsim_drone import AirSimDrone
from src.airsim.airsim_sensors import AirSimSensorSuite
from src.airsim.airsim_physics import AirSimPhysicsModel
from src.airsim.airsim_bridge import AirSimBridge
from src.airsim.airsim_world import AirSimWorldManager
from src.airsim.airsim_mission import AirSimMissionRunner

__all__ = [
    "AirSimConfig",
    "AirSimDrone",
    "AirSimSensorSuite",
    "AirSimPhysicsModel",
    "AirSimBridge",
    "AirSimWorldManager",
    "AirSimMissionRunner",
]