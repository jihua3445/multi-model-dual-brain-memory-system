"""Show the event -> state -> params mapping for two scenarios."""
from __future__ import annotations

import json

from state_params import SystemState, derive_params


def show(title: str, state: SystemState) -> None:
    p = derive_params(state)
    print(f"\n== {title} ==")
    print(f"impact_gap={state.impact_gap():.2f}  state_hash={p.state_hash[:12]}…")
    print(json.dumps(p.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    show(
        "目标被阻断 + 线索冲突",
        SystemState(goal_pressure=0.9, uncertainty=0.8, relationship_strain=0.2),
    )
    show(
        "资源紧张 + 低不确定 + 有未完成承诺",
        SystemState(resource_load=0.9, uncertainty=0.2, unresolved_commitments=2,
                    coping_capacity=0.4),
    )
