"""Single source of truth for *what symbol sits where* in a rendered system.

The renderer draws these placements and the YOLO label writer measures them.
Because both walk the same list, an image and its label file cannot disagree
about how many symbols there are, what class they have, or where they sit.

Previously the renderer and `YOLODatasetManager._structure_to_yolo_labels` each
re-derived that from the ImageSystem independently, which is how the dataset
ended up with labels sitting on symbols that were never drawn.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from src.plugins.generator.image.stanli_symbols import (
    HingeType,
    LoadType,
    StanliHinge,
    StanliLoad,
    StanliSupport,
    SupportType,
    mm,
    hingeMemberOffset,
)

# --- enum coercion ------------------------------------------------------
# Systems arriving from the editor API carry strings; generated ones carry enums.

_SUPPORT_ALIASES = {
    "FIXED": SupportType.FESTE_EINSPANNUNG,
    "PINNED": SupportType.FESTLAGER,
    "ROLLER": SupportType.LOSLAGER,
    "FREE": SupportType.FREIES_ENDE,
    "NONE": SupportType.FREIES_ENDE,
}

_LOAD_ALIASES = {
    "FORCE_POINT": LoadType.EINZELLAST,
    "FORCE": LoadType.EINZELLAST,
    "MOMENT": LoadType.MOMENT_UHRZEIGER,
    "DIST_UNIFORM": LoadType.STRECKENLAST,
}


def _coerce(value, enum_cls, aliases) -> Optional[object]:
    if value is None or isinstance(value, enum_cls):
        return value
    key = str(value).split(".")[-1].upper()
    try:
        return enum_cls[key]
    except KeyError:
        return aliases.get(key)


def coerce_support(value) -> Optional[SupportType]:
    return _coerce(value, SupportType, _SUPPORT_ALIASES)


def coerce_load(value) -> Optional[LoadType]:
    return _coerce(value, LoadType, _LOAD_ALIASES)


def coerce_hinge(value) -> Optional[HingeType]:
    return _coerce(value, HingeType, {})


@dataclass(frozen=True)
class Placement:
    """One drawable symbol: its class, where it goes, and how it is turned.

    `length` carries two different things depending on the load: the arrow
    length for an Einzellast, the loaded span for a Streckenlast. Both are "how
    long is this symbol along its own axis", which is what the drawing code and
    the box both need.
    """

    kind: str  # 'support' | 'hinge' | 'load'
    class_name: str
    pos: Tuple[float, float]
    rotation: float = 0.0
    length: float = 0.0  # loads only: arrow length, or Streckenlast span, in px
    symbol: object = field(default=None, compare=False, repr=False)

    def draw(self, d) -> None:
        if self.kind == "load":
            self.symbol.draw(d, self.pos, self.rotation, self.length)
        else:
            self.symbol.draw(d, self.pos, self.rotation)

    def bbox(self) -> Optional[Tuple[float, float, float, float]]:
        """Axis-aligned box. Used for text collision, not for labels."""
        if self.kind == "load":
            return self.symbol.get_bbox(self.pos, self.rotation, self.length)
        return self.symbol.get_bbox(self.pos, self.rotation)

    def corners(self) -> Optional[List[Tuple[float, float]]]:
        """Oriented box as four corners - the geometry the labels are written from."""
        if self.kind == "load":
            return self.symbol.get_corners(self.pos, self.rotation, self.length)
        return self.symbol.get_corners(self.pos, self.rotation)


def _visual_angle(dx: float, dy: float) -> float:
    """Degrees CCW as seen on screen, for a vector in pixel space (y points down)."""
    return math.degrees(math.atan2(-dy, dx)) % 360.0


def _node_map(system) -> Dict[str, object]:
    return {n.id: n for n in getattr(system, "nodes", [])}


def _member_ends(system) -> Dict[str, List[Tuple[object, str]]]:
    """node_id -> [(member, 'start'|'end'), ...]"""
    ends: Dict[str, List[Tuple[object, str]]] = {}
    for m in getattr(system, "members", []):
        ends.setdefault(m.start_node_id, []).append((m, "start"))
        ends.setdefault(m.end_node_id, []).append((m, "end"))
    return ends


def _direction_from(node, other) -> Tuple[float, float, float]:
    """Unit vector and length from `node` toward `other`."""
    dx = other.pixel_x - node.pixel_x
    dy = other.pixel_y - node.pixel_y
    L = math.hypot(dx, dy)
    if L == 0:
        return 0.0, 0.0, 0.0
    return dx / L, dy / L, L


def _styled(symbol, system):
    """Apply the system's style before anything measures the symbol."""
    return symbol.apply_style(getattr(system, "style", None))


