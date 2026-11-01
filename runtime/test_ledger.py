"""Tests for evidence ledger, version chain, and forgetting policy."""
from __future__ import annotations

import unittest

from ledger import (
    Evidence,
    EvidenceLedger,
    ForgettingPolicy,
    MemoryRecord,
    VersionChain,
    retention,
)


class TestEvidenceLedger(unittest.TestCase):
    def test_recall_does_not_add_evidence(self):
        led = EvidenceLedger()
        led.add(Evidence("C1", "E1", "direct", "方案已改", 0.0))
        for _ in range(50):
            led.recall("C1")
        self.assertEqual(led.evidence_count("C1"), 1)
        self.assertEqual(led.recall_count("C1"), 50)

    def test_duplicate_event_id_counts_once(self):
        led = EvidenceLedger()
        led.add(Evidence("C1", "E1", "direct", "a"))
        led.add(Evidence("C1", "E1", "relay", "a"))
        self.assertEqual(led.evidence_count("C1"), 1)

    def test_distinct_events_and_sources(self):
        led = EvidenceLedger()
        led.add(Evidence("C1", "E1", "direct", "a"))
        led.add(Evidence("C1", "E2", "document", "a"))
        self.assertEqual(led.evidence_count("C1"), 2)
        self.assertEqual(led.distinct_sources("C1"), 2)

    def test_conflicts_are_preserved(self):
        led = EvidenceLedger()
        led.add(Evidence("C1", "E1", "direct", "没回应"))
        led.add(Evidence("C1", "E2", "relay", "在忙"))
        c = led.conflicts("C1")
        self.assertEqual(len(c), 1)
        self.assertEqual(set(c[0]), {"没回应", "在忙"})


class TestVersionChain(unittest.TestCase):
    def test_low_pe_is_access_only(self):
        ch = VersionChain(theta_pe=0.5, theta_novelty=0.4)
        ch.append("v1 content", ["E1"], 0.0)
        v = ch.append("same", ["E1"], 1.0, prediction_error=0.1, novelty=0.1)
        self.assertEqual(v.version_id, "v1")
        self.assertEqual(len(ch.history()), 1)
        self.assertEqual(ch.access_count, 1)

    def test_high_pe_creates_new_version_and_preserves_old(self):
        ch = VersionChain(theta_pe=0.5, theta_novelty=0.4)
        ch.append("最初解释：他在忙", ["E1"], 0.0)
        v2 = ch.append("新解释：他回避", ["E1", "E2"], 10.0,
                       prediction_error=0.9, novelty=0.6)
        self.assertEqual(v2.version_id, "v2")
        self.assertEqual(v2.supersedes, "v1")
        self.assertEqual(len(ch.history()), 2)
        self.assertEqual(ch.history()[0].content, "最初解释：他在忙")
        self.assertEqual(ch.current().content, "新解释：他回避")

    def test_novelty_can_trigger_update(self):
        ch = VersionChain(theta_pe=0.5, theta_novelty=0.4)
        ch.append("v1", ["E1"], 0.0)
        v2 = ch.append("v2", ["E1", "E3"], 5.0, prediction_error=0.0, novelty=0.8)
        self.assertEqual(v2.version_id, "v2")


class TestForgetting(unittest.TestCase):
    def test_retention_decays_with_age_and_recovers_with_retrieval(self):
        fresh = retention(0.0, 0)
        old = retention(365.0, 0)
        spaced = retention(365.0, distinct_retrievals=8)
        self.assertGreater(fresh, old)
        self.assertGreater(spaced, old)

    def test_commitment_and_safety_are_exempt(self):
        pol = ForgettingPolicy(cold_threshold=0.15)
        c = MemoryRecord("E1", open_commitment=True)
        s = MemoryRecord("E2", safety_critical=True)
        x = MemoryRecord("E3", explicit_remember=True)
        n = MemoryRecord("E4")
        for rec in (c, s, x):
            d = pol.decide(rec, age_days=3650)
            self.assertEqual(d.state, "active")
            self.assertEqual(d.reason, "exempt")
        dn = pol.decide(n, age_days=3650)
        self.assertEqual(dn.state, "cold")

    def test_only_reliable_recall_stabilises(self):
        high = retention(365.0, 8, source_reliability=1.0)
        low = retention(365.0, 8, source_reliability=0.1)
        none = retention(365.0, 0)
        self.assertGreater(high, low)
        self.assertGreater(low, none)
        self.assertAlmostEqual(retention(365.0, 8, source_reliability=0.0), none)

    def test_negative_high_intensity_is_retained(self):
        high = retention(365.0, 0, relationship_intensity=0.9)
        low = retention(365.0, 0, relationship_intensity=0.1)
        self.assertGreater(high, low)

    def test_relationship_weight_is_a_fallback(self):
        a = retention(365.0, 0, relationship_weight=0.8)
        b = retention(365.0, 0, relationship_intensity=0.8)
        self.assertAlmostEqual(a, b)

    def test_forgetting_never_deletes_raw_events(self):
        pol = ForgettingPolicy(cold_threshold=0.15)
        rec = MemoryRecord("E1")
        d = pol.decide(rec, age_days=3650)
        self.assertEqual(d.state, "cold")
        self.assertTrue(pol.is_cold("E1"))
        self.assertEqual(pol.deleted(), set())


if __name__ == "__main__":
    unittest.main()
