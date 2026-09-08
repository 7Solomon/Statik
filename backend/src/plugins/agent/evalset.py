"""Turn generated systems into (picture, ground truth) pairs.

The generator already produces both halves of an eval sample: a random but
statically sane system, and a rendering of it in stanli's symbol language. All
that is missing is the translation of the pixel-space system into the compact
format an agent writes, so the two can be compared.

`ImageSystem.convert_to_real_system` looks like it should do this and must not
be used for it: it maps pixel y straight to world y without flipping, so every
system it returns is upside down relative to the editor's convention that +y
points up. It has no callers, which is presumably why nobody noticed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.models.image_models import ImageSystem
from src.plugins.generator.image.stanli_symbols import HingeType, LoadType, SupportType

#: Pixel-space systems have no scale. The truth gets an arbitrary but fixed
#: span; the comparison normalises it away.
DEFAULT_SPAN_METERS = 10.0

_SUPPORT_NAMES = {
    SupportType.FREIES_ENDE: "frei",
    SupportType.FESTLAGER: "festlager",
    SupportType.LOSLAGER: "loslager",
    SupportType.FESTE_EINSPANNUNG: "feste_einspannung",
    SupportType.GLEITLAGER: "gleitlager",
}

_HINGE_NAMES = {
    HingeType.VOLLGELENK: "vollgelenk",
    HingeType.SCHUBGELENK: "schubgelenk",
    HingeType.NORMALKRAFTGELENK: "normalkraftgelenk",
    HingeType.BIEGESTEIFE_ECKE: "biegesteif",
    HingeType.HALBGELENK: "vollgelenk",
}


def _name(value, table, default):
    if value is None:
        return default
    return table.get(value, default)


def image_system_to_compact(system: ImageSystem,
                            span_meters: float = DEFAULT_SPAN_METERS) -> Dict[str, Any]:
    """Pixel-space generated system -> the compact format, y pointing up."""
    xs = [n.pixel_x for n in system.nodes] or [0.0]
    ys = [n.pixel_y for n in system.nodes] or [0.0]
    width = max(max(xs) - min(xs), 1e-9)
    scale = span_meters / width

    nodes: List[dict] = []
    labels: Dict[str, str] = {}
    for index, node in enumerate(system.nodes):
        label = _label(index)
        labels[node.id] = label
        item = {
            "id": label,
            "x": round((node.pixel_x - min(xs)) * scale, 4),
            # The flip: pixel y grows downward, world y grows up.
            "y": round((max(ys) - node.pixel_y) * scale, 4),
        }
        support = _name(node.support_type, _SUPPORT_NAMES, "frei")
        if support != "frei":
            item["support"] = support
        if getattr(node, "rotation", 0.0):
            item["rotation"] = float(node.rotation)
        nodes.append(item)

    members: List[dict] = []
    member_labels: Dict[str, str] = {}
    for member in system.members:
        start = labels.get(member.start_node_id)
        end = labels.get(member.end_node_id)
        if start is None or end is None:
            continue
        item = {"id": f"{start}-{end}", "start": start, "end": end}
        member_labels[member.id] = item["id"]
        for side, hinge in (("start", member.start_hinge), ("end", member.end_hinge)):
            name = _name(hinge, _HINGE_NAMES, "biegesteif")
            if name != "biegesteif":
                item[f"hinge_{side}"] = name
        members.append(item)

    loads: List[dict] = []
    for index, load in enumerate(system.loads):
        item = _compact_load(load, index, labels, member_labels)
        if item is not None:
            loads.append(item)

    return {"nodes": nodes, "members": members, "loads": loads}


def _compact_load(load, index: int, labels: Dict[str, str],
                  member_labels: Dict[str, str]) -> Optional[dict]:
    load_id = f"L{index + 1}"

    if load.load_type == LoadType.STRECKENLAST:
        member = member_labels.get(load.member_id)
        if member is None:
            return None
        item = {"id": load_id, "on": member, "type": "distributed", "q": 10.0}
        if load.start_ratio is not None and float(load.start_ratio) != 0.0:
            item["from"] = round(float(load.start_ratio), 4)
        if load.end_ratio is not None and float(load.end_ratio) != 1.0:
            item["to"] = round(float(load.end_ratio), 4)
        return item

    if load.load_type in (LoadType.MOMENT_UHRZEIGER, LoadType.MOMENT_GEGEN_UHRZEIGER):
        node = labels.get(load.node_id)
        if node is None:
            return None
        sign = 1.0 if load.load_type == LoadType.MOMENT_GEGEN_UHRZEIGER else -1.0
        return {"id": load_id, "on": node, "type": "moment", "value": 10.0 * sign}

    node = labels.get(load.node_id)
    if node is None:
        return None
    # The renderer measures arrow angles counter-clockwise on screen, which is
    # already the +y-up convention the compact format uses.
    angle = float(getattr(load, "angle_deg", 270.0) or 0.0)
    return {"id": load_id, "on": node, "type": "point", "value": 10.0,
            "angle": round(((angle + 180.0) % 360.0) - 180.0, 2)}


def _label(index: int) -> str:
    """A, B, ... Z, AA, AB, ... - short names an agent can also produce."""
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters
