import math
from PIL import Image, ImageDraw
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# -------------------------------------------------
# enums
# -------------------------------------------------

class BeamType(Enum):
    BIEGUNG_MIT_FASER = 1
    FACHWERK = 2
    VERSTECKT = 3
    BIEGUNG_OHNE_FASER = 4

class SupportType(Enum):
    FREIES_ENDE = 1
    FESTLAGER = 2
    LOSLAGER = 3
    FESTE_EINSPANNUNG = 4
    GLEITLAGER = 5
    FEDER = 6
    TORSIONSFEDER = 7

class HingeType(Enum):
    VOLLGELENK = 1
    HALBGELENK = 2
    SCHUBGELENK = 3
    NORMALKRAFTGELENK = 4
    BIEGESTEIFE_ECKE = 5

class LoadType(Enum):
    EINZELLAST = 1
    MOMENT_UHRZEIGER = 2
    MOMENT_GEGEN_UHRZEIGER = 3
    STRECKENLAST = 4

# -------------------------------------------------
# detection vocabulary
# -------------------------------------------------
# Only variants that the generator actually draws AND that are visually
# distinguishable from every other variant may become YOLO classes. A class with
# zero instances, or one that renders to the same pixels as another class, is
# worse than useless: it burns model capacity and injects gradient noise into
# the classes that do matter.
#
# Deliberately excluded:
#   SupportType.FEDER / TORSIONSFEDER  - no draw() branch exists yet
#   HingeType.HALBGELENK               - no reference glyph, no frontend counterpart
#   HingeType.BIEGESTEIFE_ECKE         - NOT AN OBJECT. A rigid corner is the
#       absence of a release (see frontend HingeInteractionHandler: fx/fy/mz all
#       false). It is derived after reconstruction - any joint of >=2 members
#       carrying no release symbol is biegesteif - never detected. Asking a
#       detector to find it means asking it to detect nothing at all.

DETECTABLE_SUPPORTS: Tuple[SupportType, ...] = (
    SupportType.FESTLAGER,
    SupportType.LOSLAGER,
    SupportType.FESTE_EINSPANNUNG,
    SupportType.GLEITLAGER,
)

DETECTABLE_LOADS: Tuple[LoadType, ...] = (
    LoadType.EINZELLAST,
    LoadType.MOMENT_UHRZEIGER,
    LoadType.MOMENT_GEGEN_UHRZEIGER,
    # Spans a member rather than sitting on a node, and is the reason the label
    # format is oriented boxes: axis-aligned, a Streckenlast on a 45-degree
    # member fills a fifth of its own box and swallows whatever else is nearby.
    LoadType.STRECKENLAST,
)

DETECTABLE_HINGES: Tuple[HingeType, ...] = (
    HingeType.VOLLGELENK,
    HingeType.SCHUBGELENK,
    HingeType.NORMALKRAFTGELENK,
)

def detectable_class_names() -> List[str]:
    """Canonical, ordered YOLO class-name list."""
    return (
        [e.name for e in DETECTABLE_SUPPORTS]
        + [e.name for e in DETECTABLE_LOADS]
        + [e.name for e in DETECTABLE_HINGES]
    )

# -------------------------------------------------
# constants from stanli.sty (2D part)
# -------------------------------------------------

PX_PER_MM = 4.0 

def mm(x: float) -> float: return x * PX_PER_MM

# line widths 
LINE_HUGE = 4
LINE_BIG = 3
LINE_NORMAL = 2
LINE_SMALL = 1

# beam params
BAR_GAP_MM = 1.5
BAR_ANGLE_DEG = 45

# support params
supportGap = 1.0
supportBasicLength = 12.0
supportBasicHeight = 3.5
supportLength = 8.0
supportHeight = 5.0
supportHatchingLength = 20.0
supportHatchingHeight = 5.0

# FEDER params
FEDERLength = 10.0
FEDERPreLength_pt = 7.0
FEDERPostLength_pt = 3.0
FEDERAmplitude = 2.5
FEDERSegmentLength_pt = 5.0

PT_TO_MM = 0.3514598
FEDERPreLength = FEDERPreLength_pt * PT_TO_MM
FEDERPostLength = FEDERPostLength_pt * PT_TO_MM
FEDERSegmentLength = FEDERSegmentLength_pt * PT_TO_MM

