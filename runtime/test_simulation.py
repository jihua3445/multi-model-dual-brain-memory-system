"""Tests for the simulation write boundary."""
from __future__ import annotations

import unittest

from ledger import EvidenceLedger
from simulation import Scenario, can_write_as_fact, simulate, to_hypothesis


class TestSimulation(unittest.TestCase):
    def test_scenarios_are_not_facts(self):
        out = simulate(["E1", "E2"], ["A", "B"])
        self.assertEqual(len(out), 2)
        for s in out:
            self.assertEqual(s.source, "simulation")
            self.assertFalse(s.is_fact)
            self.assertFalse(can_write_as_fact(s))

    def test_confidence_does_not_make_it_a_fact(self):
        s = Scenario("S9", "x", ("E1",), confidence=1.0)
        self.assertFalse(can_write_as_fact(s))

    def test_hypothesis_requires_evidence(self):
        s = Scenario("S1", "x", ("E1",))
        with self.assertRaises(ValueError):
            to_hypothesis(s, [])
        h = to_hypothesis(s, ["E2"])
        self.assertEqual(h.status, "hypothesis")
        self.assertEqual(h.evidence_event_ids, ("E2",))

    def test_simulation_does_not_enter_evidence_ledger(self):
        led = EvidenceLedger()
        simulate(["E1"], ["A"])
        self.assertEqual(led.evidence_count("C1"), 0)

    def test_simulation_is_deterministic(self):
        a = simulate(["E1"], ["A", "B"])
        b = simulate(["E1"], ["A", "B"])
        self.assertEqual([x.scenario_id for x in a], [x.scenario_id for x in b])
        self.assertEqual([x.content for x in a], [x.content for x in b])


if __name__ == "__main__":
    unittest.main()
