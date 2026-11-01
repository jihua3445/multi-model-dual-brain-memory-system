"""Tests for memory-driven choice."""
from __future__ import annotations

import unittest

from decision import Option, Precedent, can_execute, choose, precedent_value, rank


class TestDecision(unittest.TestCase):
    def test_negative_precedent_lowers_value(self):
        p = Precedent("E1", similarity=1.0, outcome=-1.0, salience=1.0)
        self.assertLess(precedent_value(0.5, [p]), 0.5)

    def test_positive_precedent_raises_value(self):
        p = Precedent("E1", similarity=1.0, outcome=1.0, salience=1.0)
        self.assertGreater(precedent_value(0.5, [p]), 0.5)

    def test_low_reliability_is_downweighted(self):
        weak = Precedent("E1", 1.0, -1.0, 1.0, 0.1)
        strong = Precedent("E2", 1.0, -1.0, 1.0, 1.0)
        self.assertGreater(precedent_value(0.5, [weak]), precedent_value(0.5, [strong]))

    def test_conflict_precedent_is_downweighted(self):
        normal = Precedent("E1", 1.0, -1.0, 1.0, 1.0, conflict=False)
        conflicted = Precedent("E2", 1.0, -1.0, 1.0, 1.0, conflict=True)
        self.assertGreater(precedent_value(0.5, [conflicted]),
                           precedent_value(0.5, [normal]))

    def test_fast_and_slow_arbitration(self):
        self.assertEqual(choose([], 0.2, 0.9, 0.9, 0.2), "habit")
        self.assertEqual(choose([], 0.8, 0.9, 0.9, 0.2), "deliberate")
        self.assertEqual(choose([], 0.2, 0.2, 0.9, 0.2), "deliberate")

    def test_skill_execution_is_not_recall_confidence(self):
        self.assertFalse(can_execute(practice=0.2, recall_confidence=1.0))
        self.assertTrue(can_execute(practice=0.8, recall_confidence=0.0))

    def test_risk_changes_ranking_under_uncertainty(self):
        risky = Option("risky", prior_value=0.9, risk=0.8)
        safe = Option("safe", prior_value=0.6, risk=0.1)
        self.assertEqual(rank([risky, safe], uncertainty=1.0)[0].name, "safe")
        self.assertEqual(rank([risky, safe], uncertainty=0.0)[0].name, "risky")


if __name__ == "__main__":
    unittest.main()
