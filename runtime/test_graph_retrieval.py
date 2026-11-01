"""Tests for bounded typed graph retrieval."""
from __future__ import annotations

import unittest

from graph_retrieval import Edge, MemoryGraph, from_events
from memory import Event


class TestGraphRetrieval(unittest.TestCase):
    def setUp(self):
        self.g = MemoryGraph()
        self.g.add_edge(Edge("p:P1", "e:E1", "participates", 0.9))
        self.g.add_edge(Edge("e:E1", "p:P2", "participates", 0.9))
        self.g.add_edge(Edge("e:E1", "e:E2", "simulation", 1.0))

    def test_one_hop(self):
        hits = self.g.activate(["p:P1"], hops=1)
        self.assertEqual([h.node for h in hits], ["e:E1"])

    def test_two_hop(self):
        hits = self.g.activate(["p:P1"], hops=2)
        self.assertEqual({h.node for h in hits}, {"e:E1", "p:P2"})
        by = {h.node: h for h in hits}
        self.assertEqual(by["p:P2"].hop, 2)

    def test_hop_limit(self):
        hits = self.g.activate(["p:P1"], hops=1)
        self.assertNotIn("p:P2", [h.node for h in hits])

    def test_decay_reduces_score(self):
        hits = {h.node: h for h in self.g.activate(["p:P1"], hops=2)}
        self.assertGreater(hits["e:E1"].score, hits["p:P2"].score)

    def test_budget_caps_results(self):
        self.assertEqual(len(self.g.activate(["p:P1"], hops=2, budget=1)), 1)

    def test_simulation_edges_are_excluded_by_default(self):
        nodes = [h.node for h in self.g.activate(["e:E1"], hops=1)]
        self.assertNotIn("e:E2", nodes)
        nodes2 = [h.node for h in self.g.activate(["e:E1"], hops=1, allow_simulation=True)]
        self.assertIn("e:E2", nodes2)

    def test_from_events_builds_person_event_topic_commitment(self):
        ev = Event("E1", "x", person_ids=("P1",), topics=("work",), open_commitment=True)
        g = from_events([ev])
        self.assertEqual(g.edges_from("p:P1")[0].dst, "e:E1")
        self.assertIn("c:E1", [e.dst for e in g.edges_from("e:E1")])
        self.assertIn("t:work", [e.dst for e in g.edges_from("e:E1")])

    def test_deterministic(self):
        a = self.g.activate(["p:P1"], hops=2)
        b = self.g.activate(["p:P1"], hops=2)
        self.assertEqual([(h.node, h.score) for h in a], [(h.node, h.score) for h in b])


if __name__ == "__main__":
    unittest.main()
