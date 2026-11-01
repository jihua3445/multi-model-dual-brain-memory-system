"""Tests for relationship memory as threshold adjustment."""
from __future__ import annotations

import unittest

from relationship import Relationship, RelationshipEvidence


def ev(eid="E1", delta=0.5, reliability=1.0, salience=1.0, conflict=False):
    return RelationshipEvidence(eid, "trust", delta, reliability, salience, conflict)


class TestRelationship(unittest.TestCase):
    def test_positive_and_negative_update_trust(self):
        up = Relationship()
        up.update(ev(delta=0.5))
        self.assertGreater(up.values["trust"], 0.0)
        down = Relationship()
        down.update(ev(delta=-0.5))
        self.assertLess(down.values["trust"], 0.0)

    def test_negativity_bias(self):
        up = Relationship()
        up.update(ev(delta=0.5))
        down = Relationship()
        down.update(ev(delta=-0.5))
        self.assertGreater(abs(down.values["trust"]), abs(up.values["trust"]))

    def test_low_reliability_is_downweighted(self):
        weak = Relationship()
        weak.update(ev(delta=-0.5, reliability=0.1))
        strong = Relationship()
        strong.update(ev(delta=-0.5, reliability=1.0))
        self.assertGreater(weak.values["trust"], strong.values["trust"])

    def test_conflict_is_downweighted(self):
        normal = Relationship()
        normal.update(ev(delta=-0.5, conflict=False))
        conflicted = Relationship()
        conflicted.update(ev(delta=-0.5, conflict=True))
        self.assertGreater(conflicted.values["trust"], normal.values["trust"])

    def test_co_presence_is_downweighted(self):
        actual = Relationship()
        actual.update(RelationshipEvidence("E1", "trust", 0.5, 1.0, 1.0, False, 1.0))
        co = Relationship()
        co.update(RelationshipEvidence("E2", "trust", 0.5, 1.0, 1.0, False, 0.3))
        self.assertGreater(actual.values["trust"], co.values["trust"])

    def test_interaction_weight_defaults_to_full(self):
        r = Relationship()
        r.update(RelationshipEvidence("E1", "trust", 0.5, 1.0, 1.0))
        self.assertAlmostEqual(r.values["trust"], 0.05)

    def test_evidence_count_is_distinct_event_ids(self):
        r = Relationship()
        r.update(ev("E1"))
        r.update(ev("E1"))
        self.assertEqual(r.evidence_count("trust"), 1)
        r.update(ev("E2"))
        self.assertEqual(r.evidence_count("trust"), 2)

    def test_commitment_requires_trust_threshold(self):
        low = Relationship(values={"trust": 0.4, "closeness": 0.0, "commitment": 0.0, "boundary": 0.0})
        high = Relationship(values={"trust": 0.6, "closeness": 0.0, "commitment": 0.0, "boundary": 0.0})
        self.assertFalse(low.can_commit(threshold=0.5, capacity=1.0, cost=0.5))
        self.assertTrue(high.can_commit(threshold=0.5, capacity=1.0, cost=0.5))

    def test_commitment_requires_capacity(self):
        r = Relationship(values={"trust": 0.9, "closeness": 0.0, "commitment": 0.0, "boundary": 0.0})
        self.assertFalse(r.can_commit(threshold=0.5, capacity=0.3, cost=0.6))
        self.assertTrue(r.can_commit(threshold=0.5, capacity=0.8, cost=0.6))

    def test_more_dimensions_update_independently(self):
        r = Relationship()
        r.update(RelationshipEvidence("E1", "familiarity", 0.6, 1.0, 1.0))
        r.update(RelationshipEvidence("E2", "cooperation", 0.4, 1.0, 1.0))
        self.assertGreater(r.values["familiarity"], 0.0)
        self.assertGreater(r.values["cooperation"], 0.0)
        self.assertEqual(r.evidence_count("familiarity"), 1)
        self.assertEqual(r.evidence_count("cooperation"), 1)

    def test_negative_high_intensity_is_not_trust(self):
        r = Relationship(values={"trust": -0.9, "closeness": -0.8, "commitment": 0.0,
                                 "boundary": -0.7, "familiarity": 0.5, "cooperation": 0.0})
        self.assertEqual(r.intensity(), 0.8)
        self.assertLess(r.valence(), 0.0)
        self.assertFalse(r.can_commit(threshold=0.5, capacity=1.0, cost=0.5))

    def test_valence_and_intensity_are_separate(self):
        close = Relationship(values={"trust": 0.9, "closeness": 0.9, "commitment": 0.8,
                                     "boundary": 0.7, "familiarity": 0.8, "cooperation": 0.8})
        hate = Relationship(values={"trust": -0.9, "closeness": -0.9, "commitment": -0.8,
                                    "boundary": -0.7, "familiarity": 0.8, "cooperation": -0.8})
        self.assertAlmostEqual(close.intensity(), hate.intensity())
        self.assertGreater(close.valence(), 0.0)
        self.assertLess(hate.valence(), 0.0)

    def test_dislike_but_trustworthy(self):
        r = Relationship(values={"trust": 0.9, "closeness": -0.9, "commitment": 0.0,
                                 "boundary": 0.0, "familiarity": 0.8, "cooperation": 0.7})
        self.assertLess(r.valence(), 0.0)
        self.assertTrue(r.can_commit(threshold=0.5, capacity=1.0, cost=0.5))

    def test_like_but_untrustworthy(self):
        r = Relationship(values={"trust": -0.6, "closeness": 0.9, "commitment": 0.0,
                                 "boundary": 0.0, "familiarity": 0.8, "cooperation": 0.0})
        self.assertGreater(r.valence(), 0.0)
        self.assertFalse(r.can_commit(threshold=0.5, capacity=1.0, cost=0.5))

    def test_trust_updates_independently_of_affect(self):
        r = Relationship()
        r.update(RelationshipEvidence("E1", "trust", 0.8, 1.0, 1.0))
        self.assertGreater(r.values["trust"], 0.0)
        self.assertEqual(r.values.get("closeness", 0.0), 0.0)

    def test_unknown_dimension_raises(self):
        r = Relationship()
        with self.assertRaises(ValueError):
            r.update(RelationshipEvidence("E1", "unknown", 0.1))


if __name__ == "__main__":
    unittest.main()
