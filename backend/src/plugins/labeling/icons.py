"""Small preview images of every class, rendered from the real symbols.

The labelling UI needs to show what each class looks like. Drawing those icons
by hand in the frontend would mean a second, drifting definition of every
symbol - exactly the failure the generator already fixed once by making the
renderer and the label writer share one placement list. So the icons come from
StanliSymbol itself: what the rail shows is literally what the generator draws.
"""

from __future__ import annotations

import base64
import io
from functools import lru_cache
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw

from src.plugins.generator.image.stanli_symbols import (
    DETECTABLE_HINGES,
    DETECTABLE_LOADS,
    DETECTABLE_SUPPORTS,
    HingeType,
    LoadType,
    StanliHinge,
    StanliLoad,
    StanliSupport,
    SupportType,
)

#: Rendered large and downscaled, because these glyphs are mostly thin strokes
#: and hatching that alias badly if drawn straight at icon size.
CANVAS = 260
SUPERSAMPLE = 3
#: Icons keep their natural proportions and are fitted inside this box rather
#: than padded into a square. Most of these symbols are about 3:1 - a Festlager
#: is 80px of hatching under a 30px triangle - and squaring them off left the
#: drawing occupying a third of the tile and unreadable.
ICON_W = 58
ICON_H = 34
PAD = 4

MEMBER_INK = (150, 158, 170)
MEMBER_WIDTH = 3


def _build(name: str):
    """(symbol, rotation, length, member_span) for one class name, or None."""
    for st in DETECTABLE_SUPPORTS:
        if st.name == name:
            # No member stub: a support already draws its own base line and
            # hatching, and anything wider shrinks the triangle that identifies it.
            return StanliSupport(st), 0.0, 0.0, 0.0
    for ht in DETECTABLE_HINGES:
        if ht.name == name:
            # A release is a property of a member end, and Schubgelenk /
            # Normalkraftgelenk are unreadable without the member they cut.
            # Kept short so the glyph, not the line, sets the icon's size. A
            # Vollgelenk is a 12px circle; on a long member it downscales to a dot.
            return StanliHinge(ht), 0.0, 0.0, 30.0
    for lt in DETECTABLE_LOADS:
        if lt.name == name:
            # Spans and arrow lengths well under what the generator draws: these
            # are fitted into a 58x34 box, and anything long enough to be
            # realistic ends up a flat smear once scaled down.
            if lt == LoadType.STRECKENLAST:
                return StanliLoad(lt), 0.0, 62.0, 62.0
            if lt == LoadType.EINZELLAST:
                # The head is a fixed 10px of whatever length is asked for, so a
                # realistic 40px arrow scales down to a bare line with an
                # invisible tip. 18px makes the head most of the glyph.
                return StanliLoad(lt), 270.0, 18.0, 0.0
            return StanliLoad(lt), 0.0, 0.0, 0.0  # moments stand alone
    return None


def _render_one(name: str) -> Optional[str]:
    spec = _build(name)
    if spec is None:
        return None
    symbol, rotation, length, member = spec

    size = CANVAS * SUPERSAMPLE
    scale = float(SUPERSAMPLE)
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    centre = (size / 2.0, size / 2.0)

    symbol.line_width = max(1, int(round(symbol.line_width * scale)))

    ink_boxes = []
    if member > 0:
        half = member * scale / 2.0
        a = (centre[0] - half, centre[1])
        b = (centre[0] + half, centre[1])
        d.line([a, b], fill=MEMBER_INK, width=int(MEMBER_WIDTH * scale))
        ink_boxes.append((a[0], a[1] - MEMBER_WIDTH * scale,
                          b[0], b[1] + MEMBER_WIDTH * scale))

    if isinstance(symbol, StanliLoad):
        symbol.draw(d, centre, rotation, length * scale)
        box = symbol.get_bbox(centre, rotation, length * scale)
    else:
        symbol.draw(d, centre, rotation)
        box = symbol.get_bbox(centre, rotation)
    if box is not None:
        ink_boxes.append(box)
    if not ink_boxes:
        return None

    pad = PAD * scale
    x0 = max(0.0, min(b[0] for b in ink_boxes) - pad)
    y0 = max(0.0, min(b[1] for b in ink_boxes) - pad)
    x1 = min(float(size), max(b[2] for b in ink_boxes) + pad)
    y1 = min(float(size), max(b[3] for b in ink_boxes) + pad)
    if x1 <= x0 or y1 <= y0:
        return None

    crop = img.crop((int(x0), int(y0), int(x1), int(y1)))
    # Down in one step from the supersampled render, so the thin hatching keeps
    # its grey instead of dropping out.
    crop.thumbnail((ICON_W, ICON_H), Image.LANCZOS)

    buf = io.BytesIO()
    crop.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


@lru_cache(maxsize=1)
def class_icons() -> Dict[str, str]:
    """One data-URI PNG per detectable class. Cached; the symbols never change."""
    from src.plugins.generator.image.stanli_symbols import detectable_class_names

    out: Dict[str, str] = {}
    for name in detectable_class_names():
        try:
            uri = _render_one(name)
        except Exception:
            uri = None
        if uri:
            out[name] = uri
    return out
