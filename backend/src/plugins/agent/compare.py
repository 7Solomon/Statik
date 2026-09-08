"""Score one reconstructed system against the system that was actually drawn.

This is the measuring instrument for the question the whole agent path rests
on: can a model read a structural drawing well enough to be useful? The
generator can produce a picture and the exact system behind it, so the question
is answerable rather than a matter of opinion -- but only if "the same system"
is defined carefully.

Two systems are the same when they have the same joints in the same relative
places, connected the same way, carrying the same supports, releases and loads.
Three things are deliberately NOT required to match:

* **Names.** The agent invents its own node ids. Matching is by position.
* **Absolute size and origin.** A rendered drawing carries no dimensions, so an
  agent can only recover the shape, not the span. Both systems are normalised
  to a common frame before anything is compared. A drawing that *is* dimensioned
  gives the agent the numbers directly, which is the easy case -- this measures
  the hard one.
* **Load magnitudes.** Same reason: unless the renderer prints them, they are
  not in the picture. Loads are matched on where they sit, what type they are
  and which way they point.

What is NOT forgiven is a mirrored system. Normalisation translates and scales;
it never flips. Reading a drawing upside down is a real error.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment

#: A matched node may sit this far from its counterpart, as a share of the
#: system's bounding-box diagonal. Roughly "within half a joint symbol".
DEFAULT_TOLERANCE = 0.08

#: Two point loads point the same way if their angles agree this closely.
ANGLE_TOLERANCE_DEG = 30.0


def _points(system: Dict[str, Any]) -> Tuple[List[str], np.ndarray]:
    nodes = system.get("nodes") or []
    ids = [str(n.get("id")) for n in nodes]
    coords = np.array(
        [[float(n.get("x", 0.0)), float(n.get("y", 0.0))] for n in nodes],
        dtype=float,
    ).reshape(-1, 2)
    return ids, coords


def _normalise(coords: np.ndarray) -> Tuple[np.ndarray, float]:
    """Centre on the centroid and scale so the bounding-box diagonal is 1.

    Translation and uniform scale only -- no rotation and no reflection, so a
    mirrored or rotated reading stays wrong.
    """
    if len(coords) == 0:
        return coords, 0.0
    centred = coords - coords.mean(axis=0)
    span = centred.max(axis=0) - centred.min(axis=0) if len(coords) > 1 else np.zeros(2)
    diagonal = float(math.hypot(span[0], span[1]))
    if diagonal < 1e-12:
        return centred, 0.0
    return centred / diagonal, diagonal


def _match_nodes(truth: Dict[str, Any], prediction: Dict[str, Any],
                 tolerance: float) -> Tuple[Dict[str, str], List[float]]:
    """Pair predicted nodes with true ones by position. Returns pred_id -> truth_id."""
    truth_ids, truth_xy = _points(truth)
    pred_ids, pred_xy = _points(prediction)
    if not truth_ids or not pred_ids:
        return {}, []

    truth_n, _ = _normalise(truth_xy)
    pred_n, _ = _normalise(pred_xy)

    cost = np.linalg.norm(truth_n[:, None, :] - pred_n[None, :, :], axis=2)
    rows, cols = linear_sum_assignment(cost)

    mapping: Dict[str, str] = {}
    errors: List[float] = []
    for r, c in zip(rows, cols):
        distance = float(cost[r, c])
        if distance <= tolerance:
            mapping[pred_ids[c]] = truth_ids[r]
            errors.append(distance)
    return mapping, errors


def _member_key(member: dict, translate: Optional[Dict[str, str]] = None):
    """A member as the unordered pair of its endpoints, in truth's namespace."""
    a, b = str(member.get("start")), str(member.get("end"))
    if translate is not None:
        if a not in translate or b not in translate:
            return None
        a, b = translate[a], translate[b]
    return frozenset((a, b))


def _prf(hits: int, n_truth: int, n_pred: int) -> Dict[str, float]:
    precision = hits / n_pred if n_pred else (1.0 if not n_truth else 0.0)
    recall = hits / n_truth if n_truth else (1.0 if not n_pred else 0.0)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4),
            "f1": round(f1, 4), "matched": hits,
            "in_truth": n_truth, "in_prediction": n_pred}


def _support_of(system: Dict[str, Any]) -> Dict[str, str]:
    out = {}
    for node in system.get("nodes") or []:
        support = node.get("support", "frei")
        # An unusual fix combination comes back from compact() as a dict; its
        # sorted items still compare cleanly.
        out[str(node.get("id"))] = (
            support if isinstance(support, str) else str(sorted(support.items()))
        )
    return out


