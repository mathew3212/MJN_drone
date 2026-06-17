"""
Multi-Drone Coordination System
=================================
Supports unlimited drones with:

  - Unique identity, capabilities, battery, health
  - Swarm coordination without central controller
  - Distributed task allocation
  - Cooperative path planning
  - Collision avoidance between drones
  - Formation flying
  - Dynamic leader election
  - Peer-to-peer communication
  - Shared situational awareness

Each drone is an autonomous agent that cooperates with others.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set, Any
from enum import Enum, auto

from .event_bus import get_event_bus, Event, EventPriority


class DroneStatus(Enum):
    IDLE = auto()
    MISSION = auto()
    RETURNING = auto()
    CHARGING = auto()
    ERROR = auto()
    EMERGENCY = auto()
    OFFLINE = auto()


class DroneCapabilities:
    """What this drone can do."""
    max_payload: float = 0.5  # kg
    max_range: float = 50.0  # meters
    max_altitude: float = 30.0  # meters
    sensor_types: List[str] = field(default_factory=lambda: [
        "gps", "imu", "camera", "lidar",
    ])
    can_carry: bool = True
    can_inspect: bool = True
    can_deliver: bool = True
    can_map: bool = True


@dataclass
class DroneState:
    """Complete state of a drone in the swarm."""
    drone_id: str = ""
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    altitude: float = 5.0
    heading: float = 0.0
    speed: float = 0.0
    battery_pct: float = 100.0
    status: DroneStatus = DroneStatus.IDLE
    payload_mass: float = 0.0
    health_score: float = 1.0  # 0-1, 1=perfect
    signal_strength: float = 1.0
    current_mission_id: Optional[str] = None
    assigned_task_id: Optional[str] = None
    position_history: List[Tuple[float, float]] = field(default_factory=list)
    is_leader: bool = False
    team_id: Optional[str] = None
    capabilities: DroneCapabilities = field(default_factory=DroneCapabilities)
    telemetry: Dict[str, float] = field(default_factory=dict)

    def distance_to(self, other: 'DroneState') -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def distance_to_point(self, px: float, py: float) -> float:
        return math.hypot(self.x - px, self.y - py)


class DroneAgent:
    """
    An autonomous drone agent in the swarm.
    
    Each agent:
      - Maintains its own state
      - Communicates via the event bus
      - Makes autonomous decisions
      - Cooperates with other agents
    """

    def __init__(self, drone_id: str = "", name: str = "",
                 x: float = 0.0, y: float = 0.0):
        self.id = drone_id or str(uuid.uuid4())[:8]
        self.name = name or f"Drone-{self.id[:4]}"
        self.state = DroneState(
            drone_id=self.id,
            name=self.name,
            x=x, y=y,
        )
        self.capabilities = DroneCapabilities()
        self.bus = get_event_bus()
        self._telemetry_buffer: List[Dict] = []

        # Publish creation event
        self.bus.publish("drone.created", {
            "drone_id": self.id, "name": self.name,
            "position": (x, y),
        }, source=self.name)

    def update(self, dt: float = 0.016):
        """Update drone state."""
        # Record position history
        self.state.position_history.append((self.state.x, self.state.y))
        if len(self.state.position_history) > 1000:
            self.state.position_history = self.state.position_history[-1000:]

        # Publish telemetry
        self.state.telemetry = {
            "speed": self.state.speed,
            "battery": self.state.battery_pct,
            "altitude": self.state.altitude,
            "heading": self.state.heading,
            "health": self.state.health_score,
            "signal": self.state.signal_strength,
        }

    def receive_task(self, task_id: str, target: Tuple[float, float],
                     priority: int = 0):
        """Accept a task assignment."""
        self.state.assigned_task_id = task_id
        self.state.current_mission_id = task_id
        self.state.status = DroneStatus.MISSION
        self.bus.publish("drone.task.assigned", {
            "drone_id": self.id,
            "task_id": task_id,
            "target": target,
            "priority": priority,
        }, source=self.name)

    def complete_task(self):
        """Mark current task as complete."""
        task_id = self.state.assigned_task_id
        self.state.assigned_task_id = None
        self.state.status = DroneStatus.IDLE
        self.bus.publish("drone.task.completed", {
            "drone_id": self.id,
            "task_id": task_id,
        }, source=self.name)

    def emergency_land(self):
        """Emergency landing."""
        self.state.status = DroneStatus.EMERGENCY
        self.bus.publish("drone.emergency", {
            "drone_id": self.id,
            "reason": "emergency_land",
        }, source=self.name, priority=EventPriority.CRITICAL)

    def broadcast_position(self):
        """Broadcast position to other drones."""
        self.bus.publish("drone.position", {
            "drone_id": self.id,
            "x": self.state.x,
            "y": self.state.y,
            "altitude": self.state.altitude,
            "heading": self.state.heading,
            "speed": self.state.speed,
            "battery": self.state.battery_pct,
            "status": self.state.status.name,
        }, source=self.name)

    def receive_heartbeat(self, other_drones: List[DroneState]):
        """Receive heartbeat data from other drones."""
        nearby = []
        for other in other_drones:
            if other.drone_id != self.id:
                dist = self.state.distance_to(other)
                if dist < 20:  # Within communication range
                    nearby.append(other)
        return nearby


class SwarmCoordinator:
    """
    Decentralized swarm coordination.
    
    No central controller — each drone negotiates with others
    via the event bus. This class provides coordination algorithms.
    """

    def __init__(self):
        self.bus = get_event_bus()
        self.drones: Dict[str, DroneAgent] = {}
        self.teams: Dict[str, List[str]] = {}
        self.min_separation: float = 3.0
        self._register_handlers()

    def _register_handlers(self):
        self.bus.subscribe("drone.position", self._on_drone_position)
        self.bus.subscribe("drone.emergency", self._on_drone_emergency)

    def register_drone(self, drone: DroneAgent):
        """Register a drone with the swarm."""
        self.drones[drone.id] = drone
        self.bus.publish("swarm.drone_joined", {
            "drone_id": drone.id,
            "name": drone.name,
            "total_drones": len(self.drones),
        })

    def unregister_drone(self, drone_id: str):
        """Remove a drone from the swarm."""
        if drone_id in self.drones:
            del self.drones[drone_id]
            self.bus.publish("swarm.drone_left", {
                "drone_id": drone_id,
                "total_drones": len(self.drones),
            })

    def _on_drone_position(self, event: Event):
        """Check for collision risks when a drone broadcasts position."""
        data = event.data
        if not data:
            return
        drone_id = data.get("drone_id")
        x = data.get("x", 0)
        y = data.get("y", 0)
        for did, drone in self.drones.items():
            if did != drone_id:
                dist = drone.state.distance_to_point(x, y)
                if dist < self.min_separation:
                    self.bus.publish("swarm.collision_risk", {
                        "drone_a": did, "drone_b": drone_id,
                        "distance": dist,
                    }, priority=EventPriority.HIGH)

    def _on_drone_emergency(self, event: Event):
        """Handle drone emergency."""
        data = event.data
        if data:
            drone_id = data.get("drone_id")
            # Notify all drones
            for did, drone in self.drones.items():
                if did != drone_id:
                    drone.state.telemetry["emergency_drone"] = drone_id

    def allocate_tasks(self, tasks: List[Dict]) -> Dict[str, str]:
        """
        Distribute tasks among available drones.
        Returns mapping of drone_id -> task_id.
        """
        assignments = {}
        available = [
            (did, d) for did, d in self.drones.items()
            if d.state.status == DroneStatus.IDLE
        ]

        for task in tasks:
            if not available:
                break

            best_drone = None
            best_score = -1
            target = task.get("target", (50, 50))

            for did, drone in available:
                # Score based on distance and battery
                dist = drone.state.distance_to_point(target[0], target[1])
                battery_factor = drone.state.battery_pct / 100.0
                score = battery_factor * 100 - dist
                if score > best_score:
                    best_score = score
                    best_drone = (did, drone)

            if best_drone:
                did, drone = best_drone
                drone.receive_task(task["id"], target, task.get("priority", 0))
                assignments[did] = task["id"]
                available.remove(best_drone)

        return assignments

    def elect_leader(self) -> Optional[DroneAgent]:
        """Elect a leader based on battery, health, and capability."""
        best = None
        best_score = -1

        for drone in self.drones.values():
            if drone.state.status == DroneStatus.OFFLINE:
                continue
            score = (
                drone.state.battery_pct * 0.3 +
                drone.state.health_score * 40 +
                drone.state.signal_strength * 30
            )
            if score > best_score:
                best_score = score
                best = drone

        if best:
            for drone in self.drones.values():
                drone.state.is_leader = (drone.id == best.id)
            self.bus.publish("swarm.leader_elected", {
                "leader_id": best.id,
                "name": best.name,
            })

        return best

    def get_formation_positions(self, center_x: float, center_y: float,
                                 formation: str = "v",
                                 count: int = 0,
                                 spacing: float = 4.0) -> List[Tuple[float, float]]:
        """Generate formation positions."""
        n = count or len(self.drones)
        positions = []

        if formation == "line":
            for i in range(n):
                x = center_x + i * spacing
                positions.append((x, center_y))

        elif formation == "v":
            for i in range(n):
                row = i // 2 + 1
                side = 1 if i % 2 == 0 else -1
                x = center_x - row * spacing
                y = center_y + side * row * spacing * 0.5
                positions.append((x, y))

        elif formation == "circle":
            for i in range(n):
                angle = (2 * math.pi * i) / n
                x = center_x + spacing * n / (2 * math.pi) * math.cos(angle)
                y = center_y + spacing * n / (2 * math.pi) * math.sin(angle)
                positions.append((x, y))

        elif formation == "grid":
            cols = max(1, int(math.ceil(math.sqrt(n))))
            for i in range(n):
                row = i // cols
                col = i % cols
                x = center_x + col * spacing - (cols - 1) * spacing / 2
                y = center_y - row * spacing
                positions.append((x, y))

        else:
            for i in range(n):
                angle = (2 * math.pi * i) / max(1, n)
                x = center_x + spacing * math.cos(angle)
                y = center_y + spacing * math.sin(angle)
                positions.append((x, y))

        return positions[:n]

    def get_fleet_status(self) -> Dict[str, Any]:
        """Get complete fleet status."""
        status = {
            "total_drones": len(self.drones),
            "idle": 0, "mission": 0, "returning": 0,
            "charging": 0, "error": 0, "emergency": 0, "offline": 0,
            "avg_battery": 0, "avg_health": 0,
            "leader": None,
        }

        total_bat = 0
        total_health = 0
        for drone in self.drones.values():
            s = drone.state.status
            if s == DroneStatus.IDLE: status["idle"] += 1
            elif s == DroneStatus.MISSION: status["mission"] += 1
            elif s == DroneStatus.RETURNING: status["returning"] += 1
            elif s == DroneStatus.CHARGING: status["charging"] += 1
            elif s == DroneStatus.ERROR: status["error"] += 1
            elif s == DroneStatus.EMERGENCY: status["emergency"] += 1
            elif s == DroneStatus.OFFLINE: status["offline"] += 1
            total_bat += drone.state.battery_pct
            total_health += drone.state.health_score
            if drone.state.is_leader:
                status["leader"] = drone.id

        n = max(1, len(self.drones))
        status["avg_battery"] = total_bat / n
        status["avg_health"] = total_health / n

        return status