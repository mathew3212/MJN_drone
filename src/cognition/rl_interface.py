"""
Reinforcement Learning Interface
==================================

Provides an interface for integrating RL algorithms with the drone
navigation system. Supports state representation, action spaces,
reward shaping, experience replay, and policy management.
"""

import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


class RLActionType(Enum):
    MOVE_FORWARD = "move_forward"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    ACCELERATE = "accelerate"
    DECELERATE = "decelerate"
    HOVER = "hover"
    RETURN_HOME = "return_home"
    EXPLORE = "explore"


@dataclass
class RLState:
    """State representation for RL."""
    position: Tuple[float, float]
    heading: float
    speed: float
    battery_level: float
    distance_to_target: float
    nearest_obstacle_dist: float
    mission_phase: str
    velocity: Tuple[float, float] = (0.0, 0.0)
    features: Dict[str, float] = field(default_factory=dict)

    def to_vector(self) -> List[float]:
        """Convert to a feature vector for RL algorithms."""
        return [
            self.position[0], self.position[1],
            self.heading, self.speed, self.battery_level,
            self.distance_to_target, self.nearest_obstacle_dist,
            self.velocity[0], self.velocity[1],
        ]


@dataclass
class RLAction:
    """An action in the RL action space."""
    action_type: RLActionType
    parameters: Dict[str, float] = field(default_factory=dict)
    confidence: float = 1.0

    @property
    def name(self) -> str:
        return self.action_type.value


@dataclass
class RLReward:
    """Reward signal for RL."""
    reward: float
    components: Dict[str, float] = field(default_factory=dict)
    done: bool = False
    explanation: str = ""


@dataclass
class RLTransition:
    """A state transition for experience replay."""
    state: RLState
    action: RLAction
    reward: RLReward
    next_state: RLState
    done: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class RLPolicy:
    """A policy mapping states to actions."""
    name: str
    version: int = 0
    success_rate: float = 0.5
    total_episodes: int = 0
    avg_reward: float = 0.0
    exploration_rate: float = 0.1
    learning_rate: float = 0.01
    discount_factor: float = 0.99
    q_table: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def get_q_values(self, state_key: str) -> Dict[str, float]:
        return self.q_table.get(state_key, {})

    def update_q(self, state_key: str, action_name: str, value: float):
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        self.q_table[state_key][action_name] = value


class ExperienceReplay:
    """Experience replay buffer for off-policy RL."""

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self._buffer: List[RLTransition] = []
        self._position = 0

    def add(self, transition: RLTransition):
        if len(self._buffer) < self.capacity:
            self._buffer.append(transition)
        else:
            self._buffer[self._position] = transition
        self._position = (self._position + 1) % self.capacity

    def sample(self, batch_size: int) -> List[RLTransition]:
        import random
        if len(self._buffer) < batch_size:
            return list(self._buffer)
        return random.sample(self._buffer, batch_size)

    @property
    def size(self) -> int:
        return len(self._buffer)

    def clear(self):
        self._buffer.clear()
        self._position = 0


class RewardShaper:
    """Shapes raw rewards to provide denser learning signal."""

    def __init__(self):
        self._reward_weights = {
            "goal_reached": 100.0,
            "collision": -100.0,
            "progress": 1.0,
            "energy_efficiency": 0.5,
            "time_penalty": -0.01,
            "exploration_bonus": 0.3,
            "safety_margin": 0.2,
        }
        self._previous_distance = 0.0

    def shape(self, state: RLState, action: RLAction,
              done: bool, goal_reached: bool,
              collision: bool) -> RLReward:
        components = {}

        if goal_reached:
            components["goal_reached"] = self._reward_weights["goal_reached"]
        if collision:
            components["collision"] = self._reward_weights["collision"]

        # Progress reward
        progress = self._previous_distance - state.distance_to_target
        if self._previous_distance > 0:
            components["progress"] = progress * self._reward_weights["progress"]

        # Time penalty
        components["time_penalty"] = self._reward_weights["time_penalty"]

        # Energy efficiency
        if state.speed > 0:
            efficiency = progress / max(state.speed, 0.01)
            components["energy_efficiency"] = efficiency * self._reward_weights["energy_efficiency"]

        # Safety margin bonus
        if state.nearest_obstacle_dist > 3.0:
            components["safety_margin"] = self._reward_weights["safety_margin"]

        self._previous_distance = state.distance_to_target

        total = sum(components.values())
        explanation = ", ".join(f"{k}={v:.2f}" for k, v in components.items() if v != 0)

        return RLReward(
            reward=total, components=components, done=done,
            explanation=f"Reward={total:.3f}: {explanation}",
        )


