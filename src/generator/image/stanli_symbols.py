import math
from PIL import Image, ImageDraw
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# -------------------------------------------------
# enums
# -------------------------------------------------

class BeamType(Enum):
    BENDING_WITH_FIBER = 1
    TRUSS = 2
    HIDDEN = 3
    BENDING_NO_FIBER = 4

class SupportType(Enum):
    FIXED_BEARING = 1
    FLOATING_BEARING = 2
    FIXED_SUPPORT = 3
    SLIDING_SUPPORT = 4
    SPRING = 5
    TORSION_SPRING = 6

class HingeType(Enum):
    FULL_JOINT = 1
    HALF_JOINT = 2
    SHEAR_JOINT = 3
    NORMAL_FORCE_JOINT = 4
    STIFF_CORNER = 5

class LoadType(Enum):
    SINGLE_LOAD = 1
    MOMENT_CLOCKWISE = 2
    MOMENT_COUNTER = 3

# -------------------------------------------------
# constants from stanli.sty (2D part)
# -------------------------------------------------

PX_PER_MM = 4.0  # adjust if you want bigger/smaller
def mm(x: float) -> float: return x * PX_PER_MM

# line widths (approx) keep relative differences
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

# spring params
springLength = 10.0
springPreLength_pt = 7.0
springPostLength_pt = 3.0
springAmplitude = 2.5
springSegmentLength_pt = 5.0
PT_TO_MM = 0.3514598
springPreLength = springPreLength_pt * PT_TO_MM
springPostLength = springPostLength_pt * PT_TO_MM
springSegmentLength = springSegmentLength_pt * PT_TO_MM

# hinge params
hingeRadius = 1.5
hingeAxialLength = 5.0
hingeAxialHeight = 3.0
hingeCornerLength = 3.0

# load params
forceDistance = 1.5
forceLength = 10.0
momentDistance = 4.0
momentAngleDefault = 270

# hatching
hatchingAngle = 45
hatchingLength = 1.5   # segment spacing (mm) approximation

# -------------------------------------------------
# base
# -------------------------------------------------

@dataclass
class StanliSymbol:
    line_width: int = LINE_NORMAL

    def _rot(self, p: Tuple[float, float], origin: Tuple[float, float], angle_deg: float):
        if angle_deg == 0:
            return p
        a = math.radians(angle_deg)
        ox, oy = origin
        x, y = p
        return (
            ox + math.cos(a)*(x-ox) - math.sin(a)*(y-oy),
            oy + math.sin(a)*(x-ox) + math.cos(a)*(y-oy)
        )

    def _rot_many(self, pts, origin, ang):
        return [self._rot(p, origin, ang) for p in pts]

# -------------------------------------------------
# beams
# -------------------------------------------------

class StanliBeam(StanliSymbol):
    def __init__(self, beam_type: BeamType):
        super().__init__()
        self.beam_type = beam_type
        if beam_type in (BeamType.BENDING_WITH_FIBER, BeamType.BENDING_NO_FIBER):
            self.line_width = LINE_HUGE
        elif beam_type == BeamType.TRUSS:
            self.line_width = LINE_BIG
        elif beam_type == BeamType.HIDDEN:
            self.line_width = LINE_NORMAL

    def draw(self, d: ImageDraw.Draw, a: Tuple[float,float], b: Tuple[float,float],
             rounded_start=False, rounded_end=False):
        if self.beam_type == BeamType.HIDDEN:
            self._dashed(d, a, b, self.line_width)
        else:
            d.line([a, b], fill="black", width=self.line_width)
            if self.beam_type == BeamType.BENDING_WITH_FIBER:
                self._fiber(d, a, b)
            if rounded_start:
                r = self.line_width/2
                d.ellipse((a[0]-r,a[1]-r,a[0]+r,a[1]+r), fill="black")
            if rounded_end:
                r = self.line_width/2
                d.ellipse((b[0]-r,b[1]-r,b[0]+r,b[1]+r), fill="black")

    def _dashed(self, d, a, b, w, dash=mm(2), gap=mm(1.2)):
        L = math.hypot(b[0]-a[0], b[1]-a[1])
        if L == 0: return
        ux, uy = (b[0]-a[0])/L, (b[1]-a[1])/L
        s = 0
        while s < L:
            e = min(s + dash, L)
            d.line((a[0]+ux*s,a[1]+uy*s,a[0]+ux*e,a[1]+uy*e), fill="black", width=w)
            s += dash + gap

    def _fiber(self, d, a, b):
        # TikZ: (#2)!\barGap!-\barAngle:(#3)
        gap = mm(BAR_GAP_MM)
        ang = math.radians(BAR_ANGLE_DEG)
        vx, vy = b[0]-a[0], b[1]-a[1]
        theta = math.atan2(vy, vx)
        p1 = (a[0] + gap*math.cos(theta - ang), a[1] + gap*math.sin(theta - ang))
        p2 = (b[0] + gap*math.cos(theta + math.pi + ang),
              b[1] + gap*math.sin(theta + math.pi + ang))
        self._dashed(d, p1, p2, LINE_SMALL)

