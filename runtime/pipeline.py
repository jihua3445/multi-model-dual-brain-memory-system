"""End-to-end pipeline: event -> state/params -> retrieval/packet -> proposal -> ledger.

This is the glue that makes the four reference modules executable in one turn.
It is deliberately in-memory and model-free.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from constitution import ConstitutionStore, ConstitutiveProposal
from ledger import Evidence, EvidenceLedger, ForgettingPolicy, VersionChain
from memory import ContextPacket, Event, MemoryStore, SuppressionState, compile_packet, encode_gate
from segmentation import Percept, segment
from relationship import Relationship, RelationshipEvidence
from simulation import Episode, Scenario, compose, simulate
from state_params import StateParams, SystemState, derive_params

_TIER = {"direct": 0, "document": 1, "relay": 2, "inference": 3, "model": 4}


@dataclass
class TurnResult:
    params: StateParams
    packet: ContextPacket
    trace: List[Dict[str, Any]] = field(default_factory=list)


class Pipeline:
    def __init__(self) -> None:
        self.store = MemoryStore()
        self.ledger = EvidenceLedger()
        self.versions: Dict[str, VersionChain] = {}
        self.forgetting = ForgettingPolicy()
        self.suppression = SuppressionState()
        self.constitution = ConstitutionStore()
        self.trace: List[Dict[str, Any]] = []

    def _log(self, step: str, **fields: Any) -> None:
        self.trace.append({"step": step, **fields})

    def ingest(self, event: Event, state: SystemState) -> bool:
        params = derive_params(state)
        accepted = encode_gate(event, params)
        if accepted:
            self.store.add(event)
            if event.claim_id:
                self.ledger.add(Evidence(event.claim_id, event.event_id, event.source, event.text,
                                         tier=_TIER.get(event.source, 3)))
            self._log("ingest", event_id=event.event_id, accepted=True,
                      encode_threshold=params.memory.encode_threshold)
        else:
            self._log("ingest", event_id=event.event_id, accepted=False,
                      encode_threshold=params.memory.encode_threshold)
        return accepted

    def ingest_percepts(self, percepts: Sequence[Percept], state: SystemState,
                        event_id_prefix: str = "SEG", claim_id: Optional[str] = None) -> List[Event]:
        segs = segment(percepts)
        accepted: List[Event] = []
        for i, seg in enumerate(segs, start=1):
            event = seg.to_event(f"{event_id_prefix}{i:03d}", claim_id=claim_id)
            if self.ingest(event, state):
                accepted.append(event)
        self._log("segment", segments=len(segs), accepted=len(accepted))
        return accepted

    def observe(self, claim_id: str, content: str, evidence_ids: Sequence[str],
                now: float, prediction_error: float = 0.0, novelty: float = 0.0) -> VersionChain:
        chain = self.versions.setdefault(claim_id, VersionChain())
        chain.append(content, list(evidence_ids), now, prediction_error, novelty)
        self._log("observe", claim_id=claim_id, version=chain.current().version_id,
                  pe=prediction_error, novelty=novelty)
        return chain

    def offline_compose(self, episodes: Sequence[Episode], max_scenarios: int = 3) -> List[Scenario]:
        scenarios = compose(episodes, max_scenarios=max_scenarios)
        self._log("compose", scenarios=len(scenarios),
                  ids=[s.scenario_id for s in scenarios])
        return scenarios

    def record_outcome(self, event_id: str, observed: str, source: str, correct: bool,
                       now: float, claim_id: Optional[str] = None,
                       prediction_error: float = 0.0, novelty: float = 0.0,
                       relationship: Optional[Relationship] = None,
                       dimension: str = "trust") -> Event:
        """Observed result: update source calibration, write a direct event, version if PE is high."""
        self.ledger.record_outcome(source, correct)
        result_id = f"R{len(self.store.all()) + 1:03d}"
        result = Event(result_id, f"结果：{observed}", source="direct", ts=now,
                       claim_id=claim_id)
        self.store.add(result)
        version = None
        if claim_id:
            version = self.observe(claim_id, f"结果：{observed}",
                                   [event_id, result_id], now,
                                   prediction_error=prediction_error, novelty=novelty)
        if relationship is not None:
            relationship.update(RelationshipEvidence(
                result_id, dimension, 0.5 if correct else -0.5,
                reliability=1.0, salience=0.8))
        self._log("outcome", event_id=event_id, result_id=result_id,
                  source=source, correct=correct,
                  version=version.current().version_id if version else None)
        return result

    def turn(self, query: str, state: SystemState, now: float,
             person: Optional[Dict[str, Any]] = None,
             topics: Sequence[str] = ()) -> TurnResult:
        params = derive_params(state)
        packet = compile_packet(
            self.store, query, params, now, person=person, query_topics=topics,
            state=state, ledger=self.ledger, versions=self.versions,
            forgetting=self.forgetting, suppression=self.suppression,
        )
        self._log("turn", query=query, params_hash=params.params_hash,
                  packet_hash=packet.packet_hash, experiences=len(packet.experiences),
                  stale=sum(1 for x in packet.experiences if x.get("stale")))
        return TurnResult(params=params, packet=packet, trace=list(self.trace))

    def propose(self, type: str, key: str, content: Any, proposed_by: str,
                evidence_event_ids: List[str], now: float = 0.0,
                core: bool = False, cooling_off_seconds: float = 0.0) -> ConstitutiveProposal:
        p = self.constitution.propose(type, key, content, proposed_by,
                                      evidence_event_ids, now=now, core=core,
                                      cooling_off_seconds=cooling_off_seconds)
        self._log("propose", proposal_id=p.proposal_id, type=type, status=p.status)
        return p

    def ratify(self, proposal_id: str, ratifier: str, now: float,
               cosignatory: Optional[str] = None) -> ConstitutiveProposal:
        p = self.constitution.ratify(proposal_id, ratifier, now,
                                     cosignatory=cosignatory)
        self._log("ratify", proposal_id=proposal_id, status=p.status,
                  ledger_head=self.constitution.ledger.head)
        return p

    def audit(self) -> Dict[str, Any]:
        return {
            "steps": len(self.trace),
            "trace": list(self.trace),
            "ledger_ok": self.constitution.ledger.verify(),
            "ledger_entries": len(self.constitution.ledger.entries),
            "constitution_version": self.constitution.constitution.version,
        }


def demo() -> Dict[str, Any]:
    now = 1_700_000_000.0
    day = 86400.0
    pipe = Pipeline()
    state = SystemState(goal_pressure=0.8, relationship_strain=0.3,
                        resource_load=0.2, uncertainty=0.7, coping_capacity=0.5)

    e1 = Event("E001", "方案 反馈 他在忙", person_ids=("P1",), topics=("work",),
               salience=0.8, ts=now - day, claim_id="C1")
    e2 = Event("E002", "方案 两次未回", person_ids=("P1",), topics=("work",),
               salience=0.6, ts=now - 2 * day, claim_id="C1")
    e3 = Event("E003", "旧版本 他在忙", person_ids=("P1",), topics=("work",),
               salience=0.2, ts=now - 40 * day, claim_id="C1")
    for e in (e1, e2, e3):
        pipe.ingest(e, state)

    pipe.observe("C1", "他在忙", ["E001"], now)
    pipe.observe("C1", "他回避", ["E001", "E002"], now + 1, prediction_error=0.9, novelty=0.6)

    turn = pipe.turn("方案 反馈", state, now + 2, person={"person_id": "P1", "name": "小林"},
                     topics=("work",))

    proposal = pipe.propose("goal", "weekly_review", "每周复盘一次",
                            "backend:consolidator", ["E001", "E002"], now=now + 3)
    pipe.ratify(proposal.proposal_id, "main:session", now=now + 4)

    return {
        "params_hash": turn.params.params_hash,
        "packet": turn.packet.to_dict(),
        "audit": pipe.audit(),
    }


if __name__ == "__main__":
    print(json.dumps(demo(), ensure_ascii=False, indent=2, sort_keys=True))
