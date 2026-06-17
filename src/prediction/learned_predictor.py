"""
LearnedPredictor
================
Integrated predictor that combines:
- AttentionPredictor: Transformer-based trajectory forecasting
- SceneMemory: Episodic memory with attention recall
- Risk computation: Attention-weighted risk aggregation

This replaces the heuristic RiskPredictor and TrajectoryPredictor
with a unified learned system that produces richer predictions.
"""

import numpy as np

from src.prediction.attention_predictor import AttentionPredictor
from src.prediction.scene_memory import SceneMemory


class LearnedPredictor:
    """Integrated learned attention-based predictor.

    Combines trajectory prediction, scene memory, and risk estimation
    into a single learned pipeline.

    Parameters
    ----------
    width : int
        Grid width.
    height : int
        Grid height.
    pred_horizon : int
        Prediction horizon in timesteps (default 10).
    seq_len : int
        History length to condition on (default 6).
    d_model : int
        Attention model dimension (default 64).
    n_heads : int
        Number of attention heads (default 4).
    memory_capacity : int
        Scene memory capacity (default 500).
    """

    def __init__(
        self,
        width: int,
        height: int,
        pred_horizon: int = 10,
        seq_len: int = 6,
        d_model: int = 64,
        n_heads: int = 4,
        memory_capacity: int = 500,
    ):
        self.width = width
        self.height = height
        self.pred_horizon = pred_horizon
        self.seq_len = seq_len

        # Learned models
        self.trajectory_predictor = AttentionPredictor(
            input_dim=6,
            seq_len=seq_len,
            pred_horizon=pred_horizon,
            d_model=d_model,
            n_heads=n_heads,
        )

        self.scene_memory = SceneMemory(
            width=width,
            height=height,
            memory_capacity=memory_capacity,
            d_model=max(32, d_model // 2),
        )

        # Output grids
        self.grid = np.zeros((height, width), dtype=np.float32)  # Combined risk grid
        self.attention_grid = np.zeros((height, width), dtype=np.float32)  # Attention heatmap
        self.familiarity_grid = np.zeros((height, width), dtype=np.float32)  # Memory familiarity

        # Obstacle history buffer
        self._history: dict[int, list[np.ndarray]] = {}
        self._history_maxlen = seq_len

        # Training mode
        self.training = True

    def observe_obstacle(self, idx: int, x: float, y: float,
                          vx: float = 0.0, vy: float = 0.0,
                          ax: float = 0.0, ay: float = 0.0,
                          is_dynamic: bool = True) -> None:
        """Record an obstacle observation.

        Parameters
        ----------
        idx : int
            Unique obstacle identifier.
        x, y : float
            Current position.
        vx, vy : float
            Current velocity.
        ax, ay : float
            Current acceleration (optional).
        is_dynamic : bool
            Whether this is a moving obstacle.
        """
        feat = np.array([x, y, vx, vy, ax, ay], dtype=np.float32)

        if idx not in self._history:
            self._history[idx] = []
        self._history[idx].append(feat)

        # Maintain max history length
        if len(self._history[idx]) > self._history_maxlen:
            self._history[idx].pop(0)

        # Also store in scene memory
        self.scene_memory.observe(x, y, vx, vy,
                                   obstacle_type=1 if is_dynamic else 0)

    def update(self, dynamic_obstacles: list) -> np.ndarray:
        """Update all predictions based on current obstacle positions.

        Parameters
        ----------
        dynamic_obstacles : list
            List of dynamic obstacle objects with .x, .y, .velocity_x, .velocity_y attributes.

        Returns
        -------
        grid : ndarray shape (height, width)
            Combined risk/attention grid.
        """
        # Reset grids
        self.grid.fill(0)
        self.attention_grid.fill(0)

        # Update scene memory from obstacles
        self.scene_memory.update(dynamic_obstacles)
        self.familiarity_grid = self.scene_memory.grid.copy()

        # Process each obstacle through attention predictor
        for idx, obs in enumerate(dynamic_obstacles):
            x = getattr(obs, 'x', 0)
            y = getattr(obs, 'y', 0)
            vx = getattr(obs, 'velocity_x', getattr(obs, 'vx', 0))
            vy = getattr(obs, 'velocity_y', getattr(obs, 'vy', 0))

            # Observe
            self.observe_obstacle(idx, float(x), float(y), float(vx), float(vy),
                                   is_dynamic=True)

            # Predict if we have enough history
            history = self._history.get(idx, [])
            if len(history) >= self.seq_len:
                hist_array = np.array(history[-self.seq_len:], dtype=np.float32)
                if len(hist_array) < self.seq_len:
                    # Pad with duplicates
                    pad = self.seq_len - len(hist_array)
                    hist_array = np.vstack([hist_array[:1]] * pad + [hist_array])

                predictions = self.trajectory_predictor.predict_single(hist_array)

                # Rasterize predictions into risk grid
                self._rasterize_predictions(predictions, idx)
            else:
                # Fallback: linear extrapolation
                self._extrapolate_linear(obs)

        return self.grid

    def _rasterize_predictions(self, predictions: np.ndarray, obs_idx: int) -> None:
        """Rasterize predicted trajectories into the risk grid.

        Parameters
        ----------
        predictions : ndarray shape (pred_horizon, 4)
            Predicted [x, y, confidence, variance].
        obs_idx : int
            Obstacle index (for attention tracking).
        """
        for step, (px, py, conf, var) in enumerate(predictions):
            x = int(round(px))
            y = int(round(py))

            if 0 <= x < self.width and 0 <= y < self.height:
                # Risk = confidence * (1 - variance_normalized) * temporal_decay
                temporal_weight = (self.pred_horizon - step) / self.pred_horizon
                var_norm = 1.0 / (1.0 + var)  # lower variance = higher confidence
                risk = conf * var_norm * temporal_weight

                # Add to grid with spreading based on variance
                spread = int(np.clip(np.sqrt(var) * 2, 1, 3))
                for dy in range(-spread, spread + 1):
                    for dx in range(-spread, spread + 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            # Gaussian spreading
                            dist = np.sqrt(dx ** 2 + dy ** 2)
                            contribution = risk * np.exp(-dist ** 2 / (2 * (var + 1)))
                            self.grid[ny, nx] += contribution
                            self.attention_grid[ny, nx] += conf * temporal_weight

    def _extrapolate_linear(self, obs) -> None:
        """Fallback: simple linear extrapolation for obstacles without history."""
        x = getattr(obs, 'x', 0)
        y = getattr(obs, 'y', 0)
        vx = getattr(obs, 'velocity_x', getattr(obs, 'vx', 0))
        vy = getattr(obs, 'velocity_y', getattr(obs, 'vy', 0))

        for step in range(1, self.pred_horizon + 1):
            px = int(x + vx * step)
            py = int(y + vy * step)
            if 0 <= px < self.width and 0 <= py < self.height:
                risk = (self.pred_horizon - step + 1) / self.pred_horizon
                self.grid[py, px] += risk

    def get_risk(self, x: int, y: int) -> float:
        """Get the combined risk at a specific grid cell."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return float(self.grid[y, x])
        return 0.0

    def get_familiarity(self, x: int, y: int) -> float:
        """Get scene memory familiarity at a cell."""
        return self.scene_memory.get_familiarity(x, y)

    def get_attention_map(self) -> np.ndarray:
        """Return the attention heatmap."""
        return self.attention_grid.copy()

    def get_memory_heatmap(self) -> np.ndarray:
        """Return the memory familiarity heatmap."""
        return self.familiarity_grid.copy()

    def get_params(self) -> dict:
        """Get all learned parameters."""
        return {
            "trajectory_predictor": self.trajectory_predictor.get_params(),
            "scene_memory": self.scene_memory.get_params(),
        }

    def load_params(self, params: dict):
        """Load learned parameters."""
        if "trajectory_predictor" in params:
            self.trajectory_predictor.load_params(params["trajectory_predictor"])
        if "scene_memory" in params:
            self.scene_memory.load_params(params["scene_memory"])