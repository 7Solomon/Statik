"""Compact, agent-facing system format.

The editor's own JSON is shaped for the UI: camelCase, a UUID on every
element, material properties repeated on every member, releases nested two
levels deep. An agent writing that by hand gets it wrong in predictable
places -- it invents malformed UUIDs, forgets ``scope``, or puts
``releases.start.mz`` one level off.

This module defines a flatter format and translates both ways. ``expand()``
is the only place that knows the editor's field names; ``compact()`` is its
inverse, so an agent can read a system back without carrying kilobytes of
UUIDs through its context.

Identifiers are kept as written. A node called "A" is still "A" on the way
out and a member reference stays readable as "A-B". Nothing downstream needs
UUIDs: the editor's sanitiser only asks for a non-empty string id
(frontend/app/utils/sanitize_system.ts) and the analysis models stringify
whatever they are given (StructuralSystem.create).

Sign conventions are NOT unified here, because the solver's are not:

* POINT / DYNAMIC_FORCE carry an ``angle`` in degrees, measured CCW from +x,
  so -90 is the direction gravity acts. A positive ``value`` at angle -90 is
  a downward force.
* DISTRIBUTED has no angle at all. Its ``q`` acts perpendicular to the member
  and positive means along the member's local -y (see the module docstring of
  plugins/analyze/fem/loads.py). For a member drawn left-to-right that is
  downward.

Both are documented on the way in rather than silently converted, because a
conversion here would disagree with what the FEM actually integrates.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


class SchemaError(ValueError):
    """A compact document that cannot be expanded.

    The message ends up in an agent's context, so it says what to write
    instead rather than only what was wrong.
    """


# --- vocabulary -------------------------------------------------------
# Canonical spellings are the ones the editor already uses, so that a system
# built here and one drawn by hand are described with the same words.
# The support table mirrors SUPPORT_PRESETS in
# frontend/app/features/editor/interaction/NodeInteractionHandler.ts.

SUPPORTS: Dict[str, Dict[str, bool]] = {
    "frei":              {"fixN": False, "fixV": False, "fixM": False},
    "festlager":         {"fixN": True,  "fixV": True,  "fixM": False},
    "loslager":          {"fixN": False, "fixV": True,  "fixM": False},
    "feste_einspannung": {"fixN": True,  "fixV": True,  "fixM": True},
    "gleitlager":        {"fixN": True,  "fixV": False, "fixM": True},
}

_SUPPORT_ALIASES = {
    "none": "frei", "free": "frei", "keins": "frei", "kein": "frei",
    "pinned": "festlager", "pin": "festlager", "gelenklager": "festlager",
    "roller": "loslager", "rollenlager": "loslager",
    "einspannung": "feste_einspannung", "fixed": "feste_einspannung",
    "clamped": "feste_einspannung", "eingespannt": "feste_einspannung",
    "slider": "gleitlager", "schiebelager": "gleitlager",
}

# Mirrors HINGE_PRESETS in the editor's HingeInteractionHandler. A rigid
# corner is the absence of a release, not a symbol -- see the note in
# generator/image/stanli_symbols.py.
HINGES: Dict[str, Dict[str, bool]] = {
    "biegesteif":        {"fx": False, "fy": False, "mz": False},
    "vollgelenk":        {"fx": False, "fy": False, "mz": True},
    "schubgelenk":       {"fx": False, "fy": True,  "mz": False},
    "normalkraftgelenk": {"fx": True,  "fy": False, "mz": False},
}

_HINGE_ALIASES = {
    "none": "biegesteif", "rigid": "biegesteif", "keins": "biegesteif",
    "biegesteife_ecke": "biegesteif", "starr": "biegesteif",
    "gelenk": "vollgelenk", "hinge": "vollgelenk", "momentengelenk": "vollgelenk",
    "pin": "vollgelenk", "moment": "vollgelenk",
    "shear": "schubgelenk", "querkraftgelenk": "schubgelenk",
    "axial": "normalkraftgelenk", "normalkraft": "normalkraftgelenk",
}

#: Matches DEFAULT_MEMBER_PROPS in frontend/app/utils/sanitize_system.ts.
#: A system built by an agent and one drawn in the editor must not differ in
#: stiffness just because nobody typed a number.
DEFAULT_MEMBER_PROPS = {"E": 210e9, "A": 0.005, "I": 0.0001, "m": 1}

_SIGNALS = {"harmonic": "HARMONIC", "step": "STEP", "pulse": "PULSE", "ramp": "RAMP"}

#: Anything without whitespace, short enough to stay readable in a diagram.
_ID_RE = re.compile(r"^[^\s]{1,64}$")


def _norm(value: Any) -> str:
    """Fold a written keyword to its lookup form: 'Feste Einspannung' -> 'feste_einspannung'."""
    return re.sub(r"[\s\-]+", "_", str(value).strip().lower())


def _keyword(value: Any, table: Dict[str, Dict[str, bool]], aliases: Dict[str, str],
             what: str) -> str:
    key = _norm(value)
    key = aliases.get(key, key)
    if key not in table:
        raise SchemaError(
            f"unknown {what} {value!r}. Use one of: {', '.join(sorted(table))}"
        )
    return key


def _number(value: Any, field: str, where: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise SchemaError(f"{where}: {field} must be a number, got {value!r}")


def _check_id(value: Any, where: str) -> str:
    text = str(value).strip()
    if not _ID_RE.match(text):
        raise SchemaError(
            f"{where}: id {value!r} is unusable. Use a short name without "
            f"whitespace, e.g. \"A\" or \"knoten_3\"."
        )
    return text


def _ratio(value: Any, field: str, where: str, default: float) -> float:
    if value is None:
        return default
    r = _number(value, field, where)
    if not 0.0 <= r <= 1.0:
        raise SchemaError(f"{where}: {field} is a fraction of the member, 0..1, got {r}")
    return r


# --- expand -----------------------------------------------------------

def expand(doc: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Compact document -> the editor's system JSON.

    Returns the system and a list of warnings: things that were accepted but
    are probably not what was meant. Anything that cannot be represented at
    all raises SchemaError instead.
    """
    if not isinstance(doc, dict):
        raise SchemaError("the system must be a JSON object with a \"nodes\" list")

    warnings: List[str] = []
    nodes, node_ids = _expand_nodes(doc.get("nodes"), warnings)
    members, member_ids = _expand_members(doc.get("members"), node_ids, warnings)
    loads = _expand_loads(doc.get("loads"), node_ids, member_ids, warnings)

    # Scheiben and Constraints have no compact form yet: an agent working from
    # a drawing does not produce them, and inventing a second spelling for
    # something nobody writes would be a liability. Editor JSON passes through
    # untouched so a round-trip through compact()/expand() never loses them.
    scheiben = list(doc.get("scheiben") or [])
    constraints = list(doc.get("constraints") or [])

    return {
        "nodes": nodes,
        "members": members,
        "loads": loads,
        "scheiben": scheiben,
        "constraints": constraints,
    }, warnings