# hinge params (mm). Proportions mirror frontend/app/assets/hinge_symbols.json
# so the editor and the training renderer agree on what each symbol looks like.
hingeRadius = 1.5             # VOLLGELENK pin radius
hingeShearRadius = 1.0        # SCHUBGELENK pin radius
hingeShearPlateOffset = 2.0   # SCHUBGELENK plates, +/- along the member axis
hingeShearPlateHalf = 4.0     # half height of those plates
hingeNormalHalf = 2.5         # NORMALKRAFTGELENK box half-size
hingeMemberOffset = 3.0       # how far a member-end symbol sits from the joint

# load params
forceDistance = 1.5
forceLength = 10.0
momentDistance = 4.0
momentAngleDefault = 270
momentArcStartDeg = 30.0      # PIL arc angles: 0 = 3 o'clock, increasing = clockwise
momentArcEndDeg = 330.0

# Streckenlast (mm). The covering line sits `distLoadHeight` off the member axis
# and the arrows run from it down to just short of the member, so the block reads
# as loading that member and not the one behind it.
distLoadHeight = 8.0
distLoadGap = 1.0             # arrow tips stop this far short of the member
distLoadSpacing = 7.0         # target gap between arrows; count is clamped below
distLoadMinArrows = 3
distLoadMaxArrows = 14

# arrow head geometry, in pixels. Shared by draw() and the bbox, so the label can
# never disagree with the ink.
ARROW_HEAD_LENGTH = 10.0
ARROW_HEAD_HALF_WIDTH = 4.0

# hatching
hatchingAngle = 45
hatchingLength = 1.5 

# -------------------------------------------------
# base
# -------------------------------------------------
#
# Every symbol describes itself once, as a list of primitive ops in absolute,
# already-rotated pixel coordinates:
#
#   ("line",    p1, p2)
#   ("polygon", [pts...])          filled black
#   ("outline", [pts...])          stroked, not filled
#   ("circle",  center, r, fill)   fill is None or a colour
#   ("arc",     center, r, start_deg, end_deg)
#   ("hairline", p1, p2)           always 1px (hatching)
#
# draw() executes those ops; get_bbox() measures them. Because both read the same
# list there is no second implementation of the geometry that can drift out of
# sync - which is exactly how the old point-load box ended up ~12x the size of
# the arrow it was supposed to enclose.

_ARC_SAMPLES_PER_DEG = 0.2  # ~1 sample every 5 degrees

