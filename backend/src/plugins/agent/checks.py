"""Cheap plausibility checks on a system an agent just built.

The kinematics solver answers "is this rechenbar" precisely. It does not
answer "did you read the drawing correctly", and the mistakes an agent makes
reading a drawing have a recognisable shape: two nodes placed on top of each
other because a joint was seen twice, a node written down but never connected,
a system with no supports at all because the hatching was mistaken for
decoration.

None of these are errors -- each is legal input -- so they come back as
warnings next to the analysis rather than as a refusal.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

#: Two nodes closer than this share of the system's diagonal are almost
#: certainly one joint entered twice. Loose enough not to fire on a short
#: stub member, tight enough to catch a duplicate.
_DUPLICATE_FRACTION = 0.01


def geometry_warnings(system: Dict[str, Any]) -> List[str]:
    nodes = list(system.get("nodes") or [])
    members = list(system.get("members") or [])
    out: List[str] = []

    if not nodes:
        return ["the system has no nodes"]

    points = {
        str(n.get("id")): (
            float((n.get("position") or {}).get("x", 0.0)),
            float((n.get("position") or {}).get("y", 0.0)),
        )
        for n in nodes
    }

    xs = [p[0] for p in points.values()]
    ys = [p[1] for p in points.values()]
    diagonal = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    tolerance = diagonal * _DUPLICATE_FRACTION

    if tolerance > 0:
        ids = list(points)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                gap = math.dist(points[a], points[b])
                if gap <= tolerance:
                    out.append(
                        f"nodes {a} and {b} are {gap:.4g} m apart - "
                        f"is that one joint entered twice?"
                    )

    attached = set()
    for member in members:
        attached.add(str(member.get("startNodeId")))
        attached.add(str(member.get("endNodeId")))
    for node_id in points:
        if node_id not in attached:
            out.append(f"node {node_id} is not connected to any member")

    if not any(
        any(bool(v) for v in (n.get("supports") or {}).values()) for n in nodes
    ):
        out.append("no node carries a support - the system can float away")

    if not members:
        out.append("the system has no members")

    return out
