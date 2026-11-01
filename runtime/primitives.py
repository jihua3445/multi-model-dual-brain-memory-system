"""Primitive library for compositional replay.

A primitive is a typed, reusable building block: person, place, action,
relation, goal. Composition fills slots by kind, so a place cannot be used
as a person. Outputs remain simulation-tagged and never become facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from simulation import Scenario

KINDS = ("person", "place", "action", "relation", "goal")


@dataclass(frozen=True)
class Primitive:
    kind: str
    pid: str
    value: str
    tags: Tuple[str, ...] = ()


class PrimitiveLibrary:
    def __init__(self) -> None:
        self._by_kind: Dict[str, List[Primitive]] = {k: [] for k in KINDS}

    def add(self, p: Primitive) -> None:
        if p.kind not in self._by_kind:
            raise ValueError(f"unknown primitive kind: {p.kind}")
        self._by_kind[p.kind].append(p)

    def query(self, kind: str, require_tags: Sequence[str] = ()) -> List[Primitive]:
        if kind not in self._by_kind:
            raise ValueError(f"unknown primitive kind: {kind}")
        need = set(require_tags)
        return [p for p in self._by_kind[kind] if need.issubset(set(p.tags))]

    def kinds(self) -> List[str]:
        return [k for k, v in self._by_kind.items() if v]


def compose_from_primitives(library: PrimitiveLibrary, slot_kinds: Sequence[str],
                            require_tags: Sequence[str] = (),
                            max_scenarios: int = 3) -> List[Scenario]:
    if not slot_kinds:
        raise ValueError("at least one slot is required")
    pools = {k: library.query(k, require_tags) for k in slot_kinds}
    for k, pool in pools.items():
        if not pool:
            raise ValueError(f"no primitive available for kind: {k}")
    n = min(max_scenarios, max(len(p) for p in pools.values()))
    out: List[Scenario] = []
    for i in range(n):
        chosen = [pools[k][(i + j) % len(pools[k])] for j, k in enumerate(slot_kinds)]
        out.append(Scenario(
            scenario_id=f"P{i + 1}",
            content=" | ".join(f"{p.kind}:{p.value}" for p in chosen),
            assumptions=tuple(p.pid for p in chosen),
            confidence=0.4,
            source="compositional_replay",
            primitive_ids=tuple(p.pid for p in chosen),
        ))
    return out
