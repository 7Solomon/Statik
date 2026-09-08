"""Statik as a set of agent tools.

The division of labour: the agent reads the drawing -- with its own eyes, not a
detector -- and writes down what it sees; Statik draws it back, checks whether
it can be solved, and solves it. Nothing here knows any structural mechanics.
Every tool is one HTTP call against /api/agent/*, so the editor's web UI and an
agent always work from the same rules.

Because the agent is the only thing that looked at the picture, there is no
second opinion on whether it read the picture correctly. That is what
`statik_render` is for, and why the instructions below insist on it.

Configuration:
    STATIK_URL    base URL of the Statik instance (default http://localhost)
    STATIK_TOKEN  sent as `Authorization: Bearer ...` when set

Run:
    uv run statik-mcp          # or: python -m statik_mcp.server
"""

from __future__ import annotations

import os
from typing import Any, Literal

import httpx
from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

BASE_URL = os.environ.get("STATIK_URL", "http://localhost").rstrip("/")
TOKEN = os.environ.get("STATIK_TOKEN")

#: An analysis of a large system is the slow call here; a render is fast.
TIMEOUT = httpx.Timeout(120.0, connect=10.0)

INSTRUCTIONS = """\
Statik builds, draws, checks and solves 2D structural systems (Stabtragwerke).

Read a structural drawing yourself and write down what you see. Then:

  1. statik_build_system  - write the system down
  2. statik_render        - LOOK at the drawing that comes back and compare it
                            with the original. This is the only check on
                            whether you read the picture correctly. Never skip
                            it, and fix what differs with statik_update_system.
  3. statik_validate      - a system with dof > 0 is a mechanism and cannot be
                            solved statically. Fix it before step 4.
  4. statik_analyze       - internal forces, or the dynamic response.

Conventions, in every tool: +x right, +y UP. Angles in degrees counter-
clockwise from +x, so -90 points the way gravity acts. Forces in kN, moments
in kNm, lengths in m, time in s.

Take dimensions from the drawing's own annotation whenever it has any -- an
exercise sheet that says "6,00 m" is telling you the number, and reading it is
far more accurate than estimating from the picture. Only estimate coordinates
where nothing is dimensioned, and say so when you do.
"""

mcp = MCPServer(
    name="statik",
    version="0.1.0",
    instructions=INSTRUCTIONS,
    website_url=BASE_URL,
)


# --- transport --------------------------------------------------------

def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}


async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    url = f"{BASE_URL}/api/agent{path}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=_headers()) as client:
            return await client.request(method, url, **kwargs)
    except httpx.RequestError as exc:
        # A ToolError's message reaches the model; anything else is replaced by
        # a generic one, so an unreachable server has to be reported as one.
        raise ToolError(
            f"cannot reach Statik at {BASE_URL} ({exc.__class__.__name__}). "
            f"Set STATIK_URL if the instance lives somewhere else."
        ) from exc


def _json(response: httpx.Response) -> Any:
    """Unwrap a JSON response, turning the API's own error text into a ToolError.

    The backend's messages are written to be acted on -- they name the unknown
    keyword and list the valid ones. Losing them to a generic failure would
    throw away the most useful thing the API says.
    """
    if response.status_code >= 400:
        try:
            detail = response.json().get("error") or response.text
        except ValueError:
            detail = response.text.strip()[:400] or f"HTTP {response.status_code}"
        raise ToolError(detail)
    try:
        return response.json()
    except ValueError as exc:
        raise ToolError(f"Statik returned no JSON: {response.text[:200]}") from exc


# --- reference --------------------------------------------------------

@mcp.tool()
async def statik_conventions() -> dict:
    """Every keyword the system format accepts, plus a worked example.

    Read this before writing your first system: it lists the support names
    (festlager, loslager, feste_einspannung, gleitlager), the hinge names
    (vollgelenk, schubgelenk, normalkraftgelenk), the load types, the default
    member properties, and the sign conventions.
    """
    return _json(await _request("GET", "/schema"))


@mcp.tool()
async def statik_list_systems() -> list[dict]:
    """Stored systems: name, slug, when they were saved, and their URL.

    Includes both systems an agent built and ones a person drew in the editor
    -- it is one shared workspace.
    """
    return _json(await _request("GET", "/systems"))


@mcp.tool()
async def statik_examples() -> list[dict]:
    """Stored systems in the compact format, as worked examples.

    Useful before writing an unfamiliar system: seeing how a two-span beam or a
    frame with a hinge is actually written down beats deriving it from the
    schema.
    """
    return _json(await _request("GET", "/templates"))


# --- building ---------------------------------------------------------