# -------------------------------------------------
# hatching helper
# -------------------------------------------------

def draw_hatching(d: ImageDraw.Draw, clip_rect: List[Tuple[float,float]],
                  angle_deg: float, spacing_mm: float):
    # axis-aligned rectangle assumed
    xs = [p[0] for p in clip_rect]
    ys = [p[1] for p in clip_rect]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    ang = math.radians(angle_deg)
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    corners = [(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax)]
    projs = [c[0]*nx + c[1]*ny for c in corners]
    pmin, pmax = min(projs), max(projs)
    step = mm(spacing_mm)
    t = pmin - step
    while t <= pmax + step:
        pts = []
        # intersect vertical edges
        for x in (xmin, xmax):
            if abs(ny) > 1e-9:
                y = (t - nx*x)/ny
                if ymin-1 <= y <= ymax+1:
                    pts.append((x, y))
        # horizontal
        for y in (ymin, ymax):
            if abs(nx) > 1e-9:
                x = (t - ny*y)/nx
                if xmin-1 <= x <= xmax+1:
                    pts.append((x, y))
        if len(pts) >= 2:
            if len(pts) > 2:
                pts.sort(key=lambda P: P[0]*dx + P[1]*dy)
            d.line([pts[0], pts[-1]], fill="black", width=LINE_SMALL)
        t += step

# -------------------------------------------------
# supports
# -------------------------------------------------

