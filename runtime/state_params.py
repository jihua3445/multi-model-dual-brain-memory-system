"""Reference implementation of the 2.7.1/2.7.2 state -> params mapping.

Pure stdlib. No model calls, no network. The point is to make the
"event -> state -> runtime params" contract executable and testable.

Design rules (from the document):
  * params are derived deterministically from a whitelisted state;
  * every param is bounded;
  * params are versioned and hashable;
  * params never encode facts, only processing behaviour;
  * a prompt/string cannot override params.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional

SCHEMA_VERSION = "state_params.v2"
PARAMS_VERSION = "2026.11-r25"


def clamp(value: float, low: float, high: float) -> float:
    """Clamp to [low, high]; NaN is treated as low."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = low
    if v != v:  # NaN
        v = low
    return max(low, min(high, v))


def _r3(value: float) -> float:
    """Round derived floats to 3 decimals for stable JSON and hashes."""
    return round(float(value), 3)


def _unit(value: Any, default: float = 0.0) -> float:
    return clamp(value, 0.0, 1.0) if value is not None else default


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SystemState:
    """The event-derived state. All fields are normalized to [0,1] except count."""

    goal_pressure: float = 0.0
    relationship_strain: float = 0.0
    resource_load: float = 0.0
    uncertainty: float = 0.0
    unresolved_commitments: int = 0
    coping_capacity: float = 0.5
    prediction_error: float = 0.0
    precision: float = 1.0

    def normalized(self) -> "SystemState":
        return SystemState(
            goal_pressure=_unit(self.goal_pressure),
            relationship_strain=_unit(self.relationship_strain),
            resource_load=_unit(self.resource_load),
            uncertainty=_unit(self.uncertainty),
            unresolved_commitments=max(0, int(self.unresolved_commitments)),
            coping_capacity=_unit(self.coping_capacity, 0.5),
            prediction_error=clamp(self.prediction_error, -1.0, 1.0),
            precision=_unit(self.precision, 1.0),
        )

    def impact_gap(self) -> float:
        s = self.normalized()
        raw = (
            s.goal_pressure
            + s.relationship_strain
            + s.resource_load
            + s.uncertainty
            + s.precision * abs(s.prediction_error)
            - s.coping_capacity
        )
        return clamp(raw, 0.0, 2.0)

    def state_hash(self) -> str:
        return _sha256(asdict(self.normalized()))


@dataclass(frozen=True)
class RetrievalParams:
    top_k: int
    goal_weight: float
    candidate_mult: float
    retrieval_noise: float


@dataclass(frozen=True)
class AuditParams:
    verify_ratio: float
    abstain_threshold: float
    source_strictness: float


@dataclass(frozen=True)
class SchedulerParams:
    fast_path: bool
    depth: int
    max_tool_calls: int


@dataclass(frozen=True)
class ContextParams:
    slots: int
    token_budget: int
    pin_commitments: bool


@dataclass(frozen=True)
class MemoryParams:
    encode_threshold: float
    consolidation_priority: float
    forgetting_exempt: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class StateParams:
    schema_version: str
    params_version: str
    state_hash: str
    params_hash: str
    retrieval: RetrievalParams
    audit: AuditParams
    scheduler: SchedulerParams
    context: ContextParams
    memory: MemoryParams
    relationship: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Declared bounds; tests assert every derived numeric value stays inside.
BOUNDS: Dict[str, tuple] = {
    "retrieval.top_k": (4, 20),
    "retrieval.goal_weight": (0.0, 1.0),
    "retrieval.candidate_mult": (1.0, 4.0),
    "retrieval.retrieval_noise": (0.0, 0.6),
    "audit.verify_ratio": (0.0, 1.0),
    "audit.abstain_threshold": (0.1, 0.8),
    "audit.source_strictness": (0.0, 1.0),
    "scheduler.depth": (1, 3),
    "scheduler.max_tool_calls": (1, 6),
    "context.slots": (4, 5),
    "context.token_budget": (600, 2000),
    "memory.encode_threshold": (0.1, 0.9),
    "memory.consolidation_priority": (0.0, 1.0),
}


