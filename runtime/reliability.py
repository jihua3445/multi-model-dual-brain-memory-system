"""Claim-level source reliability.

Four inputs:
  * source_tier: direct 1.0, document 0.8, relay 0.6, inference 0.4, model 0.2
  * verifiability: can this claim be independently checked?
  * history: Laplace-smoothed rate of past claims that were verified/contradicted
  * consistency: 1.0 consistent, 0.5 when conflicting with other evidence

Reliability is a prior, not truth. It decides whether repeated recall may
stabilise a memory; it does not decide whether the claim is true.
"""
from __future__ import annotations

from dataclasses import dataclass

TIER_PRIOR = {
    "direct": 1.0,
    "document": 0.8,
    "relay": 0.6,
    "inference": 0.4,
    "model": 0.2,
}


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(v)))


def history_score(verified: int, contradicted: int) -> float:
    """Laplace-smoothed accuracy; no data -> 0.5, not 1.0."""
    v = max(0, int(verified))
    c = max(0, int(contradicted))
    return (v + 1.0) / (v + c + 2.0)


def reliability(source_tier: float, verifiability: float,
                verified: int = 0, contradicted: int = 0,
                consistency: float = 1.0) -> float:
    return clamp(
        0.15
        + 0.25 * clamp(source_tier)
        + 0.20 * clamp(verifiability)
        + 0.20 * history_score(verified, contradicted)
        + 0.20 * clamp(consistency)
    )


@dataclass
class SourceHistory:
    verified: int = 0
    contradicted: int = 0

    def record(self, correct: bool) -> None:
        if correct:
            self.verified += 1
        else:
            self.contradicted += 1

    @property
    def score(self) -> float:
        return history_score(self.verified, self.contradicted)