def _hinges_of(system: Dict[str, Any]) -> Dict[frozenset, Dict[str, str]]:
    """member key -> {endpoint node id: hinge name}.

    Keyed by endpoint rather than by "start"/"end" so that a member the agent
    happened to write the other way round still compares correctly.
    """
    out: Dict[frozenset, Dict[str, str]] = {}
    for member in system.get("members") or []:
        start, end = str(member.get("start")), str(member.get("end"))
        out[frozenset((start, end))] = {
            start: member.get("hinge_start", "biegesteif"),
            end: member.get("hinge_end", "biegesteif"),
        }
    return out


def _load_key(load: dict, translate: Optional[Dict[str, str]],
              member_keys: Dict[str, frozenset]) -> Optional[tuple]:
    """A load as (where it sits, what it is, which way it points).

    Magnitude is left out on purpose -- see the module docstring.
    """
    kind = str(load.get("type", "point")).lower()
    on = str(load.get("on"))

    if on in member_keys:
        target = member_keys[on]
        if translate is not None:
            if not all(n in translate for n in target):
                return None
            target = frozenset(translate[n] for n in target)
    else:
        target = translate.get(on) if translate is not None else on
        if target is None:
            return None

    if kind in ("point", "dynamic_force"):
        angle = float(load.get("angle", -90) or 0.0) % 360.0
        # Quantise so that two readings within the tolerance land together.
        bucket = round(angle / ANGLE_TOLERANCE_DEG)
        return (target, kind, bucket)
    if kind in ("moment", "dynamic_moment"):
        return (target, kind, 1 if float(load.get("value", 0) or 0) >= 0 else -1)
    return (target, kind)


def _member_keys_by_id(system: Dict[str, Any]) -> Dict[str, frozenset]:
    out = {}
    for member in system.get("members") or []:
        key = frozenset((str(member.get("start")), str(member.get("end"))))
        out[str(member.get("id") or f"{member.get('start')}-{member.get('end')}")] = key
    return out


def compare_systems(truth: Dict[str, Any], prediction: Dict[str, Any], *,
                    tolerance: float = DEFAULT_TOLERANCE) -> Dict[str, Any]:
    """Score `prediction` against `truth`. Both in the compact agent format."""
    mapping, errors = _match_nodes(truth, prediction, tolerance)
    truth_ids, _ = _points(truth)
    pred_ids, _ = _points(prediction)

    notes: List[str] = []
    nodes = _prf(len(mapping), len(truth_ids), len(pred_ids))
    nodes["mean_position_error"] = round(float(np.mean(errors)), 4) if errors else None
    nodes["max_position_error"] = round(float(np.max(errors)), 4) if errors else None
    if len(pred_ids) != len(truth_ids):
        notes.append(f"node count {len(pred_ids)}, expected {len(truth_ids)}")

    # --- members ---
    truth_members = {k for k in (_member_key(m) for m in truth.get("members") or [])
                     if k is not None}
    pred_members = {k for k in (_member_key(m, mapping)
                                for m in prediction.get("members") or [])
                    if k is not None}
    members = _prf(len(truth_members & pred_members), len(truth_members),
                   len(prediction.get("members") or []))
    for missing in truth_members - pred_members:
        notes.append(f"member {'-'.join(sorted(missing))} missing")

    # --- supports, over matched nodes only ---
    truth_supports, pred_supports = _support_of(truth), _support_of(prediction)
    support_hits = 0
    for pred_id, truth_id in mapping.items():
        if pred_supports.get(pred_id, "frei") == truth_supports.get(truth_id, "frei"):
            support_hits += 1
        else:
            notes.append(
                f"support at {truth_id}: read as "
                f"{pred_supports.get(pred_id, 'frei')}, is "
                f"{truth_supports.get(truth_id, 'frei')}"
            )
    supports = {"correct": support_hits, "of_matched_nodes": len(mapping),
                "accuracy": round(support_hits / len(mapping), 4) if mapping else None}

    # --- releases, over members present in both ---
    truth_hinges, pred_hinges_raw = _hinges_of(truth), _hinges_of(prediction)
    pred_hinges = {}
    for key, ends in pred_hinges_raw.items():
        if all(n in mapping for n in key):
            pred_hinges[frozenset(mapping[n] for n in key)] = {
                mapping[n]: h for n, h in ends.items()
            }
    shared = truth_members & set(pred_hinges)
    hinge_hits = 0
    for key in shared:
        if truth_hinges[key] == pred_hinges[key]:
            hinge_hits += 1
        else:
            notes.append(
                f"releases on {'-'.join(sorted(key))}: read as "
                f"{pred_hinges[key]}, are {truth_hinges[key]}"
            )
    hinges = {"correct": hinge_hits, "of_shared_members": len(shared),
              "accuracy": round(hinge_hits / len(shared), 4) if shared else None}

    # --- loads ---
    truth_member_keys = _member_keys_by_id(truth)
    pred_member_keys = _member_keys_by_id(prediction)
    truth_loads = [k for k in (_load_key(l, None, truth_member_keys)
                               for l in truth.get("loads") or []) if k]
    pred_loads = [k for k in (_load_key(l, mapping, pred_member_keys)
                              for l in prediction.get("loads") or []) if k]
    truth_bag, pred_bag = list(truth_loads), list(pred_loads)
    load_hits = 0
    for key in list(pred_bag):
        if key in truth_bag:
            truth_bag.remove(key)
            load_hits += 1
    loads = _prf(load_hits, len(truth_loads), len(prediction.get("loads") or []))

    topology_exact = (
        nodes["matched"] == len(truth_ids) == len(pred_ids)
        and members["f1"] == 1.0
    )
    fully_correct = (
        topology_exact
        and supports["accuracy"] == 1.0
        and (hinges["accuracy"] in (1.0, None))
        and loads["f1"] == 1.0
    )

    return {
        "nodes": nodes,
        "members": members,
        "supports": supports,
        "releases": hinges,
        "loads": loads,
        "topology_exact": topology_exact,
        "fully_correct": fully_correct,
        "notes": notes,
    }