def _support_placements(system) -> List[Placement]:
    out = []
    for node in getattr(system, "nodes", []):
        st = coerce_support(getattr(node, "support_type", None))
        if st is None or st == SupportType.FREIES_ENDE:
            continue
        symbol = _styled(StanliSupport(st), system)
        rotation = float(getattr(node, "rotation", 0.0) or 0.0)
        if symbol.get_bbox((node.pixel_x, node.pixel_y), rotation) is None:
            continue  # not implemented (FEDER / TORSIONSFEDER)
        out.append(Placement("support", st.name,
                             (node.pixel_x, node.pixel_y), rotation, symbol=symbol))
    return out


def _hinge_placements(system) -> List[Placement]:
    """Release symbols, placed on the member end they actually belong to.

    A release is a property of a *member end*, not of a node: at a joint where
    three members meet, "there is a hinge here" is ambiguous. So the symbol is
    drawn on the member, offset from the joint.

    The one exception is a full pin joint - every member end at a node released
    with a Vollgelenk - which drafting convention draws as a single circle on
    the node rather than N circles fanning out of it.
    """
    nodes = _node_map(system)
    ends = _member_ends(system)
    out: List[Placement] = []

    for node_id, attached in ends.items():
        node = nodes.get(node_id)
        if node is None:
            continue

        released = []
        for member, which in attached:
            ht = coerce_hinge(getattr(member, f"{which}_hinge", None))
            if ht is not None:
                released.append((member, which, ht))

        merged = (
            len(attached) >= 2
            and len(released) == len(attached)
            and all(ht == HingeType.VOLLGELENK for _, _, ht in released)
        )

        if merged:
            member, which, ht = released[0]
            other_id = member.end_node_id if which == "start" else member.start_node_id
            other = nodes.get(other_id)
            rot = 0.0
            if other is not None:
                ux, uy, _ = _direction_from(node, other)
                rot = _visual_angle(ux, uy)
            symbol = _styled(StanliHinge(ht), system)
            if symbol.get_bbox((node.pixel_x, node.pixel_y), rot) is not None:
                out.append(Placement("hinge", ht.name,
                                     (node.pixel_x, node.pixel_y), rot, symbol=symbol))
            continue

        for member, which, ht in released:
            other_id = member.end_node_id if which == "start" else member.start_node_id
            other = nodes.get(other_id)
            if other is None:
                continue
            ux, uy, length = _direction_from(node, other)
            if length == 0:
                continue
            # Sit just clear of the joint, but never past the member's midpoint.
            offset = min(mm(hingeMemberOffset), length * 0.25)
            pos = (node.pixel_x + ux * offset, node.pixel_y + uy * offset)
            rot = _visual_angle(ux, uy)
            symbol = _styled(StanliHinge(ht), system)
            if symbol.get_bbox(pos, rot) is None:
                continue  # BIEGESTEIFE_ECKE / HALBGELENK draw nothing
            out.append(Placement("hinge", ht.name, pos, rot, symbol=symbol))

    # Legacy node-level hinges (systems built in the editor before releases moved
    # onto member ends). Skipped when the node's members already carry releases.
    for node in getattr(system, "nodes", []):
        ht = coerce_hinge(getattr(node, "hinge_type", None))
        if ht is None:
            continue
        attached = ends.get(node.id, [])
        if any(getattr(m, f"{w}_hinge", None) is not None for m, w in attached):
            continue
        rot = 0.0
        if attached:
            member, which = attached[0]
            other_id = member.end_node_id if which == "start" else member.start_node_id
            other = nodes.get(other_id)
            if other is not None:
                ux, uy, _ = _direction_from(node, other)
                rot = _visual_angle(ux, uy)
        symbol = _styled(StanliHinge(ht), system)
        if symbol.get_bbox((node.pixel_x, node.pixel_y), rot) is None:
            continue
        out.append(Placement("hinge", ht.name,
                             (node.pixel_x, node.pixel_y), rot, symbol=symbol))

    return out


def _member_span(system, load) -> Optional[Tuple[Tuple[float, float], float, float]]:
    """Midpoint, direction and length of the stretch of member a load covers.

    `start_ratio`/`end_ratio` default to the whole member and are the same
    fractions ImageLoad already hands to the FEM as a partial-span distributed
    load, so what is drawn and what is solved describe one thing.
    """
    member_id = getattr(load, "member_id", None)
    if not member_id:
        return None
    member = next((m for m in getattr(system, "members", [])
                   if getattr(m, "id", None) == member_id), None)
    if member is None:
        return None
    nodes = _node_map(system)
    a = nodes.get(member.start_node_id)
    b = nodes.get(member.end_node_id)
    if a is None or b is None:
        return None

    ux, uy, total = _direction_from(a, b)
    if total == 0:
        return None

    r0 = getattr(load, "start_ratio", None)
    r1 = getattr(load, "end_ratio", None)
    r0 = 0.0 if r0 is None else max(0.0, min(1.0, float(r0)))
    r1 = 1.0 if r1 is None else max(0.0, min(1.0, float(r1)))
    if r1 < r0:
        r0, r1 = r1, r0
    span = (r1 - r0) * total
    if span <= 0:
        return None

    mid_t = (r0 + r1) / 2.0 * total
    mid = (a.pixel_x + ux * mid_t, a.pixel_y + uy * mid_t)

    # The block is drawn on the symbol's local -y side, which lands ABOVE the
    # member only while cos(rotation) > 0. A member whose nodes happen to run
    # right-to-left would otherwise hang its load underneath with the arrows
    # pointing up - drafting never does that for a gravity load, and the config
    # deliberately keeps rotation augmentation tiny so the model can use "which
    # way is down" as a cue. Flipping by 180 leaves the midpoint and the span
    # untouched and only moves the block to the correct side.
    rotation = _visual_angle(ux, uy)
    if math.cos(math.radians(rotation)) < 0:
        rotation = (rotation + 180.0) % 360.0
    return mid, rotation, span


