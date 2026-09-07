"""Unlabelled drawing furniture: load text, node names, dimension lines, axes.

None of this is ever written to a label file, and that is the whole point. Real
structural drawings are covered in annotation, so a detector that has only ever
seen bare symbols on empty paper treats every "F" and every dimension arrow as a
candidate object. Training on clutter that is deliberately *not* labelled is how
it learns to ignore it.

`ImageLoad.label_text` has always been generated and never drawn; it finally is.

Placement is collision-aware: text is nudged around until it clears the symbol
boxes, because annotation printed through a Festlager would teach the opposite
of the intended lesson.
"""

from __future__ import annotations

import math
import random
import string
from typing import List, Optional, Sequence, Tuple

from src.plugins.generator.image.placement import Placement
from src.plugins.generator.image.stanli_symbols import LoadType
from src.plugins.generator.image.style import RenderStyle, load_font

Box = Tuple[float, float, float, float]


def _inflate(b: Box, pad: float) -> Box:
    return (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)


def _hits(a: Box, b: Box) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


class AnnotationRenderer:
    def __init__(self, style: RenderStyle, rng: Optional[random.Random] = None):
        self.style = style
        self.rng = rng or random
        self.font = load_font(style.font_size)
        self.small = load_font(max(9, style.font_size - 3))

    # --- placement ------------------------------------------------------

    def _text_box(self, d, xy, text, font) -> Box:
        try:
            return d.textbbox(xy, text, font=font)
        except Exception:
            w, h = font.getsize(text) if hasattr(font, "getsize") else (len(text) * 7, 12)
            return (xy[0], xy[1], xy[0] + w, xy[1] + h)

    def _place_text(self, d, anchor, text, font, occupied: List[Box],
                    offsets: Sequence[Tuple[float, float]], image_size) -> bool:
        """Draw `text` at the first offset from `anchor` that collides with nothing."""
        w, h = image_size
        for dx, dy in offsets:
            xy = (anchor[0] + dx, anchor[1] + dy)
            box = self._text_box(d, xy, text, font)
            if box[0] < 2 or box[1] < 2 or box[2] > w - 2 or box[3] > h - 2:
                continue
            if any(_hits(box, o) for o in occupied):
                continue
            d.text(xy, text, fill=self.style.ink, font=font)
            occupied.append(_inflate(box, 2.0))
            return True
        return False

    # --- pieces ---------------------------------------------------------

    def _load_labels(self, d, system, placements, occupied, image_size):
        loads = list(getattr(system, "loads", []))
        arrows = [p for p in placements if p.kind == "load"]
        for i, placement in enumerate(arrows):
            text = None
            if i < len(loads):
                text = getattr(loads[i], "label_text", None)
            if not text:
                continue
            if self.rng.random() < 0.35:
                # Drawings label the symbol as often as the magnitude.
                text = ("M" if "MOMENT" in placement.class_name else "F")
                if self.rng.random() < 0.5:
                    text += str(i + 1)

            box = placement.bbox()
            if box is None:
                continue
            # Anchor off the tail of the arrow, away from the structure.
            ax = box[0] if placement.class_name == "EINZELLAST" else box[2]
            anchor = (ax, box[1])
            self._place_text(
                d, anchor, text, self.font, occupied,
                [(-6, -18), (4, -18), (-30, -6), (6, -6), (-6, 6), (6, 10)],
                image_size,
            )

    def _node_labels(self, d, system, occupied, image_size):
        letters = string.ascii_uppercase
        numeric = self.rng.random() < 0.4
        for i, node in enumerate(getattr(system, "nodes", [])):
            if self.rng.random() < 0.45:
                continue  # real drawings name some joints, not all
            text = str(i + 1) if numeric else letters[i % len(letters)]
            self._place_text(
                d, (node.pixel_x, node.pixel_y), text, self.small, occupied,
                [(6, -20), (-16, -20), (6, 6), (-16, 6), (-16, -8), (10, -8)],
                image_size,
            )

    def _member_labels(self, d, system, occupied, image_size):
        nodes = {n.id: n for n in getattr(system, "nodes", [])}
        for i, member in enumerate(getattr(system, "members", [])):
            if self.rng.random() < 0.6:
                continue
            a, b = nodes.get(member.start_node_id), nodes.get(member.end_node_id)
            if not a or not b:
                continue
            mid = ((a.pixel_x + b.pixel_x) / 2, (a.pixel_y + b.pixel_y) / 2)
            self._place_text(d, mid, f"S{i + 1}", self.small, occupied,
                             [(4, -18), (4, 6), (-18, -18), (-18, 6)], image_size)

    def _dimension_line(self, d, system, occupied, image_size):
        """A horizontal dimension under the structure, with ticks and a length."""
        nodes = list(getattr(system, "nodes", []))
        if len(nodes) < 2:
            return
        xs = sorted(n.pixel_x for n in nodes)
        x0, x1 = xs[0], xs[-1]
        if x1 - x0 < 60:
            return

        base_y = max(n.pixel_y for n in nodes)
        y = base_y + self.rng.uniform(34, 62)
        if y > image_size[1] - 22:
            return

        ink = self.style.ink
        w = max(1, int(round(self.style.line_scale)))
        d.line([(x0, y), (x1, y)], fill=ink, width=w)
        for x in (x0, x1):
            # Extension line up toward the structure, plus the 45-degree tick
            # that marks the dimension's end.
            d.line([(x, y - 8), (x, base_y + 6)], fill=ink, width=w)
            d.line([(x - 5, y + 5), (x + 5, y - 5)], fill=ink, width=w)

        metres = round((x1 - x0) / self.rng.uniform(55.0, 95.0), 2)
        text = f"{metres:.2f}".replace(".", ",") + " m"
        box = self._text_box(d, (0, 0), text, self.small)
        tw = box[2] - box[0]
        self._place_text(d, ((x0 + x1) / 2 - tw / 2, y - 20), text, self.small,
                         occupied, [(0, 0), (0, 6), (0, -8)], image_size)

    def _axes(self, d, image_size, occupied):
        w, h = image_size
        ox = self.rng.uniform(24, 70)
        oy = self.rng.uniform(h - 80, h - 30)
        L = 26
        ink = self.style.ink
        lw = max(1, int(round(self.style.line_scale)))
        d.line([(ox, oy), (ox + L, oy)], fill=ink, width=lw)
        d.line([(ox, oy), (ox, oy - L)], fill=ink, width=lw)
        d.text((ox + L + 3, oy - 7), "x", fill=ink, font=self.small)
        d.text((ox - 10, oy - L - 6), "z", fill=ink, font=self.small)
        occupied.append((ox - 14, oy - L - 12, ox + L + 16, oy + 8))

    # --- entry point ----------------------------------------------------

    def draw(self, d, system, placements: Sequence[Placement], image_size):
        # Symbol boxes are off limits; text must not print through them.
        occupied: List[Box] = []
        for p in placements:
            box = p.bbox()
            if box is not None:
                occupied.append(_inflate(box, 3.0))

        if self.style.draw_load_labels:
            self._load_labels(d, system, placements, occupied, image_size)
        if self.style.draw_node_labels:
            self._node_labels(d, system, occupied, image_size)
        if self.style.draw_member_labels:
            self._member_labels(d, system, occupied, image_size)
        if self.style.draw_dimension_line:
            self._dimension_line(d, system, occupied, image_size)
        if self.style.draw_axes:
            self._axes(d, image_size, occupied)
