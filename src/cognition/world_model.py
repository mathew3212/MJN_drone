"""
World Model - Internal Simulation Engine
=========================================

Maintains an internal representation of the environment that can be
used for prediction, planning, and hypothetical reasoning ("what-if"
analysis). The world model tracks object states, dynamics, and enables
forward simulation without interacting with the real world.

Key Capabilities:
    - State tracking of all known entities
    - Forward simulation (predict N steps ahead)
    - What-if hypothesis testing
    - Causal reasoning about action effects
    - Model confidence calibration
"""

import math
import time
import copy
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


class EntityType(Enum):
    """Types of entities tracked in the world model."""
    DRONE = "drone"
    OBSTACLE_STATIC = "obstacle_static"
    OBSTACLE_DYNAMIC = "obstacle_dynamic"
    TARGET = "target"
    HAZARD = "hazard"
    LANDMARK = "landmark"
    UNKNOWN = "unknown"


class EntityState(Enum):
    """States an entity can be in."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MOVING = "moving"
    COLLIDING = "colliding"
    DESTROYED = "destroyed"
    UNCERTAIN = "uncertain"


@dataclass
class EntityState3D:
    """Complete state of an entity in the world model."""
    entity_id: str
    entity_type: EntityType
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    heading: float = 0.0
    speed: float = 0.0
    state: EntityState = EntityState.ACTIVE
    confidence: float = 1.0
    last_updated: float = field(default_factory=time.time)
    properties: Dict[str, Any] = field(default_factory=dict)

    def distance_to(self, other: 'EntityState3D') -> float:
        """Calculate Euclidean distance to another entity."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def predicted_position(self, dt: float) -> Tuple[float, float, float]:
        """Predict position after dt seconds using constant velocity model."""
        return (
            self.x + self.vx * dt,
            self.y + self.vy * dt,
            self.z + self.vz * dt,
        )


@dataclass
class WorldState:
    """Complete snapshot of the world at a point in time."""
    timestamp: float
    entities: Dict[str, EntityState3D]
    drone_position: Tuple[float, float] = (0.0, 0.0)
    drone_heading: float = 0.0
    drone_speed: float = 0.0
    battery_level: float = 1.0
    mission_phase: str = "UNKNOWN"
    weather_conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def copy(self) -> 'WorldState':
        """Create a deep copy of this world state."""
        return WorldState(
            timestamp=self.timestamp,
            entities={k: copy.deepcopy(v) for k, v in self.entities.items()},
            drone_position=self.drone_position,
            drone_heading=self.drone_heading,
            drone_speed=self.drone_speed,
            battery_level=self.battery_level,
            mission_phase=self.mission_phase,
            weather_conditions=dict(self.weather_conditions),
            metadata=dict(self.metadata),
        )


@dataclass
class PredictedOutcome:
    """Result of a forward simulation or what-if analysis."""
    world_state: WorldState
    steps_simulated: int
    events: List[str]
    collision_detected: bool
    goal_reachable: bool
    confidence: float
    total_cost: float
    explanation: str = ""


@dataclass
class DynamicsModel:
    """Model of how entities move and change over time."""
    entity_type: EntityType
    velocity_noise: float = 0.1
    position_noise: float = 0.05
    max_speed: float = 2.0
    acceleration_limit: float = 0.5