def derive_params(state: SystemState) -> StateParams:
    """Deterministically map an event-derived state to bounded runtime params."""
    s = state.normalized()
    gap = s.impact_gap()

    # retrieval
    top_k = int(round(clamp(12.0 - 8.0 * s.goal_pressure + 4.0 * s.uncertainty, 4, 20)))
    goal_weight = _r3(clamp(0.3 + 0.5 * s.goal_pressure, 0.0, 1.0))
    candidate_mult = _r3(clamp(1.0 + 3.0 * s.uncertainty, 1.0, 4.0))
    retrieval_noise = _r3(clamp(0.05 + 0.3 * s.uncertainty + 0.2 * (1.0 - s.precision), 0.0, 0.5))

    # audit
    verify_ratio = _r3(clamp(0.2 + 0.6 * s.uncertainty + 0.2 * s.relationship_strain, 0.0, 1.0))
    abstain_threshold = _r3(clamp(0.5 - 0.3 * s.uncertainty + 0.1 * retrieval_noise, 0.1, 0.8))
    source_strictness = _r3(clamp(0.3 + 0.5 * s.relationship_strain, 0.0, 1.0))

    # scheduler
    fast_path = bool(s.resource_load > 0.7 and s.uncertainty < 0.4 and gap < 0.5)
    depth = int(1 + int(s.uncertainty > 0.5) + int(gap > 0.7))
    max_tool_calls = int(round(clamp(6.0 - 4.0 * s.resource_load, 1, 6)))

    # context
    slots = int(4 + int(gap > 0.8))
    token_budget = int(round(clamp(1800.0 - 600.0 * s.resource_load - 300.0 * s.goal_pressure, 600, 2000)))
    pin_commitments = bool(s.unresolved_commitments > 0)

    # memory
    surprise = s.precision * abs(s.prediction_error)
    encode_threshold = _r3(clamp(0.6 - 0.3 * gap - 0.2 * surprise, 0.1, 0.9))
    consolidation_priority = _r3(clamp(0.2 + 0.6 * gap + 0.2 * s.relationship_strain + 0.2 * surprise, 0.0, 1.0))
    forgetting_exempt = ["commitment"] if pin_commitments else []

    # relationship: write policy, not a trait update
    trait_update_allowed = bool(s.relationship_strain < 0.7)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "params_version": PARAMS_VERSION,
        "state_hash": s.state_hash(),
        "retrieval": {"top_k": top_k, "goal_weight": goal_weight,
                       "candidate_mult": candidate_mult, "retrieval_noise": retrieval_noise},
        "audit": {
            "verify_ratio": verify_ratio,
            "abstain_threshold": abstain_threshold,
            "source_strictness": source_strictness,
        },
        "scheduler": {"fast_path": fast_path, "depth": depth, "max_tool_calls": max_tool_calls},
        "context": {"slots": slots, "token_budget": token_budget, "pin_commitments": pin_commitments},
        "memory": {
            "encode_threshold": encode_threshold,
            "consolidation_priority": consolidation_priority,
            "forgetting_exempt": forgetting_exempt,
        },
        "relationship": {"trait_update_allowed": trait_update_allowed},
    }
    params_hash = _sha256(payload)

    return StateParams(
        schema_version=SCHEMA_VERSION,
        params_version=PARAMS_VERSION,
        state_hash=payload["state_hash"],
        params_hash=params_hash,
        retrieval=RetrievalParams(**payload["retrieval"]),
        audit=AuditParams(**payload["audit"]),
        scheduler=SchedulerParams(**payload["scheduler"]),
        context=ContextParams(**payload["context"]),
        memory=MemoryParams(**payload["memory"]),
        relationship=payload["relationship"],
    )


_ALLOWED_EVENT_KEYS = {
    "goal_pressure",
    "relationship_strain",
    "resource_load",
    "uncertainty",
    "unresolved_commitments",
    "coping_capacity",
    "prediction_error",
    "precision",
}


def derive_from_event(event: Mapping[str, Any]) -> StateParams:
    """Whitelist-only event -> params. Extra keys (e.g. prompt text) are ignored."""
    state = SystemState(
        **{k: event[k] for k in _ALLOWED_EVENT_KEYS if k in event}
    )
    return derive_params(state)


def flatten_numeric(obj: Any, prefix: str = "") -> Iterable[tuple]:
    """Yield (dotted_path, value) for numeric leaves; skip bool/str/list."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield prefix, obj
        return
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            child = f"{prefix}.{k}" if prefix else str(k)
            yield from flatten_numeric(v, child)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from flatten_numeric(v, f"{prefix}[{i}]")
