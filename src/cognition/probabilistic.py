"""
Probabilistic Reasoning Engine
===============================

Uncertainty-aware reasoning using probability theory. Supports
probability distributions, conditional probability, Bayesian inference,
MAP estimation, expected utility computation, and decision-making
under uncertainty.
"""

import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any


class DistributionType(Enum):
    GAUSSIAN = "gaussian"
    DISCRETE = "discrete"
    UNIFORM = "uniform"
    BERNOULLI = "bernoulli"


@dataclass
class ProbabilityDistribution:
    """A probability distribution over a variable."""
    name: str
    dist_type: DistributionType
    parameters: Dict[str, float]
    support: Optional[List[float]] = None
    timestamp: float = field(default_factory=time.time)

    @property
    def mean(self) -> float:
        if self.dist_type == DistributionType.GAUSSIAN:
            return self.parameters.get("mean", 0.0)
        elif self.dist_type == DistributionType.DISCRETE:
            total = 0.0
            if self.support and self.parameters.get("probs"):
                for p, s in zip(self.parameters["probs"], self.support):
                    total += p * s
            return total
        elif self.dist_type == DistributionType.UNIFORM:
            a, b = self.parameters.get("a", 0.0), self.parameters.get("b", 1.0)
            return (a + b) / 2.0
        elif self.dist_type == DistributionType.BERNOULLI:
            return self.parameters.get("p", 0.5)
        return 0.0

    @property
    def variance(self) -> float:
        if self.dist_type == DistributionType.GAUSSIAN:
            return self.parameters.get("std", 1.0) ** 2
        elif self.dist_type == DistributionType.UNIFORM:
            a, b = self.parameters.get("a", 0.0), self.parameters.get("b", 1.0)
            return (b - a) ** 2 / 12.0
        elif self.dist_type == DistributionType.BERNOULLI:
            p = self.parameters.get("p", 0.5)
            return p * (1 - p)
        return 0.0

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)

    def pdf(self, x: float) -> float:
        if self.dist_type == DistributionType.GAUSSIAN:
            mu, sigma = self.parameters.get("mean", 0.0), self.parameters.get("std", 1.0)
            if sigma == 0:
                return 1.0 if x == mu else 0.0
            return (1.0 / (sigma * math.sqrt(2 * math.pi))) * math.exp(-0.5 * ((x - mu) / sigma) ** 2)
        elif self.dist_type == DistributionType.DISCRETE:
            if self.support and x in self.support:
                idx = self.support.index(x)
                probs = self.parameters.get("probs", [])
                return probs[idx] if idx < len(probs) else 0.0
            return 0.0
        elif self.dist_type == DistributionType.UNIFORM:
            a, b = self.parameters.get("a", 0.0), self.parameters.get("b", 1.0)
            return 1.0 / (b - a) if a <= x <= b else 0.0
        elif self.dist_type == DistributionType.BERNOULLI:
            if x == 1.0:
                return self.parameters.get("p", 0.5)
            elif x == 0.0:
                return 1 - self.parameters.get("p", 0.5)
            return 0.0
        return 0.0

    def sample(self) -> float:
        import random
        if self.dist_type == DistributionType.GAUSSIAN:
            return random.gauss(self.parameters.get("mean", 0.0), self.parameters.get("std", 1.0))
        elif self.dist_type == DistributionType.DISCRETE:
            if self.support and self.parameters.get("probs"):
                return random.choices(self.support, weights=self.parameters["probs"])[0]
        elif self.dist_type == DistributionType.UNIFORM:
            return random.uniform(self.parameters.get("a", 0.0), self.parameters.get("b", 1.0))
        elif self.dist_type == DistributionType.BERNOULLI:
            return 1.0 if random.random() < self.parameters.get("p", 0.5) else 0.0
        return 0.0

    def entropy(self) -> float:
        if self.dist_type == DistributionType.GAUSSIAN:
            sigma = self.parameters.get("std", 1.0)
            return 0.5 * math.log(2 * math.pi * math.e * sigma ** 2) if sigma > 0 else 0.0
        elif self.dist_type == DistributionType.DISCRETE:
            return -sum(p * math.log(p) for p in self.parameters.get("probs", []) if p > 0)
        elif self.dist_type == DistributionType.BERNOULLI:
            p = self.parameters.get("p", 0.5)
            return -(p * math.log(p) + (1 - p) * math.log(1 - p)) if 0 < p < 1 else 0.0
        return 0.0


@dataclass
class ConditionalProbability:
    """Conditional probability P(B|A)."""
    cause: str
    effect: str
    prob_given_true: float
    prob_given_false: float
    base_rate: float
    confidence: float = 1.0

    def compute(self, cause_true: bool) -> float:
        return self.prob_given_true if cause_true else self.prob_given_false