@mcp.tool()
async def statik_build_system(name: str, system: dict) -> dict:
    """Store a structural system and get back a slug and a URL a person can open.

    `system` is the compact format:

        {
          "nodes": [
            {"id": "A", "x": 0, "y": 0, "support": "festlager"},
            {"id": "B", "x": 6, "y": 0, "support": "loslager"},
            {"id": "C", "x": 6, "y": 4}
          ],
          "members": [
            {"start": "A", "end": "B"},
            {"start": "B", "end": "C", "hinge_start": "vollgelenk"}
          ],
          "loads": [
            {"on": "A-B", "type": "distributed", "q": 10},
            {"on": "C", "type": "point", "value": 25, "angle": -90}
          ]
        }

    Node ids are names you choose and keep -- no UUIDs. A member is referred to
    as "<start>-<end>", and `on` takes either a node id or a member id.

    Supports: festlager (pinned), loslager (roller), feste_einspannung
    (clamped), gleitlager (slider). A node may also carry `rotation` in
    degrees CCW, which turns the support's own frame -- fixN then acts along
    the rotated local x, fixV along local y -- and draws the symbol turned to
    match. Use it for a support on an inclined surface, and `"rotation": 90`
    for a member clamped into a vertical wall, which is how a cantilever is
    normally drawn. Hinges per member end: `hinge_start` /
    `hinge_end` with vollgelenk (moment release), schubgelenk (shear),
    normalkraftgelenk (axial). Omit for a rigid connection -- a biegesteife
    Ecke is the absence of a release, not a symbol.

    Loads:
      point       `value` kN at `angle` degrees (default -90, i.e. downward).
                  On a member, `at` gives the position as a fraction 0..1.
      moment      `value` kNm on a node, positive counter-clockwise.
      distributed `q` kN/m along a member. It has NO angle: positive q acts
                  perpendicular to the member along its local -y, which is
                  downward for a member drawn left to right. Use `q_start` and
                  `q_end` for a trapezoid, `from`/`to` for a partial span.
      dynamic_force / dynamic_moment on a node, with a `signal`:
                  {"type": "harmonic", "amplitude": 10, "frequency": 2}.

    Member stiffness (E, A, I, m) may be given per member and otherwise takes
    the editor's defaults, which is what you want unless the drawing states a
    section.

    Saving under an existing name overwrites that system.

    Returns the slug, the URL, element counts, and any warnings -- read those:
    they flag two nodes sitting on top of each other, a node no member reaches,
    and a system without supports.

    Call statik_render next and compare the picture with your source.
    """
    payload = {"name": name, "system": system}
    return _json(await _request("POST", "/systems", json=payload))


@mcp.tool()
async def statik_get_system(slug: str) -> dict:
    """Read a stored system back in the compact format."""
    return _json(await _request("GET", f"/systems/{slug}"))


@mcp.tool()
async def statik_update_system(slug: str, patch: dict) -> dict:
    """Correct a stored system.

    Whichever of "nodes", "members" or "loads" you pass replaces that whole
    list; anything you leave out stays as it is. So to move one node, send the
    complete "nodes" list with that one changed.

    Returns the updated system and its warnings. Render it again afterwards.
    """
    return _json(await _request("PATCH", f"/systems/{slug}", json={"system": patch}))


# --- looking ----------------------------------------------------------

@mcp.tool(structured_output=False)
async def statik_render(slug: str, width: int = 900, height: int = 660) -> list:
    """Draw a stored system and return the picture. LOOK AT IT.

    The drawing uses the same symbol language as a textbook -- hatched ground
    for a clamped support, a triangle for a pinned one, a circle for a full
    hinge, arrows for loads -- so it can be compared directly against the sheet
    you read. Node names, load magnitudes and a scale bar are drawn in.

    Check, in this order: are all the joints there and in the right places; is
    each support the right kind; is every hinge on the right member end; do the
    loads point the way they do in the original, and are the magnitudes right.

    Anything that differs is your reading of the drawing, not a rendering
    quirk. Fix it with statik_update_system and render again.
    """
    response = await _request(
        "GET", f"/systems/{slug}/render",
        params={"width": width, "height": height},
    )
    if response.status_code >= 400:
        _json(response)  # raises with the API's message

    return [
        f"Rendering of '{slug}'. Compare it against your source drawing: "
        f"joint positions, support types, hinge placement, load directions "
        f"and magnitudes.",
        Image(data=response.content, format="png"),
    ]


# --- solving ----------------------------------------------------------

@mcp.tool()
async def statik_validate(slug: str) -> dict:
    """Check whether a system can be solved, before trying to solve it.

    Returns the kinematic degree of freedom. dof = 0 means the static solve
    will run. dof > 0 means the system is a mechanism: the stiffness matrix is
    singular and no static answer exists. Add supports or members, or remove a
    release, and check again.

    Also repeats the geometry warnings, which catch the mistakes that come from
    misreading a drawing rather than from the mechanics.
    """
    return _json(await _request("GET", f"/systems/{slug}/validate"))


@mcp.tool()
async def statik_analyze(
    slug: str,
    kind: Literal["solution", "simplify", "dynamics"] = "solution",
    full: bool = False,
) -> dict:
    """Solve a system. Run statik_validate first.

    kind:
      solution   Static analysis. Returns the support reactions and, per
                 member, the min/max envelope of normal force N, shear V and
                 bending moment M, plus the largest nodal displacement.
      simplify   The equivalent system after statically determinate cantilever
                 branches have been pruned and their loads transferred.
      dynamics   Time-history response over 5 s at a 20 ms step, for systems
                 carrying dynamic loads.

    full=True returns the raw solver output instead: every sampled station
    along every member. That is thousands of numbers -- ask for it only when
    you need a diagram at a specific point, not to read off a maximum.

    Sign conventions follow the model: reactions are [Rx kN, Ry kN, Mz kNm] in
    global axes.
    """
    return _json(await _request(
        "GET", f"/systems/{slug}/analyze/{kind}",
        params={"full": "1"} if full else None,
    ))


# --- resources --------------------------------------------------------

@mcp.resource("statik://conventions", mime_type="application/json",
              description="Support and hinge vocabulary, sign conventions, units.")
async def conventions_resource() -> Any:
    return _json(await _request("GET", "/schema"))


@mcp.resource("statik://examples", mime_type="application/json",
              description="Stored systems in the compact format, as worked examples.")
async def examples_resource() -> Any:
    return _json(await _request("GET", "/templates"))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