class StanliSupport(StanliSymbol):
    def __init__(self, st: SupportType):
        super().__init__(LINE_NORMAL)
        self.st = st

    def draw(self, d: ImageDraw.Draw, pos: Tuple[float,float], rotation: float=0):
        dispatch = {
            SupportType.FIXED_BEARING: self._s1,
            SupportType.FLOATING_BEARING: self._s2,
            SupportType.FIXED_SUPPORT: self._s3,
            SupportType.SLIDING_SUPPORT: self._s4,
            SupportType.SPRING: self._s5,
            SupportType.TORSION_SPRING: self._s6,
        }
        dispatch[self.st](d, pos, rotation)

    # pinned triangle
    def _s1(self, d, pos, rot, hatching=True):
        tri = [
            (pos[0], pos[1]),
            (pos[0] + mm(supportLength)/2, pos[1] + mm(supportHeight)),
            (pos[0] - mm(supportLength)/2, pos[1] + mm(supportHeight))
        ]
        tri = self._rot_many(tri, pos, rot)
        d.polygon(tri, outline="black", fill=None, width=self.line_width)

        base_y = pos[1] + mm(supportHeight)
        g_left = self._rot((pos[0] + mm(supportBasicLength)/2, base_y), pos, rot)
        g_right = self._rot((pos[0] - mm(supportBasicLength)/2, base_y), pos, rot)
        d.line([g_left, g_right], fill="black", width=self.line_width)

        # hatch clip rectangle (unrotated then rotate each corner & hatch in its local)
        # For simplicity: approximate by drawing in axis-aligned bbox if rotation=0 else skip detailed rotation hatching.
        if rot == 0:
            clip = [
                (pos[0]-mm(supportBasicLength)/2,
                 base_y),
                (pos[0]+mm(supportBasicLength)/2,
                 base_y+mm(supportBasicHeight)),
                (pos[0]+mm(supportBasicLength)/2,
                 base_y+mm(supportBasicHeight)),
                (pos[0]-mm(supportBasicLength)/2,
                 base_y+mm(supportBasicHeight))
            ]
            if hatching:
                self._draw_ground_hatching(d, clip, 180 - hatchingAngle, hatchingLength)
                


    # roller (triangle + gap line)
    def _s2(self, d, pos, rot):
        # roller (triangle + gap line)
        self._s1(d, pos, rot, hatching=False)
        if rot == 0:
            y_gap = pos[1] + mm(supportHeight) + mm(supportGap)
            d.line([
                (pos[0]+mm(supportBasicLength)/2, y_gap),
                (pos[0]-mm(supportBasicLength)/2, y_gap)
            ], fill="black", width=self.line_width)
            clip = [
                (pos[0]-mm(supportBasicLength)/2, y_gap),
                (pos[0]+mm(supportBasicLength)/2, y_gap),
                (pos[0]+mm(supportBasicLength)/2, y_gap+mm(supportBasicHeight)),
                (pos[0]-mm(supportBasicLength)/2, y_gap+mm(supportBasicHeight))
            ]
            self._draw_ground_hatching(d, clip, 180 - hatchingAngle, hatchingLength)

    def _s3(self, d, pos, rot, hatching=True):
        top_y = pos[1]
        d.line([
            self._rot((pos[0]+mm(supportBasicLength)/2, top_y), pos, rot),
            self._rot((pos[0]-mm(supportBasicLength)/2, top_y), pos, rot)
        ], fill="black", width=self.line_width)
        if rot == 0:
            clip = [
                (pos[0]-mm(supportBasicLength)/2, top_y),
                (pos[0]+mm(supportBasicLength)/2, top_y+mm(supportBasicHeight)),
                (pos[0]+mm(supportBasicLength)/2, top_y+mm(supportBasicHeight)),
                (pos[0]-mm(supportBasicLength)/2, top_y+mm(supportBasicHeight))
            ]
            if hatching:
                self._draw_ground_hatching(d, clip, 180 - hatchingAngle, hatchingLength)

    # sliding support (line + gap line + hatch)
    def _s4(self, d, pos, rot):
        self._s3(d, pos, rot, hatching=False)
        if rot == 0:
            gap_y = pos[1] + mm(supportGap)
            d.line([
                (pos[0]+mm(supportBasicLength)/2, gap_y),
                (pos[0]-mm(supportBasicLength)/2, gap_y)
            ], fill="black", width=self.line_width)
            clip = [
                (pos[0]-mm(supportBasicLength)/2, gap_y),
                (pos[0]+mm(supportBasicLength)/2, gap_y),
                (pos[0]+mm(supportBasicLength)/2, gap_y+mm(supportBasicHeight)),
                (pos[0]-mm(supportBasicLength)/2, gap_y+mm(supportBasicHeight))
            ]
            self._draw_ground_hatching(d, clip, 180 - hatchingAngle, hatchingLength)

    # spring support
    def _s5(self, d, pos, rot):
        total = mm(springLength)
        pre = mm(springPreLength)
        post = mm(springPostLength)
        usable = total - pre - post
        cycles = 4
        amp = mm(springAmplitude)

        pts = [(pos[0], pos[1])]
        y = pos[1] + pre
        pts.append((pos[0], y))

        # sinusoidal coil
        steps = 80
        for i in range(steps+1):
            frac = i / steps
            yy = y + frac * usable
            xx = pos[0] + amp * math.sin(frac * cycles * 2 * math.pi)
            pts.append((xx, yy))

        y_end = y + usable
        pts.append((pos[0], y_end + post))

        if rot != 0:
            pts = self._rot_many(pts, pos, rot)
        d.line(pts, fill="black", width=LINE_NORMAL-1)

        # base line & hatching
        base_y = pos[1] + total if rot == 0 else self._rot((pos[0], pos[1]+total), pos, rot)[1]
        if rot == 0:
            d.line([
                (pos[0]+mm(supportBasicLength)/2, base_y),
                (pos[0]-mm(supportBasicLength)/2, base_y)
            ], fill="black", width=self.line_width)
            clip = [
                (pos[0]-mm(supportBasicLength)/2, base_y),
                (pos[0]+mm(supportBasicLength)/2, base_y),
                (pos[0]+mm(supportBasicLength)/2, base_y+mm(supportBasicHeight)),
                (pos[0]-mm(supportBasicLength)/2, base_y+mm(supportBasicHeight))
            ]
            self._draw_ground_hatching(d, clip, 180 - hatchingAngle, hatchingLength)

        # torsion spring
    def _s6(self, d, pos, rot):
        pts = []
        turns = 3.5
        steps = 100
        radius = mm(1.5)
        spacing = mm(0.4)
        for i in range(steps+1):
            theta = i / steps * turns * 2 * math.pi
            r = radius + spacing * theta / (2*math.pi)
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            pts.append((pos[0]+x, pos[1]+y))
        pts = self._rot_many(pts, pos, rot - 90)
        d.line(pts, fill="black", width=LINE_NORMAL-1)

        # short ground line
        gl1 = self._rot((pos[0]-mm(supportBasicLength)/2.5, pos[1]), pos, rot)
        gl2 = self._rot((pos[0]+mm(supportBasicLength)/2.5, pos[1]), pos, rot)
        d.line([gl1, gl2], fill="black", width=self.line_width)

        # hatch below
        if rot == 0:
            clip = [
                (pos[0]-mm(supportBasicLength)/2.5, pos[1]),
                (pos[0]+mm(supportBasicLength)/2.5, pos[1]),
                (pos[0]+mm(supportBasicLength)/2.5, pos[1]+mm(supportBasicHeight)),
                (pos[0]-mm(supportBasicLength)/2.5, pos[1]+mm(supportBasicHeight))
            ]
            self._draw_ground_hatching(d, clip, 180 - hatchingAngle, hatchingLength/2)


    def _draw_ground_hatching(self, d: ImageDraw.Draw, clip_rect: List[Tuple[float,float]], 
                            angle_deg: float, spacing_mm: float):
        """Draw proper diagonal hatching like TikZ"""
        xs = [p[0] for p in clip_rect]
        ys = [p[1] for p in clip_rect]
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        ang = math.radians(angle_deg)
        dx, dy = math.cos(ang), math.sin(ang)
        nx, ny = -dy, dx
        # project corners
        projs = [x*nx + y*ny for (x, y) in clip_rect]
        pmin, pmax = min(projs), max(projs)
        step = mm(spacing_mm)
        t = pmin - step
        while t <= pmax + step:
            pts = []
            # vertical edges
            for x in (xmin, xmax):
                if abs(ny) > 1e-9:
                    y = (t - nx*x) / ny
                    if ymin-1 <= y <= ymax+1:
                        pts.append((x, y))
            # horizontal edges
            for y in (ymin, ymax):
                if abs(nx) > 1e-9:
                    x = (t - ny*y) / nx
                    if xmin-1 <= x <= xmax+1:
                        pts.append((x, y))
            if len(pts) >= 2:
                pts.sort(key=lambda P: P[0]*dx + P[1]*dy)
                d.line([pts[0], pts[-1]], fill="black", width=LINE_SMALL)
            t += step

