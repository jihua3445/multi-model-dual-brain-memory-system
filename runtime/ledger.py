"""Evidence ledger, interpretation version chain, and retention policy.

Pure stdlib. Mirrors sections 4.6 (evidence), 6.3 (reconsolidation) and
6.4 (forgetting) of the document.

Core invariants:
  * evidence is counted by distinct event_id, never by recall count;
  * a recall only increases accessibility, not evidence;
  * a new interpretation version is created only on prediction error or
    novelty above threshold; old versions are preserved;
  * forgetting moves an index to cold storage; the raw event is never deleted;
  * commitments, safety-critical items and explicit "remember" are exempt.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from reliability import SourceHistory, reliability


@dataclass(frozen=True)
class Evidence:
    claim_id: str
    event_id: str
    source: str = "direct"
    value: Optional[str] = None
    ts: float = 0.0
    tier: int = 0  # 0 direct, 1 document, 2 relay, 3 inference, 4 model
    source_reliability: float = 1.0


class EvidenceLedger:
    """Append-only evidence store with distinct-event counting."""

    def __init__(self) -> None:
        self._rows: List[Evidence] = []
        self._recalls: List[Tuple[str, float]] = []
        self._history: Dict[str, SourceHistory] = {}

    def add(self, ev: Evidence) -> None:
        # Same (claim, event) is one piece of evidence; keep the first row.
        for r in self._rows:
            if r.claim_id == ev.claim_id and r.event_id == ev.event_id:
                return
        self._rows.append(ev)

    def record_outcome(self, source: str, correct: bool) -> None:
        """Later verification updates the source's historical calibration."""
        self._history.setdefault(source, SourceHistory()).record(correct)

    def history_for(self, source: str) -> SourceHistory:
        return self._history.setdefault(source, SourceHistory())

    def claim_reliability(self, claim_id: str, event_id: str,
                          verifiability: float = 0.5,
                          consistency: float = 1.0) -> float:
        """Claim-level reliability: source tier + verifiability + history + consistency."""
        row = next((r for r in self._rows
                    if r.claim_id == claim_id and r.event_id == event_id), None)
        if row is None:
            return 0.0
        tier_prior = [1.0, 0.8, 0.6, 0.4, 0.2][max(0, min(4, row.tier))]
        h = self.history_for(row.source)
        return reliability(tier_prior, verifiability, h.verified, h.contradicted, consistency)

    def recall(self, claim_id: str, ts: float = 0.0) -> None:
        """Recall increases accessibility; it must not add evidence."""
        self._recalls.append((claim_id, ts))

    def evidence(self, claim_id: str) -> List[Evidence]:
        return [r for r in self._rows if r.claim_id == claim_id]

    def evidence_count(self, claim_id: str) -> int:
        return len({r.event_id for r in self._rows if r.claim_id == claim_id})

    def recall_count(self, claim_id: str) -> int:
        return sum(1 for c, _ in self._recalls if c == claim_id)

    def distinct_sources(self, claim_id: str) -> int:
        return len({r.source for r in self._rows if r.claim_id == claim_id})

    def evidence_values(self, claim_id: str) -> Dict[str, List[str]]:
        """Map each supported value to the distinct event ids that support it."""
        out: Dict[str, List[str]] = {}
        for r in self._rows:
            if r.claim_id == claim_id and r.value is not None:
                out.setdefault(r.value, [])
                if r.event_id not in out[r.value]:
                    out[r.value].append(r.event_id)
        return out

    def conflicts(self, claim_id: str) -> List[Tuple[str, str]]:
        """Different values supported by different events are a conflict.

        Both sides are kept; the caller must surface the conflict rather than
        silently averaging it.
        """
        by_value: Dict[str, List[str]] = {}
        for r in self._rows:
            if r.claim_id == claim_id and r.value is not None:
                by_value.setdefault(r.value, []).append(r.event_id)
        if len(by_value) <= 1:
            return []
        out: List[Tuple[str, str]] = []
        values = list(by_value)
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                out.append((values[i], values[j]))
        return out


@dataclass(frozen=True)
class Version:
    version_id: str
    content: str
    evidence_ids: Tuple[str, ...]
    created_at: float
    prediction_error: float
    novelty: float
    supersedes: Optional[str] = None
    status: str = "active"