class ReinforcementLearningInterface:
    """
    Interface between the cognitive architecture and RL algorithms.
    Manages state encoding, action selection, reward computation,
    and policy updates.
    """

    def __init__(self, exploration_rate: float = 0.1):
        self._policies: Dict[str, RLPolicy] = {}
        self._active_policy: Optional[str] = None
        self._replay = ExperienceReplay()
        self._reward_shaper = RewardShaper()
        self._transition_history: List[RLTransition] = []
        self._episode_count = 0
        self._total_reward = 0.0

        # Action space
        self._action_space = [action_type for action_type in RLActionType]
        self._exploration_rate = exploration_rate

    def create_policy(self, name: str, learning_rate: float = 0.01,
                      discount_factor: float = 0.99) -> str:
        policy = RLPolicy(
            name=name, learning_rate=learning_rate,
            discount_factor=discount_factor,
            exploration_rate=self._exploration_rate,
        )
        self._policies[name] = policy
        if self._active_policy is None:
            self._active_policy = name
        return name

    def select_action(self, state: RLState,
                      available_actions: Optional[List[RLAction]] = None
                      ) -> RLAction:
        """Select action using epsilon-greedy policy."""
        import random
        actions = available_actions or [
            RLAction(action_type=at) for at in self._action_space
        ]

        if random.random() < self._exploration_rate:
            return random.choice(actions)

        if self._active_policy and self._active_policy in self._policies:
            policy = self._policies[self._active_policy]
            state_key = self._state_to_key(state)
            q_values = policy.get_q_values(state_key)
            if q_values:
                best_action = max(q_values, key=q_values.get)
                for a in actions:
                    if a.name == best_action:
                        return a

        return actions[0]  # Default to first action

    def compute_reward(self, state: RLState, action: RLAction,
                       next_state: RLState, done: bool,
                       goal_reached: bool, collision: bool) -> RLReward:
        return self._reward_shaper.shape(state, action, done, goal_reached, collision)

    def store_transition(self, state: RLState, action: RLAction,
                         reward: RLReward, next_state: RLState, done: bool):
        transition = RLTransition(
            state=state, action=action, reward=reward,
            next_state=next_state, done=done,
        )
        self._replay.add(transition)
        self._transition_history.append(transition)
        self._total_reward += reward.reward

        if done:
            self._episode_count += 1

    def update_policy(self, state: RLState, action: RLAction,
                      reward: float, next_state: RLState, done: bool):
        """Simple Q-learning update."""
        if self._active_policy not in self._policies:
            return

        policy = self._policies[self._active_policy]
        state_key = self._state_to_key(state)
        next_state_key = self._state_to_key(next_state)
        action_name = action.name

        # Get current Q value
        q_values = policy.get_q_values(state_key)
        current_q = q_values.get(action_name, 0.0)

        # Get max future Q
        next_q_values = policy.get_q_values(next_state_key)
        max_future_q = max(next_q_values.values()) if next_q_values else 0.0

        # Q-learning update
        new_q = current_q + policy.learning_rate * (
            reward + policy.discount_factor * max_future_q * (1 - done) - current_q
        )
        policy.update_q(state_key, action_name, new_q)

    def get_action_explanation(self, state: RLState,
                                action: RLAction) -> str:
        """Explain why this action was chosen."""
        policy = self._policies.get(self._active_policy) if self._active_policy else None
        if policy:
            state_key = self._state_to_key(state)
            q_values = policy.get_q_values(state_key)
            if q_values:
                sorted_q = sorted(q_values.items(), key=lambda x: -x[1])
                top_3 = sorted_q[:3]
                q_str = ", ".join(f"{k}={v:.3f}" for k, v in top_3)
                return (f"RL chose '{action.name}' (Q={q_values.get(action.name, 0):.3f}) "
                        f"from policy '{policy.name}'. Top Q-values: {q_str}")
        return f"RL chose '{action.name}' (default/exploration)"

    def _state_to_key(self, state: RLState) -> str:
        """Discretize state for Q-table lookup."""
        x = round(state.position[0] / 2.0)
        y = round(state.position[1] / 2.0)
        bat = round(state.battery_level, 1)
        return f"s_{x}_{y}_{bat}"

    def get_performance_summary(self) -> Dict[str, Any]:
        avg_reward = self._total_reward / max(1, self._episode_count)
        return {
            "episode_count": self._episode_count,
            "total_reward": self._total_reward,
            "avg_reward_per_episode": avg_reward,
            "replay_buffer_size": self._replay.size,
            "exploration_rate": self._exploration_rate,
            "active_policy": self._active_policy,
            "num_policies": len(self._policies),
        }

    def __repr__(self) -> str:
        return (f"ReinforcementLearningInterface(policies={len(self._policies)}, "
                f"active='{self._active_policy}', replay={self._replay.size})")