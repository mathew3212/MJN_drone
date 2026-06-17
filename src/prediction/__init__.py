"""
prediction package: Learned attention-based trajectory prediction and scene memory.

Provides:
- AttentionPredictor: Cross-attention neural predictor for obstacle trajectories
- SceneMemory: Learned episodic scene memory with attention recall
- LearnedPredictor: Integrated predictor combining attention + memory + risk
- training utilities for online/offline learning
"""

from src.prediction.attention_predictor import AttentionPredictor
from src.prediction.scene_memory import SceneMemory
from src.prediction.learned_predictor import LearnedPredictor
from src.prediction.training import train_predictor, collect_training_data

__all__ = [
    "AttentionPredictor",
    "SceneMemory",
    "LearnedPredictor",
    "train_predictor",
    "collect_training_data",
]