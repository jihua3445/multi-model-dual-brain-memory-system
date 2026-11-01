"""Tests for outcome -> relationship evidence, with idempotence."""
from __future__ import annotations

import unittest

from memory import Event
from pipeline import Pipeline
from relationship import Relationship, RelationshipEvidence
from state_params import SystemState

NOW = 1_700_000_000.0


class TestOutcomeRelationship(unittest.TestCase):
    def test_outcome_updates_relationship(self):
        p = Pipeline()
        r = Relationship()
        p.ingest(Event("E1", "他说会发", source="direct", claim_id="C1",
                       salience=0.9, ts=NOW), SystemState(goal_pressure=0.8))
        p.record_outcome("E1", "已发", "direct", True, NOW + 1,
                         claim_id="C1", relationship=r)
        self.assertGreater(r.values["trust"], 0.0)
        self.assertEqual(r.evidence_count("trust"), 1)

    def test_same_event_id_is_not_counted_twice(self):
        r = Relationship()
        ev = RelationshipEvidence("R001", "trust", 0.5, 1.0, 1.0)
        r.update(ev)
        first = r.values["trust"]
        r.update(ev)
        self.assertEqual(r.values["trust"], first)
        self.assertEqual(r.evidence_count("trust"), 1)


if __name__ == "__main__":
    unittest.main()
