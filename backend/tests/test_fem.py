"""Analytical benchmarks for the static FEM solver.

These pin the physics against closed-form results, so they stay valid across
the refactor of fem.py into the fem/ package. They are deliberately written
against the public entry point only.

Run from the backend/ directory:

    PYTHONPATH=. .venv/Scripts/python.exe -m unittest discover -s tests -v

SIGN CONVENTIONS (established from the frontend renderer, see
frontend/app/features/drawing/ForceRenderer.ts):

  * Global axes are physics-style: +x right, +y UP.
  * Load.angle is degrees CCW from +x. A NODE point load of value P at
    angle -90 (or +90 with P negative) pulls downward.
  * A MEMBER DISTRIBUTED load has no angle. A POSITIVE value acts
    perpendicular to the member, pointing "down" in the member's local
    frame -- i.e. global -y for a left-to-right horizontal member.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.analyze import StructuralSystem
from src.plugins.analyze.fem import calculate_complex_fem

E = 210e9      # Pa
A = 0.01       # m^2
I = 1e-4       # m^4


def node(nid, x, y, fix_n=False, fix_v=False, fix_m=False):
    return {
        "id": nid,
        "position": {"x": x, "y": y},
        "supports": {"fixN": fix_n, "fixV": fix_v, "fixM": fix_m},
    }


def member(mid, start, end, releases=None):
    return {
        "id": mid,
        "startNodeId": start,
        "endNodeId": end,
        "properties": {"E": E, "A": A, "I": I},
        "releases": releases or {"start": {}, "end": {}},
    }


def build(nodes, members, loads, scheiben=None, constraints=None):
    return StructuralSystem.create(
        nodes, members, loads, scheiben or [], constraints or []
    )


def solve(*args, **kwargs):
    result = calculate_complex_fem(build(*args, **kwargs))
    if not result.get("success"):
        raise AssertionError("solver failed: %s" % result.get("error"))
    return result


class CantileverUDL(unittest.TestCase):
    """Cantilever, fully fixed at A, free at B, uniform load over the span.

    Closed form: v_tip = -q L^4 / (8 E I)   (negative = downward)
    """

    L = 4.0
    q = 10.0  # positive == downward, per the convention above

    def setUp(self):
        self.result = solve(
            [node("A", 0, 0, True, True, True), node("B", self.L, 0)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "MEMBER", "type": "DISTRIBUTED",
              "memberId": "m1", "value": self.q,
              "startRatio": 0.0, "endRatio": 1.0}],
        )

    def test_tip_deflection(self):
        expected = -self.q * self.L ** 4 / (8 * E * I)
        actual = self.result["displacements"]["B"][1]
        self.assertAlmostEqual(actual, expected, delta=abs(expected) * 1e-9)

    def test_tip_rotation(self):
        expected = -self.q * self.L ** 3 / (6 * E * I)
        actual = self.result["displacements"]["B"][2]
        self.assertAlmostEqual(actual, expected, delta=abs(expected) * 1e-9)

    def test_fixed_end_moment_magnitude(self):
        # |M| at the built-in end is q L^2 / 2
        stations = self.result["memberResults"]["m1"]["stations"]
        expected = self.q * self.L ** 2 / 2
        self.assertAlmostEqual(abs(stations[0]["M"]), expected,
                               delta=expected * 1e-9)

    def test_free_end_is_moment_free(self):
        stations = self.result["memberResults"]["m1"]["stations"]
        reference = self.q * self.L ** 2 / 2
        self.assertLess(abs(stations[-1]["M"]), reference * 1e-9)


class SimplySupportedNodalLoad(unittest.TestCase):
    """Pin-roller beam, point load at the midspan NODE.

    Two Hermite elements represent this exactly.
    Closed form: v_mid = P L^3 / (48 E I)
    """

    half = 4.0
    P = -1000.0  # downward at angle 90

    def setUp(self):
        self.result = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", self.half, 0),
             node("C", 2 * self.half, 0, fix_v=True)],
            [member("m1", "A", "B"), member("m2", "B", "C")],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "B", "value": self.P, "angle": 90.0}],
        )

    def test_midspan_deflection(self):
        span = 2 * self.half
        expected = self.P * span ** 3 / (48 * E * I)
        actual = self.result["displacements"]["B"][1]
        self.assertAlmostEqual(actual, expected, delta=abs(expected) * 1e-9)

    def test_midspan_moment_magnitude(self):
        span = 2 * self.half
        expected = abs(self.P) * span / 4
        peak = max(
            abs(s["M"])
            for mr in self.result["memberResults"].values()
            for s in mr["stations"]
        )
        self.assertAlmostEqual(peak, expected, delta=expected * 1e-9)

    def test_supports_are_moment_free(self):
        # A pin and a roller cannot carry moment: the diagram must close.
        reference = abs(self.P) * (2 * self.half) / 4
        at_a = self.result["memberResults"]["m1"]["stations"][0]["M"]
        at_c = self.result["memberResults"]["m2"]["stations"][-1]["M"]
        self.assertLess(abs(at_a), reference * 1e-9)
        self.assertLess(abs(at_c), reference * 1e-9)


class AxialBar(unittest.TestCase):
    """Pure axial response: u = P L / (E A)."""

    L = 4.0
    P = 1000.0

    def test_axial_extension(self):
        result = solve(
            [node("A", 0, 0, True, True, True), node("B", self.L, 0)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "B", "value": self.P, "angle": 0.0}],
        )
        expected = self.P * self.L / (E * A)
        actual = result["displacements"]["B"][0]
        self.assertAlmostEqual(actual, expected, delta=abs(expected) * 1e-9)


class EveryMemberIsReported(unittest.TestCase):
    """Regression: results were built inside the member loop and returned
    after the first iteration, so only one member ever came back."""

    L = 4.0

    def test_three_members_three_results(self):
        result = solve(
            [node("A", 0, 0, True, True, True),
             node("B", self.L, 0),
             node("C", 2 * self.L, 0),
             node("D", 3 * self.L, 0)],
            [member("m1", "A", "B"), member("m2", "B", "C"),
             member("m3", "C", "D")],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "D", "value": -1000.0, "angle": 90.0}],
        )
        self.assertEqual(
            sorted(result["memberResults"].keys()), ["m1", "m2", "m3"]
        )

    def test_every_member_has_stations(self):
        result = solve(
            [node("A", 0, 0, True, True, True),
             node("B", self.L, 0),
             node("C", 2 * self.L, 0)],
            [member("m1", "A", "B"), member("m2", "B", "C")],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "C", "value": -1000.0, "angle": 90.0}],
        )
        for mid, mr in result["memberResults"].items():
            self.assertTrue(mr["stations"], "member %s has no stations" % mid)


class MomentRelease(unittest.TestCase):
    """A member end with an mz release must carry no bending moment."""

    L = 4.0

    def test_released_end_carries_no_moment(self):
        result = solve(
            [node("A", 0, 0, True, True, True),
             node("B", self.L, 0),
             node("C", 2 * self.L, 0, fix_v=True)],
            [member("m1", "A", "B"),
             member("m2", "B", "C",
                    releases={"start": {"mz": True}, "end": {}})],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "B", "value": -1000.0, "angle": 90.0}],
        )
        stations = result["memberResults"]["m2"]["stations"]
        peak = max(abs(s["M"]) for s in stations)
        self.assertLess(abs(stations[0]["M"]), max(peak, 1.0) * 1e-9)


class UnstableStructure(unittest.TestCase):
    """An unsupported system must report failure, not raise."""

    def test_singular_system_reports_failure(self):
        result = calculate_complex_fem(build(
            [node("A", 0, 0), node("B", 4.0, 0)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "B", "value": -1000.0, "angle": 90.0}],
        ))
        self.assertFalse(result["success"])
        self.assertIn("error", result)


class MemberPointLoad(unittest.TestCase):
    """Point load applied along a member, not at a node.

    Fixed-fixed beam, central point load P:
      |M| at both ends and at midspan is P L / 8.
    """

    L = 4.0
    P = -1000.0

    def setUp(self):
        self.result = solve(
            [node("A", 0, 0, True, True, True),
             node("B", self.L, 0, True, True, True)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "MEMBER", "type": "POINT",
              "memberId": "m1", "value": self.P, "angle": 90.0,
              "ratio": 0.5}],
        )

    def test_load_is_not_dropped(self):
        stations = self.result["memberResults"]["m1"]["stations"]
        self.assertGreater(max(abs(s["M"]) for s in stations), 1.0)

    def test_end_moment_magnitude(self):
        stations = self.result["memberResults"]["m1"]["stations"]
        expected = abs(self.P) * self.L / 8
        self.assertAlmostEqual(abs(stations[0]["M"]), expected,
                               delta=expected * 1e-6)

    def test_midspan_moment_magnitude(self):
        stations = self.result["memberResults"]["m1"]["stations"]
        midspan = [s for s in stations if abs(s["x"] - self.L / 2) < 1e-9]
        self.assertTrue(midspan, "no station sampled at midspan")
        expected = abs(self.P) * self.L / 8
        self.assertAlmostEqual(abs(midspan[0]["M"]), expected,
                               delta=expected * 1e-6)


# ---------------------------------------------------------------------------
# Phase 3: features that the model parsed but the solver used to ignore.
# ---------------------------------------------------------------------------

class Reactions(unittest.TestCase):

    L = 4.0

    def test_cantilever_reaction_balances_the_load(self):
        result = solve(
            [node("A", 0, 0, True, True, True), node("B", self.L, 0)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "B", "value": -1000.0, "angle": 90.0}],
        )
        self.assertTrue(result["reactions"])
        # Vertical reaction at the built-in end balances the applied load.
        self.assertAlmostEqual(result["reactions"]["A"][1], 1000.0, delta=1e-6)
        # ... and the fixing moment is P * L.
        self.assertAlmostEqual(abs(result["reactions"]["A"][2]),
                               1000.0 * self.L, delta=1e-6)

    def test_reactions_sum_to_the_applied_load(self):
        # Simply supported, load at the third point: 2/3 and 1/3 split.
        span = 3 * self.L
        result = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", self.L, 0),
             node("C", span, 0, fix_v=True)],
            [member("m1", "A", "B"), member("m2", "B", "C")],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "B", "value": -900.0, "angle": 90.0}],
        )
        reactions = result["reactions"]
        self.assertAlmostEqual(reactions["A"][1], 600.0, delta=1e-6)
        self.assertAlmostEqual(reactions["C"][1], 300.0, delta=1e-6)
        total = sum(r[1] for r in reactions.values())
        self.assertAlmostEqual(total, 900.0, delta=1e-6)

    def test_unsupported_nodes_are_absent(self):
        result = solve(
            [node("A", 0, 0, True, True, True), node("B", self.L, 0)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "B", "value": -1000.0, "angle": 90.0}],
        )
        self.assertIn("A", result["reactions"])
        self.assertNotIn("B", result["reactions"])

    def test_distributed_load_reaction(self):
        q = 10.0
        result = solve(
            [node("A", 0, 0, True, True, True), node("B", self.L, 0)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "MEMBER", "type": "DISTRIBUTED",
              "memberId": "m1", "value": q,
              "startRatio": 0.0, "endRatio": 1.0}],
        )
        self.assertAlmostEqual(result["reactions"]["A"][1], q * self.L,
                               delta=abs(q * self.L) * 1e-9)


class PartialAndTrapezoidalLoads(unittest.TestCase):

    L = 4.0

    def test_partial_distributed_load(self):
        q = 10.0
        result = solve(
            [node("A", 0, 0, True, True, True), node("B", self.L, 0)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "MEMBER", "type": "DISTRIBUTED",
              "memberId": "m1", "value": q,
              "startRatio": 0.0, "endRatio": 0.5}],
        )
        # Statically determinate: resultant q*L/2 acting at L/4 from the fix.
        expected = (q * self.L / 2) * (self.L / 4)
        actual = abs(result["memberResults"]["m1"]["stations"][0]["M"])
        self.assertAlmostEqual(actual, expected, delta=expected * 1e-6)

    def test_partial_load_differs_from_full(self):
        common = [node("A", 0, 0, True, True, True), node("B", self.L, 0)]
        full = solve(common, [member("m1", "A", "B")],
                     [{"id": "l1", "scope": "MEMBER", "type": "DISTRIBUTED",
                       "memberId": "m1", "value": 10.0,
                       "startRatio": 0.0, "endRatio": 1.0}])
        half = solve(common, [member("m1", "A", "B")],
                     [{"id": "l1", "scope": "MEMBER", "type": "DISTRIBUTED",
                       "memberId": "m1", "value": 10.0,
                       "startRatio": 0.0, "endRatio": 0.5}])
        self.assertLess(abs(half["displacements"]["B"][1]),
                        abs(full["displacements"]["B"][1]))

    def test_offset_distributed_load(self):
        # Load only over the outer half: resultant q*L/2 at 3L/4 from the fix.
        q = 10.0
        result = solve(
            [node("A", 0, 0, True, True, True), node("B", self.L, 0)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "MEMBER", "type": "DISTRIBUTED",
              "memberId": "m1", "value": q,
              "startRatio": 0.5, "endRatio": 1.0}],
        )
        expected = (q * self.L / 2) * (3 * self.L / 4)
        actual = abs(result["memberResults"]["m1"]["stations"][0]["M"])
        self.assertAlmostEqual(actual, expected, delta=expected * 1e-6)

    def test_trapezoidal_distributed_load(self):
        """Triangular load, zero at the fixed end rising to q at the tip."""
        result = solve(
            [node("A", 0, 0, True, True, True), node("B", self.L, 0)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "MEMBER", "type": "DISTRIBUTED",
              "memberId": "m1", "value": 0.0,
              "startRatio": 0.0, "endRatio": 1.0,
              "startValue": 0.0, "endValue": 10.0}],
        )
        # v_tip = -11 q L^4 / 120 EI
        expected = -11 * 10.0 * self.L ** 4 / (120 * E * I)
        self.assertAlmostEqual(result["displacements"]["B"][1], expected,
                               delta=abs(expected) * 1e-6)

    def test_triangular_load_reaction(self):
        q = 10.0
        result = solve(
            [node("A", 0, 0, True, True, True), node("B", self.L, 0)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "MEMBER", "type": "DISTRIBUTED",
              "memberId": "m1", "value": 0.0,
              "startRatio": 0.0, "endRatio": 1.0,
              "startValue": 0.0, "endValue": q}],
        )
        # Total load is the area of the triangle.
        self.assertAlmostEqual(result["reactions"]["A"][1], q * self.L / 2,
                               delta=abs(q * self.L / 2) * 1e-9)


class DiscreteConstraints(unittest.TestCase):

    L = 4.0

    def _common(self):
        return (
            [node("A", 0, 0, True, True, True),
             node("B", self.L, 0),
             node("C", self.L, -1.0, True, True, True)],
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "B", "value": -1000.0, "angle": 90.0}],
        )

    def test_spring_stiffens_the_structure(self):
        without = solve(*self._common())
        with_spring = solve(*self._common(), constraints=[
            {"id": "c1", "type": "SPRING", "startNodeId": "B",
             "endNodeId": "C", "k": 1e7},
        ])
        self.assertLess(abs(with_spring["displacements"]["B"][1]),
                        abs(without["displacements"]["B"][1]))

    def test_stiffer_spring_deflects_less(self):
        soft = solve(*self._common(), constraints=[
            {"id": "c1", "type": "SPRING", "startNodeId": "B",
             "endNodeId": "C", "k": 1e5}])
        stiff = solve(*self._common(), constraints=[
            {"id": "c1", "type": "SPRING", "startNodeId": "B",
             "endNodeId": "C", "k": 1e8}])
        self.assertLess(abs(stiff["displacements"]["B"][1]),
                        abs(soft["displacements"]["B"][1]))

    def test_spring_alone_carries_a_known_load(self):
        # A single vertical spring between a fixed node and a free one.
        # No members, so the spring takes the whole load: d = -P / k.
        k = 1e5
        P = -500.0
        result = solve(
            [node("A", 0, 0, True, True, True),
             node("B", 0, 1.0, fix_n=True, fix_m=True)],
            [],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "B", "value": P, "angle": 90.0}],
            constraints=[{"id": "c1", "type": "SPRING", "startNodeId": "A",
                          "endNodeId": "B", "k": k}],
        )
        self.assertAlmostEqual(result["displacements"]["B"][1], P / k,
                               delta=abs(P / k) * 1e-9)

    def test_cable_uses_ea_over_length(self):
        # Same geometry, EA chosen so EA/L equals the spring stiffness above.
        k = 1e5
        P = -500.0
        result = solve(
            [node("A", 0, 0, True, True, True),
             node("B", 0, 1.0, fix_n=True, fix_m=True)],
            [],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "B", "value": P, "angle": 90.0}],
            constraints=[{"id": "c1", "type": "CABLE", "startNodeId": "A",
                          "endNodeId": "B", "EA": k * 1.0}],
        )
        self.assertAlmostEqual(result["displacements"]["B"][1], P / k,
                               delta=abs(P / k) * 1e-9)

    def test_damper_without_stiffness_is_inert_statically(self):
        without = solve(*self._common())
        with_damper = solve(*self._common(), constraints=[
            {"id": "c1", "type": "DAMPER", "startNodeId": "B",
             "endNodeId": "C", "c": 500.0},
        ])
        self.assertAlmostEqual(with_damper["displacements"]["B"][1],
                               without["displacements"]["B"][1])

    def test_spring_preload_acts_as_tension(self):
        # Preload pulls B toward A, i.e. downward, with no other load.
        k = 1e5
        preload = 200.0
        result = solve(
            [node("A", 0, 0, True, True, True),
             node("B", 0, 1.0, fix_n=True, fix_m=True)],
            [], [],
            constraints=[{"id": "c1", "type": "SPRING", "startNodeId": "A",
                          "endNodeId": "B", "k": k, "preload": preload}],
        )
        self.assertLess(result["displacements"]["B"][1], 0.0)


class ReleaseCorrectsFixedEndForces(unittest.TestCase):

    L = 4.0

    def test_hinged_member_under_uniform_load(self):
        """Both ends hinged under a UDL must behave as simply supported."""
        result = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True, fix_m=True),
             node("B", self.L, 0, fix_v=True, fix_m=True)],
            [member("m1", "A", "B", releases={"start": {"mz": True},
                                              "end": {"mz": True}})],
            [{"id": "l1", "scope": "MEMBER", "type": "DISTRIBUTED",
              "memberId": "m1", "value": 10.0,
              "startRatio": 0.0, "endRatio": 1.0}],
        )
        stations = result["memberResults"]["m1"]["stations"]
        # Both ends hinged => simply supported => peak sagging moment qL^2/8
        expected = 10.0 * self.L ** 2 / 8
        self.assertLess(abs(stations[0]["M"]), expected * 1e-6)
        self.assertAlmostEqual(max(abs(s["M"]) for s in stations), expected,
                               delta=expected * 1e-6)

    def test_propped_cantilever_reactions(self):
        """One end hinged: the classic 3qL/8 and 5qL/8 split."""
        q = 10.0
        result = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True, fix_m=True),
             node("B", self.L, 0, fix_v=True, fix_m=True)],
            [member("m1", "A", "B",
                    releases={"start": {"mz": True}, "end": {}})],
            [{"id": "l1", "scope": "MEMBER", "type": "DISTRIBUTED",
              "memberId": "m1", "value": q,
              "startRatio": 0.0, "endRatio": 1.0}],
        )
        total = q * self.L
        self.assertAlmostEqual(result["reactions"]["A"][1], 3 * total / 8,
                               delta=total * 1e-9)
        self.assertAlmostEqual(result["reactions"]["B"][1], 5 * total / 8,
                               delta=total * 1e-9)
        # The hinged end carries no moment.
        self.assertLess(abs(result["reactions"]["A"][2]), total * self.L * 1e-9)


class SkewedSupport(unittest.TestCase):
    """node.rotation defines the frame a support restrains."""

    L = 4.0

    def _solve(self, rotation):
        nodes = [node("A", 0, 0, True, True, True),
                 node("B", self.L, 0, fix_v=True)]
        nodes[1]["rotation"] = rotation
        return solve(
            nodes,
            [member("m1", "A", "B")],
            [{"id": "l1", "scope": "NODE", "type": "POINT",
              "nodeId": "B", "value": -1000.0, "angle": 90.0}],
        )

    def test_axis_aligned_roller_has_no_horizontal_motion(self):
        result = self._solve(0.0)
        self.assertLess(abs(result["displacements"]["B"][0]), 1e-12)
        self.assertLess(abs(result["displacements"]["B"][1]), 1e-12)

    def test_skewed_roller_slides_along_its_own_axis(self):
        result = self._solve(45.0)
        u, v = result["displacements"]["B"][:2]
        # Free to slide along the local axis, which at 45 degrees has equal
        # global components; the restrained direction stays exactly zero.
        self.assertGreater(abs(u), 1e-12)
        self.assertAlmostEqual(u, v, delta=max(abs(u), 1e-12) * 1e-9)

    def test_skewed_reaction_has_both_components(self):
        result = self._solve(45.0)
        rx, ry = result["reactions"]["B"][:2]
        self.assertGreater(abs(rx), 1e-9)
        self.assertAlmostEqual(abs(rx), abs(ry), delta=abs(ry) * 1e-9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
