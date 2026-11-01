"""Counterfactual simulation with a hard write boundary.

A simulation may generate candidate scenarios, but it is never a fact:
  * source is always "simulation";
  * it cannot be written to the event log;
  * it does not count as evidence;
  * only observed outcomes become events; only evidence can promote a
    hypothesis, and even then it stays a hypothesis.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class Episode:
    event_id: str
    elements: tuple


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    content: str
    assumptions: tuple
    confidence: float = 0.5
    source: str = "simulation"
    primitive_ids: tuple = ()

    @property
    def is_fact(self) -> bool:
        return False


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    content: str
    evidence_event_ids: tuple
    status: str = "hypothesis"


def simulate(seed_event_ids: Sequence[str], options: Sequence[str]) -> List[Scenario]:
    """Deterministic candidate generation; no model call."""
    out: List[Scenario] = []
    for i, opt in enumerate(options, start=1):
        out.append(Scenario(
            scenario_id=f"S{i}",
            content=f"如果选择 {opt}，可能出现的结果",
            assumptions=tuple(seed_event_ids),
            confidence=0.5,
        ))
    return out


def compose(episodes: Sequence[Episode], max_scenarios: int = 3) -> List[Scenario]:
    """Recombine elements from different episodes into future candidates.

    This is not consolidation: outputs are simulation-tagged and never facts.
    """
    if len(episodes) < 2:
        raise ValueError("compositional replay needs at least two episodes")
    out: List[Scenario] = []
    for i in range(min(max_scenarios, len(episodes) - 1)):
        a, b = episodes[i], episodes[i + 1]
        cut = max(1, len(a.elements) // 2)
        content = " + ".join(tuple(a.elements[:cut]) + tuple(b.elements[cut:]))
        out.append(Scenario(
            scenario_id=f"C{i + 1}",
            content=content,
            assumptions=(a.event_id, b.event_id),
            confidence=0.4,
            source="compositional_replay",
        ))
    return out


def can_write_as_fact(scenario: Scenario) -> bool:
    """Simulations are never facts, regardless of confidence."""
    return False


def to_hypothesis(scenario: Scenario, evidence_event_ids: Sequence[str],
                  hypothesis_id: str = "H1") -> Hypothesis:
    if not evidence_event_ids:
        raise ValueError("a hypothesis requires independent evidence")
    return Hypothesis(hypothesis_id, scenario.content, tuple(evidence_event_ids))
