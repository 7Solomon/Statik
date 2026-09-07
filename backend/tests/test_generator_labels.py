"""Guards on the synthetic dataset: labels must match the pixels, and the class
list must match what the generator actually draws.

The bugs these pin down were all silent - a dataset generated with them looks
completely normal until a model trained on it fails on real images:

  * point-load boxes were ~12x the area of the arrow they enclosed (68x58 px of
    label around a 40x8 px arrow), so box regression had almost no signal about
    where the force actually applies;
  * every HingeType rendered as the same white circle, so five classes shared
    one appearance;
  * the renderer and the label writer each derived symbol placement separately
    and could disagree;
  * five of sixteen classes never received a single instance.

Run from the backend/ directory:

    PYTHONPATH=. python -m unittest discover -s tests -v
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image, ImageDraw

from src.models.image_models import ImageMember, ImageNode, ImageSystem
from src.plugins.generator.config import DatasetConfig
from src.plugins.generator.generate import DatasetPipeline, LayoutRejected
from src.plugins.generator.image.placement import (
    compute_placements,
    max_symbol_overlap,
    polygon_area,
)
from src.plugins.generator.image.stanli_symbols import (
    DETECTABLE_HINGES,
    DETECTABLE_LOADS,
    DETECTABLE_SUPPORTS,
    HingeType,
    LoadType,
    StanliHinge,
    StanliLoad,
    StanliSupport,
    SupportType,
    detectable_class_names,
)
from src.plugins.generator.image.style import RenderStyle, random_style
from src.plugins.generator.image.structure_generator import (
    RandomStructureGenerator,
    static_indeterminacy,
    validate_system,
)

CANVAS = 400
CENTER = (200.0, 200.0)
#: A declared box may exceed the ink by the stroke pad, but never miss any of it.
BBOX_TOLERANCE_PX = 3.0


def ink_bbox(draw_fn):
    """Tight box around every non-white pixel the symbol actually paints."""
    img = Image.new("RGB", (CANVAS, CANVAS), (255, 255, 255))
    draw_fn(ImageDraw.Draw(img))
    arr = np.array(img.convert("L"))
    ys, xs = np.where(arr < 250)
    if len(xs) == 0:
        return None
    return (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))


class TestLabelsMatchInk(unittest.TestCase):
    """get_bbox() must describe the pixels draw() paints, at every rotation."""

    def _check(self, name, draw_fn, declared):
        ink = ink_bbox(draw_fn)
        self.assertIsNotNone(ink, f"{name}: declared a box but painted nothing")
        self.assertIsNotNone(declared, f"{name}: painted ink but declared no box")
        for i, axis in enumerate(("min_x", "min_y", "max_x", "max_y")):
            self.assertLessEqual(
                abs(declared[i] - ink[i]), BBOX_TOLERANCE_PX,
                f"{name}: {axis} label={declared[i]:.1f} ink={ink[i]:.1f} "
                f"(declared {declared}, ink {ink})",
            )

    def test_supports(self):
        for st in DETECTABLE_SUPPORTS:
            for rot in (0, 30, 90, 200, 315):
                sym = StanliSupport(st)
                self._check(f"{st.name} rot={rot}",
                            lambda d, s=sym, r=rot: s.draw(d, CENTER, r),
                            sym.get_bbox(CENTER, rot))

    def test_hinges(self):
        for ht in DETECTABLE_HINGES:
            for rot in (0, 45, 90, 137, 270):
                sym = StanliHinge(ht)
                self._check(f"{ht.name} rot={rot}",
                            lambda d, s=sym, r=rot: s.draw(d, CENTER, r),
                            sym.get_bbox(CENTER, rot))

    def test_loads(self):
        for lt in DETECTABLE_LOADS:
            for rot in (0, 45, 90, 180, 270, 312):
                sym = StanliLoad(lt)
                self._check(f"{lt.name} rot={rot}",
                            lambda d, s=sym, r=rot: s.draw(d, CENTER, r, 40.0),
                            sym.get_bbox(CENTER, rot, 40.0))

    def test_point_load_box_is_not_bloated(self):
        """Regression: the old box was ~12x the arrow's area."""
        sym = StanliLoad(LoadType.EINZELLAST)
        x0, y0, x1, y1 = sym.get_bbox(CENTER, 270, 40.0)
        ix0, iy0, ix1, iy1 = ink_bbox(lambda d: sym.draw(d, CENTER, 270, 40.0))
        declared_area = (x1 - x0) * (y1 - y0)
        ink_area = (ix1 - ix0) * (iy1 - iy0)
        self.assertLess(declared_area / ink_area, 2.0,
                        f"point-load box is {declared_area / ink_area:.1f}x the ink")