@dataclass
class StanliSymbol:
    line_width: int = LINE_NORMAL
    #: Stroke colour and the colour that "white" knock-out fills resolve to.
    #: Set together by apply_style() so a hinge circle punched through a member
    #: matches the paper it is drawn on, not a hard-coded white.
    ink: Tuple[int, int, int] = (0, 0, 0)
    paper: Tuple[int, int, int] = (255, 255, 255)

    def apply_style(self, style) -> "StanliSymbol":
        """Re-ink this symbol. Idempotent - the base stroke width is remembered.

        Stroke width feeds get_bbox()'s padding, so styling must happen before
        the box is measured; that is why placement.py styles symbols at
        construction and both the renderer and the label writer go through it.
        """
        if style is None:
            return self
        base = getattr(self, "_base_line_width", None)
        if base is None:
            base = self.line_width
            self._base_line_width = base
        self.line_width = max(1, int(round(base * getattr(style, "line_scale", 1.0))))
        self.ink = tuple(style.ink)
        self.paper = tuple(style.paper)
        return self

    def _rot(self, p, origin, angle_deg):
        a = math.radians(angle_deg)
        ox, oy = origin
        x, y = p
        dx = x - ox
        dy = y - oy
        # Screen space has y pointing down, so this is a visually CCW rotation.
        qx = ox + dx * math.cos(a) + dy * math.sin(a)
        qy = oy - dx * math.sin(a) + dy * math.cos(a)
        return qx, qy

    def _rot_many(self, pts, origin, ang):
        return [self._rot(p, origin, ang) for p in pts]

    # --- op plumbing -----------------------------------------------------

    def _ops(self, *args, **kwargs) -> List[tuple]:
        raise NotImplementedError

    def _execute(self, d: "ImageDraw.Draw", ops: List[tuple]):
        for op in ops:
            kind = op[0]
            if kind == "line":
                d.line([op[1], op[2]], fill=self.ink, width=self.line_width)
            elif kind == "hairline":
                d.line([op[1], op[2]], fill=self.ink, width=max(1, self.line_width // 2))
            elif kind == "polygon":
                d.polygon(op[1], fill=self.ink)
            elif kind == "outline":
                d.polygon(op[1], outline=self.ink, fill=None, width=self.line_width)
            elif kind == "filled_outline":
                d.polygon(op[1], outline=self.ink, fill=self._fill(op[2]),
                          width=self.line_width)
            elif kind == "circle":
                c, r, fill = op[1], op[2], op[3]
                d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r),
                          fill=self._fill(fill), outline=self.ink, width=self.line_width)
            elif kind == "arc":
                c, r, s, e = op[1], op[2], op[3], op[4]
                d.arc((c[0] - r, c[1] - r, c[0] + r, c[1] + r),
                      start=s, end=e, fill=self.ink, width=self.line_width)

    def _fill(self, fill):
        """A "white" knock-out fill means "the paper", whatever colour that is."""
        return self.paper if fill == "white" else fill

    @staticmethod
    def _arc_points(center, r, start_deg, end_deg) -> List[Tuple[float, float]]:
        cx, cy = center
        span = (end_deg - start_deg) % 360.0
        if span == 0:
            span = 360.0
        n = max(2, int(span * _ARC_SAMPLES_PER_DEG) + 1)
        pts = []
        for i in range(n + 1):
            a = math.radians(start_deg + span * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return pts

    def _ink_points(self, ops: List[tuple]) -> List[Tuple[float, float]]:
        pts: List[Tuple[float, float]] = []
        for op in ops:
            kind = op[0]
            if kind in ("line", "hairline"):
                pts.append(op[1])
                pts.append(op[2])
            elif kind in ("polygon", "outline", "filled_outline"):
                pts.extend(op[1])
            elif kind == "circle":
                c, r = op[1], op[2]
                pts.extend([(c[0] - r, c[1]), (c[0] + r, c[1]),
                            (c[0], c[1] - r), (c[0], c[1] + r)])
            elif kind == "arc":
                pts.extend(self._arc_points(op[1], op[2], op[3], op[4]))
        return pts

    def _bbox_from_ops(self, ops: List[tuple]) -> Optional[Tuple[float, float, float, float]]:
        pts = self._ink_points(ops)
        if not pts:
            return None
        pad = self.line_width / 2.0 + 1.0
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

    def _obb_from_ops(self, ops: List[tuple], origin, rotation_deg: float
                      ) -> Optional[List[Tuple[float, float]]]:
        """Oriented box: the four corners, in draw order, or None for no ink.

        `_ops` emits absolute, already-rotated points, so measuring them
        directly gives an axis-aligned box that grows as the symbol turns. The
        box is instead measured in the symbol's OWN frame - un-rotate the ink,
        take the extent there, rotate the four corners back - which is tight at
        every angle.

        The difference is small for the near-square symbols and decisive for
        the elongated one: a Streckenlast on a 45-degree member fills about a
        fifth of its axis-aligned box, and the rest of that box is usually
        somebody else's Festlager.
        """
        pts = self._ink_points(ops)
        if not pts:
            return None
        local = [self._rot(p, origin, -rotation_deg) for p in pts]
        pad = self.line_width / 2.0 + 1.0
        xs = [p[0] for p in local]
        ys = [p[1] for p in local]
        x0, y0 = min(xs) - pad, min(ys) - pad
        x1, y1 = max(xs) + pad, max(ys) + pad
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return [self._rot(c, origin, rotation_deg) for c in corners]

    # --- shared geometry helpers ----------------------------------------

    def _arrow_ops(self, start, end) -> List[tuple]:
        """A straight arrow from `start` to a head whose tip sits on `end`."""
        vx, vy = end[0] - start[0], end[1] - start[1]
        L = math.hypot(vx, vy)
        if L == 0:
            return []
        ux, uy = vx / L, vy / L
        return self._head_ops(end, (ux, uy)) + [("line", start, end)]

    def _head_ops(self, tip, direction) -> List[tuple]:
        """Filled triangular head with its tip at `tip`, pointing along `direction`."""
        ux, uy = direction
        bx = tip[0] - ux * ARROW_HEAD_LENGTH
        by = tip[1] - uy * ARROW_HEAD_LENGTH
        px, py = -uy, ux
        c1 = (bx + px * ARROW_HEAD_HALF_WIDTH, by + py * ARROW_HEAD_HALF_WIDTH)
        c2 = (bx - px * ARROW_HEAD_HALF_WIDTH, by - py * ARROW_HEAD_HALF_WIDTH)
        return [("polygon", [tip, c1, c2])]

    def _hatch_ops(self, p1, p2) -> List[tuple]:
        """Hatching marks hanging off the ground line p1->p2."""
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        L = math.hypot(dx, dy)
        if L == 0:
            return []
        ux, uy = dx / L, dy / L
        nx, ny = -uy, ux  # normal, "below" the line

        h_len = mm(supportHatchingHeight)
        step = mm(hatchingLength)
        ops = []
        for i in range(int(L / step) + 1):
            t = i * step
            sx = p1[0] + ux * t
            sy = p1[1] + uy * t
            ex = sx + nx * h_len - ux * (h_len * 0.5)
            ey = sy + ny * h_len - uy * (h_len * 0.5)
            ops.append(("hairline", (sx, sy), (ex, ey)))
        return ops

# -------------------------------------------------
# beams
# -------------------------------------------------

class StanliBeam(StanliSymbol):
    def __init__(self, beam_type: BeamType):
        super().__init__()
        self.beam_type = beam_type
        if beam_type in (BeamType.BIEGUNG_MIT_FASER, BeamType.BIEGUNG_OHNE_FASER):
            self.line_width = LINE_HUGE 
        elif beam_type == BeamType.FACHWERK:
            self.line_width = LINE_NORMAL 
        elif beam_type == BeamType.VERSTECKT:
            self.line_width = LINE_SMALL 
        else:
            self.line_width = LINE_BIG 

    def draw(self, d: ImageDraw.Draw, a: Tuple[float,float], b: Tuple[float,float], 
             rounded_start=False, rounded_end=False):
        if self.beam_type == BeamType.VERSTECKT:
            self._dashed(d, a, b, self.line_width)
        else:
            d.line([a, b], fill=self.ink, width=self.line_width)
        
        if self.beam_type == BeamType.BIEGUNG_MIT_FASER:
            self._fiber(d, a, b)
            
        if rounded_start and self.line_width >= LINE_NORMAL:
            r = max(self.line_width / 2, LINE_SMALL)
            d.ellipse((a[0]-r,a[1]-r,a[0]+r,a[1]+r), fill=self.ink)
        if rounded_end and self.line_width >= LINE_NORMAL:
            r = max(self.line_width / 2, LINE_SMALL)
            d.ellipse((b[0]-r,b[1]-r,b[0]+r,b[1]+r), fill=self.ink)

    def _dashed(self, d, a, b, w, dash=mm(2), gap=mm(1.2)):
        L = math.hypot(b[0]-a[0], b[1]-a[1])
        if L == 0: return
        ux, uy = (b[0]-a[0])/L, (b[1]-a[1])/L
        s = 0
        while s < L:
            e = min(s + dash, L)
            d.line((a[0]+ux*s,a[1]+uy*s,a[0]+ux*e,a[1]+uy*e), fill=self.ink, width=w)
            s += dash + gap

    def _fiber(self, d, a, b):
        gap = mm(BAR_GAP_MM)
        ang = math.radians(BAR_ANGLE_DEG)
        vx, vy = b[0]-a[0], b[1]-a[1]
        theta = math.atan2(vy, vx)
        p1 = (a[0] + gap*math.cos(theta - ang), a[1] + gap*math.sin(theta - ang))
        p2 = (b[0] + gap*math.cos(theta + math.pi + ang), 
              b[1] + gap*math.sin(theta + math.pi + ang))
        self._dashed(d, p1, p2, LINE_SMALL)

    def get_bbox(self, a: Tuple[float,float], b: Tuple[float,float]) -> Tuple[float, float, float, float]:
        """Simple bounding box for line segment + padding."""
        xs = [a[0], b[0]]
        ys = [a[1], b[1]]
        
        pad = self.line_width / 2.0 + 1.0
        if self.beam_type == BeamType.BIEGUNG_MIT_FASER:
            pad += mm(BAR_GAP_MM) # Account for fiber dashed line offset

        return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

# -------------------------------------------------
# supports
# -------------------------------------------------

class StanliSupport(StanliSymbol):
    def __init__(self, st: SupportType):
        super().__init__(LINE_NORMAL)
        self.st = st

    def _ops(self, pos: Tuple[float, float], rotation: float = 0) -> List[tuple]:
        def p(dx, dy):
            return self._rot((pos[0] + mm(dx), pos[1] + mm(dy)), pos, rotation)

        ops: List[tuple] = []

        if self.st in (SupportType.FESTLAGER, SupportType.LOSLAGER):
            ops.append(("outline", [
                p(0, 0),
                p(-supportLength / 2, supportHeight),
                p(supportLength / 2, supportHeight),
            ]))
            # Festlager sits directly on the ground; Loslager rolls, so its ground
            # line is offset by supportGap. That gap is the only discriminator
            # between the two, which is why both keep their hatching.
            y_line = supportHeight if self.st == SupportType.FESTLAGER else supportHeight + supportGap
            a = p(-supportHatchingLength / 2, y_line)
            b = p(supportHatchingLength / 2, y_line)
            ops.append(("line", a, b))
            ops.extend(self._hatch_ops(a, b))

        elif self.st == SupportType.FESTE_EINSPANNUNG:
            a = p(-supportHatchingLength / 2, 0)
            b = p(supportHatchingLength / 2, 0)
            ops.append(("line", a, b))
            ops.extend(self._hatch_ops(a, b))

        elif self.st == SupportType.GLEITLAGER:
            r = mm(1.5)
            ops.append(("circle", p(-supportLength / 2, r / PX_PER_MM), r, None))
            ops.append(("circle", p(supportLength / 2, r / PX_PER_MM), r, None))
            y_line = (r * 2) / PX_PER_MM + supportGap
            a = p(-supportHatchingLength / 2, y_line)
            b = p(supportHatchingLength / 2, y_line)
            ops.append(("line", a, b))
            ops.extend(self._hatch_ops(a, b))

        # FREIES_ENDE draws nothing. FEDER / TORSIONSFEDER are not implemented
        # yet and are excluded from DETECTABLE_SUPPORTS for exactly that reason.
        return ops

    def draw(self, d: ImageDraw.Draw, pos: Tuple[float, float], rotation: float = 0):
        self._execute(d, self._ops(pos, rotation))

    def get_bbox(self, pos: Tuple[float, float], rotation: float = 0):
        """Tight box around the ink, or None when this support draws nothing."""
        return self._bbox_from_ops(self._ops(pos, rotation))

    def get_corners(self, pos: Tuple[float, float], rotation: float = 0):
        """Oriented box, four corners. See StanliSymbol._obb_from_ops."""
        return self._obb_from_ops(self._ops(pos, rotation), pos, rotation)

# -------------------------------------------------
# hinges
# -------------------------------------------------

class StanliHinge(StanliSymbol):
    """Release symbols.

    `rotation` is the direction of the member the release belongs to (degrees,
    visually CCW). It matters: a Schubgelenk's plates stand perpendicular to the
    member and a Normalkraftgelenk's split line runs across it. Drawing every
    type as the same circle - as this class used to - collapses several classes
    into one appearance and makes them unlearnable.
    """

    def __init__(self, ht: HingeType):
        super().__init__()
        self.ht = ht

    def _ops(self, pos: Tuple[float, float], rotation: float = 0) -> List[tuple]:
        def p(dx, dy):
            return self._rot((pos[0] + mm(dx), pos[1] + mm(dy)), pos, rotation)

        if self.ht == HingeType.VOLLGELENK:
            return [("circle", pos, mm(hingeRadius), "white")]

        if self.ht == HingeType.SCHUBGELENK:
            o, h = hingeShearPlateOffset, hingeShearPlateHalf
            return [
                ("line", p(-o, -h), p(-o, h)),
                ("line", p(o, -h), p(o, h)),
                ("circle", pos, mm(hingeShearRadius), "white"),
            ]

        if self.ht == HingeType.NORMALKRAFTGELENK:
            s = hingeNormalHalf
            return [
                ("filled_outline", [p(-s, -s), p(s, -s), p(s, s), p(-s, s)], "white"),
                ("line", p(0, -s), p(0, s)),
            ]

        # BIEGESTEIFE_ECKE renders nothing by design - a rigid corner is the
        # default state of a joint, not a symbol. HALBGELENK has no reference
        # glyph. Both are excluded from DETECTABLE_HINGES.
        return []

    def draw(self, d: ImageDraw.Draw, pos: Tuple[float, float],
             rotation: float = 0, start_point=None, end_point=None):
        self._execute(d, self._ops(pos, rotation))

    def get_bbox(self, pos: Tuple[float, float], rotation: float = 0):
        return self._bbox_from_ops(self._ops(pos, rotation))

    def get_corners(self, pos: Tuple[float, float], rotation: float = 0):
        """Oriented box, four corners. See StanliSymbol._obb_from_ops."""
        return self._obb_from_ops(self._ops(pos, rotation), pos, rotation)

# -------------------------------------------------
# loads
# -------------------------------------------------

class StanliLoad(StanliSymbol):
    def __init__(self, lt: LoadType):
        super().__init__()
        self.lt = lt

    def _ops(self, pos: Tuple[float, float], rotation: float = 0,
             length: float = 40.0, distance: float = 0.0) -> List[tuple]:
        dist_px = mm(forceDistance) if distance == 0 else distance

        if self.lt == LoadType.EINZELLAST:
            # Force acts along `rotation`: the tip stops `dist_px` short of the
            # node, the tail sits `length` further back. rotation=270 is the
            # usual downward gravity load.
            tail = self._rot((pos[0] - (length + dist_px), pos[1]), pos, rotation)
            tip = self._rot((pos[0] - dist_px, pos[1]), pos, rotation)
            return self._arrow_ops(tail, tip)

        if self.lt in (LoadType.MOMENT_UHRZEIGER, LoadType.MOMENT_GEGEN_UHRZEIGER):
            r = mm(momentDistance) + 10
            # A visually CCW rotation of the symbol is a decreasing PIL arc angle.
            start = momentArcStartDeg - rotation
            end = momentArcEndDeg - rotation

            if self.lt == LoadType.MOMENT_UHRZEIGER:
                # Sweep runs clockwise, so the head caps the far end of the sweep.
                theta = math.radians(end)
                direction = (-math.sin(theta), math.cos(theta))
            else:
                theta = math.radians(start)
                direction = (math.sin(theta), -math.cos(theta))

            tip = (pos[0] + r * math.cos(theta), pos[1] + r * math.sin(theta))
            # Without a head the two moment directions are the same pixels, and
            # no model can separate them.
            return [("arc", pos, r, start, end)] + self._head_ops(tip, direction)

        if self.lt == LoadType.STRECKENLAST:
            # Member-spanning, unlike every other symbol here. `pos` is the
            # midpoint of the loaded span, `rotation` the member's direction and
            # `length` the span in pixels. Laid out along local +x and then
            # turned, so the block always sits square on its member.
            span = max(float(length), mm(8.0))
            top = mm(distLoadHeight)
            gap = mm(distLoadGap)
            x0 = pos[0] - span / 2.0
            y_top = pos[1] - top
            y_tip = pos[1] - gap

            def R(p):
                return self._rot(p, pos, rotation)

            ops = [("line", R((x0, y_top)), R((x0 + span, y_top)))]
            n = int(span / mm(distLoadSpacing)) + 1
            n = max(distLoadMinArrows, min(distLoadMaxArrows, n))
            for i in range(n):
                x = x0 + span * i / (n - 1)
                ops.extend(self._arrow_ops(R((x, y_top)), R((x, y_tip))))
            return ops

        return []

    def draw(self, d: ImageDraw.Draw, pos: Tuple[float, float], rotation: float = 0,
             length: float = 40.0, distance: float = 0.0):
        self._execute(d, self._ops(pos, rotation, length, distance))

    def get_bbox(self, pos: Tuple[float, float], rotation: float = 0,
                 length: float = 40.0, distance: float = 0.0):
        return self._bbox_from_ops(self._ops(pos, rotation, length, distance))

    def get_corners(self, pos: Tuple[float, float], rotation: float = 0,
                    length: float = 40.0, distance: float = 0.0):
        """Oriented box, four corners. See StanliSymbol._obb_from_ops."""
        return self._obb_from_ops(
            self._ops(pos, rotation, length, distance), pos, rotation)
