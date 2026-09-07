#!/usr/bin/env python3
"""Export the backend's stanli symbol geometry as SVG paths for the frontend.

`frontend/app/assets/support_symbols.json` and `hinge_symbols.json` are what the
editor canvas draws (see features/drawing/SymbolRenderer.ts). They were generated
from the backend symbol definitions once and have drifted since: the backend now
draws each release type differently, while hinge_symbols.json still carries a
plain circle for the Vollgelenk, nothing at all for the Halbgelenk, and an empty
BIEGESTEIFE_ECKE. Running this regenerates them from the one definition that the
training renderer also uses, so the editor and the dataset agree on what a
Schubgelenk looks like.

Coordinates are backend pixels with the node at the origin, matching the
convention already used by support_symbols.json (a Festlager triangle is
"M 0 0 L 16 20 L -16 20 Z" = supportLength/2 and supportHeight in px).

    python convert-stanli.py                # print a diff against the current files
    python convert-stanli.py --write        # merge the changes in

MERGING, NOT OVERWRITING: entries the backend cannot currently draw are kept as
they are. FEDER and TORSIONSFEDER are the live example - the frontend has full
spring paths from an older backend, but StanliSupport has no branch for them any
more, so regenerating blindly would silently delete them from the editor.
"""

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

from src.plugins.generator.image.stanli_symbols import (  # noqa: E402
    HingeType,
    StanliHinge,
    StanliSupport,
    SupportType,
)
from src.plugins.generator.image.style import RenderStyle  # noqa: E402

FRONTEND_ASSETS = ROOT / "frontend" / "app" / "assets"
SUPPORT_JSON = FRONTEND_ASSETS / "support_symbols.json"
HINGE_JSON = FRONTEND_ASSETS / "hinge_symbols.json"

#: Canonical export ink. "white" fills become an explicit white so the frontend
#: knocks the member line out from under a hinge exactly as the renderer does.
EXPORT_STYLE = RenderStyle(ink=(0, 0, 0), paper=(255, 255, 255), line_scale=1.0)


def _fmt(x: float) -> str:
    return f"{x:.2f}"


