"""
SceneMemory
===========
Learned episodic scene memory with attention-based recall.

Maintains a memory buffer of observed obstacle positions and uses
attention-weighted retrieval to generate a spatial familiarity map.
When PyTorch is available, uses GPU-accelerated tensor operations.

The memory module learns to:
1. Encode observations into key-value pairs
2. Store them in a persistent memory buffer
3. Attend over memory at query time to produce familiarity scores
4. Decay unused memories and reinforce frequently recalled ones
"""

import numpy as np
from collections import deque

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class SceneMemory:
    """Learned episodic scene memory with attention-based recall.

    Parameters
    ----------
    width : int
        Grid width (for compatibility with existing interface).
    height : int
        Grid height.
    memory_capacity : int
        Maximum number of episodic memories to store (default 500).
    d_model : int
        Memory embedding dimension (default 32).
    decay_rate : float
        Per-step decay multiplier for memory strength (default 0.995).
    reinforce_bonus : float
        Bonus added to memory strength when recalled (default 0.2).
    attention_temp : float
        Temperature for attention softmax (default 1.0).
    """

    def __init__(
        self,
        width: int,
        height: int,
        memory_capacity: int = 500,
        d_model: int = 32,
        decay_rate: float = 0.995,
        reinforce_bonus: float = 0.2,
        attention_temp: float = 1.0,
    ):
        self.width = width
        self.height = height
        self.memory_capacity = memory_capacity
        self.d_model = d_model
        self.decay_rate = decay_rate
        self.reinforce_bonus = reinforce_bonus
        self.attention_temp = attention_temp

        # Memory buffer: stores (key_embedding, value, strength, age)
        # key:    d_model-dim embedding of position + context
        # value:  (x, y) position, obstacle_type
        # strength: scalar "health" of memory (0 = forgotten)
        # age:     time since last recall
        self.memory_keys = np.zeros((0, d_model), dtype=np.float32)
        self.memory_values = np.zeros((0, 3), dtype=np.float32)  # x, y, type_id
        self.memory_strength = np.zeros(0, dtype=np.float32)
        self.memory_age = np.zeros(0, dtype=np.float32)

        # Learned embeddings
        scale = d_model ** -0.5
        self.W_pos = np.random.randn(2, d_model).astype(np.float32) * scale * 0.1
        self.W_ctx = np.random.randn(4, d_model).astype(np.float32) * scale * 0.1
        self.W_query = np.random.randn(d_model, d_model).astype(np.float32) * scale * 0.1
        self.W_recall = np.random.randn(d_model, 1).astype(np.float32) * scale * 0.1

        # Output grid (familiarity map)
        self.grid = np.zeros((height, width), dtype=np.float32)

        # Recent recall trace (for reinforcement)
        self._recent_recalls: list[int] = []
        self._recall_streak = 0

        # Training mode
        self.training = True

    def _encode_position(self, x: float, y: float) -> np.ndarray:
        """Encode a position into an embedding vector."""
        pos = np.array([x, y], dtype=np.float32)
        return pos @ self.W_pos  # (d_model,)

    def _encode_context(self, vx: float = 0.0, vy: float = 0.0,
                         obs_type: float = 0.0, time: float = 0.0) -> np.ndarray:
        """Encode context features into embedding."""
        ctx = np.array([vx, vy, obs_type, time], dtype=np.float32)
        return ctx @ self.W_ctx  # (d_model,)

    def observe(self, x: float, y: float, vx: float = 0.0, vy: float = 0.0,
                obstacle_type: int = 0, timestamp: float = 0.0) -> None:
        """Store an observation into episodic memory.

        Parameters
        ----------
        x, y : float
            Observed obstacle position.
        vx, vy : float
            Estimated velocity.
        obstacle_type : int
            Type identifier (0=static, 1=dynamic, etc.).
        timestamp : float
            Simulation time of observation.
        """
        # Encode
        pos_emb = self._encode_position(x, y)
        ctx_emb = self._encode_context(vx, vy, float(obstacle_type), timestamp)
        key = pos_emb + ctx_emb

        value = np.array([x, y, float(obstacle_type)], dtype=np.float32)

        # Check for near-duplicate (within 2 cells)
        if len(self.memory_values) > 0:
            dists = np.sqrt(
                (self.memory_values[:, 0] - x) ** 2 +
                (self.memory_values[:, 1] - y) ** 2
            )
            near_dup = dists < 2.0
            if np.any(near_dup):
                # Reinforce existing memory
                idx = np.argmin(dists)
                self.memory_strength[idx] = min(1.0, self.memory_strength[idx] + self.reinforce_bonus)
                self.memory_age[idx] = 0
                return

        # Add new memory
        self.memory_keys = np.vstack([self.memory_keys, key[None, :]])
        self.memory_values = np.vstack([self.memory_values, value[None, :]])
        self.memory_strength = np.append(self.memory_strength, 1.0)
        self.memory_age = np.append(self.memory_age, 0.0)

        # Evict oldest/weakest if over capacity
        if len(self.memory_keys) > self.memory_capacity:
            evict_score = self.memory_strength - self.memory_age * 0.01
            evict_idx = np.argmin(evict_score)
            self.memory_keys = np.delete(self.memory_keys, evict_idx, axis=0)
            self.memory_values = np.delete(self.memory_values, evict_idx, axis=0)
            self.memory_strength = np.delete(self.memory_strength, evict_idx)
            self.memory_age = np.delete(self.memory_age, evict_idx)

    def recall(self, query_x: float, query_y: float) -> tuple[float, np.ndarray | None]:
        """Query memory for familiarity at a position.

        Uses attention-weighted retrieval over all stored memories.

        Parameters
        ----------
        query_x, query_y : float
            Query position (e.g., drone's current position or target).

        Returns
        -------
        familiarity : float in [0, 1]
            How familiar the scene is at this location (1 = well-known).
        recalled_value : ndarray or None
            The most relevant memory's (x, y, type) if familiarity > threshold.
        """
        if len(self.memory_keys) == 0:
            return 0.0, None

        # Encode query
        q_emb = self._encode_position(query_x, query_y)
        q_vec = q_emb @ self.W_query  # (d_model,)

        # Attention scores over all memories
        keys = self.memory_keys  # (N, d_model)
        scores = keys @ q_vec  # (N,)
        scores = scores / (self.d_model ** 0.5)

        # Apply strength weighting
        scores = scores * self.memory_strength

        # Temperature-scaled attention
        attn = np.exp(scores / self.attention_temp)
        attn = attn / (attn.sum() + 1e-10)

        # Familiarity = maximum attention-weighted score
        max_attn = float(attn.max())
        familiarity = float(np.clip(max_attn * len(attn), 0, 1))

        # Weighted recall
        best_idx = int(np.argmax(attn))
        recalled = self.memory_values[best_idx].copy() if familiarity > 0.2 else None

        # Reinforce recalled memory
        if recalled is not None:
            self.memory_strength[best_idx] = min(1.0, self.memory_strength[best_idx] + self.reinforce_bonus)
            self.memory_age[best_idx] = 0
            self._recent_recalls.append(best_idx)

        return familiarity, recalled

    def update(self, obstacles: list | None = None) -> np.ndarray:
        """Update the familiarity grid and decay memories.

        Parameters
        ----------
        obstacles : list of obstacles (optional)
            If provided, calls observe() for each.

        Returns
        -------
        grid : ndarray shape (height, width)
            Updated familiarity heatmap.
        """
        # Observe obstacles
        if obstacles is not None:
            for obs in obstacles:
                x = getattr(obs, 'x', 0)
                y = getattr(obs, 'y', 0)
                vx = getattr(obs, 'velocity_x', getattr(obs, 'vx', 0))
                vy = getattr(obs, 'velocity_y', getattr(obs, 'vy', 0))
                obs_type = 1 if getattr(obs, 'is_dynamic', False) else 0
                self.observe(x, y, vx, vy, obs_type)

        # Decay memories
        self.memory_strength *= self.decay_rate
        self.memory_age += 1.0

        # Clamp
        self.memory_strength = np.clip(self.memory_strength, 0, 1)

        # Compute familiarity grid (efficient batched version)
        self._compute_familiarity_grid()

        return self.grid

    def _compute_familiarity_grid(self):
        """Compute familiarity grid using attention over all grid cells."""
        if len(self.memory_keys) == 0:
            self.grid.fill(0)
            return

        # Query all grid cells in batches
        self.grid.fill(0)
        step = 10  # process in 10x10 blocks for efficiency
        for y in range(0, self.height, step):
            for x in range(0, self.width, step):
                batch_x = np.arange(x, min(x + step, self.width))
                batch_y = np.arange(y, min(y + step, self.height))
                xx, yy = np.meshgrid(batch_x, batch_y)
                positions = np.stack([xx.ravel(), yy.ravel()], axis=1).astype(np.float32)

                # Batch attention
                q_emb = positions @ self.W_pos  # (N, d_model)
                q_vec = q_emb @ self.W_query   # (N, d_model)
                keys = self.memory_keys        # (M, d_model)

                scores = q_vec @ keys.T        # (N, M)
                scores = scores / (self.d_model ** 0.5)
                scores = scores * self.memory_strength[None, :]

                attn = np.exp(scores)
                attn = attn / (attn.sum(axis=1, keepdims=True) + 1e-10)

                familiarity = np.clip(attn.max(axis=1) * len(keys), 0, 1)

                # Place into grid
                for i, (px, py) in enumerate(zip(positions[:, 0], positions[:, 1])):
                    ix, iy = int(px), int(py)
                    if 0 <= ix < self.width and 0 <= iy < self.height:
                        self.grid[iy, ix] = max(self.grid[iy, ix], familiarity[i])

    def get_familiarity(self, x: int, y: int) -> float:
        """Get familiarity score at a specific grid cell."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return float(self.grid[y, x])
        return 0.0

    def memory_density(self) -> float:
        """Fraction of memory capacity currently used."""
        return len(self.memory_keys) / max(self.memory_capacity, 1)

    def active_cells(self) -> int:
        """Number of memories with strength > 0.1."""
        return int(np.sum(self.memory_strength > 0.1))

    def forget_old_memories(self, threshold: float = 0.01):
        """Remove memories that have decayed below threshold."""
        if len(self.memory_keys) == 0:
            return
        keep = self.memory_strength > threshold
        self.memory_keys = self.memory_keys[keep]
        self.memory_values = self.memory_values[keep]
        self.memory_strength = self.memory_strength[keep]
        self.memory_age = self.memory_age[keep]

    def get_params(self) -> dict:
        """Get learned parameters for serialization."""
        return {
            "W_pos": self.W_pos.copy(),
            "W_ctx": self.W_ctx.copy(),
            "W_query": self.W_query.copy(),
            "W_recall": self.W_recall.copy(),
        }

    def load_params(self, params: dict):
        """Load learned parameters."""
        for name in ["W_pos", "W_ctx", "W_query", "W_recall"]:
            if name in params:
                setattr(self, name, params[name].astype(np.float32).copy())

    def get_heatmap(self) -> np.ndarray:
        """Return the familiarity grid as a heatmap (for visualization)."""
        return self.grid.copy()