def _expand_nodes(raw: Any, warnings: List[str]) -> Tuple[List[dict], List[str]]:
    if not isinstance(raw, list) or not raw:
        raise SchemaError(
            "\"nodes\" must be a non-empty list of "
            "{\"id\": \"A\", \"x\": 0, \"y\": 0, \"support\": \"festlager\"}"
        )

    out: List[dict] = []
    seen: Dict[str, int] = {}
    for i, item in enumerate(raw):
        where = f"nodes[{i}]"
        if not isinstance(item, dict):
            raise SchemaError(f"{where}: expected an object, got {item!r}")

        node_id = _check_id(item.get("id", chr(ord('A') + i) if i < 26 else f"N{i}"), where)
        if node_id in seen:
            raise SchemaError(
                f"{where}: node id {node_id!r} is already used by nodes[{seen[node_id]}]"
            )
        seen[node_id] = i

        support = item.get("support")
        if support is None:
            fixes = dict(SUPPORTS["frei"])
        elif isinstance(support, dict):
            # Escape hatch for spring stiffnesses, which are numbers rather
            # than booleans in the editor (Supports.fix_* is bool | float).
            fixes = {k: support.get(k, False) for k in ("fixN", "fixV", "fixM")}
        else:
            fixes = dict(SUPPORTS[_keyword(support, SUPPORTS, _SUPPORT_ALIASES, "support")])

        out.append({
            "id": node_id,
            "position": {
                "x": _number(item.get("x", 0), "x", where),
                "y": _number(item.get("y", 0), "y", where),
            },
            "rotation": _number(item.get("rotation", 0), "rotation", where),
            "supports": fixes,
        })

    return out, list(seen)


