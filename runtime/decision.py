"""Memory-driven choice: precedents, arbitration, and skill vs recall.

No hormones. A precedent is (situation, action, outcome); it changes the
expected value of an option. Skill execution is separate from recall confidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


@dataclass(frozen=True)
class Option:
    name: str
    prior_value: float = 0.0
    risk: float = 0.0


@dataclass(frozen=True)
class Precedent:
    event_id: str
    similarity: float
    outcome: float
    salience: float = 0.5
    source_reliability: float = 1.0
    conflict: bool = False


def precedent_value(base: float, precedents: Sequence[Precedent],
                    alpha: float = 0.5) -> float:
    """Weighted update of an option's value from retrieved precedents.

    w = similarity * salience * reliability * (0.5 if conflict else 1)
    V = base + alpha * sum(w * (outcome - base)) / sum(w)
    """
    num = 0.0
    den = 0.0
    for p in precedents:
        w = (clamp(p.similarity, 0, 1) * clamp(p.salience, 0, 1)
             * clamp(p.source_reliability, 0, 1))
        if p.conflict:
            w *= 0.5
        num += w * (clamp(p.outcome, -1, 1) - base)
        den += w
    if den <= 0:
        return clamp(base, -1, 1)
    return clamp(base + alpha * num / max(1.0, den), -1, 1)


def choose(options: Sequence[Option], uncertainty: float, resource_load: float,
           habit_confidence: float, stakes: float) -> str:
    """Return 'habit' or 'deliberate'. The caller still decides the option."""
    if (habit_confidence >= 0.7 and stakes < 0.4 and uncertainty < 0.4
            and resource_load > 0.7):
        return "habit"
    return "deliberate"


def rank(options: Sequence[Option], uncertainty: float) -> List[Option]:
    """Deliberate ranking: value minus risk scaled by uncertainty."""
    return sorted(options, key=lambda o: (-(o.prior_value - o.risk * uncertainty), o.name))


def can_execute(practice: float, recall_confidence: float, threshold: float = 0.6) -> bool:
    """Skill execution depends on practice, not on how confidently it is recalled."""
    return practice >= threshold
