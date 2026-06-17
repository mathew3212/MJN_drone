"""
MJN Cognitive AI Architecture
=============================

A comprehensive cognitive architecture for autonomous drone navigation
that provides world modeling, hierarchical memory, attention mechanisms,
uncertainty estimation, probabilistic reasoning, Bayesian belief updates,
reinforcement learning interfaces, mission context understanding,
explainable AI decision logging, adaptive planning, self-evaluation,
confidence estimation, and continuous learning.

Architecture Overview:
    - WorldModel: Internal simulation of the environment for prediction and planning
    - HierarchicalMemory: Working/episodic/semantic/procedural memory layers
    - AttentionMechanism: Relevance-based focus on sensory information
    - UncertaintyEstimator: Quantifies uncertainty in beliefs and predictions
    - ProbabilisticReasoner: Reasons under uncertainty using probability theory
    - BayesianBeliefNetwork: Maintains and updates beliefs with new evidence
    - ReinforcementLearningInterface: RL integration for policy optimization
    - MissionContextManager: Deep understanding of mission goals and constraints
    - ExplainableAILogger: Transparent decision logging with full traceability
    - AdaptivePlanner: Plans that evolve based on experience and context
    - SelfEvaluator: Continuous self-assessment of performance and capability
    - ConfidenceEstimator: Estimates confidence levels for all decisions
    - ContinuousLearningHooks: Mechanisms for ongoing adaptation and learning
    - CognitiveArchitecture: Main orchestrator tying all subsystems together

Every decision made by the system is traceable with an explanation of WHY
it was chosen,WHAT evidence supported it, and HOW confident the system was.
"""

__version__ = "1.0.0"
__author__ = "MJN Drone Project"

from src.cognition.world_model import WorldModel, WorldState, PredictedOutcome
from src.cognition.hierarchical_memory import (
    HierarchicalMemory,
    WorkingMemory,
    EpisodicMemory,
    SemanticMemory,
    ProceduralMemory,
    MemoryEpisode,
    SemanticFact,
    ProceduralRule,
)
from src.cognition.attention import (
    AttentionMechanism,
    AttentionFocus,
    RelevanceScore,
)
from src.cognition.uncertainty import (
    UncertaintyEstimator,
    UncertaintyProfile,
    UncertaintyMethod,
)
from src.cognition.probabilistic import (
    ProbabilisticReasoner,
    ProbabilityDistribution,
    ConditionalProbability,
    InferenceResult,
)
from src.cognition.bayesian import (
    BayesianBeliefNetwork,
    Belief,
    Evidence,
    BeliefUpdate,
)
from src.cognition.rl_interface import (
    ReinforcementLearningInterface,
    RLState,
    RLAction,
    RLReward,
    RLTransition,
    RLPolicy,
)
from src.cognition.mission_context import (
    MissionContextManager,
    MissionGoal,
    MissionConstraint,
    MissionPhase,
    SituationalAssessment,
)
from src.cognition.explainability import (
    ExplainableAILogger,
    DecisionRecord,
    Explanation,
    DecisionCategory,
    ExplanationLevel,
)
from src.cognition.adaptive_planner import (
    AdaptivePlanner,
    Plan,
    PlanStep,
    PlanAdaptation,
    PlanningStrategy,
)
from src.cognition.self_evaluation import (
    SelfEvaluator,
    EvaluationReport,
    PerformanceMetric,
    CapabilityAssessment,
)
from src.cognition.confidence import (
    ConfidenceEstimator,
    ConfidenceReport,
    ConfidenceLevel,
)
from src.cognition.learning import (
    ContinuousLearningHooks,
    LearningEvent,
    LearningStrategy,
    AdaptationResult,
)
from src.cognition.cognitive_architecture import CognitiveArchitecture