class TestStyledLabelsMatchInk(unittest.TestCase):
    """Styling must not break the label/ink invariant.

    RenderStyle scales every stroke, and stroke width feeds get_bbox()'s
    padding. If a symbol were drawn at one width and measured at another, every
    label in the dataset would be quietly wrong by a few pixels.
    """

    def _styled_ink_bbox(self, draw_fn, paper):
        img = Image.new("RGB", (CANVAS, CANVAS), tuple(paper))
        draw_fn(ImageDraw.Draw(img))
        arr = np.array(img.convert("L")).astype(int)
        # Paper is no longer white, so compare against the page, not against 250.
        ys, xs = np.where(np.abs(arr - int(np.median(arr))) > 12)
        if len(xs) == 0:
            return None
        return (float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1))

    def test_boxes_track_ink_at_every_stroke_weight(self):
        random.seed(7)
        cases = (
            [(StanliSupport, e, (0, 25)) for e in DETECTABLE_SUPPORTS]
            + [(StanliHinge, e, (0, 45)) for e in DETECTABLE_HINGES]
            + [(StanliLoad, e, (0, 45, 270)) for e in DETECTABLE_LOADS]
        )
        for _ in range(15):
            style = random_style()
            for cls, member, rotations in cases:
                for rot in rotations:
                    sym = cls(member).apply_style(style)
                    if cls is StanliLoad:
                        draw_fn = lambda d, s=sym, r=rot: s.draw(d, CENTER, r, 40.0)
                        declared = sym.get_bbox(CENTER, rot, 40.0)
                    else:
                        draw_fn = lambda d, s=sym, r=rot: s.draw(d, CENTER, r)
                        declared = sym.get_bbox(CENTER, rot)
                    ink = self._styled_ink_bbox(draw_fn, style.paper)
                    self.assertIsNotNone(ink)
                    for i, axis in enumerate(("min_x", "min_y", "max_x", "max_y")):
                        self.assertLessEqual(
                            abs(declared[i] - ink[i]), BBOX_TOLERANCE_PX + 1.0,
                            f"{member.name} rot={rot} line_scale={style.line_scale} "
                            f"{axis}: label={declared[i]:.1f} ink={ink[i]:.1f}",
                        )

    def test_apply_style_is_idempotent(self):
        """Placement styles symbols once; re-styling must not compound widths."""
        style = RenderStyle(line_scale=2.0)
        sym = StanliSupport(SupportType.FESTLAGER)
        once = sym.apply_style(style).line_width
        twice = sym.apply_style(style).line_width
        self.assertEqual(once, twice)


class TestAnnotationsAreNeverLabelled(unittest.TestCase):
    """Drawing furniture must add ink but never a label row."""

    def test_clutter_adds_no_labels(self):
        from src.plugins.generator.image.renderer import StanliRenderer
        from src.plugins.generator.yolo import YOLODatasetManager
        import tempfile
        from pathlib import Path

        random.seed(3)
        config = DatasetConfig()
        gen = RandomStructureGenerator(640, 640)
        renderer = StanliRenderer(config)

        with tempfile.TemporaryDirectory() as tmp:
            manager = YOLODatasetManager(Path(tmp), config.classes, "t",
                                         config.load_arrow_length_px)
            for _ in range(25):
                system = gen.generate()

                system.style = None
                plain = renderer.render_structure(system)
                bare = manager._structure_to_yolo_labels(system, plain.size)

                # Same system, now with every annotation switched on.
                system.style = RenderStyle(
                    draw_load_labels=True, draw_node_labels=True,
                    draw_dimension_line=True, draw_member_labels=True,
                    draw_axes=True,
                )
                busy = renderer.render_structure(system)
                cluttered = manager._structure_to_yolo_labels(system, busy.size)

                self.assertEqual(len(bare), len(cluttered),
                                 "annotation changed the label count")
                self.assertFalse(np.array_equal(np.array(plain), np.array(busy)),
                                 "annotation was requested but nothing was drawn")


