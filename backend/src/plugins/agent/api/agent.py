"""HTTP surface for agents.

Everything an agent needs to go from "I have looked at a drawing" to "here is
the moment diagram", in the vocabulary of plugins/agent/schema.py rather than
the editor's.

Deliberately thin: no structural logic lives here. Systems are stored through
the same SystemManager the Save button uses, so a system an agent builds
appears in the editor's Open dialog and vice versa -- that shared workspace is
the point. Analysis is delegated to the existing solvers; this module only
translates the payload and shortens the answer.
"""

from __future__ import annotations

import io
import traceback
from typing import Any, Dict, Tuple

from flask import Blueprint, current_app, jsonify, request, send_file

from src.models.analyze import StructuralSystem
from src.plugins.agent import render as agent_render
from src.plugins.agent.checks import geometry_warnings
from src.plugins.agent.schema import (
    DEFAULT_MEMBER_PROPS, HINGES, SUPPORTS, SchemaError, compact, expand,
)
from src.plugins.analyze.fem import calculate_complex_fem
from src.plugins.analyze.kinematics import analyse as analyse_kinematics
from src.plugins.analyze.langrage.core import analyze_lagrangian_dynamics
from src.plugins.analyze.simplify import prune_cantilevers

bp = Blueprint("agent", __name__, url_prefix="/api/agent")

#: Renders are for looking at, not for archiving. Bigger costs the agent
#: tokens without telling it anything more.
_MAX_RENDER = (1600, 1200)


def _manager():
    return current_app.app_state.system_manager