class VersionChain:
    """Reconsolidation as an append-only chain; never overwrite."""

    def __init__(self, theta_pe: float = 0.5, theta_novelty: float = 0.4) -> None:
        self.theta_pe = theta_pe
        self.theta_novelty = theta_novelty
        self._versions: List[Version] = []
        self.access_count = 0

    def append(self, content: str, evidence_ids: Sequence[str], now: float,
               prediction_error: float = 0.0, novelty: float = 0.0) -> Version:
        if not self._versions:
            v = Version("v1", content, tuple(evidence_ids), now,
                        prediction_error, novelty, None)
            self._versions.append(v)
            return v

        self.access_count += 1
        current = self._versions[-1]
        if prediction_error <= self.theta_pe and novelty <= self.theta_novelty:
            return current  # access only, no rewrite

        v = Version(
            version_id=f"v{len(self._versions) + 1}",
            content=content,
            evidence_ids=tuple(evidence_ids),
            created_at=now,
            prediction_error=prediction_error,
            novelty=novelty,
            supersedes=current.version_id,
        )
        self._versions.append(v)
        return v

    def current(self) -> Optional[Version]:
        return self._versions[-1] if self._versions else None

    def history(self) -> List[Version]:
        return list(self._versions)


@dataclass(frozen=True)
class MemoryRecord:
    event_id: str
    open_commitment: bool = False
    safety_critical: bool = False
    explicit_remember: bool = False
    arched: bool = False

    @property
    def exempt(self) -> bool:
        return self.open_commitment or self.safety_critical or self.explicit_remember


def stability(distinct_retrievals: int, schema_fit: float = 0.0,
              base: float = 1.0, source_reliability: float = 1.0) -> float:
    """Stability grows with reliable spaced retrieval and schema fit."""
    rel = max(0.0, min(1.0, float(source_reliability)))
    n_eff = max(0, distinct_retrievals) * rel
    return max(0.1, base * (1.0 + 0.6 * n_eff) * (1.0 + 0.4 * schema_fit))


def retention(age_days: float, distinct_retrievals: int = 0, valence: float = 0.0,
              utility: float = 0.5, relationship_weight: float = 0.5,
              schema_fit: float = 0.0, base_stability: float = 14.0,
              source_reliability: float = 1.0,
              relationship_intensity: Optional[float] = None) -> float:
    """R = exp(-age/S) * (1+a|v|) * (0.5+0.5*utility) * (0.5+0.5*rel)."""
    s = stability(distinct_retrievals, schema_fit, base_stability, source_reliability)
    r = math.exp(-max(0.0, age_days) / s)
    r *= 1.0 + 0.5 * abs(valence)
    r *= 0.5 + 0.5 * max(0.0, min(1.0, utility))
    rel = relationship_weight if relationship_intensity is None else relationship_intensity
    r *= 0.5 + 0.5 * max(0.0, min(1.0, rel))
    return max(0.0, min(1.0, r))


@dataclass(frozen=True)
class RetentionDecision:
    event_id: str
    state: str  # active | cold
    score: float
    reason: str


class ForgettingPolicy:
    def __init__(self, cold_threshold: float = 0.15) -> None:
        self.cold_threshold = cold_threshold
        self._cold: set = set()
        self._deleted: set = set()

    def decide(self, rec: MemoryRecord, age_days: float, distinct_retrievals: int = 0,
               valence: float = 0.0, utility: float = 0.5,
               relationship_weight: float = 0.5, schema_fit: float = 0.0,
               source_reliability: float = 1.0,
               relationship_intensity: Optional[float] = None) -> RetentionDecision:
        if rec.exempt:
            return RetentionDecision(rec.event_id, "active", 1.0, "exempt")
        score = retention(age_days, distinct_retrievals, valence, utility,
                          relationship_weight, schema_fit,
                          source_reliability=source_reliability,
                          relationship_intensity=relationship_intensity)
        if score < self.cold_threshold:
            self._cold.add(rec.event_id)
            return RetentionDecision(rec.event_id, "cold", round(score, 4), "below_threshold")
        return RetentionDecision(rec.event_id, "active", round(score, 4), "retained")

    def is_cold(self, event_id: str) -> bool:
        return event_id in self._cold

    def deleted(self) -> set:
        """This policy never deletes raw events; it only moves indexes."""
        return set(self._deleted)