class TestSymbolsAreDistinguishable(unittest.TestCase):
    """Two classes that render to the same pixels cannot both be learned."""

    def _raster(self, draw_fn):
        # RGB, not "L": symbols now paint with an RGB ink tuple from RenderStyle.
        img = Image.new("RGB", (CANVAS, CANVAS), (255, 255, 255))
        draw_fn(ImageDraw.Draw(img))
        return np.array(img.convert("L"))

    def test_every_detectable_class_renders_differently(self):
        rasters = {}
        for st in DETECTABLE_SUPPORTS:
            rasters[st.name] = self._raster(lambda d, s=st: StanliSupport(s).draw(d, CENTER, 0))
        for ht in DETECTABLE_HINGES:
            rasters[ht.name] = self._raster(lambda d, h=ht: StanliHinge(h).draw(d, CENTER, 0))
        for lt in DETECTABLE_LOADS:
            rasters[lt.name] = self._raster(lambda d, l=lt: StanliLoad(l).draw(d, CENTER, 0, 40.0))

        names = list(rasters)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = rasters[names[i]], rasters[names[j]]
                self.assertGreater(
                    int((a != b).sum()), 20,
                    f"{names[i]} and {names[j]} render to (nearly) identical pixels",
                )

    def test_biegesteife_ecke_draws_nothing(self):
        """A rigid corner is the absence of a release, not a symbol."""
        sym = StanliHinge(HingeType.BIEGESTEIFE_ECKE)
        self.assertIsNone(sym.get_bbox(CENTER, 0))
        self.assertIsNone(ink_bbox(lambda d: sym.draw(d, CENTER, 0)))
        self.assertNotIn("BIEGESTEIFE_ECKE", detectable_class_names())


class TestPlacementIsSingleSource(unittest.TestCase):
    def test_release_lives_on_the_member_end(self):
        """A release on one member end must not label the whole joint."""
        a = ImageNode(id="a", pixel_x=100.0, pixel_y=200.0)
        b = ImageNode(id="b", pixel_x=250.0, pixel_y=200.0)
        c = ImageNode(id="c", pixel_x=400.0, pixel_y=200.0)
        system = ImageSystem(
            width=500, height=400, nodes=[a, b, c],
            members=[
                ImageMember(id="m1", start_node_id="a", end_node_id="b",
                            end_hinge=HingeType.VOLLGELENK),
                ImageMember(id="m2", start_node_id="b", end_node_id="c"),
            ],
        )
        hinges = [p for p in compute_placements(system) if p.kind == "hinge"]
        self.assertEqual(len(hinges), 1)
        # Offset onto the released member, not sitting on the joint itself.
        self.assertLess(hinges[0].pos[0], b.pixel_x)
        self.assertGreater(hinges[0].pos[0], a.pixel_x)


class TestGeneratedSystemsAreValid(unittest.TestCase):
    def test_systems_are_determinate_and_well_formed(self):
        random.seed(1234)
        gen = RandomStructureGenerator(640, 640, enforce_static_determinacy=True)
        for _ in range(150):
            system = gen.generate()
            self.assertIsNone(validate_system(system, require_determinate=True))
            self.assertEqual(static_indeterminacy(system), 0)

    def test_releases_are_never_stored_on_nodes(self):
        random.seed(99)
        gen = RandomStructureGenerator(640, 640)
        for _ in range(50):
            for node in gen.generate().nodes:
                self.assertIsNone(node.hinge_type)


