"""Who is asking, as far as the gateway is concerned.

Statik itself has no accounts. Authentication happens one layer up, in Caddy,
which sends selected paths through Authelia before they ever reach this
process (gateway/Caddyfile, the `geschuetzt_pfad` snippet). On the way through,
Authelia adds Remote-User / Remote-Groups / Remote-Name / Remote-Email.

So this endpoint does not decide anything -- it reports. Its usefulness is that
it is registered on a *protected* path: whether the browser can reach it at all
is the answer.

    reached, with Remote-User      signed in
    reached, without Remote-User   no gateway in front (local dev, direct
                                   container access) -- nothing is restricted
    not reached (401 / redirect)   a gateway is in front and says no

The frontend uses this only to grey out buttons whose requests the gateway
would reject anyway. It is a courtesy, not a lock: the lock is in the
Caddyfile, and it stays there.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

bp = Blueprint("auth_session", __name__, url_prefix="/api/auth")

#: Set by Authelia via `copy_headers` in gateway/Caddyfile. Changing the names
#: there means changing them here.
_USER = "Remote-User"
_GROUPS = "Remote-Groups"
_NAME = "Remote-Name"
_EMAIL = "Remote-Email"


@bp.get("/whoami")
def whoami():
    user = request.headers.get(_USER) or None
    raw_groups = request.headers.get(_GROUPS) or ""
    groups = [g.strip() for g in raw_groups.split(",") if g.strip()]

    response = jsonify({
        # True only when the request actually carried an identity, which can
        # only have come from the gateway.
        "authenticated": bool(user),
        "user": user,
        "groups": groups,
        "name": request.headers.get(_NAME) or None,
        "email": request.headers.get(_EMAIL) or None,
        # Reaching this at all without an identity means nothing checked the
        # request, so nothing is restricted either.
        "behind_gateway": bool(user),
    })

    # A GET with no validators is fair game for the browser's heuristic cache,
    # and a stale "you may save" would outlive a sign-out. Whether the gateway
    # lets this through is exactly the thing that must not be remembered.
    response.headers["Cache-Control"] = "no-store"
    return response
