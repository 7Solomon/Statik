"""Benchmarks for the kinematic (mechanism) analysis.

Every case has a textbook degree-of-freedom count, so these stay valid across
the refactor of kinematics.py into the kinematics/ package.

Run from the backend/ directory:

    PYTHONPATH=. .venv/Scripts/python.exe -m unittest discover -s tests -v

DOF here means kinematic degrees of freedom of the structure as a mechanism:
0 means rigid (kinematically determinate), n > 0 means an n-fold mechanism.
"""

import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.analyze import StructuralSystem
from src.plugins.analyze.kinematics import solve_kinematics

#: Both ends released for moment: a pin-jointed link.
HINGE_BOTH = {"start": {"mz": True}, "end": {"mz": True}}


def node(nid, x, y, fix_n=False, fix_v=False, fix_m=False, rotation=0.0):
    return {
        "id": nid,
        "position": {"x": x, "y": y},
        "rotation": rotation,
        "supports": {"fixN": fix_n, "fixV": fix_v, "fixM": fix_m},
    }


def member(mid, start, end, releases=None):
    return {
        "id": mid,
        "startNodeId": start,
        "endNodeId": end,
        "properties": {"E": 1.0, "A": 1.0, "I": 1.0},
        "releases": releases or {"start": {}, "end": {}},
    }


def build(nodes, members, scheiben=None):
    return StructuralSystem.create(nodes, members, [], scheiben or [], [])


def solve(nodes, members, scheiben=None):
    return solve_kinematics(build(nodes, members, scheiben))


class RigidStructures(unittest.TestCase):
    """Structures that must report zero degrees of freedom."""

    def test_cantilever(self):
        _, dof = solve(
            [node("A", 0, 0, True, True, True), node("B", 1, 0)],
            [member("m1", "A", "B")],
        )
        self.assertEqual(dof, 0)

    def test_simply_supported_beam(self):
        _, dof = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", 2, 0, fix_v=True)],
            [member("m1", "A", "B")],
        )
        self.assertEqual(dof, 0)

    def test_three_hinged_arch(self):
        """Statically determinate and rigid.

        Every node here is hinge-only, so no constraint references any nodal
        rotation. Those coordinates describe nothing and must not be counted
        as freedoms -- doing so reported this rigid arch as a 3-fold
        mechanism.
        """
        _, dof = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", 1, 1),
             node("C", 2, 0, fix_n=True, fix_v=True)],
            [member("m1", "A", "B", HINGE_BOTH),
             member("m2", "B", "C", HINGE_BOTH)],
        )
        self.assertEqual(dof, 0)

    def test_portal_frame(self):
        _, dof = solve(
            [node("A", 0, 0, True, True, True),
             node("B", 0, 1),
             node("C", 1, 1),
             node("D", 1, 0, True, True, True)],
            [member("m1", "A", "B"), member("m2", "B", "C"),
             member("m3", "C", "D")],
        )
        self.assertEqual(dof, 0)


class Mechanisms(unittest.TestCase):
    """Structures with a known non-zero mechanism count."""

    def test_free_member_has_three_rigid_body_modes(self):
        _, dof = solve(
            [node("A", 0, 0), node("B", 1, 0)],
            [member("m1", "A", "B")],
        )
        self.assertEqual(dof, 3)

    def test_collinear_three_hinged_arch_is_an_infinitesimal_mechanism(self):
        """The classic exceptional case: with the crown on the line joining
        the supports, the arch loses its rigidity."""
        _, dof = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", 1, 0),
             node("C", 2, 0, fix_n=True, fix_v=True)],
            [member("m1", "A", "B", HINGE_BOTH),
             member("m2", "B", "C", HINGE_BOTH)],
        )
        self.assertEqual(dof, 1)

    def test_two_bar_linkage_on_a_roller(self):
        _, dof = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", 1, 1),
             node("C", 2, 0, fix_v=True)],
            [member("m1", "A", "B", HINGE_BOTH),
             member("m2", "B", "C", HINGE_BOTH)],
        )
        self.assertEqual(dof, 1)

    def test_four_bar_linkage(self):
        _, dof = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", 0, 1),
             node("C", 1, 1),
             node("D", 1, 0, fix_n=True, fix_v=True)],
            [member("m1", "A", "B", HINGE_BOTH),
             member("m2", "B", "C", HINGE_BOTH),
             member("m3", "C", "D", HINGE_BOTH)],
        )
        self.assertEqual(dof, 1)


