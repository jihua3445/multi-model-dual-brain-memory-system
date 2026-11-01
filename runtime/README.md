# state / memory reference implementation

Executable counterpart of sections 2.7, 5.1, 6.3–6.6 and 3.7. Pure Python
standard library. No model calls, no network, no external deps.

```
event -> system_state -> state_params -> retrieval -> ContextPacket
      -> proposal -> ratify -> ledger
```

## Files

- `state_params.py` — event-derived state, bounded params, hashing.
- `memory.py` — in-memory events, retriever, `ContextPacket` compiler.
- `ledger.py` — evidence ledger, interpretation version chain, retention.
- `constitution.py` — proposals, ratification, cooling-off, rollback.
- `segmentation.py` — event segmentation by PE / topic / person / gap / duration.
- `decision.py` — precedent value, fast/slow arbitration, skill vs recall.
- `simulation.py` — counterfactual candidates with a hard no-fact boundary.
- `primitives.py` — typed primitive library and slot-constrained composition.
- `relationship.py` — trust/commitment thresholds from precedents.
- `graph_retrieval.py` — lightweight typed adjacency + bounded 1–2 hop expansion.
- `reliability.py` — claim-level source reliability (tier, verifiability, history, consistency).
- `pipeline.py` — end-to-end ingest → turn → propose → ratify → audit.
- `test_decision.py` — 7 cases for precedent value and arbitration.
- `test_simulation.py` — 5 cases for the simulation write boundary.
- `test_relationship.py` — 16 cases for multi-dimensional relationships, affect/trust separation and interaction weight.
- `test_reliability.py` — 6 cases for source reliability.
- `test_reliability_history.py` — 3 cases for outcome-driven calibration.
- `demo.py` — two state-mapping examples.

## Run

```bash
cd runtime
python3 -m unittest -v      # 117 tests
python3 demo.py             # state mapping examples
python3 pipeline.py         # end-to-end JSON with audit trace
```

## What the tests establish

- Params are deterministic: same state -> same `params_hash`.
- Every numeric param stays inside its declared bound, including extremes.
- `goal_pressure` up -> `top_k` down; `uncertainty` up -> more candidates,
  stricter verification, deeper path.
- `encode_threshold` falls with impact gap and precision-weighted error;
  `consolidation_priority` rises with both.
- Fast path only when resource load is high, uncertainty low and impact gap low.
- Unresolved commitments are pinned and exempt from forgetting.
- High relationship strain raises source strictness and blocks trait updates.
- Conflict evidence is shown side by side; a high score cannot silently cover it.
- Evidence is counted by distinct `event_id`; 50 recalls still count once.
- High prediction error/novelty appends a version and preserves the old one.
- Forgetting moves an index to cold storage; the raw event is never deleted.
- Backend proposals stay `pending`; ratification applies them; core changes
  need user co-sign; reject/expire/rollback are recorded in a hash chain.
- Segmentation splits on PE, topic/person change, time gap and max duration.
- Negative precedents lower an option's value; low reliability and conflict are
  downweighted; fast path requires high habit confidence, low stakes/uncertainty
  and high resource load; skill execution depends on practice, not recall.
- A simulation is never a fact, never enters the evidence ledger, and can only
  become a `hypothesis` when independent evidence is supplied.
- Relationship updates are threshold adjustments: negative precedents weigh more,
  low reliability/conflict are downweighted, and commitment needs trust plus capacity.
- Only reliable recall stabilises memory: `n_eff = distinct_retrievals * source_reliability`.
  Low-reliability repetition raises accessibility, not stability.
- `ConstitutionStore(mode="companion")` requires equal co-signature for core
  changes; `mode="engineering"` gives the user sole authority over core changes.
- `EvidenceLedger.record_outcome()` updates a source's historical calibration:
  later verification raises reliability, contradiction lowers it.
- `Pipeline.record_outcome()` writes the observed result as a direct event,
  updates source calibration, and versions the interpretation only on high PE.
- The same `event_id` is idempotent for relationship evidence: repeated
  write-back neither adds evidence nor amplifies the relationship value.
- Compositional replay recombines elements from at least two episodes, tags
  output as `compositional_replay`, and never writes it as fact or evidence.
- The primitive library is typed (person/place/action/relation/goal); composition
  fills slots by kind, so a place cannot be used as a person.
- Retrieval can apply a reversible, time-limited suppression (×0.85 for 3 logical units)
  to competitors; it never changes evidence or relationship values.
- Association retrieval is a lightweight adjacency index, not a graph database:
  1–2 hops, decay, budget, path/hop output; simulation edges are excluded.
- Co-presence is downweighted (0.3) relative to actual interaction (1.0).
- Relationships keep separate dimensions; `valence` (emotional direction) and
  `intensity` (emotional strength) are distinct. Retention uses `intensity`, not direction.
- Affect and trust are separate: dislike does not imply untrustworthy, and liking
  does not imply trustworthy; commitment uses trust, not valence.
- A prompt string or arbitrary extra key cannot change params.

## What it does not establish

- No embeddings, vector store, persistence, signing keys or writer service.
- The formulas are illustrative defaults; production values need calibration.
- It does not show that these params improve decisions; that needs the
  evaluation harness in section 8.
- The tokenizer is character/word based, not semantic.
