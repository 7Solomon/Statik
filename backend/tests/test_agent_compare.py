"""The measuring instrument has to be right before its readings mean anything.

Run from the backend/ directory:

    PYTHONPATH=. python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugins.agent.compare import (
    aggregate, compare_systems, identifiability, unobservable_nodes,
)

FRAME = {
    "nodes": [
        {"id": "A", "x": 0, "y": 0, "support": "feste_einspannung"},
        {"id": "B", "x": 0, "y": 4},
        {"id": "C", "x": 6, "y": 4},
        {"id": "D", "x": 6, "y": 0, "support": "festlager"},
    ],
    "members": [
        {"id": "A-B", "start": "A", "end": "B"},
        {"id": "B-C", "start": "B", "end": "C"},
        {"id": "C-D", "start": "C", "end": "D", "hinge_start": "vollgelenk"},
    ],
    "loads": [
        {"id": "L1", "on": "B-C", "type": "distributed", "q": 12},
        {"id": "L2", "on": "B", "type": "point", "value": 20, "angle": 0},
    ],
}


def renamed_and_rescaled(system, factor=3.7, dx=100.0, dy=-40.0, prefix="n"):
    """The same system as an agent would plausibly write it: other names,
    other origin, other scale."""
    names = {n["id"]: f"{prefix}{i}" for i, n in enumerate(system["nodes"])}
    return {
        "nodes": [{**n, "id": names[n["id"]],
                   "x": n["x"] * factor + dx, "y": n["y"] * factor + dy}
                  for n in system["nodes"]],
        "members": [{**m, "id": f"{names[m['start']]}-{names[m['end']]}",
                     "start": names[m["start"]], "end": names[m["end"]]}
                    for m in system["members"]],
        "loads": [{**l, "on": (names[l["on"]] if l["on"] in names
                               else f"{names[l['on'].split('-')[0]]}-{names[l['on'].split('-')[1]]}")}
                  for l in system["loads"]],
    }


class TestIdentity(unittest.TestCase):
    def test_a_system_scores_perfectly_against_itself(self):
        r = compare_systems(FRAME, FRAME)
        self.assertTrue(r["fully_correct"], r["notes"])
        self.assertEqual(r["members"]["f1"], 1.0)
        self.assertEqual(r["supports"]["accuracy"], 1.0)
        self.assertEqual(r["loads"]["f1"], 1.0)

    def test_names_scale_and_origin_do_not_matter(self):
        r = compare_systems(FRAME, renamed_and_rescaled(FRAME))
        self.assertTrue(r["fully_correct"], r["notes"])

    def test_member_written_the_other_way_round_still_matches(self):
        flipped = dict(FRAME, members=[
            {"id": "B-A", "start": "B", "end": "A"},
            {"id": "C-B", "start": "C", "end": "B"},
            {"id": "D-C", "start": "D", "end": "C", "hinge_end": "vollgelenk"},
        ])
        r = compare_systems(FRAME, flipped)
        self.assertEqual(r["members"]["f1"], 1.0, r["notes"])
        self.assertEqual(r["releases"]["accuracy"], 1.0, r["notes"])


class TestCatchesRealErrors(unittest.TestCase):
    def test_mirrored_asymmetric_system_is_caught_by_position(self):
        asymmetric = dict(
            FRAME,
            nodes=FRAME["nodes"] + [{"id": "E", "x": 9, "y": 6}],
            members=FRAME["members"] + [{"id": "C-E", "start": "C", "end": "E"}],
        )
        mirrored = dict(asymmetric,
                        nodes=[{**n, "y": -n["y"]} for n in asymmetric["nodes"]])
        r = compare_systems(asymmetric, mirrored)
        self.assertLess(r["nodes"]["f1"], 1.0, r["notes"])
        self.assertFalse(r["fully_correct"])

    def test_mirrored_symmetric_system_is_caught_by_the_supports(self):
        """A flipped rectangle occupies the same four corners, so position
        matching alone cannot see it - the supports move, and that is what
        gives it away. Worth pinning: it is the one case where a real error
        leaves the geometry score untouched."""
        mirrored = dict(FRAME, nodes=[{**n, "y": -n["y"]} for n in FRAME["nodes"]])
        r = compare_systems(FRAME, mirrored)
        self.assertEqual(r["nodes"]["f1"], 1.0)
        self.assertLess(r["supports"]["accuracy"], 1.0)
        self.assertFalse(r["fully_correct"])

    def test_missing_member(self):
        r = compare_systems(FRAME, dict(FRAME, members=FRAME["members"][:2]))
        self.assertLess(r["members"]["f1"], 1.0)
        self.assertTrue(any("missing" in n for n in r["notes"]), r["notes"])
        self.assertFalse(r["topology_exact"])

    def test_extra_node(self):
        extra = dict(FRAME, nodes=FRAME["nodes"] + [{"id": "X", "x": 3, "y": 8}])
        r = compare_systems(FRAME, extra)
        self.assertLess(r["nodes"]["precision"], 1.0)
        self.assertFalse(r["topology_exact"])

    def test_wrong_support_is_named(self):
        wrong = dict(FRAME, nodes=[
            {**n, "support": "loslager"} if n["id"] == "D" else n
            for n in FRAME["nodes"]
        ])
        r = compare_systems(FRAME, wrong)
        self.assertEqual(r["supports"]["correct"], 3)
        self.assertTrue(any("support at D" in n for n in r["notes"]), r["notes"])
        self.assertFalse(r["fully_correct"])

    def test_missed_hinge(self):
        wrong = dict(FRAME, members=[
            {k: v for k, v in m.items() if k != "hinge_start"} for m in FRAME["members"]
        ])
        r = compare_systems(FRAME, wrong)
        self.assertLess(r["releases"]["accuracy"], 1.0)
        self.assertFalse(r["fully_correct"])

    def test_load_on_the_wrong_member(self):
        wrong = dict(FRAME, loads=[
            {**l, "on": "A-B"} if l["id"] == "L1" else l for l in FRAME["loads"]
        ])
        r = compare_systems(FRAME, wrong)
        self.assertLess(r["loads"]["f1"], 1.0)

    def test_load_pointing_the_wrong_way(self):
        wrong = dict(FRAME, loads=[
            {**l, "angle": 180} if l["id"] == "L2" else l for l in FRAME["loads"]
        ])
        r = compare_systems(FRAME, wrong)
        self.assertLess(r["loads"]["f1"], 1.0)

    def test_magnitudes_are_deliberately_ignored(self):
        """A drawing without printed values cannot convey them - see compare.py."""
        other = dict(FRAME, loads=[{**l, "q": 999, "value": 999} for l in FRAME["loads"]])
        r = compare_systems(FRAME, other)
        self.assertEqual(r["loads"]["f1"], 1.0, r["notes"])

    def test_slightly_off_coordinates_still_match(self):
        jittered = dict(FRAME, nodes=[{**n, "x": n["x"] + 0.1, "y": n["y"] - 0.1}
                                      for n in FRAME["nodes"]])
        r = compare_systems(FRAME, jittered)
        self.assertEqual(r["nodes"]["matched"], 4)

    def test_grossly_off_coordinates_do_not(self):
        moved = dict(FRAME, nodes=[
            {**n, "x": 3.0, "y": 2.0} if n["id"] == "C" else n for n in FRAME["nodes"]
        ])
        r = compare_systems(FRAME, moved)
        self.assertLess(r["nodes"]["matched"], 4)


class TestIdentifiability(unittest.TestCase):
    """What the drawing can show at all - see unobservable_nodes."""

    def test_a_corner_is_visible(self):
        self.assertEqual(unobservable_nodes(FRAME), [])

    def test_a_node_in_the_middle_of_a_straight_run_is_not(self):
        beam = {
            "nodes": [{"id": "A", "x": 0, "y": 0, "support": "festlager"},
                      {"id": "M", "x": 3, "y": 0},
                      {"id": "B", "x": 6, "y": 0, "support": "loslager"}],
            "members": [{"id": "A-M", "start": "A", "end": "M"},
                        {"id": "M-B", "start": "M", "end": "B"}],
            "loads": [],
        }
        self.assertEqual(unobservable_nodes(beam), ["M"])
        self.assertFalse(identifiability(beam)["fully_recoverable"])

    def test_a_load_or_a_release_makes_it_visible_again(self):
        beam = {
            "nodes": [{"id": "A", "x": 0, "y": 0, "support": "festlager"},
                      {"id": "M", "x": 3, "y": 0},
                      {"id": "B", "x": 6, "y": 0, "support": "loslager"}],
            "members": [{"id": "A-M", "start": "A", "end": "M"},
                        {"id": "M-B", "start": "M", "end": "B"}],
            "loads": [{"id": "L1", "on": "M", "type": "point", "value": 10}],
        }
        self.assertEqual(unobservable_nodes(beam), [])

        hinged = dict(beam, loads=[], members=[
            {"id": "A-M", "start": "A", "end": "M"},
            {"id": "M-B", "start": "M", "end": "B", "hinge_start": "vollgelenk"},
        ])
        self.assertEqual(unobservable_nodes(hinged), [])

    def test_a_kink_is_visible(self):
        bent = {
            "nodes": [{"id": "A", "x": 0, "y": 0, "support": "festlager"},
                      {"id": "M", "x": 3, "y": 1},
                      {"id": "B", "x": 6, "y": 0, "support": "loslager"}],
            "members": [{"id": "A-M", "start": "A", "end": "M"},
                        {"id": "M-B", "start": "M", "end": "B"}],
            "loads": [],
        }
        self.assertEqual(unobservable_nodes(bent), [])


class TestEmptyAndAggregate(unittest.TestCase):
    def test_empty_prediction_scores_zero_without_crashing(self):
        r = compare_systems(FRAME, {"nodes": [], "members": [], "loads": []})
        self.assertEqual(r["nodes"]["matched"], 0)
        self.assertFalse(r["fully_correct"])

    def test_aggregate(self):
        good = compare_systems(FRAME, FRAME)
        bad = compare_systems(FRAME, dict(FRAME, members=FRAME["members"][:1]))
        summary = aggregate([good, bad])
        self.assertEqual(summary["samples"], 2)
        self.assertEqual(summary["fully_correct_rate"], 0.5)
        self.assertLess(summary["member_f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
