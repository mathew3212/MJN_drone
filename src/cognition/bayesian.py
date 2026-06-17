"""
Bayesian Belief Network
========================

Implements Bayesian belief networks for maintaining and updating
beliefs about the world as new evidence arrives. Supports:
- Bayesian belief nodes with priors
- Evidence-based belief updates (Bayes' rule)
- Belief propagation
- Causal reasoning
- Belief persistence and decay
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set


@dataclass
class Belief:
    """A belief about a variable with prior and posterior probability."""
    variable: str
    prior: float = 0.5
    posterior: float = 0.5
    variance: float = 0.25
    observations: int = 0
    last_updated: float = field(default_factory=time.time)
    source: str = "prior"
    explanation: str = ""

    @property
    def confidence(self) -> float:
        return 1.0 - min(1.0, self.variance * 4)

    @property
    def certainty(self) -> float:
        return abs(self.posterior - 0.5) * 2

    def is_certain(self, threshold: float = 0.9) -> bool:
        return self.posterior > threshold or self.posterior < (1 - threshold)


@dataclass
class Evidence:
    """An observation that can update beliefs."""
    variable: str
    value: float
    reliability: float = 1.0
    timestamp: float = field(default_factory=time.time)
    source: str = "sensor"
    explanation: str = ""


@dataclass
class BeliefUpdate:
    """Record of how a belief was updated."""
    variable: str
    prior: float
    posterior: float
    evidence_used: List[str]
    likelihood: float
    timestamp: float = field(default_factory=time.time)
    explanation: str = ""

    @property
    def change(self) -> float:
        return self.posterior - self.prior


@dataclass
class BeliefNode:
    """A node in the belief network."""
    name: str
    belief: Belief
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    conditional_table: Dict[str, float] = field(default_factory=dict)
    decay_rate: float = 0.99


class BayesianBeliefNetwork:
    """
    Bayesian belief network for maintaining probabilistic beliefs
    about the world state.
    """

    def __init__(self):
        self._nodes: Dict[str, BeliefNode] = {}
        self._edges: List[Tuple[str, str]] = []
        self._update_history: List[BeliefUpdate] = []
        self._evidence_buffer: List[Evidence] = []

    # ==========================================
    # Network Construction
    # ==========================================

    def add_belief(self, variable: str, prior: float = 0.5,
                   variance: float = 0.25) -> str:
        """Add a belief node with a prior probability."""
        self._nodes[variable] = BeliefNode(
            name=variable,
            belief=Belief(variable=variable, prior=prior, posterior=prior, variance=variance),
        )
        return variable

    def add_edge(self, parent: str, child: str,
                 conditional_table: Optional[Dict[str, float]] = None):
        """Add a directed edge (parent influences child)."""
        if parent not in self._nodes:
            self.add_belief(parent)
        if child not in self._nodes:
            self.add_belief(child)
        self._nodes[parent].children.append(child)
        self._nodes[child].parents.append(parent)
        if conditional_table:
            self._nodes[child].conditional_table = conditional_table
        self._edges.append((parent, child))

    def get_belief(self, variable: str) -> Optional[Belief]:
        node = self._nodes.get(variable)
        return node.belief if node else None

    def get_all_beliefs(self) -> Dict[str, Belief]:
        return {name: node.belief for name, node in self._nodes.items()}

    # ==========================================
    # Bayesian Updates
    # ==========================================

    def update_with_evidence(self, evidence: Evidence) -> BeliefUpdate:
        """Update beliefs using Bayesian rule with new evidence."""
        node = self._nodes.get(evidence.variable)
        if node is None:
            self.add_belief(evidence.variable)
            node = self._nodes[evidence.variable]

        prior = node.belief.posterior
        likelihood = evidence.value * evidence.reliability

        # Bayes' rule: P(H|E) = P(E|H) * P(H) / P(E)
        p_e = likelihood * prior + (1 - likelihood) * (1 - prior)
        if p_e > 0:
            posterior = (likelihood * prior) / p_e
        else:
            posterior = prior

        # Apply reliability
        posterior = prior + evidence.reliability * (posterior - prior)

        # Clamp to [0.01, 0.99] to avoid certainty
        posterior = max(0.01, min(0.99, posterior))

        # Update variance (decreases with more observations)
        node.belief.observations += 1
        variance_reduction = 1.0 / (1.0 + node.belief.observations * 0.1)
        node.belief.variance *= variance_reduction

        node.belief.prior = prior
        node.belief.posterior = posterior
        node.belief.last_updated = time.time()

        update = BeliefUpdate(
            variable=evidence.variable,
            prior=prior,
            posterior=posterior,
            evidence_used=[evidence.source],
            likelihood=likelihood,
            explanation=f"Evidence '{evidence.source}': P={evidence.value:.3f}, "
                        f"reliability={evidence.reliability:.3f}, "
                        f"prior={prior:.3f} -> posterior={posterior:.3f}",
        )
        self._update_history.append(update)

        # Propagate to children
        self._propagate(evidence.variable, posterior)

        return update

    def observe(self, variable: str, value: float,
                reliability: float = 1.0, source: str = "observation"):
        """Convenience method: observe evidence and update."""
        evidence = Evidence(variable=variable, value=value, reliability=reliability, source=source)
        return self.update_with_evidence(evidence)

    def batch_update(self, evidences: List[Evidence]) -> List[BeliefUpdate]:
        """Process multiple pieces of evidence."""
        updates = []
        for ev in evidences:
            updates.append(self.update_with_evidence(ev))
        return updates

    def _propagate(self, source_variable: str, source_posterior: float):
        """Propagate belief changes to child nodes."""
        node = self._nodes.get(source_variable)
        if node is None:
            return

        for child_name in node.children:
            child = self._nodes.get(child_name)
            if child is None:
                continue

            # Use conditional probability table if available
            cpt = child.conditional_table
            if cpt:
                parent_true_key = f"{source_variable}_true"
                parent_false_key = f"{source_variable}_false"
                p_true = cpt.get(parent_true_key, 0.5)
                p_false = cpt.get(parent_false_key, 0.5)
                p_child = source_posterior * p_true + (1 - source_posterior) * p_false
                child.belief.posterior = max(0.01, min(0.99, p_child))

    # ==========================================
    # Belief Queries
    # ==========================================

    def query(self, variable: str) -> Optional[Belief]:
        """Query the current belief about a variable."""
        return self.get_belief(variable)

    def query_most_uncertain(self) -> Optional[str]:
        """Find the variable with the most uncertainty."""
        if not self._nodes:
            return None
        return max(self._nodes.keys(),
                   key=lambda v: self._nodes[v].belief.variance)

    def query_most_certain(self) -> Optional[str]:
        """Find the variable we are most certain about."""
        if not self._nodes:
            return None
        return min(self._nodes.keys(),
                   key=lambda v: self._nodes[v].belief.variance)

    def get_causal_chain(self, cause: str, effect: str) -> Optional[List[str]]:
        """Find causal path from cause to effect using BFS."""
        if cause not in self._nodes or effect not in self._nodes:
            return None

        visited = {cause}
        queue = [(cause, [cause])]

        while queue:
            current, path = queue.pop(0)
            if current == effect:
                return path
            node = self._nodes.get(current)
            if node:
                for child in node.children:
                    if child not in visited:
                        visited.add(child)
                        queue.append((child, path + [child]))
        return None

    # ==========================================
    # Belief Maintenance
    # ==========================================

    def decay_beliefs(self, time_factor: float = 1.0):
        """Apply time-based decay to all beliefs (regression to prior)."""
        for node in self._nodes.values():
            decay = node.decay_rate ** time_factor
            node.belief.posterior = (
                node.belief.prior + decay * (node.belief.posterior - node.belief.prior)
            )
            node.belief.variance = min(0.25, node.belief.variance * (1 + 0.01 * time_factor))

    def reset_belief(self, variable: str, new_prior: float = 0.5):
        """Reset a belief to a new prior."""
        if variable in self._nodes:
            self._nodes[variable].belief = Belief(
                variable=variable, prior=new_prior, posterior=new_prior
            )

    def get_update_history(self, variable: Optional[str] = None,
                           last_n: int = 50) -> List[BeliefUpdate]:
        history = self._update_history
        if variable:
            history = [u for u in history if u.variable == variable]
        return history[-last_n:]

    def get_network_summary(self) -> Dict[str, Any]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "total_observations": sum(
                n.belief.observations for n in self._nodes.values()
            ),
            "avg_variance": (
                sum(n.belief.variance for n in self._nodes.values()) / len(self._nodes)
                if self._nodes else 0
            ),
            "total_updates": len(self._update_history),
        }

    def __repr__(self) -> str:
        return f"BayesianBeliefNetwork(nodes={len(self._nodes)}, edges={len(self._edges)})"