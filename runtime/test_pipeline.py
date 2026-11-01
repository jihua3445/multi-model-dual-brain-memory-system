"""Tests for the end-to-end pipeline."""
from __future__ import annotations

import json
import unittest

from constitution import RatificationPermissionError
from memory import Event
from pipeline import Pipeline
from state_params import SystemState

NOW = 1_700_000_000.0
DAY = 86400.0


def event(i, text, salience=0.7, claim="C1", commitment=False, age=1):
    return Event(f"E{i:03d}", text, person_ids=("P1",), topics=("work",),
                 salience=salience, ts=NOW - age * DAY, claim_id=claim,
                 open_commitment=commitment)


class TestPipeline(unittest.TestCase):
    def test_ingest_gate(self):
        p = Pipeline()
        low_state = SystemState()
        self.assertFalse(p.ingest(event(1, "普通 事件", salience=0.4), low_state))
        self.assertTrue(p.ingest(event(2, "承诺 事件", salience=0.1, commitment=True), low_state))
        high_state = SystemState(goal_pressure=0.9, relationship_strain=0.9,
                                 uncertainty=0.9, coping_capacity=0.1)
        self.assertTrue(p.ingest(event(3, "普通 事件", salience=0.4), high_state))

    def test_turn_uses_current_interpretation_and_marks_stale(self):
        p = Pipeline()
        state = SystemState(goal_pressure=0.8, relationship_strain=0.3,
                            uncertainty=0.7, coping_capacity=0.5)
        for i, text in [(1, "方案 反馈 他在忙"), (2, "方案 两次未回"), (3, "旧版本 他在忙")]:
            p.ingest(event(i, text, salience=0.8 if i < 3 else 0.3, age=1 if i < 3 else 40), state)
        p.observe("C1", "他在忙", ["E001", "E002"], NOW)
        p.observe("C1", "他回避", ["E001", "E002"], NOW + 1, prediction_error=0.9, novelty=0.6)
        turn = p.turn("方案 反馈", state, NOW + 2, person={"person_id": "P1"}, topics=("work",))
        by_id = {x["event_id"]: x for x in turn.packet.experiences}
        self.assertEqual(by_id["E001"]["interpretation"], "他回避")
        self.assertEqual(by_id["E001"]["version_id"], "v2")
        self.assertTrue(by_id["E003"]["stale"])
        self.assertEqual(by_id["E001"]["evidence_count"], 3)

    def test_proposal_requires_ratification(self):
        p = Pipeline()
        prop = p.propose("goal", "g1", "每周复盘", "backend:consolidator", ["E001"], now=NOW)
        self.assertEqual(p.constitution.constitution.items["goals"], {})
        p.ratify(prop.proposal_id, "main:session", now=NOW + 1)
        self.assertEqual(p.constitution.constitution.items["goals"]["g1"], "每周复盘")
        self.assertTrue(p.constitution.ledger.verify())

    def test_core_proposal_requires_user_cosign(self):
        p = Pipeline()
        prop = p.propose("value", "honesty", "always", "backend:consolidator",
                         ["E001"], now=NOW, core=True)
        with self.assertRaises(RatificationPermissionError):
            p.ratify(prop.proposal_id, "main:session", now=NOW + 1)
        self.assertEqual(p.constitution.constitution.items["values"], {})

    def test_audit_trace_is_json_and_ledger_ok(self):
        p = Pipeline()
        state = SystemState(goal_pressure=0.5, uncertainty=0.5)
        p.ingest(event(1, "方案 反馈", salience=0.8), state)
        p.turn("方案", state, NOW + 1)
        prop = p.propose("goal", "g1", "v1", "backend", ["E001"], now=NOW + 2)
        p.ratify(prop.proposal_id, "main:session", now=NOW + 3)
        audit = p.audit()
        self.assertTrue(audit["ledger_ok"])
        self.assertEqual(audit["steps"], len(p.trace))
        json.dumps(audit, ensure_ascii=False)
        self.assertEqual([s["step"] for s in p.trace][:2], ["ingest", "turn"])

    def test_turn_is_deterministic(self):
        p = Pipeline()
        state = SystemState(goal_pressure=0.5, uncertainty=0.5)
        p.ingest(event(1, "方案 反馈", salience=0.8), state)
        a = p.turn("方案", state, NOW + 1)
        b = p.turn("方案", state, NOW + 1)
        self.assertEqual(a.params.params_hash, b.params.params_hash)
        self.assertEqual(a.packet.packet_hash, b.packet.packet_hash)

    def test_ingest_adds_evidence_by_claim(self):
        p = Pipeline()
        state = SystemState(goal_pressure=0.8, uncertainty=0.5)
        p.ingest(event(1, "a", salience=0.9), state)
        p.ingest(event(2, "b", salience=0.9), state)
        self.assertEqual(p.ledger.evidence_count("C1"), 2)


if __name__ == "__main__":
    unittest.main()