@dataclass
class InferenceResult:
    """Result of a probabilistic inference."""
    query_variable: str
    value: float
    probability: float
    distribution: Optional[ProbabilityDistribution]
    explanation: str = ""
    method: str = "direct"
    certainty: float = 1.0


class ProbabilisticReasoner:
    """Reasoning engine that operates under uncertainty."""

    def __init__(self):
        self._variables: Dict[str, ProbabilityDistribution] = {}
        self._conditionals: Dict[str, ConditionalProbability] = {}
        self._evidence: Dict[str, float] = {}
        self._inference_log: List[InferenceResult] = []

    def add_variable(self, distribution: ProbabilityDistribution):
        self._variables[distribution.name] = distribution

    def add_gaussian(self, name: str, mean: float, std: float):
        self.add_variable(ProbabilityDistribution(name=name, dist_type=DistributionType.GAUSSIAN, parameters={"mean": mean, "std": std}))

    def add_discrete(self, name: str, values: List[float], probs: List[float]):
        self.add_variable(ProbabilityDistribution(name=name, dist_type=DistributionType.DISCRETE, parameters={"probs": probs}, support=values))

    def add_bernoulli(self, name: str, p: float):
        self.add_variable(ProbabilityDistribution(name=name, dist_type=DistributionType.BERNOULLI, parameters={"p": p}))

    def add_uniform(self, name: str, a: float, b: float):
        self.add_variable(ProbabilityDistribution(name=name, dist_type=DistributionType.UNIFORM, parameters={"a": a, "b": b}))

    def get_variable(self, name: str) -> Optional[ProbabilityDistribution]:
        return self._variables.get(name)

    def add_conditional(self, cause: str, effect: str, prob_given_true: float,
                        prob_given_false: float, base_rate: float):
        key = f"{cause}->{effect}"
        self._conditionals[key] = ConditionalProbability(
            cause=cause, effect=effect,
            prob_given_true=prob_given_true, prob_given_false=prob_given_false,
            base_rate=base_rate,
        )

    def get_conditional(self, cause: str, effect: str) -> Optional[ConditionalProbability]:
        return self._conditionals.get(f"{cause}->{effect}")

    def set_evidence(self, variable: str, value: float):
        self._evidence[variable] = value

    def clear_evidence(self):
        self._evidence.clear()

    def infer(self, query: str) -> InferenceResult:
        """Perform probabilistic inference for a query variable."""
        dist = self._variables.get(query)
        if dist is None:
            return InferenceResult(query_variable=query, value=0, probability=0, distribution=None, explanation=f"Variable '{query}' not found")

        # Start with prior
        prior_mean = dist.mean
        prior_std = dist.std

        # Update using evidence via Bayes-like computation
        posterior_mean = prior_mean
        posterior_variance = dist.variance
        evidence_used = []

        for ev_var, ev_val in self._evidence.items():
            cond = self.get_conditional(ev_var, query)
            if cond is not None:
                if ev_val > 0.5:
                    likelihood = cond.prob_given_true
                    posterior_mean = likelihood
                else:
                    likelihood = cond.prob_given_false
                    posterior_mean = likelihood
                posterior_variance *= (1 - cond.confidence * 0.3)
                evidence_used.append(f"{ev_var}={ev_val:.2f}")

        posterior_std = math.sqrt(max(0, posterior_variance))
        certainty = max(0, min(1, 1.0 - posterior_std))

        result = InferenceResult(
            query_variable=query, value=posterior_mean,
            probability=posterior_mean, distribution=dist,
            method="bayesian_update" if evidence_used else "prior",
            certainty=certainty,
            explanation=f"Prior mean={prior_mean:.3f}, posterior={posterior_mean:.3f}, evidence={evidence_used}",
        )
        self._inference_log.append(result)
        return result

    def expected_utility(self, action: str,
                         utilities: Dict[str, float]) -> float:
        """Compute expected utility of an action over all variables."""
        total = 0.0
        for var_name, dist in self._variables.items():
            if var_name in utilities:
                total += utilities[var_name] * dist.mean
        return total

    def maximum_a_posteriori(self, candidates: List[str]) -> Tuple[str, float]:
        """Find the candidate with highest posterior probability."""
        best, best_val = candidates[0], -float('inf')
        for c in candidates:
            dist = self._variables.get(c)
            val = dist.mean if dist else 0.0
            if val > best_val:
                best, best_val = c, val
        return best, best_val

    def get_all_variables(self) -> Dict[str, ProbabilityDistribution]:
        return dict(self._variables)

    def get_inference_history(self) -> List[InferenceResult]:
        return list(self._inference_log)

    def __repr__(self) -> str:
        return f"ProbabilisticReasoner(variables={len(self._variables)}, conditionals={len(self._conditionals)})"