# -------------------------------------------------
# hinges
# -------------------------------------------------

class StanliHinge(StanliSymbol):
    def __init__(self, ht: HingeType):
        super().__init__(LINE_NORMAL)
        self.ht = ht

    def draw(self, d: ImageDraw.Draw, pos: Tuple[float,float],
             rotation: float=0,
             p_init: Optional[Tuple[float,float]]=None,
             p_end: Optional[Tuple[float,float]]=None):
        r = mm(hingeRadius)
        if self.ht == HingeType.FULL_JOINT:
            d.ellipse((pos[0]-r,pos[1]-r,pos[0]+r,pos[1]+r), fill="white", outline="black", width=self.line_width)

        elif self.ht == HingeType.HALF_JOINT and p_init and p_end:
            # circle
            d.ellipse((pos[0]-r,pos[1]-r,pos[0]+r,pos[1]+r), fill="white", outline="black", width=self.line_width)
            # thick bars (approx hugeLine)
            self._radial_bar(d, pos, p_init, r)
            self._radial_bar(d, pos, p_end, r)

        elif self.ht == HingeType.SHEAR_JOINT:
            gap = mm(supportGap)/2
            L = mm(supportBasicLength)
            # two vertical bars and a small white core
            d.ellipse((pos[0]-gap,pos[1]-gap,pos[0]+gap,pos[1]+gap), fill="white", outline="black", width=LINE_SMALL)
            d.line([(pos[0]-gap, pos[1]-L/2),(pos[0]-gap,pos[1]+L/2)], fill="black", width=self.line_width)
            d.line([(pos[0]+gap, pos[1]-L/2),(pos[0]+gap,pos[1]+L/2)], fill="black", width=self.line_width)

        elif self.ht == HingeType.NORMAL_FORCE_JOINT:
            w = mm(hingeAxialLength)
            h = mm(hingeAxialHeight)
            left = pos[0] - w/3
            right = pos[0] + 2*w/3
            top = pos[1] - h/2
            bot = pos[1] + h/2

            # outline only
            d.rectangle([left, top, right, bot], outline="white", fill="white", width=self.line_width)

            # horizontal lines inside
            d.line([(left, top), (right, top)], fill="black", width=LINE_SMALL)
            d.line([(left, bot), (right, bot)], fill="black", width=LINE_SMALL)

        elif self.ht == HingeType.STIFF_CORNER and p_init and p_end:
            # filled triangle
            a = self._point_along(pos, p_init, mm(hingeCornerLength))
            b = self._point_along(pos, p_end, mm(hingeCornerLength))
            d.polygon([pos, a, b], fill="black")
            d.ellipse((pos[0]-LINE_HUGE/2,pos[1]-LINE_HUGE/2,pos[0]+LINE_HUGE/2,pos[1]+LINE_HUGE/2),
                      fill="black")

    def _point_along(self, origin, target, dist):
        vx, vy = target[0]-origin[0], target[1]-origin[1]
        L = math.hypot(vx, vy) or 1
        return (origin[0]+vx/L*dist, origin[1]+vy/L*dist)

    def _radial_bar(self, d, origin, target, r):
        p = self._point_along(origin, target, r)
        d.line([origin, p], fill="black", width=LINE_HUGE)