class TestPipelineOutput(unittest.TestCase):
    def test_every_class_gets_instances_and_symbols_do_not_pile_up(self):
        random.seed(5)
        config = DatasetConfig()
        pipeline = DatasetPipeline(None, config)

        counts = {name: 0 for name in config.classes}
        cluttered = 0
        built = 0
        for _ in range(300):
            try:
                _, structure = pipeline.build_sample()
            except LayoutRejected:
                continue
            built += 1
            placements = compute_placements(structure, config.load_arrow_length_px)
            overlap = max_symbol_overlap(placements)
            # Anything past the discard threshold should have been rejected.
            self.assertLessEqual(overlap, config.discard_symbol_overlap + 1e-6)
            if overlap > config.max_symbol_overlap:
                cluttered += 1
            for p in placements:
                if p.class_name in counts:
                    counts[p.class_name] += 1

        empty = [name for name, n in counts.items() if n == 0]
        self.assertEqual(empty, [], f"classes with zero instances: {empty}")

        # Every class needs enough instances to be learnable at all, not just
        # one lucky sample. Scaled to this sample count.
        rare = {name: n for name, n in counts.items() if n < 10}
        self.assertEqual(rare, {}, f"classes too rare to learn: {rare}")

        self.assertLess(cluttered / built, 0.2,
                        f"{cluttered}/{built} samples have crowded symbols")

    def test_labels_are_obb_rows_inside_the_image(self):
        """Every row is `class` plus four normalised corners, all on the image.

        The format is YOLO OBB, not YOLO detect: a five-number row here would
        be read by ultralytics as a different task and silently mis-parsed.
        """
        random.seed(11)
        config = DatasetConfig()
        pipeline = DatasetPipeline(None, config)
        from src.plugins.generator.yolo import YOLODatasetManager
        import tempfile
        from pathlib import Path

        seen = 0
        with tempfile.TemporaryDirectory() as tmp:
            manager = YOLODatasetManager(Path(tmp), config.classes, "t",
                                         config.load_arrow_length_px)
            for _ in range(60):
                try:
                    image, structure = pipeline.build_sample()
                except LayoutRejected:
                    continue
                for row in manager._structure_to_yolo_labels(structure, image.size):
                    self.assertEqual(len(row), 9, f"not an OBB row: {row}")
                    self.assertIn(int(row[0]), range(len(config.classes)))
                    for v in row[1:]:
                        self.assertGreaterEqual(v, -1e-6)
                        self.assertLessEqual(v, 1.0 + 1e-6)
                    corners = [(row[1 + 2 * i], row[2 + 2 * i]) for i in range(4)]
                    self.assertGreater(polygon_area(corners), 0.0)
                    seen += 1
        self.assertGreater(seen, 0, "no labels produced at all")


class TestOrientedBoxesAreTight(unittest.TestCase):
    """The reason the labels are oriented rather than axis-aligned.

    A Streckenlast is the one elongated symbol. Axis-aligned, its box grows with
    the sine of the member angle until most of it is empty paper - and whatever
    else is standing on that paper gets a second ground-truth box drawn over it.
    """

    def _streckenlast(self, angle_deg):
        from src.plugins.generator.image.stanli_symbols import StanliLoad
        symbol = StanliLoad(LoadType.STRECKENLAST)
        pos = (320.0, 320.0)
        corners = symbol.get_corners(pos, angle_deg, 220.0)
        bbox = symbol.get_bbox(pos, angle_deg, 220.0)
        return corners, bbox

    def test_oriented_box_area_is_constant_under_rotation(self):
        areas = [polygon_area(self._streckenlast(a)[0]) for a in (0, 20, 45, 70, 90)]
        for area in areas[1:]:
            self.assertAlmostEqual(area / areas[0], 1.0, delta=0.02)

    def test_axis_aligned_box_would_be_several_times_too_big(self):
        corners, bbox = self._streckenlast(45.0)
        aabb = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        self.assertGreater(aabb / polygon_area(corners), 3.0)

    def test_streckenlast_is_drawn_and_detectable(self):
        from src.plugins.generator.image.stanli_symbols import StanliLoad
        self.assertIn(LoadType.STRECKENLAST, DETECTABLE_LOADS)
        self.assertIsNotNone(
            StanliLoad(LoadType.STRECKENLAST).get_corners((100.0, 100.0), 0.0, 200.0))

    def test_load_block_sits_on_the_gravity_side_of_its_member(self):
        """Whichever way the member's nodes are ordered, the arrows point down.

        The generator keeps rotation augmentation to a few degrees precisely so
        the model can use "which way is down"; a load block that flips sides
        with node order would teach the opposite.
        """
        from src.plugins.generator.image.placement import _member_span

        for a_x, b_x in ((100.0, 400.0), (400.0, 100.0)):  # both node orders
            nodes = [ImageNode(id="a", pixel_x=a_x, pixel_y=200.0),
                     ImageNode(id="b", pixel_x=b_x, pixel_y=200.0)]
            member = ImageMember(id="m", start_node_id="a", end_node_id="b")
            load = _StreckenlastStub("m")
            system = ImageSystem(width=640, height=640, nodes=nodes,
                                 members=[member], loads=[load])
            _mid, rotation, _span = _member_span(system, load)
            self.assertGreater(math.cos(math.radians(rotation)), 0.0,
                               f"block hangs under the member for {a_x}->{b_x}")


class _StreckenlastStub:
    """Minimal duck-typed load; ImageLoad's own defaults would do, but this
    keeps the test independent of its constructor signature."""

    def __init__(self, member_id):
        self.id = "l"
        self.member_id = member_id
        self.node_id = None
        self.load_type = LoadType.STRECKENLAST
        self.start_ratio = 0.0
        self.end_ratio = 1.0


if __name__ == "__main__":
    unittest.main()