def _expand_members(raw: Any, node_ids: List[str],
                    warnings: List[str]) -> Tuple[List[dict], List[str]]:
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        raise SchemaError("\"members\" must be a list of {\"start\": \"A\", \"end\": \"B\"}")

    known = set(node_ids)
    out: List[dict] = []
    used: Dict[str, int] = {}
    pairs: Dict[frozenset, int] = {}

    for i, item in enumerate(raw):
        where = f"members[{i}]"
        if not isinstance(item, dict):
            raise SchemaError(f"{where}: expected an object, got {item!r}")

        start = str(item.get("start", "")).strip()
        end = str(item.get("end", "")).strip()
        for name, value in (("start", start), ("end", end)):
            if value not in known:
                raise SchemaError(
                    f"{where}: {name} {value!r} is not a node id. "
                    f"Known nodes: {', '.join(node_ids)}"
                )
        if start == end:
            raise SchemaError(f"{where}: a member cannot start and end at {start!r}")

        pair = frozenset((start, end))
        if pair in pairs:
            warnings.append(
                f"{where}: a second member already connects {start} and {end} "
                f"(members[{pairs[pair]}])"
            )
        pairs.setdefault(pair, i)

        member_id = _check_id(item.get("id") or f"{start}-{end}", where)
        if member_id in used:
            member_id = f"{member_id}#{i}"
        used[member_id] = i

        props = dict(DEFAULT_MEMBER_PROPS)
        for key in props:
            if item.get(key) is not None:
                props[key] = _number(item[key], key, where)

        out.append({
            "id": member_id,
            "startNodeId": start,
            "endNodeId": end,
            "properties": props,
            "releases": {
                "start": dict(HINGES[_keyword(item.get("hinge_start", "biegesteif"),
                                              HINGES, _HINGE_ALIASES, "hinge")]),
                "end": dict(HINGES[_keyword(item.get("hinge_end", "biegesteif"),
                                            HINGES, _HINGE_ALIASES, "hinge")]),
            },
        })

    return out, list(used)


def _resolve_target(on: Any, node_ids: List[str], member_ids: List[str],
                    where: str) -> Tuple[str, str]:
    """Return ('node'|'member', id) for a load's ``on`` reference.

    Members are checked first because their default id is built from two node
    names ("A-B") and can never collide with a single node's.
    """
    ref = str(on).strip()
    if ref in member_ids:
        return "member", ref
    if ref in node_ids:
        return "node", ref

    # "B-A" for a member stored as "A-B": the agent named the same member from
    # the other end, which is not a mistake worth failing over.
    if "-" in ref:
        a, _, b = ref.partition("-")
        flipped = f"{b}-{a}"
        if flipped in member_ids:
            return "member", flipped

    raise SchemaError(
        f"{where}: \"on\": {on!r} matches no node or member. "
        f"Nodes: {', '.join(node_ids)}. Members: {', '.join(member_ids) or '(none)'}"
    )


