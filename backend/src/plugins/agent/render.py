"""Draw a stored system back into a structural drawing.

This closes the loop for an agent working from a picture: it reads a drawing,
writes a system, and gets a drawing back to compare against the original. It
is the only check on whether the agent read the picture correctly, so it has
to be honest about what is actually stored.

The generator already renders ImageSystems in stanli's symbol language -- the
same vocabulary a textbook uses -- so the comparison is meaningful rather than
a diagram-versus-drawing guess. What is reused is the geometry
(`compute_placements`) and the symbols; what is NOT reused is
`AnnotationRenderer`, which exists to produce *training clutter*: it drops 45%
of node labels at random, replaces load values with "F1" a third of the time,
and prints a dimension line whose length is invented from a random scale
factor. Excellent for teaching a detector to ignore text, actively misleading
for someone checking whether the numbers are right. The annotation below is
deterministic and says only what the system actually contains.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw

from src.models.image_models import ImageLoad, ImageMember, ImageNode, ImageSystem
from src.plugins.generator.image.placement import compute_placements
from src.plugins.generator.image.renderer import StanliRenderer
from src.plugins.generator.image.stanli_symbols import (
    BeamType, HingeType, LoadType, SupportType,
)
from src.plugins.generator.image.style import load_font

DEFAULT_SIZE = (900, 660)
ARROW_PX = 40.0

#: Symbols hang outside the node bounding box -- a Festlager below its node, a
#: load arrow above it -- so the structure gets less than the full frame.
_MARGIN_FRAC = 0.16
_MARGIN_MIN_PX = 80.0

_INK = (0, 0, 0)
_MUTED = (90, 90, 96)

# Inverse of schema.SUPPORTS. Ordered longest-first so that a fully clamped
# node never matches a looser preset by accident.
_SUPPORT_BY_FIXES: Sequence[Tuple[Tuple[bool, bool, bool], SupportType]] = (
    ((True, True, True), SupportType.FESTE_EINSPANNUNG),
    ((True, False, True), SupportType.GLEITLAGER),
    ((True, True, False), SupportType.FESTLAGER),
    ((False, True, False), SupportType.LOSLAGER),
)

_HINGE_BY_RELEASE: Sequence[Tuple[Tuple[bool, bool, bool], HingeType]] = (
    ((False, False, True), HingeType.VOLLGELENK),
    ((False, True, False), HingeType.SCHUBGELENK),
    ((True, False, False), HingeType.NORMALKRAFTGELENK),
)


class _Config:
    """The three fields StanliRenderer reads off a DatasetConfig."""

    def __init__(self, size: Tuple[int, int]):
        self.image_size = size
        self.background_color = (255, 255, 255)
        self.load_arrow_length_px = ARROW_PX


class Projection:
    """World metres -> image pixels, uniform scale, y flipped.

    Kept as an object because the annotation needs the scale back to draw a
    truthful scale bar.
    """

    def __init__(self, nodes: Sequence[dict], size: Tuple[int, int]):
        width, height = size
        xs = [float((n.get("position") or {}).get("x", 0.0)) for n in nodes] or [0.0]
        ys = [float((n.get("position") or {}).get("y", 0.0)) for n in nodes] or [0.0]

        margin = max(_MARGIN_MIN_PX, min(width, height) * _MARGIN_FRAC)
        usable_w = max(1.0, width - 2 * margin)
        usable_h = max(1.0, height - 2 * margin)

        # A single node, or a system on one straight line, has zero extent in
        # at least one direction. Fall back to a span rather than dividing by
        # it: the drawing is then centred at a plausible scale instead of
        # collapsing or raising.
        span_x = max(max(xs) - min(xs), 1e-9)
        span_y = max(max(ys) - min(ys), 1e-9)
        candidates = []
        if max(xs) - min(xs) > 1e-6:
            candidates.append(usable_w / span_x)
        if max(ys) - min(ys) > 1e-6:
            candidates.append(usable_h / span_y)
        self.scale = min(candidates) if candidates else 60.0

        self.cx_world = (max(xs) + min(xs)) / 2.0
        self.cy_world = (max(ys) + min(ys)) / 2.0
        self.cx_img = width / 2.0
        self.cy_img = height / 2.0

    def __call__(self, x: float, y: float) -> Tuple[float, float]:
        return (
            self.cx_img + (float(x) - self.cx_world) * self.scale,
            self.cy_img - (float(y) - self.cy_world) * self.scale,
        )


def _support_type(supports: dict) -> SupportType:
    """A stiffness (a number) restrains the DOF just as a boolean does."""
    key = tuple(bool(supports.get(k, False)) for k in ("fixN", "fixV", "fixM"))
    for fixes, symbol in _SUPPORT_BY_FIXES:
        if key == fixes:
            return symbol
    return SupportType.FREIES_ENDE


def _hinge_type(release: dict) -> Optional[HingeType]:
    key = tuple(bool((release or {}).get(k, False)) for k in ("fx", "fy", "mz"))
    for flags, symbol in _HINGE_BY_RELEASE:
        if key == flags:
            return symbol
    return None  # biegesteif: the absence of a release draws nothing


def system_to_image_system(system: Dict[str, Any],
                           size: Tuple[int, int] = DEFAULT_SIZE) -> Tuple[ImageSystem, Projection]:
    """Editor system JSON -> the pixel-space system the renderer understands."""
    nodes = list(system.get("nodes") or [])
    project = Projection(nodes, size)

    img_system = ImageSystem(width=size[0], height=size[1])
    positions: Dict[str, Tuple[float, float]] = {}

    for node in nodes:
        pos = node.get("position") or {}
        px, py = project(pos.get("x", 0.0), pos.get("y", 0.0))
        node_id = str(node.get("id"))
        positions[node_id] = (px, py)
        img_system.nodes.append(ImageNode(
            id=node_id,
            pixel_x=px,
            pixel_y=py,
            support_type=_support_type(node.get("supports") or {}),
            rotation=float(node.get("rotation", 0) or 0),
        ))

    for member in system.get("members") or []:
        releases = member.get("releases") or {}
        img_system.members.append(ImageMember(
            id=str(member.get("id")),
            start_node_id=str(member.get("startNodeId")),
            end_node_id=str(member.get("endNodeId")),
            # A solid line without the fibre marking: the systems an agent
            # builds are frames, not trusses, and the fibre would assert a
            # bending convention nobody asked for.
            beam_type=BeamType.BIEGUNG_OHNE_FASER,
            start_hinge=_hinge_type(releases.get("start")),
            end_hinge=_hinge_type(releases.get("end")),
        ))

    members_by_id = {str(m.get("id")): m for m in (system.get("members") or [])}
    for load in system.get("loads") or []:
        drawn = _image_load(load, members_by_id, positions)
        if drawn is not None:
            img_system.loads.append(drawn)

    return img_system, project


def _image_load(load: dict, members_by_id: Dict[str, dict],
                positions: Dict[str, Tuple[float, float]]) -> Optional[ImageLoad]:
    kind = str(load.get("type", "POINT")).upper()
    load_id = str(load.get("id"))

    if kind == "DISTRIBUTED":
        member_id = str(load.get("memberId"))
        if member_id not in members_by_id:
            return None
        return ImageLoad(
            id=load_id,
            member_id=member_id,
            load_type=LoadType.STRECKENLAST,
            start_ratio=float(load.get("startRatio", 0.0) or 0.0),
            end_ratio=1.0 if load.get("endRatio") is None else float(load["endRatio"]),
            label_text="",
        )

    if kind in ("MOMENT", "DYNAMIC_MOMENT"):
        node_id = str(load.get("nodeId"))
        if node_id not in positions:
            return None
        value = _magnitude(load)
        # Counter-clockwise is positive, matching the maths convention the
        # README states for the whole application.
        symbol = (LoadType.MOMENT_GEGEN_UHRZEIGER if value >= 0
                  else LoadType.MOMENT_UHRZEIGER)
        px, py = positions[node_id]
        return ImageLoad(id=load_id, node_id=node_id, pixel_x=px, pixel_y=py,
                         load_type=symbol, label_text="")

    # POINT and DYNAMIC_FORCE both draw as a single arrow.
    angle = float(load.get("angle", -90) or 0.0)
    if load.get("scope") == "MEMBER":
        member = members_by_id.get(str(load.get("memberId")))
        if member is None:
            return None
        a = positions.get(str(member.get("startNodeId")))
        b = positions.get(str(member.get("endNodeId")))
        if a is None or b is None:
            return None
        t = float(load.get("ratio", 0.5) or 0.5)
        px, py = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        node_id = None
    else:
        node_id = str(load.get("nodeId"))
        if node_id not in positions:
            return None
        px, py = positions[node_id]

    return ImageLoad(id=load_id, node_id=node_id, pixel_x=px, pixel_y=py,
                     angle_deg=angle % 360.0, load_type=LoadType.EINZELLAST,
                     label_text="")


def _magnitude(load: dict) -> float:
    signal = load.get("signal")
    if isinstance(signal, dict) and signal.get("amplitude") is not None:
        return float(signal["amplitude"])
    return float(load.get("value", 0) or 0)


# --- annotation -------------------------------------------------------

def _fmt(value: float) -> str:
    """Round for reading, not for storage: 10.0 -> '10', 2.5 -> '2.5'."""
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:g}"


def _load_caption(load: dict) -> str:
    kind = str(load.get("type", "POINT")).upper()
    value = _magnitude(load)
    if kind == "DISTRIBUTED":
        q_start = float(load.get("startValue", load.get("value", 0)) or 0)
        q_end = float(load.get("endValue", load.get("value", 0)) or 0)
        if q_start != q_end:
            return f"q={_fmt(q_start)}..{_fmt(q_end)} kN/m"
        return f"q={_fmt(q_start)} kN/m"
    if kind in ("MOMENT", "DYNAMIC_MOMENT"):
        return f"M={_fmt(value)} kNm"
    return f"{_fmt(value)} kN"


class _Annotator:
    """Deterministic labels: node names, load magnitudes, a real scale bar."""

    def __init__(self, draw: ImageDraw.ImageDraw, size: Tuple[int, int]):
        self.d = draw
        self.size = size
        self.font = load_font(15)
        self.small = load_font(12)
        self.occupied: List[Tuple[float, float, float, float]] = []

    def block(self, box, pad: float = 3.0) -> None:
        if box is not None:
            self.occupied.append((box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad))

    def _box(self, xy, text, font):
        try:
            return self.d.textbbox(xy, text, font=font)
        except Exception:
            return (xy[0], xy[1], xy[0] + len(text) * 7, xy[1] + 12)

    def text(self, anchor, text, font, offsets, fill=_INK, force: bool = False) -> bool:
        """Place `text` at the first offset from `anchor` that hits nothing.

        With `force`, a label that fits nowhere clean is drawn at the first
        offset that is at least inside the image. A node whose name is missing
        is worse for checking a drawing than one whose name grazes a symbol.
        """
        w, h = self.size
        fallback = None
        for dx, dy in offsets:
            xy = (anchor[0] + dx, anchor[1] + dy)
            box = self._box(xy, text, font)
            if box[0] < 2 or box[1] < 2 or box[2] > w - 2 or box[3] > h - 2:
                continue
            if any(not (box[2] <= o[0] or o[2] <= box[0]
                        or box[3] <= o[1] or o[3] <= box[1]) for o in self.occupied):
                if fallback is None:
                    fallback = (xy, box)
                continue
            self.d.text(xy, text, fill=fill, font=font)
            self.block(box)
            return True

        if force and fallback is not None:
            xy, box = fallback
            self.d.text(xy, text, fill=fill, font=font)
            self.block(box)
            return True
        return False


_NODE_OFFSETS = ((8, -22), (-20, -22), (8, 8), (-20, 8), (-22, -8), (12, -8),
                 (16, -30), (-28, -30), (16, 16), (-28, 16), (0, -34), (0, 20))
_LOAD_OFFSETS = ((-8, -20), (6, -20), (-38, -6), (8, -6), (-8, 8), (8, 12))


def annotate(image: Image.Image, system: Dict[str, Any], img_system: ImageSystem,
             project: Projection) -> None:
    """Write node ids, load magnitudes and a scale bar onto a rendered image."""
    draw = ImageDraw.Draw(image)
    ann = _Annotator(draw, (image.width, image.height))

    placements = compute_placements(img_system, ARROW_PX)
    for placement in placements:
        ann.block(placement.bbox())

    for node in img_system.nodes:
        ann.text((node.pixel_x, node.pixel_y), node.id, ann.small, _NODE_OFFSETS,
                 fill=_MUTED, force=True)

    # compute_placements emits load symbols in the order it walks system.loads,
    # so the nth arrow belongs to the nth *drawable* load.
    arrows = [p for p in placements if p.kind == "load"]
    for placement, load in zip(arrows, _drawable_loads(system, img_system)):
        box = placement.bbox()
        if box is None:
            continue
        anchor = (box[0] if placement.class_name == "EINZELLAST" else box[2], box[1])
        ann.text(anchor, _load_caption(load), ann.small, _LOAD_OFFSETS)

    _scale_bar(draw, ann, project, image.size)


def _drawable_loads(system: Dict[str, Any], img_system: ImageSystem) -> List[dict]:
    """The stored loads, in the order their symbols were emitted."""
    by_id = {str(l.get("id")): l for l in (system.get("loads") or [])}
    return [by_id[l.id] for l in img_system.loads if l.id in by_id]


def _scale_bar(draw: ImageDraw.ImageDraw, ann: _Annotator, project: Projection,
               size: Tuple[int, int]) -> None:
    """A bar of a round number of metres, measured from the actual projection.

    Without it the drawing carries no absolute size at all, and 'looks right'
    would stop short of 'is the right length'.
    """
    width, height = size
    target_px = width * 0.18
    metres = target_px / project.scale if project.scale > 0 else 1.0
    # Round down to 1, 2 or 5 times a power of ten.
    exponent = math.floor(math.log10(metres)) if metres > 0 else 0
    base = 10.0 ** exponent
    metres = next((m * base for m in (5.0, 2.0, 1.0) if m * base <= metres), base)
    length_px = metres * project.scale
    if not (10 <= length_px <= width * 0.6):
        return

    x0 = 24.0
    y = height - 24.0
    draw.line([(x0, y), (x0 + length_px, y)], fill=_MUTED, width=2)
    for x in (x0, x0 + length_px):
        draw.line([(x, y - 5), (x, y + 5)], fill=_MUTED, width=2)
    ann.text((x0, y - 20), f"{_fmt(metres)} m", ann.small, ((0, 0),), fill=_MUTED)


def render_system(system: Dict[str, Any], size: Tuple[int, int] = DEFAULT_SIZE,
                  labels: bool = True) -> Image.Image:
    """Editor system JSON -> a PNG-able structural drawing."""
    img_system, project = system_to_image_system(system, size)
    image = StanliRenderer(_Config(size)).render_structure(img_system)
    if labels:
        annotate(image, system, img_system, project)
    return image