def aggregate(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Averages over a batch of comparisons."""
    if not results:
        return {"samples": 0}

    def mean(values):
        values = [v for v in values if v is not None]
        return round(float(np.mean(values)), 4) if values else None

    return {
        "samples": len(results),
        "node_f1": mean([r["nodes"]["f1"] for r in results]),
        "member_f1": mean([r["members"]["f1"] for r in results]),
        "support_accuracy": mean([r["supports"]["accuracy"] for r in results]),
        "release_accuracy": mean([r["releases"]["accuracy"] for r in results]),
        "load_f1": mean([r["loads"]["f1"] for r in results]),
        "mean_position_error": mean([r["nodes"]["mean_position_error"] for r in results]),
        "topology_exact_rate": round(
            sum(1 for r in results if r["topology_exact"]) / len(results), 4),
        "fully_correct_rate": round(
            sum(1 for r in results if r["fully_correct"]) / len(results), 4),
    }


# --- what the picture can even show ------------------------------------

def unobservable_nodes(system: Dict[str, Any]) -> List[str]:
    """Nodes that leave no mark in the rendering, and so cannot be read off it.

    The generator draws members, supports, releases and loads -- it does not
    draw joints. A node in the middle of a straight run, carrying no support,
    no release and no load, is therefore invisible: the drawing is pixel for
    pixel identical whether it is there or not.

    This matters for interpreting a score. A reconstruction that misses such a
    node is not a misreading; the information was not in the image. Measuring
    it separates "the model read badly" from "the eval set asks the
    impossible".
    """
    nodes = {str(n.get("id")): n for n in system.get("nodes") or []}
    positions = {
        nid: (float(n.get("x", 0.0)), float(n.get("y", 0.0)))
        for nid, n in nodes.items()
    }

    attached: Dict[str, List[dict]] = {nid: [] for nid in nodes}
    for member in system.get("members") or []:
        for side in ("start", "end"):
            nid = str(member.get(side))
            if nid in attached:
                attached[nid].append({"member": member, "side": side})

    marked = set()
    for load in system.get("loads") or []:
        on = str(load.get("on"))
        if on in nodes:
            marked.add(on)

    invisible = []
    for nid, node in nodes.items():
        if node.get("support") not in (None, "frei"):
            continue
        if nid in marked:
            continue
        ends = attached[nid]
        if len(ends) != 2:
            continue  # a free end or a real junction shows in the line work
        if any(e["member"].get(f"hinge_{e['side']}", "biegesteif") != "biegesteif"
               for e in ends):
            continue

        others = []
        for end in ends:
            member = end["member"]
            other = member["end"] if end["side"] == "start" else member["start"]
            others.append(positions.get(str(other)))
        if any(p is None for p in others):
            continue

        (x0, y0), (x1, y1) = others
        x, y = positions[nid]
        # Collinear when the cross product of the two directions vanishes,
        # scaled by the segment lengths so the tolerance means "degrees".
        ax, ay = x - x0, y - y0
        bx, by = x1 - x, y1 - y
        la, lb = math.hypot(ax, ay), math.hypot(bx, by)
        if la < 1e-9 or lb < 1e-9:
            continue
        if abs(ax * by - ay * bx) / (la * lb) < 0.02:
            invisible.append(nid)

    return sorted(invisible)


def identifiability(system: Dict[str, Any]) -> Dict[str, Any]:
    """How much of a system a perfect reader could recover from its picture."""
    total = len(system.get("nodes") or [])
    hidden = unobservable_nodes(system)
    return {
        "nodes": total,
        "unobservable": hidden,
        "recoverable_fraction": round((total - len(hidden)) / total, 4) if total else 1.0,
        "fully_recoverable": not hidden,
    }
