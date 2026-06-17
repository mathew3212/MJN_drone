"""
Training Utilities
==================
Online and offline training support for the learned prediction models.

Provides:
- collect_training_data(): Gathers simulation data for training
- train_predictor(): Fine-tunes the attention model using collected data
- Simple gradient-free optimization for the NumPy backend
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional

from src.prediction.attention_predictor import AttentionPredictor
from src.prediction.scene_memory import SceneMemory
from src.prediction.learned_predictor import LearnedPredictor


@dataclass
class TrainingSample:
    """A single training example."""
    history: np.ndarray       # (seq_len, 6) obstacle features
    future: np.ndarray        # (pred_horizon, 2) actual future positions
    obstacle_type: float = 1.0


@dataclass
class TrainingConfig:
    """Configuration for training."""
    learning_rate: float = 1e-3
    batch_size: int = 32
    num_epochs: int = 100
    val_split: float = 0.2
    weight_decay: float = 1e-4
    grad_clip: float = 1.0
    print_every: int = 10


class TrainingBuffer:
    """Buffer that stores training data from simulation episodes."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.samples: List[TrainingSample] = []

    def add(self, sample: TrainingSample):
        """Add a training sample to the buffer."""
        self.samples.append(sample)
        if len(self.samples) > self.max_size:
            self.samples.pop(0)

    def add_batch(self, samples: List[TrainingSample]):
        """Add multiple samples."""
        for s in samples:
            self.add(s)

    def sample(self, batch_size: int) -> List[TrainingSample]:
        """Randomly sample a batch from the buffer."""
        if len(self.samples) == 0:
            return []
        indices = np.random.choice(
            len(self.samples),
            size=min(batch_size, len(self.samples)),
            replace=False
        )
        return [self.samples[i] for i in indices]

    def split(self, val_ratio: float = 0.2):
        """Split into train and validation sets."""
        n = len(self.samples)
        val_n = max(1, int(n * val_ratio))
        indices = np.random.permutation(n)
        val_indices = indices[:val_n]
        train_indices = indices[val_n:]
        train = [self.samples[i] for i in train_indices]
        val = [self.samples[i] for i in val_indices]
        return train, val

    def __len__(self):
        return len(self.samples)

    def clear(self):
        self.samples.clear()


class SimpleSGDOptimizer:
    """Minimal SGD with momentum for training NumPy weight arrays."""

    def __init__(self, params: list, lr: float = 1e-3, momentum: float = 0.9):
        self.params = params
        self.lr = lr
        self.momentum = momentum
        self.velocities = [np.zeros_like(p) for p in params]

    def step(self, grads: list):
        """Perform one optimization step."""
        for i, (p, g) in enumerate(zip(self.params, grads)):
            self.velocities[i] = self.momentum * self.velocities[i] + self.lr * g
            p -= self.velocities[i]

    def zero_grad(self):
        pass


def collect_training_data(
    predictor: LearnedPredictor,
    dynamic_obstacles: list,
    step: int,
) -> Optional[TrainingSample]:
    """Collect a training sample from the current simulation state.

    Records the current obstacle history as input and future positions as ground truth.
    Call this every simulation step to gather training data.

    Parameters
    ----------
    predictor : LearnedPredictor
        The predictor instance (for accessing history).
    dynamic_obstacles : list
        Current dynamic obstacles.
    step : int
        Current simulation step.

    Returns
    -------
    sample : TrainingSample or None
        If there's enough data to form a training example.
    """
    if not hasattr(predictor, '_training_buffer'):
        predictor._training_buffer = TrainingBuffer()

    # For each obstacle with sufficient history, create a training sample
    samples = []
    for idx, obs in enumerate(dynamic_obstacles):
        if idx not in predictor._history:
            continue
        history = predictor._history[idx]
        if len(history) < predictor.seq_len + 2:
            continue

        # Use the last seq_len observations as input
        hist = np.array(history[-predictor.seq_len:], dtype=np.float32)

        # Future positions would be the next observations
        # For now we use the current position as "best guess" of future
        x = getattr(obs, 'x', 0)
        y = getattr(obs, 'y', 0)
        vx = getattr(obs, 'velocity_x', getattr(obs, 'vx', 0))
        vy = getattr(obs, 'velocity_y', getattr(obs, 'vy', 0))

        future = np.array([
            [x + vx * (i + 1), y + vy * (i + 1)]
            for i in range(predictor.pred_horizon)
        ], dtype=np.float32)

        samples.append(TrainingSample(
            history=hist,
            future=future,
            obstacle_type=1.0,
        ))

    if samples:
        predictor._training_buffer.add_batch(samples)

    return samples[0] if samples else None