class WorldModel:
    """
    Internal world model for cognitive reasoning.

    Maintains a belief about the state of the world and enables
    forward simulation, what-if analysis, and causal reasoning.
    """

    def __init__(self, grid_width: int = 100, grid_height: int = 100):
        self.grid_width = grid_width
        self.grid_height = grid_height

        # Current believed state
        self._current_state: Optional[WorldState] = None
        self._state_history: List[WorldState] = []
        self._max_history = 100

        # Entity tracking
        self._entities: Dict[str, EntityState3D] = {}
        self._entity_trajectories: Dict[str, List[Tuple[float, float]]] = {}

        # Dynamics models per entity type
        self._dynamics: Dict[EntityType, DynamicsModel] = {
            EntityType.DRONE: DynamicsModel(EntityType.DRONE, 0.0, 0.0, 5.0, 2.0),
            EntityType.OBSTACLE_STATIC: DynamicsModel(EntityType.OBSTACLE_STATIC, 0.0, 0.0, 0.0, 0.0),
            EntityType.OBSTACLE_DYNAMIC: DynamicsModel(EntityType.OBSTACLE_DYNAMIC, 0.3, 0.1, 2.0, 1.0),
            EntityType.TARGET: DynamicsModel(EntityType.TARGET, 0.0, 0.0, 0.0, 0.0),
        }

        # Model confidence tracking
        self._model_confidence: float = 0.8
        self._prediction_errors: List[float] = []
        self._max_prediction_errors = 50

        # Causal rules: action -> effect templates
        self._causal_rules: Dict[str, Dict[str, Any]] = {
            "move_forward": {"velocity_factor": 1.0, "energy_cost": 0.01},
            "turn_left": {"heading_change": -0.3, "energy_cost": 0.005},
            "turn_right": {"heading_change": 0.3, "energy_cost": 0.005},
            "hover": {"velocity_factor": 0.0, "energy_cost": 0.003},
            "accelerate": {"speed_change": 0.5, "energy_cost": 0.02},
            "decelerate": {"speed_change": -0.5, "energy_cost": 0.001},
            "return_home": {"velocity_factor": 0.8, "energy_cost": 0.015},
        }

        self._step_count = 0

    # ==========================================
    # State Management
    # ==========================================

    def initialize(self, drone_position: Tuple[float, float],
                   target_position: Tuple[float, float],
                   obstacles: List[Tuple[int, int]],
                   dynamic_obstacles: Optional[List[str]] = None):
        """Initialize the world model with known entities."""
        entities = {}

        # Drone
        entities["drone"] = EntityState3D(
            entity_id="drone",
            entity_type=EntityType.DRONE,
            x=float(drone_position[0]),
            y=float(drone_position[1]),
            confidence=1.0,
        )

        # Target
        entities["target"] = EntityState3D(
            entity_id="target",
            entity_type=EntityType.TARGET,
            x=float(target_position[0]),
            y=float(target_position[1]),
            confidence=1.0,
        )

        # Static obstacles
        for i, (ox, oy) in enumerate(obstacles):
            entities[f"obstacle_{i}"] = EntityState3D(
                entity_id=f"obstacle_{i}",
                entity_type=EntityType.OBSTACLE_STATIC,
                x=float(ox),
                y=float(oy),
                confidence=0.9,
            )

        self._current_state = WorldState(
            timestamp=time.time(),
            entities=entities,
            drone_position=drone_position,
        )
        self._entities = entities

        # Initialize trajectories
        for eid in entities:
            self._entity_trajectories[eid] = [
                (entities[eid].x, entities[eid].y)
            ]

    def update_from_sensors(self, drone_position: Tuple[float, float],
                            drone_heading: float, drone_speed: float,
                            visible_obstacles: List[Tuple[float, float]],
                            battery_level: float = 1.0,
                            mission_phase: str = "UNKNOWN"):
        """Update world model with new sensor observations."""
        if self._current_state is None:
            return

        # Save previous state to history
        self._state_history.append(self._current_state)
        if len(self._state_history) > self._max_history:
            self._state_history.pop(0)

        # Update drone state
        if "drone" in self._entities:
            drone_entity = self._entities["drone"]
            # Compute velocity from position change
            dt = 0.1  # assumed time step
            drone_entity.vx = (drone_position[0] - drone_entity.x) / max(dt, 1e-6)
            drone_entity.vy = (drone_position[1] - drone_entity.y) / max(dt, 1e-6)
            drone_entity.x = float(drone_position[0])
            drone_entity.y = float(drone_position[1])
            drone_entity.heading = drone_heading
            drone_entity.speed = drone_speed
            drone_entity.confidence = 1.0
            drone_entity.last_updated = time.time()

            self._entity_trajectories["drone"].append(drone_position)
            if len(self._entity_trajectories["drone"]) > 200:
                self._entity_trajectories["drone"].pop(0)

        # Update visible obstacles (increase confidence for seen ones)
        visible_set = set()
        for ox, oy in visible_obstacles:
            key = f"obs_{round(ox)}_{round(oy)}"
            visible_set.add(key)

            # Find closest existing obstacle entity or create new one
            best_match = None
            best_dist = float('inf')
            for eid, entity in self._entities.items():
                if entity.entity_type in (EntityType.OBSTACLE_STATIC, EntityType.OBSTACLE_DYNAMIC):
                    d = math.sqrt((entity.x - ox) ** 2 + (entity.y - oy) ** 2)
                    if d < best_dist:
                        best_dist = d
                        best_match = eid

            if best_match and best_dist < 3.0:
                # Update existing obstacle
                self._entities[best_match].confidence = min(
                    1.0, self._entities[best_match].confidence + 0.1
                )
                self._entities[best_match].last_updated = time.time()
            else:
                # New obstacle discovered
                new_id = f"obstacle_{len(self._entities)}"
                self._entities[new_id] = EntityState3D(
                    entity_id=new_id,
                    entity_type=EntityType.OBSTACLE_STATIC,
                    x=float(ox),
                    y=float(oy),
                    confidence=0.8,
                )
                self._entity_trajectories[new_id] = [(ox, oy)]

        # Decay confidence of non-visible obstacles
        for eid, entity in self._entities.items():
            if entity.entity_type in (EntityType.OBSTACLE_STATIC, EntityType.OBSTACLE_DYNAMIC):
                if eid not in [f"obs_{round(entity.x)}_{round(entity.y)}" for _ in [1]]:
                    entity.confidence *= 0.99

        # Update world state
        self._current_state = WorldState(
            timestamp=time.time(),
            entities=dict(self._entities),
            drone_position=drone_position,
            drone_heading=drone_heading,
            drone_speed=drone_speed,
            battery_level=battery_level,
            mission_phase=mission_phase,
        )
        self._step_count += 1

    # ==========================================
    # Forward Simulation
    # ==========================================

    def simulate_forward(self, actions: List[str],
                         steps: int = 20) -> PredictedOutcome:
        """
        Simulate forward given a sequence of actions.
        Returns predicted outcome with events and costs.
        """
        if self._current_state is None:
            return PredictedOutcome(
                world_state=WorldState(timestamp=0, entities={}),
                steps_simulated=0,
                events=["No world model initialized"],
                collision_detected=False,
                goal_reachable=False,
                confidence=0.0,
                total_cost=0.0,
                explanation="Cannot simulate: world model not initialized",
            )

        state = self._current_state.copy()
        events = []
        total_cost = 0.0
        collision_detected = False
        goal_reached = False
        dt = 0.1

        for step in range(steps):
            action = actions[step % len(actions)] if actions else "hover"

            # Apply causal rules
            rule = self._causal_rules.get(action, {})
            energy_cost = rule.get("energy_cost", 0.01)

            # Update drone state based on action
            drone = state.entities.get("drone")
            if drone is None:
                break

            if action == "move_forward":
                drone.x += math.cos(drone.heading) * drone.speed * dt
                drone.y += math.sin(drone.heading) * drone.speed * dt
            elif action == "turn_left":
                drone.heading -= rule.get("heading_change", 0.3)
            elif action == "turn_right":
                drone.heading += rule.get("heading_change", 0.3)
            elif action == "accelerate":
                drone.speed = min(drone.speed + rule.get("speed_change", 0.5),
                                  self._dynamics[EntityType.DRONE].max_speed)
            elif action == "decelerate":
                drone.speed = max(drone.speed + rule.get("speed_change", -0.5), 0.0)
            elif action == "return_home":
                # Steer toward home
                home = state.metadata.get("home_position", (0, 0))
                dx = home[0] - drone.x
                dy = home[1] - drone.y
                dist = math.sqrt(dx ** 2 + dy ** 2)
                if dist > 0:
                    drone.heading = math.atan2(dy, dx)
                drone.x += math.cos(drone.heading) * drone.speed * dt
                drone.y += math.sin(drone.heading) * drone.speed * dt

            total_cost += energy_cost
            state.battery_level -= energy_cost

            # Simulate dynamic obstacles
            for eid, entity in state.entities.items():
                if entity.entity_type == EntityType.OBSTACLE_DYNAMIC:
                    dyn_model = self._dynamics[EntityType.OBSTACLE_DYNAMIC]
                    # Random walk with noise
                    entity.x += entity.vx * dt + self._simple_noise(dyn_model.position_noise)
                    entity.y += entity.vy * dt + self._simple_noise(dyn_model.position_noise)

            # Check collisions
            for eid, entity in state.entities.items():
                if eid == "drone":
                    continue
                if entity.entity_type in (EntityType.OBSTACLE_STATIC, EntityType.OBSTACLE_DYNAMIC):
                    dist = math.sqrt((drone.x - entity.x) ** 2 + (drone.y - entity.y) ** 2)
                    if dist < 1.0:
                        collision_detected = True
                        events.append(f"COLLISION at step {step} with {eid}")

            # Check goal
            target = state.entities.get("target")
            if target:
                dist_to_target = math.sqrt(
                    (drone.x - target.x) ** 2 + (drone.y - target.y) ** 2
                )
                if dist_to_target < 1.5:
                    goal_reached = True
                    events.append(f"GOAL REACHED at step {step}")

            # Battery check
            if state.battery_level <= 0:
                events.append(f"BATTERY DEPLETED at step {step}")
                break

        # Confidence based on model accuracy
        confidence = self._model_confidence * max(0.1, 1.0 - len(self._prediction_errors) * 0.01)

        explanation = self._generate_simulation_explanation(
            actions, steps, collision_detected, goal_reached, total_cost
        )

        return PredictedOutcome(
            world_state=state,
            steps_simulated=min(steps, len(actions)),
            events=events,
            collision_detected=collision_detected,
            goal_reachable=goal_reached,
            confidence=confidence,
            total_cost=total_cost,
            explanation=explanation,
        )

    def what_if(self, hypothetical_change: Dict[str, Any],
                actions: List[str],
                steps: int = 20) -> PredictedOutcome:
        """
        What-if analysis: apply a hypothetical change and simulate.
        
        hypothetical_change examples:
            {"type": "obstacle_added", "x": 10, "y": 20}
            {"type": "battery_level", "value": 0.5}
            {"type": "speed", "value": 3.0}
        """
        if self._current_state is None:
            return PredictedOutcome(
                world_state=WorldState(timestamp=0, entities={}),
                steps_simulated=0,
                events=["No world model"],
                collision_detected=False,
                goal_reachable=False,
                confidence=0.0,
                total_cost=0.0,
                explanation="World model not initialized",
            )

        # Create hypothetical state
        hypo_state = self._current_state.copy()

        change_type = hypothetical_change.get("type", "")
        if change_type == "obstacle_added":
            new_id = f"hypo_obstacle_{len(hypo_state.entities)}"
            hypo_state.entities[new_id] = EntityState3D(
                entity_id=new_id,
                entity_type=EntityType.OBSTACLE_STATIC,
                x=float(hypothetical_change.get("x", 0)),
                y=float(hypothetical_change.get("y", 0)),
                confidence=1.0,
            )
        elif change_type == "battery_level":
            hypo_state.battery_level = hypothetical_change.get("value", 1.0)
        elif change_type == "speed":
            drone = hypo_state.entities.get("drone")
            if drone:
                drone.speed = hypothetical_change.get("value", 1.0)
        elif change_type == "obstacle_removed":
            target_id = hypothetical_change.get("entity_id")
            if target_id and target_id in hypo_state.entities:
                del hypo_state.entities[target_id]

        # Temporarily swap state and simulate
        original_state = self._current_state
        self._current_state = hypo_state
        outcome = self.simulate_forward(actions, steps)
        self._current_state = original_state

        outcome.explanation = (
            f"What-if analysis ({change_type}): {outcome.explanation}"
        )
        return outcome

    # ==========================================
    # Model Confidence
    # ==========================================

    def record_prediction_error(self, predicted: Tuple[float, float],
                                actual: Tuple[float, float]):
        """Record a prediction error to calibrate model confidence."""
        error = math.sqrt(
            (predicted[0] - actual[0]) ** 2 +
            (predicted[1] - actual[1]) ** 2
        )
        self._prediction_errors.append(error)
        if len(self._prediction_errors) > self._max_prediction_errors:
            self._prediction_errors.pop(0)

        # Recalibrate confidence
        if self._prediction_errors:
            avg_error = sum(self._prediction_errors) / len(self._prediction_errors)
            self._model_confidence = max(0.1, min(1.0, 1.0 / (1.0 + avg_error)))

    @property
    def model_confidence(self) -> float:
        """Current confidence in the world model's accuracy."""
        return self._model_confidence

    # ==========================================
    # Queries
    # ==========================================

    def get_entity(self, entity_id: str) -> Optional[EntityState3D]:
        """Get current state of a specific entity."""
        return self._entities.get(entity_id)

    def get_all_entities(self) -> Dict[str, EntityState3D]:
        """Get all tracked entities."""
        return dict(self._entities)

    def get_entities_near(self, x: float, y: float,
                          radius: float) -> List[EntityState3D]:
        """Get all entities within a radius of a point."""
        result = []
        for entity in self._entities.values():
            dist = math.sqrt((entity.x - x) ** 2 + (entity.y - y) ** 2)
            if dist <= radius:
                result.append(entity)
        return result

    def get_trajectory(self, entity_id: str) -> List[Tuple[float, float]]:
        """Get the recorded trajectory of an entity."""
        return list(self._entity_trajectories.get(entity_id, []))

    def predict_position(self, entity_id: str,
                         dt: float) -> Optional[Tuple[float, float, float]]:
        """Predict where an entity will be after dt time units."""
        entity = self._entities.get(entity_id)
        if entity is None:
            return None
        return entity.predicted_position(dt)

    def get_current_state(self) -> Optional[WorldState]:
        """Get the current world state."""
        return self._current_state

    def get_state_history(self) -> List[WorldState]:
        """Get the history of world states."""
        return list(self._state_history)

    # ==========================================
    # Internal Helpers
    # ==========================================

    def _simple_noise(self, magnitude: float) -> float:
        """Simple deterministic noise for simulation reproducibility."""
        import random
        random.seed(int(time.time() * 1000) % 2 ** 31)
        return random.gauss(0, magnitude)

    def _generate_simulation_explanation(self, actions: List[str],
                                          steps: int,
                                          collision: bool,
                                          goal: bool,
                                          cost: float) -> str:
        """Generate a human-readable explanation of the simulation."""
        parts = [
            f"Simulated {steps} steps with actions: {', '.join(set(actions))}.",
            f"Total energy cost: {cost:.4f}.",
        ]
        if goal:
            parts.append("Goal is reachable in this simulation.")
        else:
            parts.append("Goal was NOT reached in this simulation.")
        if collision:
            parts.append("COLLISION was detected during simulation.")
        parts.append(f"Model confidence: {self._model_confidence:.2f}.")
        return " ".join(parts)

    def __repr__(self) -> str:
        n_entities = len(self._entities)
        conf = self._model_confidence
        return (
            f"WorldModel(entities={n_entities}, "
            f"confidence={conf:.2f}, steps={self._step_count})"
        )