def _load_placements(system, load_arrow_length_px: float) -> List[Placement]:
    nodes = _node_map(system)
    out = []
    for load in getattr(system, "loads", []):
        lt = coerce_load(getattr(load, "load_type", None))
        if lt is None:
            continue

        if lt == LoadType.STRECKENLAST:
            # Spans a member, so position and rotation come from the member
            # rather than from the load's own pixel coordinates.
            span = _member_span(system, load)
            if span is None:
                continue
            pos, rotation, length = span
        else:
            node_id = getattr(load, "node_id", None)
            node = nodes.get(node_id) if node_id else None
            pos = (node.pixel_x, node.pixel_y) if node else (load.pixel_x, load.pixel_y)
            rotation = float(getattr(load, "angle_deg", 270.0) or 0.0)
            length = load_arrow_length_px

        symbol = _styled(StanliLoad(lt), system)
        if symbol.get_corners(pos, rotation, length) is None:
            continue  # draws nothing
        out.append(Placement("load", lt.name, pos, rotation,
                             length=length, symbol=symbol))
    return out


def compute_placements(system, load_arrow_length_px: float = 40.0) -> List[Placement]:
    """Every symbol in `system`, in draw order (supports, hinges, loads)."""
    if system is None:
        return []
    return (
        _support_placements(system)
        + _hinge_placements(system)
        + _load_placements(system, load_arrow_length_px)
    )


def polygon_area(poly: Sequence[Tuple[float, float]]) -> float:
    """Shoelace area, sign discarded."""
    n = len(poly)
    if n < 3:
        return 0.0
    total = 0.0
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        total += x0 * y1 - x1 * y0
    return abs(total) / 2.0


def clip_polygon(subject: Sequence[Tuple[float, float]],
                 clip: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Sutherland-Hodgman: intersection of two CONVEX polygons.

    Both inputs here are rotated rectangles, so convexity holds and this is
    exact. Written out rather than pulled from shapely to keep the generator's
    dependency list as it is.
    """
    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0.0

    def intersect(p, q, a, b):
        x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
        x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-12:
            return q
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    # Sutherland-Hodgman assumes a consistently wound clip polygon.
    clip = list(clip)
    if _signed_area(clip) < 0:
        clip = clip[::-1]

    output = list(subject)
    for i in range(len(clip)):
        a, b = clip[i], clip[(i + 1) % len(clip)]
        current, output = output, []
        if not current:
            break
        prev = current[-1]
        for point in current:
            if inside(point, a, b):
                if not inside(prev, a, b):
                    output.append(intersect(prev, point, a, b))
                output.append(point)
            elif inside(prev, a, b):
                output.append(intersect(prev, point, a, b))
            prev = point
    return output


def _signed_area(poly: Sequence[Tuple[float, float]]) -> float:
    total = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        total += x0 * y1 - x1 * y0
    return total / 2.0


def _overlap_ratio(a, b) -> float:
    """Intersection area over the *smaller* polygon's area."""
    inter = polygon_area(clip_polygon(a, b))
    if inter <= 0.0:
        return 0.0
    smaller = min(polygon_area(a), polygon_area(b))
    return inter / smaller if smaller > 0 else 0.0


def max_symbol_overlap(placements: Sequence[Placement]) -> float:
    """Worst pairwise overlap among symbol boxes.

    Symbols piled on top of each other give the detector two ground-truth boxes
    for one blob of ink; it cannot win, and NMS will drop one of them at
    inference anyway. Used to reject over-cluttered samples.

    Measured on the ORIENTED boxes. On axis-aligned ones this used to reject
    perfectly clean layouts: a Streckenlast on a diagonal member reports a huge
    square that overlaps everything, even when no ink is anywhere near.
    """
    polys = [p.corners() for p in placements]
    polys = [q for q in polys if q]
    worst = 0.0
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            worst = max(worst, _overlap_ratio(polys[i], polys[j]))
    return worst
