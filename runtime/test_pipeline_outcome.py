"""Tests for action outcome write-back."""
from __future__ import annotations

import unittest

from memory import Event
from pipeline import Pipeline
from state_params import SystemState

NOW = 1_700_000_000.0


class TestOutcomeWriteBack(unittest.TestCase):
    def setUp(self):
        self.p = Pipeline()
        self.state = SystemState(goal_pressure=0.8, uncertainty=0.5)
        self.p.ingest(Event("E1", "他说会发方案", source="relay", claim_id="C1",
                            salience=0.9, ts=NOW), self.state)
        self.p.observe("C1", "他会发方案", ["E1"], NOW)

    def test_outcome_updates_source_calibration(self):
        before = self.p.ledger.claim_reliability("C1", "E1", 0.5)
        self.p.record_outcome("E1", "已发", "relay", True, NOW + 1, claim_id="C1")
        after = self.p.ledger.claim_reliability("C1", "E1", 0.5)
        self.assertGreater(after, before)

    def test_high_pe_creates_new_version(self):
        self.p.record_outcome("E1", "未发", "relay", False, NOW + 1,
                              claim_id="C1", prediction_error=0.9)
        chain = self.p.versions["C1"]
        self.assertEqual(chain.current().version_id, "v2")
        self.assertIn("未发", chain.current().content)

    def test_low_pe_only_accesses(self):
        self.p.record_outcome("E1", "已发", "relay", True, NOW + 1,
                              claim_id="C1", prediction_error=0.1)
        chain = self.p.versions["C1"]
        self.assertEqual(chain.current().version_id, "v1")
        self.assertEqual(chain.access_count, 1)


if __name__ == "__main__":
    unittest.main()
