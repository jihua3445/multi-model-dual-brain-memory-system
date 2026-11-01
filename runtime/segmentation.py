"""Event segmentation from a percept stream.

Boundary rule (section 5.1.1):
  boundary = precision-weighted |observed - expected| > theta_pe
             or topic/person changed
             or gap > theta_gap
             or duration > theta_max

No model calls. The point is to make "segment by prediction error" executable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from memory import Event


@dataclass(frozen=True)
class Percept:
    text: str
    ts: float
    person_ids: Tuple[str, ...] = ()
    topics: Tuple[str, ...] = ()
    expected: float = 0.0
    observed: float = 0.0
    precision: float = 1.0
    salience: float = 0.5
    source: str = "direct"
    open_commitment: bool = False


@dataclass(frozen=True)
class Segment:
    percepts: Tuple[Percept, ...]
    start: float
    end: float
    reason: str

    def to_event(self, event_id: str, claim_id: Optional[str] = None) -> Event:
        people: List[str] = []
        topics: List[str] = []
        for p in self.percepts:
            for x in p.person_ids:
                if x not in people:
                    people.append(x)
            for x in p.topics:
                if x not in topics:
                    topics.append(x)
        return Event(
            event_id=event_id,
            text=" ".join(p.text for p in self.percepts),
            person_ids=tuple(people),
            topics=tuple(topics),
            salience=max(p.salience for p in self.percepts),
            ts=self.start,
            source=self.percepts[0].source,
            open_commitment=any(p.open_commitment for p in self.percepts),
            claim_id=claim_id,
        )


def _changed(a: Sequence[str], b: Sequence[str]) -> bool:
    if not a or not b:
        return False
    return not (set(a) & set(b))


def segment(percepts: Sequence[Percept], theta_pe: float = 0.5,
            theta_gap: float = 120.0, theta_max: float = 600.0) -> List[Segment]:
    if not percepts:
        return []

    segments: List[Segment] = []
    current: List[Percept] = [percepts[0]]
    start = percepts[0].ts
    reason = "start"

    for p in percepts[1:]:
        last = current[-1]
        surprise = p.precision * abs(p.observed - p.expected)
        gap = p.ts - last.ts
        duration = p.ts - start
        why = None
        if surprise > theta_pe:
            why = "prediction_error"
        elif _changed(p.topics, last.topics):
            why = "topic_change"
        elif _changed(p.person_ids, last.person_ids):
            why = "person_change"
        elif gap > theta_gap:
            why = "time_gap"
        elif duration > theta_max:
            why = "max_duration"

        if why:
            segments.append(Segment(tuple(current), start, last.ts, reason))
            current = [p]
            start = p.ts
            reason = why
        else:
            current.append(p)

    segments.append(Segment(tuple(current), start, current[-1].ts, reason))
    return segments
