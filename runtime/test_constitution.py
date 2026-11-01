"""Tests for constitutive proposals, ratification, cooling-off and rollback."""
from __future__ import annotations

import unittest

from constitution import (
    ConstitutionStore,
    ProposalError,
    RatificationPermissionError,
)

DAY = 86400.0


class TestConstitution(unittest.TestCase):
    def setUp(self):
        self.store = ConstitutionStore()

    def test_backend_proposal_does_not_change_constitution(self):
        p = self.store.propose("goal", "g1", "每周复盘", "backend:consolidator", ["E1"], now=0)
        self.assertEqual(p.status, "pending")
        self.assertEqual(self.store.constitution.items["goals"], {})

    def test_main_ratifies_ordinary_goal(self):
        p = self.store.propose("goal", "g1", "每周复盘", "backend:consolidator", ["E1"], now=0)
        done = self.store.ratify(p.proposal_id, "main:session", now=10)
        self.assertEqual(done.status, "ratified")
        self.assertEqual(self.store.constitution.items["goals"]["g1"], "每周复盘")
        self.assertEqual(len(self.store.ledger.entries), 1)
        self.assertTrue(self.store.ledger.verify())

    def test_core_change_requires_user_cosign(self):
        p = self.store.propose("value", "honesty", "always", "backend:consolidator",
                               ["E1"], core=True, now=0)
        with self.assertRaises(RatificationPermissionError):
            self.store.ratify(p.proposal_id, "main:session", now=10)
        self.assertEqual(p.status, "pending")
        self.assertEqual(self.store.constitution.items["values"], {})
        self.assertEqual(len(self.store.ledger.entries), 0)

    def test_core_with_user_cosign_applies(self):
        p = self.store.propose("value", "honesty", "always", "backend:consolidator",
                               ["E1"], core=True, now=0)
        done = self.store.ratify(p.proposal_id, "main:session", now=10, cosignatory="user")
        self.assertEqual(done.status, "ratified")
        self.assertEqual(self.store.constitution.items["values"]["honesty"], "always")
        self.assertEqual(done.cosigned_by, "user")

    def test_cooling_off_delays_application(self):
        p = self.store.propose("role", "role_x", "合作者", "backend:consolidator",
                               ["E1"], core=True, cooling_off_seconds=7 * DAY, now=0)
        cooling = self.store.ratify(p.proposal_id, "main:session", now=10, cosignatory="user")
        self.assertEqual(cooling.status, "cooling")
        self.assertEqual(self.store.constitution.items["roles"], {})
        with self.assertRaises(ProposalError):
            self.store.finalize_cooling(p.proposal_id, "main:session", now=6 * DAY)
        done = self.store.finalize_cooling(p.proposal_id, "main:session", now=8 * DAY)
        self.assertEqual(done.status, "ratified")
        self.assertEqual(self.store.constitution.items["roles"]["role_x"], "合作者")

    def test_reject_and_expire(self):
        p = self.store.propose("habit_rule", "h1", "if A then B", "backend:consolidator",
                               ["E1"], now=0, expires_at=100)
        self.store.reject(p.proposal_id, "main:session", "evidence weak", now=10)
        self.assertEqual(p.status, "rejected")
        self.assertEqual(len(self.store.ledger.entries), 1)

        q = self.store.propose("habit_rule", "h2", "if C then D", "backend:consolidator",
                               ["E2"], now=0, expires_at=50)
        self.assertEqual(self.store.expire(now=60), [q.proposal_id])
        with self.assertRaises(ProposalError):
            self.store.ratify(q.proposal_id, "main:session", now=70)

    def test_rollback_restores_previous_value(self):
        p1 = self.store.propose("goal", "g1", "v1", "backend:consolidator", ["E1"], now=0)
        self.store.ratify(p1.proposal_id, "main:session", now=1)
        p2 = self.store.propose("goal", "g1", "v2", "backend:consolidator", ["E2"], now=2)
        self.store.ratify(p2.proposal_id, "main:session", now=3)
        self.assertEqual(self.store.constitution.items["goals"]["g1"], "v2")
        self.store.rollback(p2.proposal_id, "main:session", now=4)
        self.assertEqual(self.store.constitution.items["goals"]["g1"], "v1")
        self.assertEqual(p2.status, "rolled_back")
        self.assertTrue(self.store.ledger.verify())

    def test_ledger_detects_tampering(self):
        p = self.store.propose("goal", "g1", "v1", "backend:consolidator", ["E1"], now=0)
        self.store.ratify(p.proposal_id, "main:session", now=1)
        self.assertTrue(self.store.ledger.verify())
        self.store.ledger.entries[0]["decision"] = "forged"
        self.assertFalse(self.store.ledger.verify())

    def test_proposals_require_evidence_and_known_type(self):
        with self.assertRaises(ProposalError):
            self.store.propose("goal", "g1", "v", "backend", [])
        with self.assertRaises(ProposalError):
            self.store.propose("unknown", "k", "v", "backend", ["E1"])

    def test_engineering_mode_user_has_highest_permission(self):
        store = ConstitutionStore(mode="engineering")
        p = store.propose("value", "honesty", "always", "backend", ["E1"], core=True, now=0)
        with self.assertRaises(RatificationPermissionError):
            store.ratify(p.proposal_id, "main:session", now=1)
        done = store.ratify(p.proposal_id, "user", now=2)
        self.assertEqual(done.status, "ratified")
        self.assertEqual(store.constitution.items["values"]["honesty"], "always")

    def test_cannot_ratify_twice(self):
        p = self.store.propose("goal", "g1", "v1", "backend:consolidator", ["E1"], now=0)
        self.store.ratify(p.proposal_id, "main:session", now=1)
        with self.assertRaises(ProposalError):
            self.store.ratify(p.proposal_id, "main:session", now=2)


if __name__ == "__main__":
    unittest.main()
