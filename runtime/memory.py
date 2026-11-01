"""Minimal in-memory retriever + context compiler driven by state_params.

Pure stdlib. No model calls. It demonstrates that the runtime parameters
actually change what is retrieved and what enters the ContextPacket.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from state_params import StateParams, SystemState
from ledger import EvidenceLedger, ForgettingPolicy, VersionChain
from graph_retrieval import MemoryGraph

SOURCE_RELIABILITY = {
    "direct": 1.0,
    "document": 0.8,
    "relay": 0.6,
    "inference": 0.4,
    "model": 0.2,
}

_UNTRUSTED_MARKERS = ("ignore previous", "ignore all previous", "system prompt", "忽略之前", "忽略以上")


def _canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(obj) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def tokenize(text: str) -> Set[str]:
    """ASCII words + CJK characters. Good enough for a reference demo."""
    return set(re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]", text.lower()))


def is_untrusted(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in _UNTRUSTED_MARKERS)


@dataclass(frozen=True)
class Event:
    event_id: str
    text: str
    person_ids: Tuple[str, ...] = ()
    topics: Tuple[str, ...] = ()
    salience: float = 0.5
    ts: float = 0.0
    source: str = "direct"
    open_commitment: bool = False
    claim_id: Optional[str] = None

    def age_days(self, now: float) -> float:
        return max(0.0, (now - self.ts) / 86400.0)


@dataclass(frozen=True)
class Candidate:
    event: Event
    score: float
    reason: str
    age_days: float
    verified: bool = False
    claim_id: Optional[str] = None
    conflict: bool = False
    confidence: float = 1.0
    suppressed: bool = False


@dataclass(frozen=True)
class ContextPacket:
    state_view: Dict
    state_params_ref: Dict
    who: Dict
    experiences: List[Dict]
    omitted: Dict
    commitments: List[Dict]
    uncertainties: List[Dict]
    budget: Dict
    packet_hash: str

    def to_dict(self) -> Dict:
        d = asdict(self)
        d.pop("packet_hash", None)
        return d


class SuppressionState:
    """Reversible, time-limited accessibility penalty; never touches evidence."""

    def __init__(self, factor: float = 0.85) -> None:
        self.factor_value = factor
        self._until: Dict[str, float] = {}

    def suppress(self, event_ids: Sequence[str], now: float, ttl: float = 3.0) -> None:
        """ttl is in the same logical units as now (turns in tests, seconds in prod)."""
        for eid in event_ids:
            self._until[eid] = max(self._until.get(eid, 0.0), now + ttl)

    def factor(self, event_id: str, now: float) -> float:
        until = self._until.get(event_id)
        if until is None or now >= until:
            self._until.pop(event_id, None)
            return 1.0
        return self.factor_value

    def is_suppressed(self, event_id: str, now: float) -> bool:
        return self.factor(event_id, now) < 1.0


class MemoryStore:
    def __init__(self, events: Optional[Iterable[Event]] = None) -> None:
        self._events: List[Event] = list(events or [])

    def add(self, event: Event) -> None:
        self._events.append(event)

    def all(self) -> List[Event]:
        return list(self._events)

    def commitments(self) -> List[Event]:
        return [e for e in self._events if e.open_commitment]


def _source_floor(strictness: float) -> float:
    if strictness >= 0.7:
        return 0.65
    if strictness >= 0.5:
        return 0.45
    return 0.0


def score_event(event: Event, query: str, query_person: Optional[str], query_topics: Sequence[str],
                now: float, params: StateParams) -> Optional[Tuple[float, str]]:
    if event.source not in SOURCE_RELIABILITY:
        return None
    if SOURCE_RELIABILITY[event.source] < _source_floor(params.audit.source_strictness):
        return None

    q = tokenize(query)
    e = tokenize(event.text)
    overlap = len(q & e) / max(1, len(q))
    person = 1.0 if query_person and query_person in event.person_ids else 0.0
    topics = set(query_topics)
    topic = 1.0 if topics and topics & set(event.topics) else 0.0
    recency = math.exp(-event.age_days(now) / 30.0)

    person_weight = 0.20
    raw = (
        0.45 * overlap
        + person_weight * person
        + 0.15 * topic
        + 0.10 * recency
        + 0.10 * event.salience
    )
    rel = SOURCE_RELIABILITY[event.source]
    score = raw * rel
    reason = f"overlap={overlap:.2f};person={person:.0f};topic={topic:.0f};rel={rel:.1f}"
    return score, reason


def retrieve(store: MemoryStore, query: str, params: StateParams, now: float,
             query_person: Optional[str] = None,
             query_topics: Sequence[str] = (),
             ledger: Optional[EvidenceLedger] = None,
             association: Optional[MemoryGraph] = None,
             suppression: Optional[SuppressionState] = None) -> List[Candidate]:
    pool = max(1, int(round(params.retrieval.top_k * params.retrieval.candidate_mult)))
    scored: List[Candidate] = []
    for ev in store.all():
        got = score_event(ev, query, query_person, query_topics, now, params)
        if got is None:
            continue
        score, reason = got
        claim = ev.claim_id or ev.event_id
        conflict = bool(ledger.conflicts(claim)) if ledger else False
        noise = params.retrieval.retrieval_noise
        sup = suppression.factor(ev.event_id, now) if suppression else 1.0
        adjusted = (score * (1.0 - noise) + 0.5 * noise) * sup
        rel = SOURCE_RELIABILITY[ev.source]
        confidence = max(0.0, min(1.0, 1.0 - noise - 0.2 * (1.0 - rel)))
        scored.append(Candidate(ev, round(adjusted, 4), reason, round(ev.age_days(now), 2),
                                claim_id=claim, conflict=conflict,
                                confidence=round(confidence, 3),
                                suppressed=(sup < 1.0)))
    if association is not None:
        cues = []
        if query_person:
            cues.append(f"p:{query_person}")
        cues.extend(f"t:{t}" for t in query_topics)
        known = {c.event.event_id for c in scored}
        for hit in association.activate(cues, hops=2, budget=pool):
            if not hit.node.startswith("e:"):
                continue
            eid = hit.node[2:]
            if eid in known:
                continue
            ev = next((e for e in store.all() if e.event_id == eid), None)
            if ev is None or SOURCE_RELIABILITY[ev.source] < _source_floor(params.audit.source_strictness):
                continue
            claim = ev.claim_id or ev.event_id
            scored.append(Candidate(ev, round(hit.score * 0.8, 4),
                                    f"assoc:{'>'.join(hit.path)}", round(ev.age_days(now), 2),
                                    claim_id=claim,
                                    conflict=bool(ledger.conflicts(claim)) if ledger else False,
                                    confidence=0.6))
    scored.sort(key=lambda c: (-c.score, c.event.event_id))
    top = scored[:pool]
    verify_n = int(math.ceil(len(top) * params.audit.verify_ratio))
    return [
        Candidate(c.event, c.score, c.reason, c.age_days, verified=(i < verify_n),
                  claim_id=c.claim_id, conflict=c.conflict, confidence=c.confidence,
                  suppressed=c.suppressed)
        for i, c in enumerate(top)
    ]


def encode_gate(event: Event, params: StateParams) -> bool:
    """Accept if salient enough, or if it is an explicit/open commitment."""
    return event.salience >= params.memory.encode_threshold or event.open_commitment


def compile_packet(store: MemoryStore, query: str, params: StateParams, now: float,
                   person: Optional[Dict] = None,
                   query_topics: Sequence[str] = (),
                   state: Optional[SystemState] = None,
                   ledger: Optional[EvidenceLedger] = None,
                   versions: Optional[Dict[str, VersionChain]] = None,
                   forgetting: Optional[ForgettingPolicy] = None,
                   association: Optional[MemoryGraph] = None,
                   suppression: Optional[SuppressionState] = None) -> ContextPacket:
    candidates = retrieve(store, query, params, now,
                          query_person=(person or {}).get("person_id"),
                          query_topics=query_topics, ledger=ledger,
                          association=association, suppression=suppression)
    slots = params.context.slots
    max_chars = max(60, params.context.token_budget // max(1, slots) // 2)

    selected = list(candidates[:slots])
    if ledger:
        required = []
        for claim in {c.claim_id for c in candidates if c.conflict}:
            for value, ids in ledger.evidence_values(claim).items():
                if any(x.event.event_id in ids for x in selected):
                    continue
                best = next((c for c in candidates if c.event.event_id in ids), None)
                if best is not None:
                    required.append(best)
        for req in required:
            if any(x.event.event_id == req.event.event_id for x in selected):
                continue
            replaceable = [i for i, x in enumerate(selected)
                           if x.event.event_id not in {r.event.event_id for r in required}
                           and not x.event.open_commitment and not x.conflict]
            if replaceable:
                idx = min(replaceable, key=lambda i: selected[i].score)  # replace the lowest-score non-conflict item
                selected[idx] = req
            elif len(selected) < slots:
                selected.append(req)
        selected.sort(key=lambda c: (-c.score, c.event.event_id))

    selected_ids = {c.event.event_id for c in selected}
    omitted_candidates = [c for c in candidates if c.event.event_id not in selected_ids]
    if suppression:
        selected_people = {p for c in selected for p in c.event.person_ids}
        selected_topics = {t for c in selected for t in c.event.topics}
        competitors = [c.event.event_id for c in omitted_candidates
                       if (set(c.event.person_ids) & selected_people)
                       or (set(c.event.topics) & selected_topics)]
        if competitors:
            suppression.suppress(competitors, now, ttl=3.0)
    omitted = {
        "count": len(omitted_candidates),
        "topics": sorted({t for c in omitted_candidates for t in c.event.topics}),
        "event_ids": [c.event.event_id for c in omitted_candidates[:20]],
    }

    experiences = []
    for c in selected:
        text = c.event.text
        if len(text) > max_chars:
            text = text[: max_chars - 1] + "…"
        claim_id = c.event.claim_id or c.event.event_id
        chain = (versions or {}).get(claim_id)
        current = chain.current() if chain else None
        stale = bool(current and c.event.event_id not in current.evidence_ids)
        experiences.append({
            "event_id": c.event.event_id,
            "claim_id": claim_id,
            "summary": text,
            "source": c.event.source,
            "score": c.score,
            "verified": c.verified,
            "untrusted": is_untrusted(c.event.text),
            "reason": c.reason,
            "evidence_count": ledger.evidence_count(claim_id) if ledger else None,
            "interpretation": current.content if current else None,
            "version_id": current.version_id if current else None,
            "stale": stale,
            "has_conflict": bool(ledger.conflicts(claim_id)) if ledger else False,
            "cold": forgetting.is_cold(c.event.event_id) if forgetting else False,
            "confidence": c.confidence,
            "suppressed": c.suppressed,
        })

    commitments = []
    if params.context.pin_commitments:
        for ev in store.commitments()[:3]:
            commitments.append({
                "event_id": ev.event_id,
                "content": ev.text[:max_chars],
                "status": "open",
            })

    uncertainties = []
    if not candidates:
        uncertainties.append({"question": "没有可用候选", "evidence_needed": True})
    elif any(not c.verified for c in candidates[:slots]):
        uncertainties.append({"question": "部分候选未核验来源", "evidence_needed": True})
    if any(x.get("stale") for x in experiences):
        uncertainties.append({"question": "存在旧版本证据，需核对当前解释", "evidence_needed": True})
    if any(x.get("has_conflict") for x in experiences):
        uncertainties.append({"question": "存在冲突证据，已并列展示", "evidence_needed": True})

    if state is None:
        state_view = {"goal_pressure": 0.0, "impact_gap": 0.0}
    else:
        s = state.normalized()
        state_view = {
            "goal_pressure": s.goal_pressure,
            "relationship_strain": s.relationship_strain,
            "resource_load": s.resource_load,
            "uncertainty": s.uncertainty,
            "unresolved_commitments": s.unresolved_commitments,
            "impact_gap": s.impact_gap(),
        }
    # state_view is intentionally small; the caller fills it from SystemState.
    packet = {
        "state_view": state_view,
        "state_params_ref": {
            "schema_version": params.schema_version,
            "params_version": params.params_version,
            "state_hash": params.state_hash,
            "params_hash": params.params_hash,
        },
        "who": person or {},
        "experiences": experiences,
        "omitted": omitted,
        "commitments": commitments,
        "uncertainties": uncertainties,
        "budget": {
            "slots": slots,
            "header_tokens": 300,
            "slot_tokens": max(300, params.context.token_budget - 300),
            "tokens": params.context.token_budget,
            "max_chars_per_experience": max_chars,
        },
    }
    return ContextPacket(
        state_view=packet["state_view"],
        state_params_ref=packet["state_params_ref"],
        who=packet["who"],
        experiences=packet["experiences"],
        omitted=packet["omitted"],
        commitments=packet["commitments"],
        uncertainties=packet["uncertainties"],
        budget=packet["budget"],
        packet_hash=_hash(packet),
    )