class SvgPathRecorder:
    """A stand-in for PIL's ImageDraw that records SVG path ops instead of pixels."""

    def __init__(self):
        self.paths = []

    # --- helpers --------------------------------------------------------

    @staticmethod
    def _points(xy):
        """PIL accepts [(x,y), ...] or a flat (x0,y0,x1,y1); normalise both."""
        if not xy:
            return []
        if isinstance(xy[0], (int, float)):
            return [(xy[i], xy[i + 1]) for i in range(0, len(xy) - 1, 2)]
        return list(xy)

    @staticmethod
    def _is_white(color):
        if color is None:
            return False
        if isinstance(color, str):
            return color.lower() == "white"
        return tuple(color[:3]) == (255, 255, 255)

    def _polyline(self, points, close=False):
        d = f"M {_fmt(points[0][0])} {_fmt(points[0][1])}"
        for p in points[1:]:
            d += f" L {_fmt(p[0])} {_fmt(p[1])}"
        return d + " Z" if close else d

    def _emit_fill(self, d, color):
        op = {"d": d, "type": "fill"}
        if self._is_white(color):
            op["color"] = "white"
        self.paths.append(op)

    def _emit_stroke(self, d, width):
        self.paths.append({"d": d, "type": "stroke", "width": width})

    # --- ImageDraw surface ----------------------------------------------

    def line(self, xy, fill=None, width=1, **_):
        points = self._points(xy)
        if len(points) < 2:
            return
        self._emit_stroke(self._polyline(points), width)

    def polygon(self, xy, fill=None, outline=None, width=1, **_):
        points = self._points(xy)
        if len(points) < 2:
            return
        d = self._polyline(points, close=True)
        if fill is not None:
            self._emit_fill(d, fill)
        if outline is not None:
            self._emit_stroke(d, width)

    def ellipse(self, xy, fill=None, outline=None, width=1, **_):
        x0, y0, x1, y1 = xy
        rx, ry = (x1 - x0) / 2.0, (y1 - y0) / 2.0
        cx, cy = x0 + rx, y0 + ry
        d = (f"M {_fmt(cx - rx)} {_fmt(cy)} "
             f"A {_fmt(rx)} {_fmt(ry)} 0 1 0 {_fmt(cx + rx)} {_fmt(cy)} "
             f"A {_fmt(rx)} {_fmt(ry)} 0 1 0 {_fmt(cx - rx)} {_fmt(cy)} Z")
        if fill is not None:
            self._emit_fill(d, fill)
        if outline is not None:
            self._emit_stroke(d, width)

    def arc(self, xy, start=0, end=360, fill=None, width=1, **_):
        """PIL angles: 0 at 3 o'clock, increasing clockwise on screen.

        SVG's sweep flag 1 is also clockwise in a y-down space, so an increasing
        PIL sweep maps straight onto sweep=1.
        """
        x0, y0, x1, y1 = xy
        rx, ry = (x1 - x0) / 2.0, (y1 - y0) / 2.0
        cx, cy = x0 + rx, y0 + ry
        span = (end - start) % 360.0 or 360.0

        def point(a_deg):
            a = math.radians(a_deg)
            return cx + rx * math.cos(a), cy + ry * math.sin(a)

        sx, sy = point(start)
        # A single elliptical arc cannot express a full circle; split at the
        # halfway point, which also keeps the large-arc flag unambiguous.
        mx, my = point(start + span / 2.0)
        ex, ey = point(start + span)
        large_half = 1 if span / 2.0 > 180.0 else 0
        d = (f"M {_fmt(sx)} {_fmt(sy)} "
             f"A {_fmt(rx)} {_fmt(ry)} 0 {large_half} 1 {_fmt(mx)} {_fmt(my)} "
             f"A {_fmt(rx)} {_fmt(ry)} 0 {large_half} 1 {_fmt(ex)} {_fmt(ey)}")
        self._emit_stroke(d, width)

    def rectangle(self, xy, fill=None, outline=None, width=1, **_):
        x0, y0, x1, y1 = xy
        self.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, outline, width)

    def text(self, *args, **kwargs):
        pass  # annotation is never exported


def export(symbol_cls, members) -> dict:
    out = {}
    for member in members:
        recorder = SvgPathRecorder()
        symbol_cls(member).apply_style(EXPORT_STYLE).draw(recorder, (0.0, 0.0))
        out[member.name] = recorder.paths
    return out


def merge_report(name: str, generated: dict, path: Path):
    """Report per-key changes and return the merged library.

    Keys the backend produces nothing for keep whatever the frontend already
    has - that is what protects the spring symbols.
    """
    current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    merged = dict(current)

    print(f"\n=== {name} ({path.relative_to(ROOT)}) ===")
    for key, ops in generated.items():
        old = current.get(key)
        if not ops:
            if old:
                print(f"  KEPT      {key:22s} backend draws nothing; "
                      f"frontend keeps its {len(old)} existing op(s)")
            else:
                print(f"  empty     {key:22s} (draws nothing on either side)")
            continue
        if old is None:
            print(f"  NEW       {key:22s} {len(ops)} op(s)")
        elif old != ops:
            print(f"  CHANGED   {key:22s} {len(old)} -> {len(ops)} op(s)")
        else:
            print(f"  unchanged {key:22s} {len(ops)} op(s)")
        merged[key] = ops

    for key in current:
        if key not in generated:
            print(f"  ORPHAN    {key:22s} only in the frontend; left untouched")
    return merged


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true",
                        help="write the merged libraries back to frontend/app/assets")
    args = parser.parse_args()

    libraries = [
        ("supports", export(StanliSupport, list(SupportType)), SUPPORT_JSON),
        ("hinges", export(StanliHinge, list(HingeType)), HINGE_JSON),
    ]

    for name, generated, path in libraries:
        merged = merge_report(name, generated, path)
        if args.write:
            path.write_text(json.dumps(merged, indent=1) + "\n", encoding="utf-8")
            print(f"  -> wrote {path.relative_to(ROOT)}")

    if not args.write:
        print("\nDry run. Re-run with --write to apply.")


if __name__ == "__main__":
    main()