def train_predictor(
    predictor: LearnedPredictor,
    config: Optional[TrainingConfig] = None,
    buffer: Optional[TrainingBuffer] = None,
) -> dict:
    """Fine-tune the attention predictor using collected training data.

    Uses a simple forward-difference gradient estimation approach
    for the NumPy backend (no PyTorch autograd needed).

    Parameters
    ----------
    predictor : LearnedPredictor
        The model to train (modifies parameters in-place).
    config : TrainingConfig or None
        Training hyperparameters.
    buffer : TrainingBuffer or None
        Training data buffer. If None, uses predictor._training_buffer.

    Returns
    -------
    history : dict
        Training history with losses.
    """
    if config is None:
        config = TrainingConfig()
    if buffer is None:
        buffer = getattr(predictor, '_training_buffer', None)
    if buffer is None or len(buffer) < config.batch_size:
        return {"losses": [], "val_losses": []}

    predictor.trajectory_predictor.training = True
    train_data, val_data = buffer.split(config.val_split)

    history = {"losses": [], "val_losses": []}

    for epoch in range(config.num_epochs):
        # Training
        batch = buffer.sample(config.batch_size)
        train_loss = _train_step(predictor.trajectory_predictor, batch, config)
        history["losses"].append(train_loss)

        # Validation
        if val_data:
            val_loss = _evaluate(predictor.trajectory_predictor, val_data, config)
            history["val_losses"].append(val_loss)

        if (epoch + 1) % config.print_every == 0:
            val_str = f", val_loss={history['val_losses'][-1]:.4f}" if val_data else ""
            print(f"  Epoch {epoch + 1}/{config.num_epochs}: loss={train_loss:.4f}{val_str}")

    predictor.trajectory_predictor.training = False
    return history


def _train_step(
    model: AttentionPredictor,
    batch: list,
    config: TrainingConfig,
) -> float:
    """One training step using forward perturbation for gradient estimation."""
    if not batch:
        return 0.0

    total_loss = 0.0
    lr = config.learning_rate

    for sample in batch:
        # Forward pass
        pred = model.predict_single(sample.history)
        target = sample.future

        # MSE loss on (x, y) predictions
        dx = pred[:, :2] - target
        loss = float(np.mean(dx ** 2))
        total_loss += loss

        # Simple parameter perturbation for gradient-free optimization
        # Only perturb output weights for speed
        for name in ["W_out", "b_out"]:
            param = getattr(model, name)
            epsilon = np.random.randn(*param.shape).astype(np.float32) * lr * 0.01
            old_val = param.copy()

            # Positive perturbation
            setattr(model, name, param + epsilon)
            pred_pos = model.predict_single(sample.history)
            loss_pos = float(np.mean((pred_pos[:, :2] - target) ** 2))

            # Negative perturbation
            setattr(model, name, param - epsilon)
            pred_neg = model.predict_single(sample.history)
            loss_neg = float(np.mean((pred_neg[:, :2] - target) ** 2))

            # Gradient approximation
            grad = (loss_pos - loss_neg) / (2.0 * epsilon + 1e-10) * (loss - 0)
            setattr(model, name, old_val - lr * grad * 0.001)

    return total_loss / max(len(batch), 1)


def _evaluate(
    model: AttentionPredictor,
    data: list,
    config: TrainingConfig,
) -> float:
    """Evaluate model on validation data."""
    model.training = False
    total_loss = 0.0

    for sample in data[:min(50, len(data))]:
        pred = model.predict_single(sample.history)
        target = sample.future
        dx = pred[:, :2] - target
        loss = float(np.mean(dx ** 2))
        total_loss += loss

    model.training = True
    return total_loss / max(min(50, len(data)), 1)