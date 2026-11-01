"""Relationship memory as threshold adjustment, not fact recall.

A relationship is updated by precedents: reliability, salience, and whether the
event was positive or negative. Negative precedents weigh more (negativity
bias), conflict is downweighted, and a single event cannot rewrite a trait.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set

DIMENSIONS = ("familiarity", "closeness", "trust", "cooperation", "commitment", "boundary")


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


@dataclass(frozen=True)
class RelationshipEvidence:
    event_id: str
    dimension: str
    delta: float  # -1..1
    reliability: float = 1.0
    salience: float = 0.5
    conflict: bool = False
    interaction_weight: float = 1.0  # co-presence 0.3, actual interaction 1.0


@dataclass
class Relationship:
    values: Dict[str, float] = field(default_factory=lambda: {d: 0.0 for d in DIMENSIONS})
    evidence: Dict[str, Set[str]] = field(default_factory=lambda: {d: set() for d in DIMENSIONS})

    def update(self, ev: RelationshipEvidence, eta: float = 0.1,
               negativity_bias: float = 1.5) -> float:
        if ev.dimension not in DIMENSIONS:
            raise ValueError(f"unknown dimension: {ev.dimension}")
        if ev.event_id in self.evidence[ev.dimension]:
            return self.values[ev.dimension]  # idempotent: one event, one evidence
        w = (clamp(ev.reliability, 0, 1) * clamp(ev.salience, 0, 1)
             * clamp(ev.interaction_weight, 0, 1))
        if ev.conflict:
            w *= 0.5
        delta = clamp(ev.delta, -1, 1)
        if delta < 0:
            delta *= negativity_bias
        old = self.values.get(ev.dimension, 0.0)
        new = clamp(old + eta * w * delta, -1, 1)
        self.values[ev.dimension] = new
        self.evidence[ev.dimension].add(ev.event_id)
        return new

    def evidence_count(self, dimension: str) -> int:
        return len(self.evidence.get(dimension, set()))

    def valence(self) -> float:
        """Emotional direction: liking/closeness (+) vs dislike/hatred (-).

        Trust is an objective judgment about the person, not an emotion; it must
        not be averaged into valence.
        """
        return clamp(self.values.get("closeness", 0.0), -1, 1)

    def intensity(self) -> float:
        """Emotional intensity: |affect|. Trustworthiness is not emotional intensity."""
        return clamp(abs(self.values.get("closeness", 0.0)), 0, 1)

    def can_commit(self, threshold: float = 0.5, capacity: float = 1.0,
                   cost: float = 0.5) -> bool:
        """Commitment requires trust above threshold and capacity above cost."""
        return self.values.get("trust", 0.0) >= threshold and capacity >= cost
