"""Round-trip and validation tests for the compact agent format.

Run from the backend/ directory:

    PYTHONPATH=. python -m unittest discover -s tests -v

The sign conventions asserted here are the ones tests/test_fem.py pins against
closed-form results: +y is up, a POINT load of positive value at angle -90
pulls down, and a positive DISTRIBUTED q acts along the member's local -y.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugins.agent.checks import geometry_warnings
from src.plugins.agent.schema import SchemaError, compact, expand

BEAM = {
    "nodes": [
        {"id": "A", "x": 0, "y": 0, "support": "festlager"},
        {"id": "B", "x": 6, "y": 0, "support": "loslager"},
    ],
    "members": [{"start": "A", "end": "B"}],
    "loads": [{"on": "A-B", "type": "distributed", "q": 10}],
}


class TestExpand(unittest.TestCase):
    def test_beam_expands_to_editor_shape(self):
        system, warnings = expand(BEAM)
        self.assertEqual(warnings, [])

        a, b = system["nodes"]
        self.assertEqual(a["position"], {"x": 0.0, "y": 0.0})
        self.assertEqual(a["supports"], {"fixN": True, "fixV": True, "fixM": False})
        self.assertEqual(b["supports"], {"fixN": False, "fixV": True, "fixM": False})

        member = system["members"][0]
        self.assertEqual(member["id"], "A-B")
        self.assertEqual((member["startNodeId"], member["endNodeId"]), ("A", "B"))
        self.assertEqual(member["releases"]["start"],
                         {"fx": False, "fy": False, "mz": False})
        # Absent properties come from the same defaults the editor uses.
        self.assertEqual(member["properties"]["E"], 210e9)

        load = system["loads"][0]
        self.assertEqual(load["scope"], "MEMBER")
        self.assertEqual(load["type"], "DISTRIBUTED")
        self.assertEqual(load["memberId"], "A-B")
        self.assertEqual((load["startRatio"], load["endRatio"]), (0.0, 1.0))
        self.assertEqual(load["value"], 10.0)

    def test_node_ids_survive(self):
        """An agent that writes "A" must read "A" back, not a UUID."""
        system, _ = expand(BEAM)
        self.assertEqual([n["id"] for n in system["nodes"]], ["A", "B"])

    def test_support_and_hinge_aliases(self):
        doc = {
            "nodes": [
                {"id": "A", "x": 0, "y": 0, "support": "Feste Einspannung"},
                {"id": "B", "x": 4, "y": 0, "support": "PINNED"},
            ],
            "members": [{"start": "A", "end": "B", "hinge_end": "gelenk"}],
        }
        system, _ = expand(doc)
        self.assertEqual(system["nodes"][0]["supports"],
                         {"fixN": True, "fixV": True, "fixM": True})
        self.assertEqual(system["nodes"][1]["supports"],
                         {"fixN": True, "fixV": True, "fixM": False})
        self.assertTrue(system["members"][0]["releases"]["end"]["mz"])

    def test_point_load_defaults_to_gravity(self):
        doc = dict(BEAM, loads=[{"on": "B", "type": "point", "value": 25}])
        load = expand(doc)[0]["loads"][0]
        self.assertEqual(load["scope"], "NODE")
        self.assertEqual(load["angle"], -90.0)

    def test_member_point_load_position(self):
        doc = dict(BEAM, loads=[{"on": "A-B", "type": "point", "value": 5, "at": 0.25}])
        load = expand(doc)[0]["loads"][0]
        self.assertEqual(load["scope"], "MEMBER")
        self.assertEqual(load["ratio"], 0.25)

    def test_trapezoidal_distributed_load(self):
        doc = dict(BEAM, loads=[{"on": "A-B", "type": "distributed",
                                 "q_start": 4, "q_end": 10, "from": 0.2, "to": 0.8}])
        load = expand(doc)[0]["loads"][0]
        self.assertEqual((load["startValue"], load["endValue"]), (4.0, 10.0))
        self.assertEqual((load["startRatio"], load["endRatio"]), (0.2, 0.8))

    def test_reversed_member_reference_is_accepted(self):
        doc = dict(BEAM, loads=[{"on": "B-A", "type": "distributed", "q": 3}])
        self.assertEqual(expand(doc)[0]["loads"][0]["memberId"], "A-B")

    def test_dynamic_load_needs_a_signal(self):
        doc = dict(BEAM, loads=[{"on": "B", "type": "dynamic_force", "value": 10}])
        with self.assertRaises(SchemaError):
            expand(doc)

    def test_dynamic_load_with_signal(self):
        doc = dict(BEAM, loads=[{
            "on": "B", "type": "dynamic_force",
            "signal": {"type": "harmonic", "amplitude": 12, "frequency": 3},
        }])
        load = expand(doc)[0]["loads"][0]
        self.assertEqual(load["type"], "DYNAMIC_FORCE")
        self.assertEqual(load["signal"]["type"], "HARMONIC")
        self.assertEqual(load["signal"]["frequency"], 3.0)


class TestExpandErrors(unittest.TestCase):
    def test_unknown_node_reference_names_the_known_ones(self):
        doc = dict(BEAM, members=[{"start": "A", "end": "Z"}])
        with self.assertRaises(SchemaError) as ctx:
            expand(doc)
        self.assertIn("Z", str(ctx.exception))
        self.assertIn("A", str(ctx.exception))

    def test_duplicate_node_id(self):
        doc = dict(BEAM, nodes=[{"id": "A", "x": 0, "y": 0},
                                {"id": "A", "x": 1, "y": 0}])
        with self.assertRaises(SchemaError):
            expand(doc)

    def test_unknown_support(self):
        doc = dict(BEAM, nodes=[{"id": "A", "x": 0, "y": 0, "support": "schwebelager"}])
        with self.assertRaises(SchemaError) as ctx:
            expand(doc)
        self.assertIn("festlager", str(ctx.exception))

    def test_moment_on_a_member_is_rejected(self):
        doc = dict(BEAM, loads=[{"on": "A-B", "type": "moment", "value": 5}])
        with self.assertRaises(SchemaError):
            expand(doc)

    def test_distributed_load_on_a_node_is_rejected(self):
        doc = dict(BEAM, loads=[{"on": "A", "type": "distributed", "q": 5}])
        with self.assertRaises(SchemaError):
            expand(doc)

    def test_self_loop_member(self):
        doc = dict(BEAM, members=[{"start": "A", "end": "A"}])
        with self.assertRaises(SchemaError):
            expand(doc)

    def test_ratio_out_of_range(self):
        doc = dict(BEAM, loads=[{"on": "A-B", "type": "point", "value": 5, "at": 1.5}])
        with self.assertRaises(SchemaError):
            expand(doc)


class TestRoundTrip(unittest.TestCase):
    def assert_round_trip(self, doc):
        expanded, _ = expand(doc)
        again, _ = expand(compact(expanded))
        self.assertEqual(expanded, again)

    def test_beam(self):
        self.assert_round_trip(BEAM)

    def test_frame_with_hinges_and_mixed_loads(self):
        self.assert_round_trip({
            "nodes": [
                {"id": "A", "x": 0, "y": 0, "support": "feste_einspannung"},
                {"id": "B", "x": 0, "y": 4},
                {"id": "C", "x": 6, "y": 4},
                {"id": "D", "x": 6, "y": 0, "support": "loslager", "rotation": 15},
            ],
            "members": [
                {"start": "A", "end": "B"},
                {"start": "B", "end": "C", "hinge_start": "vollgelenk", "I": 0.0005},
                {"start": "C", "end": "D", "hinge_end": "normalkraftgelenk"},
            ],
            "loads": [
                {"on": "B-C", "type": "distributed", "q_start": 4, "q_end": 9},
                {"on": "B", "type": "point", "value": 20, "angle": 0},
                {"on": "C", "type": "moment", "value": -8},
                {"on": "C-D", "type": "point", "value": 7, "at": 0.3},
            ],
        })

    def test_compact_omits_what_is_default(self):
        small = compact(expand(BEAM)[0])
        self.assertNotIn("support", small["nodes"][0].keys() - {"support"})
        self.assertEqual(small["nodes"][0]["support"], "festlager")
        # A member with default properties and no releases stays three fields.
        self.assertEqual(set(small["members"][0]), {"id", "start", "end"})


class TestGeometryWarnings(unittest.TestCase):
    def test_clean_system_is_quiet(self):
        self.assertEqual(geometry_warnings(expand(BEAM)[0]), [])

    def test_duplicate_node(self):
        doc = {
            "nodes": [
                {"id": "A", "x": 0, "y": 0, "support": "festlager"},
                {"id": "B", "x": 6, "y": 0, "support": "loslager"},
                {"id": "C", "x": 6.001, "y": 0},
            ],
            "members": [{"start": "A", "end": "B"}, {"start": "B", "end": "C"}],
        }
        warnings = geometry_warnings(expand(doc)[0])
        self.assertTrue(any("entered twice" in w for w in warnings), warnings)

    def test_unconnected_node_and_missing_supports(self):
        doc = {
            "nodes": [{"id": "A", "x": 0, "y": 0}, {"id": "B", "x": 3, "y": 0},
                      {"id": "C", "x": 9, "y": 0}],
            "members": [{"start": "A", "end": "B"}],
        }
        warnings = geometry_warnings(expand(doc)[0])
        self.assertTrue(any("node C is not connected" in w for w in warnings), warnings)
        self.assertTrue(any("no node carries a support" in w for w in warnings), warnings)


if __name__ == "__main__":
    unittest.main()
