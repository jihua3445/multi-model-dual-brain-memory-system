"""Tests for the primitive library and typed composition."""
from __future__ import annotations

import unittest

from primitives import Primitive, PrimitiveLibrary, compose_from_primitives
from simulation import can_write_as_fact


def lib():
    L = PrimitiveLibrary()
    L.add(Primitive("person", "p1", "小林", ("work",)))
    L.add(Primitive("person", "p2", "小周", ("family",)))
    L.add(Primitive("place", "l1", "会议室"))
    L.add(Primitive("action", "a1", "看方案"))
    L.add(Primitive("goal", "g1", "反馈"))
    return L


class TestPrimitives(unittest.TestCase):
    def test_query_by_kind(self):
        self.assertEqual([p.pid for p in lib().query("person")], ["p1", "p2"])

    def test_slots_are_type_constrained(self):
        out = compose_from_primitives(lib(), ["person", "action", "goal"])
        self.assertTrue(out)
        for s in out:
            self.assertIn("person:", s.content)
            self.assertIn("action:", s.content)
            self.assertNotIn("place:", s.content)

    def test_cross_event_reuse(self):
        out = compose_from_primitives(lib(), ["person", "action"], max_scenarios=2)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].primitive_ids[0], "p1")
        self.assertEqual(out[1].primitive_ids[0], "p2")

    def test_output_is_simulation_not_fact(self):
        out = compose_from_primitives(lib(), ["person", "goal"])
        for s in out:
            self.assertEqual(s.source, "compositional_replay")
            self.assertFalse(s.is_fact)
            self.assertFalse(can_write_as_fact(s))
            self.assertTrue(s.primitive_ids)

    def test_missing_kind_raises(self):
        L = lib()
        with self.assertRaises(ValueError):
            compose_from_primitives(L, ["person", "relation"])

    def test_deterministic(self):
        a = compose_from_primitives(lib(), ["person", "action"], max_scenarios=2)
        b = compose_from_primitives(lib(), ["person", "action"], max_scenarios=2)
        self.assertEqual([s.content for s in a], [s.content for s in b])


if __name__ == "__main__":
    unittest.main()