def _expand_loads(raw: Any, node_ids: List[str], member_ids: List[str],
                  warnings: List[str]) -> List[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise SchemaError(
            "\"loads\" must be a list of "
            "{\"on\": \"A-B\", \"type\": \"distributed\", \"q\": -10}"
        )

    out: List[dict] = []
    for i, item in enumerate(raw):
        where = f"loads[{i}]"
        if not isinstance(item, dict):
            raise SchemaError(f"{where}: expected an object, got {item!r}")

        kind = _norm(item.get("type", "point"))
        scope, target = _resolve_target(item.get("on"), node_ids, member_ids, where)
        load_id = _check_id(item.get("id") or f"L{i + 1}", where)

        if kind in ("dynamic_force", "dynamic_moment"):
            if scope != "node":
                raise SchemaError(
                    f"{where}: dynamic loads sit on a node, not on member {target!r}. "
                    f"See the README under Current Limitations."
                )
            out.append(_dynamic_load(item, load_id, target, kind, where))
            continue

        if kind == "distributed":
            if scope != "member":
                raise SchemaError(
                    f"{where}: a distributed load runs along a member; {target!r} is a node"
                )
            out.append(_distributed_load(item, load_id, target, where))
            continue

        if kind not in ("point", "moment"):
            raise SchemaError(
                f"{where}: unknown load type {item.get('type')!r}. Use point, "
                f"moment, distributed, dynamic_force or dynamic_moment."
            )

        value = _number(item.get("value", item.get("f", 0)), "value", where)
        if value == 0:
            warnings.append(f"{where}: value is 0, this load does nothing")

        if kind == "moment":
            if scope != "node":
                raise SchemaError(
                    f"{where}: a moment attaches to a node; {target!r} is a member. "
                    f"Put it on one of the member's end nodes."
                )
            out.append({"id": load_id, "scope": "NODE", "type": "MOMENT",
                        "nodeId": target, "value": value, "isGlobal": True})
            continue

        # POINT, on a node or somewhere along a member.
        angle = _number(item.get("angle", -90), "angle", where)
        load = {"id": load_id, "type": "POINT", "value": value,
                "angle": angle, "isGlobal": True}
        if scope == "node":
            load.update({"scope": "NODE", "nodeId": target})
        else:
            load.update({"scope": "MEMBER", "memberId": target,
                         "ratio": _ratio(item.get("at"), "at", where, 0.5)})
        out.append(load)

    return out


def _distributed_load(item: dict, load_id: str, member_id: str, where: str) -> dict:
    """Uniform or trapezoidal load over all or part of a member.

    ``q`` is perpendicular to the member, positive along its local -y. There is
    deliberately no angle: the solver has none either.
    """
    has_ends = item.get("q_start") is not None or item.get("q_end") is not None
    if has_ends:
        q_start = _number(item.get("q_start", item.get("q", 0)), "q_start", where)
        q_end = _number(item.get("q_end", item.get("q", 0)), "q_end", where)
    else:
        q_start = q_end = _number(item.get("q", item.get("value", 0)), "q", where)

    start_ratio = _ratio(item.get("from"), "from", where, 0.0)
    end_ratio = _ratio(item.get("to"), "to", where, 1.0)
    if end_ratio < start_ratio:
        start_ratio, end_ratio = end_ratio, start_ratio

    load = {
        "id": load_id, "scope": "MEMBER", "type": "DISTRIBUTED",
        "memberId": member_id,
        # `value` is the fallback the solver reads when the per-end values are
        # absent (distributed_profile in fem/loads.py), so it must stay set.
        "value": q_start,
        "startRatio": start_ratio, "endRatio": end_ratio,
        "isGlobal": True,
    }
    if q_start != q_end:
        load["startValue"] = q_start
        load["endValue"] = q_end
    return load


def _dynamic_load(item: dict, load_id: str, node_id: str, kind: str, where: str) -> dict:
    raw = item.get("signal")
    if not isinstance(raw, dict):
        raise SchemaError(
            f"{where}: a dynamic load needs a \"signal\", e.g. "
            f"{{\"type\": \"harmonic\", \"amplitude\": 10, \"frequency\": 2}}"
        )

    sig_type = _SIGNALS.get(_norm(raw.get("type", "harmonic")))
    if sig_type is None:
        raise SchemaError(
            f"{where}: unknown signal type {raw.get('type')!r}. "
            f"Use one of: {', '.join(sorted(_SIGNALS))}"
        )

    amplitude = _number(raw.get("amplitude", item.get("value", 0)), "amplitude", where)
    signal = {
        "type": sig_type,
        "amplitude": amplitude,
        "startTime": _number(raw.get("start_time", raw.get("startTime", 0)),
                             "start_time", where),
        "frequency": _number(raw.get("frequency", 0), "frequency", where),
        "phase": _number(raw.get("phase", 0), "phase", where),
        "endTime": _number(raw.get("end_time", raw.get("endTime", 0)), "end_time", where),
        "offset": _number(raw.get("offset", 0), "offset", where),
    }

    load = {
        "id": load_id, "scope": "NODE", "nodeId": node_id,
        "type": "DYNAMIC_FORCE" if kind == "dynamic_force" else "DYNAMIC_MOMENT",
        "value": amplitude, "signal": signal, "isGlobal": True,
    }
    if kind == "dynamic_force":
        load["angle"] = _number(item.get("angle", -90), "angle", where)
    return load


# --- compact ----------------------------------------------------------

def _support_name(supports: dict) -> Any:
    fixes = {k: supports.get(k, False) for k in ("fixN", "fixV", "fixM")}
    for name, preset in SUPPORTS.items():
        if fixes == preset:
            return name
    # A spring stiffness, or some combination the editor has no button for.
    return fixes


def _hinge_name(release: dict) -> str:
    flags = {k: bool(release.get(k, False)) for k in ("fx", "fy", "mz")}
    for name, preset in HINGES.items():
        if flags == preset:
            return name
    return "biegesteif"


def compact(system: Dict[str, Any]) -> Dict[str, Any]:
    """Editor system JSON -> the compact format. Inverse of expand().

    Lossy only where the editor holds something the compact format has no word
    for: Scheiben and Constraints are copied through verbatim, and an exotic
    support combination comes back as its raw fixN/fixV/fixM object.
    """
    out: Dict[str, Any] = {"nodes": [], "members": [], "loads": []}

    for node in system.get("nodes") or []:
        pos = node.get("position") or {}
        item = {
            "id": node.get("id"),
            "x": round(float(pos.get("x", 0)), 6),
            "y": round(float(pos.get("y", 0)), 6),
        }
        support = _support_name(node.get("supports") or {})
        if support != "frei":
            item["support"] = support
        if float(node.get("rotation", 0) or 0):
            item["rotation"] = float(node["rotation"])
        out["nodes"].append(item)

    for member in system.get("members") or []:
        item = {
            "id": member.get("id"),
            "start": member.get("startNodeId"),
            "end": member.get("endNodeId"),
        }
        releases = member.get("releases") or {}
        for side in ("start", "end"):
            hinge = _hinge_name(releases.get(side) or {})
            if hinge != "biegesteif":
                item[f"hinge_{side}"] = hinge
        props = member.get("properties") or {}
        for key, default in DEFAULT_MEMBER_PROPS.items():
            value = props.get(key)
            if value is not None and float(value) != float(default):
                item[key] = float(value)
        out["members"].append(item)

    for load in system.get("loads") or []:
        out["loads"].append(_compact_load(load))

    for key in ("scheiben", "constraints"):
        if system.get(key):
            out[key] = system[key]

    return out


def _compact_load(load: dict) -> dict:
    kind = str(load.get("type", "POINT")).upper()
    on = load.get("memberId") if load.get("scope") == "MEMBER" else load.get("nodeId")
    item: Dict[str, Any] = {"id": load.get("id"), "on": on}

    if kind == "DISTRIBUTED":
        item["type"] = "distributed"
        q_start = load.get("startValue", load.get("value", 0))
        q_end = load.get("endValue", load.get("value", 0))
        if float(q_start) == float(q_end):
            item["q"] = float(q_start)
        else:
            item["q_start"] = float(q_start)
            item["q_end"] = float(q_end)
        if float(load.get("startRatio", 0) or 0) != 0.0:
            item["from"] = float(load["startRatio"])
        if load.get("endRatio") is not None and float(load["endRatio"]) != 1.0:
            item["to"] = float(load["endRatio"])
        return item

    if kind.startswith("DYNAMIC"):
        item["type"] = kind.lower()
        signal = load.get("signal") or {}
        compact_signal = {"type": str(signal.get("type", "HARMONIC")).lower(),
                          "amplitude": float(signal.get("amplitude", 0) or 0)}
        for src, dst in (("frequency", "frequency"), ("phase", "phase"),
                         ("startTime", "start_time"), ("endTime", "end_time"),
                         ("offset", "offset")):
            if float(signal.get(src, 0) or 0):
                compact_signal[dst] = float(signal[src])
        item["signal"] = compact_signal
        if kind == "DYNAMIC_FORCE":
            item["angle"] = float(load.get("angle", -90) or 0)
        return item

    item["type"] = "moment" if kind == "MOMENT" else "point"
    item["value"] = float(load.get("value", 0) or 0)
    if kind != "MOMENT":
        item["angle"] = float(load.get("angle", -90) or 0)
        if load.get("scope") == "MEMBER":
            item["at"] = float(load.get("ratio", 0.5) or 0.5)
    return item
