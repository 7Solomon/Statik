"""Per-sample appearance: ink, paper, stroke weight, fonts, clutter.

Every image the old generator produced was the same point in appearance space -
pure #000 on pure #FFF, every stroke exactly 2px, no text anywhere. A detector
trained on that has never seen a grey scan, a blue-pen sketch, a photographed
page, or a single character of the annotation that covers every real structural
drawing. Text in particular is the top source of false positives on real images,
and the model had no way to learn to ignore it.

A style is drawn once per sample and stored on the ImageSystem, so the renderer
and the label writer resolve identical geometry from it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional, Tuple

# Tried in order; the first that loads wins. Falls back to PIL's built-in font.
_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/droid/DroidSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


@lru_cache(maxsize=32)
def load_font(size: int):
    from PIL import ImageFont

    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


@dataclass
class RenderStyle:
    """How one sample is inked. Defaults reproduce the plain black-on-white look."""

    ink: Tuple[int, int, int] = (0, 0, 0)
    paper: Tuple[int, int, int] = (255, 255, 255)
    #: Multiplies every symbol and member stroke width.
    line_scale: float = 1.0
    font_size: int = 15

    # Annotation clutter. None of it is ever labelled - it exists so the model
    # learns that text and dimension lines are *not* structural symbols.
    draw_load_labels: bool = True
    draw_node_labels: bool = True
    draw_dimension_line: bool = True
    draw_member_labels: bool = False
    draw_axes: bool = False

    #: Illumination ramp strength, 0 = flat lighting.
    illumination: float = 0.0
    #: JPEG quality for a recompression pass; None skips it.
    jpeg_quality: Optional[int] = None
    blur_radius: float = 0.0
    noise_sigma: float = 0.0


#: Ink colours seen in real material: printer black, faded scan, pencil, biro.
_INKS = (
    (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (34, 34, 34), (60, 60, 66), (90, 90, 96),
    (24, 40, 110), (30, 60, 140),
)

#: Paper: bright print, off-white scan, aged/cream, cool photocopy.
_PAPERS = (
    (255, 255, 255), (255, 255, 255),
    (250, 249, 245), (244, 242, 235), (238, 236, 228),
    (247, 249, 252), (235, 235, 235),
)


def random_style(rng: Optional[random.Random] = None) -> RenderStyle:
    rng = rng or random

    ink = rng.choice(_INKS)
    paper = rng.choice(_PAPERS)
    # Keep ink and paper far enough apart to stay legible after blur and noise.
    if sum(paper) - sum(ink) < 240:
        ink, paper = (0, 0, 0), (255, 255, 255)

    return RenderStyle(
        ink=ink,
        paper=paper,
        # Real drawings run from hairline CAD output to thick marker.
        line_scale=rng.choice([0.5, 0.75, 1.0, 1.0, 1.25, 1.5, 2.0]),
        font_size=rng.randint(11, 20),
        draw_load_labels=rng.random() < 0.85,
        draw_node_labels=rng.random() < 0.55,
        draw_dimension_line=rng.random() < 0.45,
        draw_member_labels=rng.random() < 0.25,
        draw_axes=rng.random() < 0.15,
        illumination=rng.choice([0.0, 0.0, 0.10, 0.18, 0.28]),
        jpeg_quality=rng.choice([None, None, 85, 70, 55, 40]),
        # Mostly crisp: blurring every single image taught the old dataset that
        # sharp line work is out of distribution.
        blur_radius=rng.choice([0.0, 0.0, 0.0, 0.4, 0.7, 1.1, 1.6]),
        noise_sigma=rng.choice([0.0, 0.0, 2.0, 4.0, 7.0, 11.0]),
    )
