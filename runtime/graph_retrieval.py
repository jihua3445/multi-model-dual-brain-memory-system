"""Bounded, typed graph retrieval for person-event memory.

Nodes are opaque ids ("p:小林", "e:E001", "t:work", "c:commitment").
Edges are typed: participates, co_presence, interaction, causes, before,
same_topic, commitment, conflict. Retrieval is 1-2 hops with decay and a
budget, so a high-degree hub cannot flood the context.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str
    weight: float = 1.0
    provenance: str = "direct"
    confidence: float = 1.0


@dataclass(frozen=True)
class GraphHit:
    node: str
    path: Tuple[str, ...]
    hop: int
    score: float
    kinds: Tuple[str, ...]


class MemoryGraph:
    def __init__(self) -> None:
        self._adj: Dict[str, List[Edge]] = {}

    def add_edge(self, e: Edge) -> None:
        self._adj.setdefault(e.src, []).append(e)

    def edges_from(self, node: str) -> List[Edge]:
        return list(self._adj.get(node, ()))

    def activate(self, cues: Sequence[str], hops: int = 2, budget: int = 20,
                 decay: float = 0.5, allowed_kinds: Optional[Iterable[str]] = None,
                 allow_simulation: bool = False) -> List[GraphHit]:
        allowed = set(allowed_kinds) if allowed_kinds else None
        best: Dict[str, GraphHit] = {}
        frontier: List[Tuple[str, Tuple[str, ...], Tuple[str, ...], float]] = [
            (c, (c,), (), 1.0) for c in cues
        ]
        for depth in range(1, max(0, hops) + 1):
            nxt = []
            for node, path, kinds, score in frontier:
                for e in self.edges_from(node):
                    if e.dst in path:
                        continue
                    if allowed is not None and e.kind not in allowed:
                        continue
                    if not allow_simulation and e.kind == "simulation":
                        continue
                    s = score * max(0.0, min(1.0, e.weight)) * (decay ** depth) \
                        * max(0.0, min(1.0, e.confidence))
                    npath = path + (e.dst,)
                    nkinds = kinds + (e.kind,)
                    prev = best.get(e.dst)
                    if prev is None or s > prev.score:
                        best[e.dst] = GraphHit(e.dst, npath, depth, round(s, 4), nkinds)
                    nxt.append((e.dst, npath, nkinds, s))
            frontier = nxt
        hits = sorted(best.values(), key=lambda h: (-h.score, h.hop, h.node))
        return hits[:max(0, budget)]


def from_events(events: Iterable) -> MemoryGraph:
    """Build person/event/topic/commitment nodes from Event objects."""
    g = MemoryGraph()
    for ev in events:
        enode = f"e:{ev.event_id}"
        for pid in getattr(ev, "person_ids", ()):
            pnode = f"p:{pid}"
            g.add_edge(Edge(pnode, enode, "participates", 0.9))
            g.add_edge(Edge(enode, pnode, "participates", 0.9))
        for topic in getattr(ev, "topics", ()):
            tnode = f"t:{topic}"
            g.add_edge(Edge(tnode, enode, "same_topic", 0.6))
            g.add_edge(Edge(enode, tnode, "same_topic", 0.6))
        if getattr(ev, "open_commitment", False):
            cnode = f"c:{ev.event_id}"
            g.add_edge(Edge(enode, cnode, "commitment", 1.0))
    return g