class ModesMatchTheDofCount(unittest.TestCase):
    """The reported count and the returned mode shapes must agree."""

    def test_mechanism_returns_one_mode_per_dof(self):
        modes, dof = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", 1, 1),
             node("C", 2, 0, fix_v=True)],
            [member("m1", "A", "B", HINGE_BOTH),
             member("m2", "B", "C", HINGE_BOTH)],
        )
        self.assertEqual(len(modes), dof)

    def test_rigid_structure_returns_no_modes(self):
        modes, dof = solve(
            [node("A", 0, 0, True, True, True), node("B", 1, 0)],
            [member("m1", "A", "B")],
        )
        self.assertEqual(dof, 0)
        self.assertEqual(modes, [])

    def test_unconstrained_nodes_still_yield_modes(self):
        """Two loose nodes and nothing else: reporting a DOF count with no
        modes to draw left the frontend with nothing to show."""
        modes, dof = solve([node("A", 0, 0), node("B", 1, 0)], [])
        self.assertGreater(dof, 0)
        self.assertEqual(len(modes), dof)

    def test_modes_have_a_velocity_for_every_node(self):
        modes, _ = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", 1, 1),
             node("C", 2, 0, fix_v=True)],
            [member("m1", "A", "B", HINGE_BOTH),
             member("m2", "B", "C", HINGE_BOTH)],
        )
        self.assertTrue(modes)
        for mode in modes:
            self.assertEqual(set(mode.node_velocities), {"A", "B", "C"})

    def test_modes_are_non_trivial(self):
        modes, _ = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", 1, 1),
             node("C", 2, 0, fix_v=True)],
            [member("m1", "A", "B", HINGE_BOTH),
             member("m2", "B", "C", HINGE_BOTH)],
        )
        for mode in modes:
            peak = max(float(np.linalg.norm(v))
                       for v in mode.node_velocities.values())
            self.assertGreater(peak, 1e-6)


class ModesRespectSupports(unittest.TestCase):
    """A mode shape may not move a restrained direction."""

    def test_pinned_nodes_do_not_translate(self):
        modes, _ = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", 1, 1),
             node("C", 2, 0, fix_v=True)],
            [member("m1", "A", "B", HINGE_BOTH),
             member("m2", "B", "C", HINGE_BOTH)],
        )
        for mode in modes:
            self.assertLess(float(np.linalg.norm(mode.node_velocities["A"])),
                            1e-9)
            # C is on a vertical roller: no vertical motion.
            self.assertLess(abs(float(mode.node_velocities["C"][1])), 1e-9)

    def test_axial_length_is_preserved(self):
        """A rigid link cannot stretch: the relative velocity of its ends has
        no component along the member axis."""
        modes, _ = solve(
            [node("A", 0, 0, fix_n=True, fix_v=True),
             node("B", 1, 1),
             node("C", 2, 0, fix_v=True)],
            [member("m1", "A", "B", HINGE_BOTH),
             member("m2", "B", "C", HINGE_BOTH)],
        )
        axes = {"m1": np.array([1.0, 1.0]) / np.sqrt(2),
                "m2": np.array([1.0, -1.0]) / np.sqrt(2)}
        for mode in modes:
            for mid, (start, end) in {"m1": ("A", "B"),
                                      "m2": ("B", "C")}.items():
                rel = mode.node_velocities[end] - mode.node_velocities[start]
                self.assertLess(abs(float(np.dot(rel, axes[mid]))), 1e-9)


class ScaleRobustness(unittest.TestCase):
    """Rank determination must not depend on the model's units.

    Constraint entries scale as 1/L, so an absolute rank tolerance made a
    rigid cantilever look like a mechanism once the span grew large enough.
    """

    def test_cantilever_is_rigid_at_every_scale(self):
        for L in (1e-6, 1e-3, 1.0, 1e3, 1e6, 1e9, 1e12):
            with self.subTest(L=L):
                _, dof = solve(
                    [node("A", 0, 0, True, True, True), node("B", L, 0)],
                    [member("m1", "A", "B")],
                )
                self.assertEqual(dof, 0)

    def test_mechanism_is_detected_at_every_scale(self):
        for L in (1e-3, 1.0, 1e3, 1e6):
            with self.subTest(L=L):
                _, dof = solve(
                    [node("A", 0, 0, fix_n=True, fix_v=True),
                     node("B", L, L),
                     node("C", 2 * L, 0, fix_v=True)],
                    [member("m1", "A", "B", HINGE_BOTH),
                     member("m2", "B", "C", HINGE_BOTH)],
                )
                self.assertEqual(dof, 1)


class SkewedSupports(unittest.TestCase):

    def test_skewed_roller_restrains_its_own_direction(self):
        # A 45-degree roller under a member along x.
        _, dof = solve(
            [node("A", 0, 0, True, True, True),
             node("B", 1, 0, fix_v=True, rotation=45.0)],
            [member("m1", "A", "B")],
        )
        self.assertEqual(dof, 0)


class RigidScheiben(unittest.TestCase):

    def _scheibe(self, node_ids, releases_for=None):
        releases_for = releases_for or {}
        return {
            "id": "s1",
            "shape": "rectangle",
            "corner1": {"x": 0, "y": 0},
            "corner2": {"x": 2, "y": 1},
            "type": "RIGID",
            "connections": [
                {"nodeId": nid, "releases": releases_for.get(nid)}
                for nid in node_ids
            ],
        }

    def test_rigid_scheibe_ties_its_nodes_together(self):
        """Two otherwise loose nodes bound to one RIGID Scheibe move as a
        single body: 3 rigid-body modes rather than 4 free translations."""
        _, dof = solve(
            [node("A", 0, 0), node("B", 2, 1)],
            [],
            [self._scheibe(["A", "B"])],
        )
        self.assertEqual(dof, 3)

    def test_supported_scheibe_is_rigid(self):
        _, dof = solve(
            [node("A", 0, 0, True, True, True), node("B", 2, 1)],
            [],
            [self._scheibe(["A", "B"])],
        )
        self.assertEqual(dof, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
