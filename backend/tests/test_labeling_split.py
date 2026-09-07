"""Guards on the train/val split for the hand-labelled real images.

The split this replaced was a seeded per-image shuffle, and it failed the set in
two ways that both read as a model problem rather than a data problem:

  * pages of one PDF landed on both sides - 8 of 14 val source documents were
    also in train - so the val number was partly a training number;
  * the five classes with 3-8 instances in the whole set drew zero val
    instances, and their AP read 0.0 regardless of the model.

Run from the backend/ directory:

    PYTHONPATH=. python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugins.labeling.split import (
    TRAIN, VAL, group_key, page_of, plan_split,
)


def _items(spec):
    """(group, [[class ids per image], ...]) pairs -> plan_split items."""
    out = []
    for group, images in spec:
        for i, classes in enumerate(images):
            out.append((f"{group}_p{i:03d}.png", group, classes))
    return out


class TestGroupsStayWhole(unittest.TestCase):
    """A document must not appear on both sides; that is the leakage fix."""

    def test_no_document_spans_both_splits(self):
        spec = [(f"doc{d}", [[0, 1], [1], [], [2, 0]]) for d in range(12)]
        plan = plan_split(_items(spec), val_ratio=0.25)
        self.assertEqual(plan["shared_documents"], [])

    def test_shared_documents_sees_through_page_blocks(self):
        # A subdivided document has a different key per block, so comparing
        # keys would report clean even with both halves of one PDF in play.
        plan = plan_split(TestOversizedDocument._dominant(), val_ratio=0.2)
        both = set(plan["documents"][TRAIN]) & set(plan["documents"][VAL])
        self.assertEqual(sorted(both), plan["shared_documents"])

    def test_every_file_is_placed_exactly_once(self):
        spec = [(f"doc{d}", [[0], [], [1, 1]]) for d in range(9)]
        items = _items(spec)
        plan = plan_split(items, val_ratio=0.2)
        placed = plan["picked"][TRAIN] + plan["picked"][VAL]
        self.assertEqual(sorted(placed), sorted(f for f, _, _ in items))
        self.assertEqual(len(placed), len(set(placed)))


class TestRareClassesReachVal(unittest.TestCase):
    """The reason for rarest-first ordering, pinned to the real distribution."""

    def test_class_in_two_documents_lands_in_val(self):
        # 9 = SCHUBGELENK-shaped: one box each in two documents, against a
        # head class with two orders of magnitude more instances.
        spec = [(f"common{d}", [[0] * 12, [0] * 12]) for d in range(10)]
        spec += [("rare_a", [[9]]), ("rare_b", [[9]])]
        plan = plan_split(_items(spec), val_ratio=0.2)
        self.assertGreaterEqual(plan["per_class"][9][VAL], 1)
        self.assertGreaterEqual(plan["per_class"][9][TRAIN], 1)

    def test_head_class_still_lands_near_the_ratio(self):
        spec = [(f"doc{d}", [[0] * 10]) for d in range(20)]
        plan = plan_split(_items(spec), val_ratio=0.25)
        share = plan["per_class"][0][VAL] / sum(plan["per_class"][0].values())
        self.assertGreater(share, 0.1)
        self.assertLess(share, 0.45)

    def test_single_document_class_is_reported_not_hidden(self):
        # A class living in one PDF cannot reach both splits however the groups
        # are dealt. The caller has to be told, or a 0 reads as a split bug.
        spec = [(f"doc{d}", [[0, 0]]) for d in range(8)]
        spec += [("only_here", [[10, 10, 10]])]
        plan = plan_split(_items(spec), val_ratio=0.2)
        self.assertIn(10, plan["single_group_classes"])
        self.assertNotIn(0, plan["single_group_classes"])


class TestBackgroundImages(unittest.TestCase):
    """Skipped pages are the false-positive correction; they must not pile up
    on one side, which a class-only objective would happily let happen."""

    def test_negatives_reach_both_splits(self):
        spec = [(f"pos{d}", [[0], [1]]) for d in range(8)]
        spec += [(f"neg{d}", [[], [], []]) for d in range(8)]
        plan = plan_split(_items(spec), val_ratio=0.25)
        for split in (TRAIN, VAL):
            names = plan["picked"][split]
            self.assertTrue(any(n.startswith("neg") for n in names),
                            f"{split} got no background images")


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_split(self):
        spec = [(f"doc{d}", [[0], [1], []]) for d in range(15)]
        items = _items(spec)
        a = plan_split(items, val_ratio=0.2, seed=7)
        b = plan_split(items, val_ratio=0.2, seed=7)
        self.assertEqual(a["picked"], b["picked"])

    def test_order_of_items_does_not_change_the_split(self):
        spec = [(f"doc{d}", [[0], [1], []]) for d in range(15)]
        items = _items(spec)
        a = plan_split(items, val_ratio=0.2)
        b = plan_split(list(reversed(items)), val_ratio=0.2)
        self.assertEqual({k: sorted(v) for k, v in a["picked"].items()},
                         {k: sorted(v) for k, v in b["picked"].items()})


class TestGroupKey(unittest.TestCase):
    def test_manifest_source_pdf_wins(self):
        meta = {"source_pdf": "Werkle_Finite Elemente in der Baustatik.pdf"}
        self.assertEqual(group_key("0001_08-FEM_Werkle_p164.png", meta),
                         "Werkle_Finite Elemente in der Baustatik.pdf")

    def test_falls_back_to_the_document_part_of_the_crop_name(self):
        # Index and page differ; the document does not, so these must group.
        a = group_key("0006_Baustatik-I_BS1-U4-Aufgaben_p006.png", None)
        b = group_key("0012_Baustatik-I_BS1-U4-Aufgaben_p003.png", None)
        self.assertEqual(a, b)
        self.assertEqual(a, "Baustatik-I_BS1-U4-Aufgaben")

    def test_empty_manifest_entry_does_not_collapse_groups(self):
        a = group_key("0001_L_docA_p001.png", {"source_pdf": ""})
        b = group_key("0002_L_docB_p001.png", {"source_pdf": ""})
        self.assertNotEqual(a, b)


class TestDegenerateInputs(unittest.TestCase):
    def test_single_document_puts_everything_on_one_side(self):
        plan = plan_split(_items([("solo", [[0], [1]])]), val_ratio=0.2)
        sizes = sorted(len(v) for v in plan["picked"].values())
        self.assertEqual(sizes, [0, 2])

    def test_zero_val_ratio_keeps_val_empty(self):
        spec = [(f"doc{d}", [[0], [1]]) for d in range(10)]
        plan = plan_split(_items(spec), val_ratio=0.0)
        self.assertEqual(plan["picked"][VAL], [])

    def test_no_items(self):
        plan = plan_split([], val_ratio=0.2)
        self.assertEqual(plan["picked"][TRAIN], [])
        self.assertEqual(plan["picked"][VAL], [])
        self.assertEqual(plan["n_groups"], 0)


class TestOversizedDocument(unittest.TestCase):
    """One PDF is 51% of the real set. Kept whole it cannot be placed at all:
    the first version of this module put all 183 of its crops in val, which
    made val bigger than train on a val_ratio of 0.2."""

    @staticmethod
    def _dominant(n_big=180, n_small=180, per_doc=4):
        spec = [("big", [[0, 1] for _ in range(n_big)])]
        spec += [(f"small{d}", [[0, 1]] * per_doc)
                 for d in range(n_small // per_doc)]
        return _items(spec)

    def test_val_ratio_is_respected_despite_the_dominant_document(self):
        plan = plan_split(self._dominant(), val_ratio=0.2)
        n = sum(len(v) for v in plan["picked"].values())
        share = len(plan["picked"][VAL]) / n
        self.assertGreater(share, 0.1)
        self.assertLess(share, 0.35)

    def test_blocks_of_a_split_document_keep_their_pages_contiguous(self):
        # The leakage worth stopping is between neighbouring pages, so a block
        # has to be a stretch of the document, not a scatter through it.
        plan = plan_split(self._dominant(), val_ratio=0.2)
        for split in (TRAIN, VAL):
            pages = sorted(page_of(f) for f in plan["picked"][split]
                           if f.startswith("big_"))
            if len(pages) < 2:
                continue
            runs = sum(1 for a, b in zip(pages, pages[1:]) if b != a + 1) + 1
            self.assertLessEqual(runs, 3, f"{split} pages are scattered: {runs} runs")

    def test_small_documents_are_never_subdivided(self):
        spec = [(f"doc{d}", [[0], [1], []]) for d in range(20)]
        plan = plan_split(_items(spec), val_ratio=0.2)
        self.assertTrue(all("#p" not in k
                            for s in (TRAIN, VAL) for k in plan["groups"][s]))


class TestRareClassBelowOneBoxOfQuota(unittest.TestCase):
    """GLEITLAGER: 4 boxes in 2 documents. At val_ratio 0.2 the val quota is
    0.8 of a box, so every possible assignment to val looks like an overshoot
    to a proportional objective - and both documents went to train."""

    def test_class_whose_val_quota_is_under_one_box_still_reaches_val(self):
        spec = [(f"common{d}", [[0] * 8]) for d in range(20)]
        spec += [("gleit_a", [[3, 3]]), ("gleit_b", [[3, 3]])]
        plan = plan_split(_items(spec), val_ratio=0.2)
        self.assertGreater(plan["per_class"][3][VAL], 0)
        self.assertGreater(plan["per_class"][3][TRAIN], 0)

    def test_seeding_never_empties_train_of_a_class(self):
        # Only one document holds class 5; seeding val with it would leave the
        # model no instance to learn from at all.
        spec = [(f"doc{d}", [[0]]) for d in range(10)]
        spec += [("solo", [[5]])]
        plan = plan_split(_items(spec), val_ratio=0.2)
        self.assertEqual(plan["per_class"][5][TRAIN], 1)
        self.assertEqual(plan["per_class"][5][VAL], 0)
        self.assertIn(5, plan["single_group_classes"])


class TestPageOf(unittest.TestCase):
    def test_reads_the_page_suffix(self):
        self.assertEqual(page_of("0006_Baustatik-I_BS1-U4-Aufgaben_p006.png"), 6)

    def test_missing_page_suffix_is_zero(self):
        self.assertEqual(page_of("whatever.png"), 0)


if __name__ == "__main__":
    unittest.main()
