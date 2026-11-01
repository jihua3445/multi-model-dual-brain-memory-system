"""Tests for claim-level source reliability."""
from __future__ import annotations

import unittest

from reliability import SourceHistory, history_score, reliability


class TestReliability(unittest.TestCase):
    def test_high_trust_beats_low_trust(self):
        high = reliability(1.0, 1.0, verified=5, contradicted=0, consistency=1.0)
        low = reliability(0.2, 0.1, verified=0, contradicted=5, consistency=0.5)
        self.assertGreater(high, low)
        self.assertLessEqual(high, 1.0)
        self.assertGreaterEqual(low, 0.0)

    def test_history_is_laplace_smoothed(self):
        self.assertAlmostEqual(history_score(0, 0), 0.5)
        self.assertAlmostEqual(history_score(3, 1), 4 / 6)
        self.assertGreater(history_score(5, 0), history_score(0, 5))

    def test_reliability_is_claim_level(self):
        verifiable = reliability(1.0, 0.9, 2, 0, 1.0)
        unverifiable = reliability(1.0, 0.1, 2, 0, 1.0)
        self.assertGreater(verifiable, unverifiable)

    def test_conflict_reduces_reliability(self):
        consistent = reliability(0.6, 0.5, 1, 0, 1.0)
        conflicted = reliability(0.6, 0.5, 1, 0, 0.5)
        self.assertGreater(consistent, conflicted)

    def test_reliability_stays_bounded(self):
        for tier in (0.0, 0.5, 1.0):
            for ver in (0.0, 0.5, 1.0):
                for cons in (0.5, 1.0):
                    r = reliability(tier, ver, 0, 0, cons)
                    self.assertGreaterEqual(r, 0.0)
                    self.assertLessEqual(r, 1.0)

    def test_source_history_records_outcomes(self):
        h = SourceHistory()
        self.assertAlmostEqual(h.score, 0.5)
        h.record(True)
        h.record(False)
        self.assertAlmostEqual(h.score, 2 / 4)


if __name__ == "__main__":
    unittest.main()
