"""Tests for reliability history in the evidence ledger."""
from __future__ import annotations

import unittest

from ledger import Evidence, EvidenceLedger


class TestReliabilityHistory(unittest.TestCase):
    def setUp(self):
        self.led = EvidenceLedger()
        self.led.add(Evidence("C1", "E1", "relay", "x", tier=2))

    def test_verified_outcomes_raise_reliability(self):
        before = self.led.claim_reliability("C1", "E1", verifiability=0.5)
        for _ in range(3):
            self.led.record_outcome("relay", True)
        after = self.led.claim_reliability("C1", "E1", verifiability=0.5)
        self.assertGreater(after, before)

    def test_contradicted_outcomes_lower_reliability(self):
        before = self.led.claim_reliability("C1", "E1", verifiability=0.5)
        for _ in range(3):
            self.led.record_outcome("relay", False)
        after = self.led.claim_reliability("C1", "E1", verifiability=0.5)
        self.assertLess(after, before)

    def test_same_source_different_claim_verifiability(self):
        high = self.led.claim_reliability("C1", "E1", verifiability=0.9)
        low = self.led.claim_reliability("C1", "E1", verifiability=0.1)
        self.assertGreater(high, low)


if __name__ == "__main__":
    unittest.main()
