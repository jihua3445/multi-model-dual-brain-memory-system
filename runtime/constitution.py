"""Constitutive proposals, ratification ledger, and a minimal constitution store.

Mirrors section 3.7 of the document:
  * backend may only propose; it cannot write the constitution directly;
  * the main brain ratifies ordinary changes; core changes need user co-sign
    and a cooling-off period;
  * every decision is appended to a hash-chained ledger;
  * ratified changes can be rolled back, and the old value is preserved.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

PROPOSAL_TYPES = {
    "value": "values",
    "role": "roles",
    "goal": "goals",
    "commitment": "commitments",
    "habit_rule": "habits",
    "relationship_weight": "relationships",
}


class ProposalError(Exception):
    pass


class RatificationPermissionError(ProposalError):
    pass


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


@dataclass
class ConstitutiveProposal:
    proposal_id: str
    type: str
    key: str
    content: Any
    proposed_by: str
    evidence_event_ids: List[str]
    rationale: str = ""
    core: bool = False
    cooling_off_seconds: float = 0.0
    created_at: float = 0.0
    expires_at: Optional[float] = None
    status: str = "pending"  # pending | cooling | ratified | rejected | expired | rolled_back
    ratified_by: Optional[str] = None
    ratified_at: Optional[float] = None
    cooling_off_until: Optional[float] = None
    cosigned_by: Optional[str] = None
    prev_value: Any = None

    def proposal_hash(self) -> str:
        return _hash({
            "proposal_id": self.proposal_id,
            "type": self.type,
            "key": self.key,
            "content": self.content,
            "proposed_by": self.proposed_by,
            "evidence_event_ids": self.evidence_event_ids,
            "core": self.core,
        })


class RatificationLedger:
    """Append-only hash chain. Tampering breaks `verify()`."""

    def __init__(self) -> None:
        self.entries: List[Dict[str, Any]] = []

    @property
    def head(self) -> str:
        return self.entries[-1]["hash"] if self.entries else "GENESIS"

    def append(self, proposal: ConstitutiveProposal, decision: str, ratifier: str,
               now: float, conditions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "proposal_id": proposal.proposal_id,
            "proposal_hash": proposal.proposal_hash(),
            "decision": decision,
            "ratifier": ratifier,
            "timestamp": now,
            "conditions": conditions or {},
            "prev_hash": self.head,
        }
        entry = dict(payload)
        entry["hash"] = _hash(payload)
        self.entries.append(entry)
        return entry

    def verify(self) -> bool:
        prev = "GENESIS"
        for e in self.entries:
            payload = {k: e[k] for k in
                       ("proposal_id", "proposal_hash", "decision", "ratifier",
                        "timestamp", "conditions", "prev_hash")}
            if payload["prev_hash"] != prev:
                return False
            if _hash(payload) != e["hash"]:
                return False
            prev = e["hash"]
        return True


@dataclass
class Constitution:
    version: int = 1
    items: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {s: {} for s in PROPOSAL_TYPES.values()})

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        return {k: dict(v) for k, v in self.items.items()}

    def apply(self, p: ConstitutiveProposal) -> Any:
        section = PROPOSAL_TYPES[p.type]
        prev = self.items[section].get(p.key)
        self.items[section][p.key] = p.content
        self.version += 1
        return prev

    def restore(self, p: ConstitutiveProposal, prev: Any) -> None:
        section = PROPOSAL_TYPES[p.type]
        if prev is None:
            self.items[section].pop(p.key, None)
        else:
            self.items[section][p.key] = prev
        self.version += 1


class ConstitutionStore:
    def __init__(self, constitution: Optional[Constitution] = None,
                 mode: str = "companion") -> None:
        if mode not in ("companion", "engineering"):
            raise ValueError("mode must be companion or engineering")
        self.mode = mode
        self.constitution = constitution or Constitution()
        self.ledger = RatificationLedger()
        self._proposals: Dict[str, ConstitutiveProposal] = {}
        self._counter = 0

    # ---- proposal: backend can only add a pending proposal ----
    def propose(self, type: str, key: str, content: Any, proposed_by: str,
                evidence_event_ids: List[str], rationale: str = "", core: bool = False,
                cooling_off_seconds: float = 0.0, now: float = 0.0,
                expires_at: Optional[float] = None) -> ConstitutiveProposal:
        if type not in PROPOSAL_TYPES:
            raise ProposalError(f"unknown type: {type}")
        if not evidence_event_ids:
            raise ProposalError("constitutive proposals require evidence_event_ids")
        self._counter += 1
        p = ConstitutiveProposal(
            proposal_id=f"P{self._counter:04d}", type=type, key=key, content=content,
            proposed_by=proposed_by, evidence_event_ids=list(evidence_event_ids),
            rationale=rationale, core=core, cooling_off_seconds=cooling_off_seconds,
            created_at=now, expires_at=expires_at,
        )
        self._proposals[p.proposal_id] = p
        return p

    def get(self, proposal_id: str) -> ConstitutiveProposal:
        return self._proposals[proposal_id]

    def pending(self) -> List[ConstitutiveProposal]:
        return [p for p in self._proposals.values() if p.status in ("pending", "cooling")]

    # ---- ratification: main brain; core needs user co-sign ----
    def ratify(self, proposal_id: str, ratifier: str, now: float,
               cosignatory: Optional[str] = None) -> ConstitutiveProposal:
        p = self._proposals[proposal_id]
        if p.status not in ("pending",):
            raise ProposalError(f"cannot ratify in status {p.status}")
        if p.expires_at is not None and now > p.expires_at:
            p.status = "expired"
            raise ProposalError("proposal expired")
        if p.core:
            if self.mode == "companion":
                if not cosignatory:
                    raise RatificationPermissionError("companion mode: core change requires equal co-signature")
            else:  # engineering: the user holds the highest permission
                if ratifier not in ("user", "owner"):
                    raise RatificationPermissionError("engineering mode: only the user can ratify a core change")
            p.cosigned_by = cosignatory

        if p.cooling_off_seconds > 0 and p.cooling_off_until is None:
            p.status = "cooling"
            p.cooling_off_until = now + p.cooling_off_seconds
            return p

        prev = self.constitution.apply(p)
        p.prev_value = prev
        p.status = "ratified"
        p.ratified_by = ratifier
        p.ratified_at = now
        self.ledger.append(p, "ratified", ratifier, now,
                           {"core": p.core, "cosigned_by": p.cosigned_by, "mode": self.mode, "mode": self.mode})
        return p

    def finalize_cooling(self, proposal_id: str, ratifier: str, now: float) -> ConstitutiveProposal:
        p = self._proposals[proposal_id]
        if p.status != "cooling" or p.cooling_off_until is None:
            raise ProposalError("proposal is not cooling")
        if now < p.cooling_off_until:
            raise ProposalError("cooling-off period has not ended")
        prev = self.constitution.apply(p)
        p.prev_value = prev
        p.status = "ratified"
        p.ratified_by = ratifier
        p.ratified_at = now
        self.ledger.append(p, "ratified_after_cooling", ratifier, now,
                           {"core": p.core, "cosigned_by": p.cosigned_by, "mode": self.mode,
                            "cooling_off_until": p.cooling_off_until})
        return p

    def reject(self, proposal_id: str, ratifier: str, reason: str, now: float) -> ConstitutiveProposal:
        p = self._proposals[proposal_id]
        if p.status not in ("pending", "cooling"):
            raise ProposalError(f"cannot reject in status {p.status}")
        p.status = "rejected"
        self.ledger.append(p, "rejected", ratifier, now, {"reason": reason})
        return p

    def expire(self, now: float) -> List[str]:
        out = []
        for p in self._proposals.values():
            if p.status == "pending" and p.expires_at is not None and now > p.expires_at:
                p.status = "expired"
                self.ledger.append(p, "expired", "system", now, {})
                out.append(p.proposal_id)
        return out

    def rollback(self, proposal_id: str, ratifier: str, now: float) -> ConstitutiveProposal:
        p = self._proposals[proposal_id]
        if p.status != "ratified":
            raise ProposalError("only a ratified proposal can be rolled back")
        self.constitution.restore(p, p.prev_value)
        p.status = "rolled_back"
        self.ledger.append(p, "rolled_back", ratifier, now, {"restored": p.prev_value})
        return p