# -------------------------------------------------
# loads
# -------------------------------------------------

class StanliLoad(StanliSymbol):
    def __init__(self, lt: LoadType):
        super().__init__(LINE_NORMAL)
        self.lt = lt

    def draw(self, d: ImageDraw.Draw, pos: Tuple[float,float],
             rotation_deg: float=0,
             length: Optional[float]=None,
             distance: Optional[float]=None,
             arc_angle: Optional[float]=None):
        if self.lt == LoadType.SINGLE_LOAD:
            self._single(d, pos, rotation_deg,
                         length if length is not None else forceLength,
                         distance if distance is not None else forceDistance)
        else:
            self._moment(d, pos,
                         distance if distance is not None else momentDistance,
                         arc_angle if arc_angle is not None else momentAngleDefault,
                         rotation_deg,
                         clockwise=(self.lt == LoadType.MOMENT_CLOCKWISE))

    def _single(self, d, pos, rot, L_mm, D_mm):
        # TikZ: start at offset D, line forward length L, arrowhead at start (<-)
        ang = math.radians(rot)
        start = (pos[0] + mm(D_mm)*math.cos(ang),
                 pos[1] - mm(D_mm)*math.sin(ang))  # minus sin for TikZ up
        end = (start[0] + mm(L_mm)*math.cos(ang),
               start[1] - mm(L_mm)*math.sin(ang))
        # draw line from end to start (so we can put arrow at start consistent)
        d.line([end, start], fill="black", width=self.line_width)
        self._arrow_head(d, start, ang + math.pi)  # head pointing toward pos

    def _moment(self, d, pos, radius_mm, angle_deg, rot_deg, clockwise: bool):
        # Build arc in TikZ sense: start angle 0 at +x (after rotation)
        # We'll param manually (TikZ positive angle CCW; we invert y with -sin).
        base_rot = math.radians(rot_deg)
        r_px = mm(radius_mm)
        steps = max(10, int(angle_deg/6))
        if clockwise:
            angle_list = [i*angle_deg/steps for i in range(steps+1)]
        else:
            angle_list = [i*angle_deg/steps for i in range(steps+1)]
        # start point angle = 0
        coords = []
        for a in angle_list:
            a_rad = math.radians(a)
            # CCW in TikZ: x=r cos(a), y= r sin(a) (y up). We do y= -r sin(a).
            x_local = r_px*math.cos(a_rad)
            y_local = -r_px*math.sin(a_rad)
            # rotate by base_rot
            x = pos[0] + x_local*math.cos(base_rot) - y_local*math.sin(base_rot)
            y = pos[1] + x_local*math.sin(base_rot) + y_local*math.cos(base_rot)
            coords.append((x,y))
        if clockwise:
            # arrow head at start
            d.line(coords, fill="black", width=self.line_width)
            self._arrow_head(d, coords[0],
                             math.atan2(coords[1][1]-coords[0][1],
                                        coords[1][0]-coords[0][0]))
        else:
            # counter: arrow at end
            d.line(coords, fill="black", width=self.line_width)
            self._arrow_head(d, coords[-1],
                             math.atan2(coords[-1][1]-coords[-2][1],
                                        coords[-1][0]-coords[-2][0]))

    def _arrow_head(self, d, tip, ang, size_px=mm(2.2)):
        spread = math.radians(22)
        p1 = (tip[0] + size_px*math.cos(ang+spread),
              tip[1] + size_px*math.sin(ang+spread))
        p2 = (tip[0] + size_px*math.cos(ang-spread),
              tip[1] + size_px*math.sin(ang-spread))
        d.polygon([tip, p1, p2], fill="black")

