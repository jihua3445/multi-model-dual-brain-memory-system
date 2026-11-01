"""Tests for compositional replay."""
from __future__ import annotations

import unittest

from ledger import EvidenceLedger
from pipeline import Pipeline
from simulation import Episode, can_write_as_fact, compose, to_hypothesis


class TestCompositionalReplay(unittest.TestCase):
    def setUp(self):
        self.eps = [
            Episode("E1", ("小林", "看方案", "答应反馈")),
            Episode("E2", ("会议室", "讨论预算", "未定")),
            Episode("E3", ("周五", "发邮件", "已完成")),
        ]

    def test_needs_at_least_two_episodes(self):
        with self.assertRaises(ValueError):
            compose([self.eps[0]])

    def test_output_is_simulation_and_combines_two_events(self):
        out = compose(self.eps, max_scenarios=2)
        self.assertEqual(len(out), 2)
        for s in out:
            self.assertEqual(s.source, "compositional_replay")
            self.assertFalse(s.is_fact)
            self.assertFalse(can_write_as_fact(s))
            self.assertEqual(len(s.assumptions), 2)

    def test_cannot_enter_evidence_ledger(self):
        led = EvidenceLedger()
        compose(self.eps)
        self.assertEqual(led.evidence_count("C1"), 0)

    def test_pipeline_compose_logs_without_writing(self):
        p = Pipeline()
        out = p.offline_compose(self.eps)
        self.assertEqual(len(out), 2)
        self.assertEqual(p.trace[-1]["step"], "compose")
        self.assertEqual(len(p.store.all()), 0)


if __name__ == "__main__":
    unittest.main()