def _fail(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _public_url(slug: str) -> str:
    """Where a human opens this system. nginx serves the SPA and proxies
    /api/ on the same host, so the request's own host is the right one."""
    return f"{request.host_url.rstrip('/')}/s/{slug}"


def _load_or_404(slug: str):
    system = _manager().load_system(slug)
    if system is None:
        raise LookupError(f"no system named {slug!r}. Call GET /api/agent/systems to list them.")
    return system


def _structural(system: Dict[str, Any]) -> StructuralSystem:
    return StructuralSystem.create(
        system.get("nodes", []), system.get("members", []), system.get("loads", []),
        system.get("scheiben", []), system.get("constraints", []),
    )


def _size_from_query() -> Tuple[int, int]:
    try:
        width = int(request.args.get("width", agent_render.DEFAULT_SIZE[0]))
        height = int(request.args.get("height", agent_render.DEFAULT_SIZE[1]))
    except (TypeError, ValueError):
        return agent_render.DEFAULT_SIZE
    return (max(200, min(width, _MAX_RENDER[0])), max(200, min(height, _MAX_RENDER[1])))


def _png(system: Dict[str, Any], download_name: str):
    image = agent_render.render_system(
        system,
        size=_size_from_query(),
        labels=request.args.get("labels", "1") not in ("0", "false", "no"),
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png", download_name=download_name)


@bp.errorhandler(SchemaError)
def _on_schema_error(exc: SchemaError):
    return _fail(str(exc))


@bp.errorhandler(LookupError)
def _on_missing(exc: LookupError):
    return _fail(str(exc), 404)


@bp.errorhandler(Exception)
def _on_unexpected(exc: Exception):
    traceback.print_exc()
    return _fail(f"server error: {exc}", 500)


# --- vocabulary -------------------------------------------------------

@bp.get("/schema")
def schema():
    """What may be written, so an agent never has to guess a keyword."""
    return jsonify({
        "supports": SUPPORTS,
        "hinges": HINGES,
        "load_types": ["point", "moment", "distributed",
                       "dynamic_force", "dynamic_moment"],
        "member_defaults": DEFAULT_MEMBER_PROPS,
        "conventions": {
            "axes": "+x right, +y up. Angles in degrees CCW from +x.",
            "gravity": "angle -90 with a positive value is a downward force.",
            "distributed": ("q has no angle. It acts perpendicular to the member, "
                            "positive along the member's local -y, which is downward "
                            "for a member drawn left to right."),
            "node_rotation": ("A node's optional `rotation` (degrees CCW) turns "
                              "the support's own frame: fixN then acts along the "
                              "rotated local x and fixV along local y, and the "
                              "symbol is drawn turned to match. Use it for a "
                              "support on an inclined surface, and 90 for a "
                              "member clamped into a vertical wall."),
            "units": {"force": "kN", "moment": "kNm", "length": "m", "time": "s"},
        },
        "example": {
            "nodes": [
                {"id": "A", "x": 0, "y": 0, "support": "festlager"},
                {"id": "B", "x": 6, "y": 0, "support": "loslager"},
            ],
            "members": [{"start": "A", "end": "B"}],
            "loads": [{"on": "A-B", "type": "distributed", "q": 10}],
        },
    })


@bp.get("/templates")
def templates():
    """Stored systems in compact form, for use as worked examples."""
    manager = _manager()
    out = []
    for meta in manager.list_systems():
        slug = meta.get("slug")
        system = manager.load_system(slug) if slug else None
        if not system:
            continue
        out.append({
            "slug": slug,
            "name": meta.get("name", slug),
            "saved_at": meta.get("saved_at"),
            "system": compact(system),
        })
    return jsonify(out)


# --- systems ----------------------------------------------------------

@bp.get("/systems")
def list_systems():
    return jsonify([
        {**meta, "url": _public_url(meta.get("slug", ""))}
        for meta in _manager().list_systems()
    ])


@bp.post("/systems")
def create_system():
    payload = request.get_json(force=True, silent=True) or {}
    name = str(payload.get("name") or "").strip()
    if not name:
        return _fail("a \"name\" is required; it becomes the slug in the URL")

    system, warnings = expand(payload.get("system") or {})
    slug = _manager().save_system(name, system)

    return jsonify({
        "slug": slug,
        "url": _public_url(slug),
        "warnings": warnings + geometry_warnings(system),
        "counts": {
            "nodes": len(system["nodes"]),
            "members": len(system["members"]),
            "loads": len(system["loads"]),
        },
    }), 201


@bp.get("/systems/<slug>")
def get_system(slug: str):
    system = _load_or_404(slug)
    return jsonify({
        "slug": slug,
        "url": _public_url(slug),
        "system": compact(system),
    })


@bp.patch("/systems/<slug>")
def patch_system(slug: str):
    """Replace whole sections of a stored system.

    Any of "nodes", "members" or "loads" that is present replaces that list
    entirely; anything absent is kept. Element-level merging was considered
    and dropped: an agent correcting a drawing rewrites a whole list far more
    often than it edits one node, and a half-merged system is hard to reason
    about from either side.
    """
    existing = _load_or_404(slug)
    payload = request.get_json(force=True, silent=True) or {}
    patch = payload.get("system", payload)

    merged = compact(existing)
    for key in ("nodes", "members", "loads", "scheiben", "constraints"):
        if key in patch:
            merged[key] = patch[key]

    system, warnings = expand(merged)
    name = payload.get("name") or slug
    new_slug = _manager().save_system(name, system)

    return jsonify({
        "slug": new_slug,
        "url": _public_url(new_slug),
        "warnings": warnings + geometry_warnings(system),
        "system": compact(system),
    })


# --- drawing ----------------------------------------------------------

@bp.get("/systems/<slug>/render")
def render_stored(slug: str):
    return _png(_load_or_404(slug), f"{slug}.png")


@bp.post("/render")
def render_unsaved():
    """Draw a compact system without storing it, for a quick look."""
    payload = request.get_json(force=True, silent=True) or {}
    system, _ = expand(payload.get("system") or payload)
    return _png(system, "system.png")


# --- analysis ---------------------------------------------------------

@bp.get("/systems/<slug>/validate")
@bp.post("/systems/<slug>/validate")
def validate(slug: str):
    """Can this be solved, and does it look like what was drawn?

    A system with dof > 0 is a mechanism: the stiffness matrix is singular and
    the static solve cannot produce an answer (README, Current Limitations).
    Saying so here is the difference between a useful message and a traceback.
    """
    system = _load_or_404(slug)
    result = analyse_kinematics(_structural(system)).to_dict()
    dof = int(result.get("dof", 0))

    return jsonify({
        "slug": slug,
        "dof": dof,
        "ready_for_analysis": dof == 0,
        "note": (
            "statically determinate or indeterminate - the static solve will run"
            if dof == 0 else
            f"{dof} kinematic degree(s) of freedom: this is a mechanism. Add "
            f"supports or members, or remove releases, before calling analyze."
        ),
        "modes": [
            {"index": m.get("index"),
             "moving_nodes": sorted(m.get("node_velocities", {}))}
            for m in result.get("modes", [])
        ],
        "warnings": geometry_warnings(system),
    })


@bp.get("/systems/<slug>/analyze/<kind>")
@bp.post("/systems/<slug>/analyze/<kind>")
def analyze(slug: str, kind: str):
    """Run one analysis. `?full=1` returns the raw solver output instead of a summary."""
    system = _load_or_404(slug)
    structural = _structural(system)
    full = request.args.get("full", "0") not in ("0", "false", "no")

    if kind == "simplify":
        return jsonify({"system": compact(prune_cantilevers(structural).to_dict())})

    if kind == "solution":
        result = calculate_complex_fem(structural)
        if not result.get("success"):
            return jsonify({"success": False, "error": result.get("error")})
        return jsonify(result if full else _summarise_solution(result))

    if kind == "dynamics":
        result = analyze_lagrangian_dynamics(
            system=structural, t_span=(0.0, 5.0), dt=0.02
        ).to_dict()
        if full or not result.get("success", False):
            return jsonify(result)
        return jsonify(_summarise_dynamics(result))

    return _fail(f"unknown analysis {kind!r}. Use simplify, solution or dynamics.")


def _summarise_solution(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extremes and reactions only.

    The raw result carries a sampled station for every point along every
    member -- thousands of numbers that would fill an agent's context without
    telling it anything the envelope does not. `?full=1` still returns them.
    """
    members = {}
    for member_id, member in (result.get("memberResults") or {}).items():
        members[member_id] = {
            "N": [member.get("minN"), member.get("maxN")],
            "V": [member.get("minV"), member.get("maxV")],
            "M": [member.get("minM"), member.get("maxM")],
        }

    displacements = result.get("displacements") or {}
    worst = max(
        ((node_id, max(abs(v) for v in vec[:2]))
         for node_id, vec in displacements.items() if vec),
        key=lambda pair: pair[1], default=(None, 0.0),
    )

    return {
        "success": True,
        "units": {"N": "kN", "V": "kN", "M": "kNm",
                  "reactions": "[Rx kN, Ry kN, Mz kNm]", "displacement": "m"},
        "reactions": result.get("reactions") or {},
        "members": members,
        "largest_displacement": {"node": worst[0], "magnitude": worst[1]},
        "note": "min/max envelopes per member. Add ?full=1 for the full diagrams.",
    }


def _summarise_dynamics(result: Dict[str, Any]) -> Dict[str, Any]:
    """Frequencies and peak response; the time series stays behind ?full=1."""
    summary = {"success": True, "note": "add ?full=1 for the full time history."}
    for key in ("frequencies", "natural_frequencies", "eigenfrequencies"):
        if result.get(key):
            summary["natural_frequencies_hz"] = result[key]
            break

    history = result.get("displacements") or result.get("u")
    if isinstance(history, dict):
        summary["peak_displacement"] = {
            node_id: max((abs(float(v)) for row in series
                          for v in (row if isinstance(row, (list, tuple)) else [row])),
                         default=0.0)
            for node_id, series in history.items()
        }
    return summary
