"""Tests for event segmentation and pipeline integration."""
from __future__ import annotations

import unittest

from pipeline import Pipeline
from segmentation import Percept, segment
from state_params import SystemState

NOW = 1_700_000_000.0


def p(i, text="t", ts=None, person=("P1",), topic=("work",), expected=0.0,
      observed=0.0, precision=1.0, salience=0.9, commitment=False):
    return Percept(text=text, ts=NOW + (i if ts is None else ts), person_ids=person,
                   topics=topic, expected=expected, observed=observed,
                   precision=precision, salience=salience, open_commitment=commitment)


class TestSegmentation(unittest.TestCase):
    def test_low_error_same_context_is_one_segment(self):
        segs = segment([p(0, "a"), p(1, "b"), p(2, "c")])
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].reason, "start")

    def test_prediction_error_splits(self):
        segs = segment([p(0, "a"), p(1, "b"), p(2, "c", expected=0.0, observed=0.9)])
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[1].reason, "prediction_error")

    def test_topic_change_splits(self):
        segs = segment([p(0, topic=("work",)), p(1, topic=("family",))])
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[1].reason, "topic_change")

    def test_person_change_splits(self):
        segs = segment([p(0, person=("P1",)), p(1, person=("P2",))])
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[1].reason, "person_change")

    def test_time_gap_splits(self):
        segs = segment([p(0), p(1, ts=200.0)])
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[1].reason, "time_gap")

    def test_max_duration_splits(self):
        segs = segment([p(0), p(1, ts=300.0), p(2, ts=700.0)],
                       theta_gap=1000.0, theta_max=600.0)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[1].reason, "max_duration")

    def test_low_precision_suppresses_error_boundary(self):
        segs = segment([p(0), p(1, observed=0.9, precision=0.1)])
        self.assertEqual(len(segs), 1)

    def test_to_event_merges_fields(self):
        seg = segment([p(0, "a", person=("P1",), topic=("work",), salience=0.4),
                       p(1, "b", person=("P1", "P2"), topic=("work", "family"), salience=0.8)])[0]
        e = seg.to_event("E1", claim_id="C1")
        self.assertEqual(e.text, "a b")
        self.assertEqual(set(e.person_ids), {"P1", "P2"})
        self.assertEqual(set(e.topics), {"work", "family"})
        self.assertEqual(e.salience, 0.8)
        self.assertEqual(e.claim_id, "C1")
        self.assertEqual(e.ts, NOW)

    def test_empty(self):
        self.assertEqual(segment([]), [])

    def test_pipeline_ingests_segments(self):
        pipe = Pipeline()
        state = SystemState(goal_pressure=0.8, uncertainty=0.5)
        accepted = pipe.ingest_percepts(
            [p(0, "a"), p(1, "b"), p(2, "c", observed=0.9)], state,
            event_id_prefix="S", claim_id="C1")
        self.assertEqual(len(accepted), 2)
        self.assertEqual(len(pipe.store.all()), 2)
        self.assertEqual(pipe.ledger.evidence_count("C1"), 2)
        self.assertEqual(pipe.trace[-1]["step"], "segment")


if __name__ == "__main__":
    unittest.main()
