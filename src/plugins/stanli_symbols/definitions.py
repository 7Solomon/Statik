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
    FESTLAGER = 1
    LOSLAGER = 2
    FESTE_EINSPANNUNG = 3
    GLEITLAGER = 4
    FEDER = 5
    TORSIONSFEDER = 6

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
    STRECKENLAST = 4 # EXPERIMENTAL BE CAREFULL 


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
        if beam_type in (BeamType.BIEGUNG_MIT_FASER, BeamType.BIEGUNG_OHNE_FASER):
            self.line_width = LINE_HUGE
        elif beam_type == BeamType.FACHWERK:
            self.line_width = LINE_BIG
        elif beam_type == BeamType.VERSTECKT:
            self.line_width = LINE_NORMAL

    def draw(self, d: ImageDraw.Draw, a: Tuple[float,float], b: Tuple[float,float],
             rounded_start=False, rounded_end=False):
        if self.beam_type == BeamType.VERSTECKT:
            self._dashed(d, a, b, self.line_width)
        else:
            d.line([a, b], fill="black", width=self.line_width)
            if self.beam_type == BeamType.BIEGUNG_MIT_FASER:
                self._fiber(d, a, b)
            # Only add rounded ends if line is thick enough to avoid artifacts
            if rounded_start and self.line_width >= LINE_NORMAL:
                r = max(self.line_width / 2, LINE_SMALL)
                d.ellipse((a[0]-r,a[1]-r,a[0]+r,a[1]+r), fill="black")
            if rounded_end and self.line_width >= LINE_NORMAL:
                r = max(self.line_width / 2, LINE_SMALL)
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
# supports
# -------------------------------------------------

class StanliSupport(StanliSymbol):
    def __init__(self, st: SupportType):
        super().__init__(LINE_NORMAL)
        self.st = st

    def draw(self, d: ImageDraw.Draw, pos: Tuple[float,float], rotation: float=0):
        dispatch = {
            SupportType.FESTLAGER: self._s1,
            SupportType.LOSLAGER: self._s2,
            SupportType.FESTE_EINSPANNUNG: self._s3,
            SupportType.GLEITLAGER: self._s4,
            SupportType.FEDER: self._s5,
            SupportType.TORSIONSFEDER: self._s6,
        }
        dispatch[self.st](d, pos, rotation)
    
    def get_bbox(self, pos: Tuple[float, float], rotation: float = 0) -> Tuple[float, float, float, float]:
        """Calculate axis-aligned bounding box for support symbol.
        Returns (min_x, min_y, max_x, max_y) in pixel coordinates."""
        # Different support types have different extents
        if self.st == SupportType.FESTLAGER:
            # Triangle + hatching
            half_width = mm(supportBasicLength) / 2
            height = mm(supportHeight) + mm(supportBasicHeight)
            corners = [
                (pos[0], pos[1]),
                (pos[0] + mm(supportLength)/2, pos[1] + mm(supportHeight)),
                (pos[0] - mm(supportLength)/2, pos[1] + mm(supportHeight)),
                (pos[0] + half_width, pos[1] + height),
                (pos[0] - half_width, pos[1] + height)
            ]
        elif self.st == SupportType.LOSLAGER:
            # Triangle + gap + line
            half_width = mm(supportBasicLength) / 2
            height = mm(supportHeight) + mm(supportGap) + mm(supportBasicHeight)
            corners = [
                (pos[0], pos[1]),
                (pos[0] + mm(supportLength)/2, pos[1] + mm(supportHeight)),
                (pos[0] - mm(supportLength)/2, pos[1] + mm(supportHeight)),
                (pos[0] + half_width, pos[1] + height),
                (pos[0] - half_width, pos[1] + height)
            ]
        elif self.st == SupportType.FESTE_EINSPANNUNG:
            # Horizontal line at top + hatching below
            # The _s3 method draws: horizontal line from -half_width to +half_width at pos[1]
            # Then (when rot=0) draws hatching extending down by supportBasicHeight
            # For bbox, we always include the hatching area (even if not rendered when rotated)
            # to ensure consistent labeling
            half_width = mm(supportBasicLength) / 2
            height = mm(supportBasicHeight)
            corners = [
                (pos[0] - half_width, pos[1]),  # Top left of line
                (pos[0] + half_width, pos[1]),  # Top right of line
                (pos[0] - half_width, pos[1] + height),  # Bottom left (hatching extent)
                (pos[0] + half_width, pos[1] + height)   # Bottom right (hatching extent)
            ]
        elif self.st == SupportType.GLEITLAGER:
            # Horizontal line + gap + hatching
            half_width = mm(supportBasicLength) / 2
            height = mm(supportGap) + mm(supportBasicHeight)
            corners = [
                (pos[0] - mm(supportBasicLength)/2, pos[1]),
                (pos[0] + mm(supportBasicLength)/2, pos[1]),
                (pos[0] - half_width, pos[1] + height),
                (pos[0] + half_width, pos[1] + height)
            ]
        elif self.st == SupportType.FEDER:
            # FEDER extends downward
            total_len = mm(FEDERLength) + mm(FEDERPreLength) + mm(FEDERPostLength)
            half_amp = mm(FEDERAmplitude)
            corners = [
                (pos[0], pos[1]),
                (pos[0] - half_amp, pos[1] + total_len),
                (pos[0] + half_amp, pos[1] + total_len)
            ]
        elif self.st == SupportType.TORSIONSFEDER:
            # Torsion FEDER (circular + radial bars)
            radius = mm(FEDERLength) / 2
            corners = [
                (pos[0] - radius, pos[1] - radius),
                (pos[0] + radius, pos[1] + radius),
                (pos[0], pos[1] + radius + mm(FEDERPreLength))
            ]
        else:
            # Default fallback
            corners = [
                (pos[0] - mm(supportBasicLength)/2, pos[1]),
                (pos[0] + mm(supportBasicLength)/2, pos[1] + mm(supportHeight))
            ]
        
        # Rotate corners if needed
        if rotation != 0:
            corners = [self._rot(c, pos, rotation) for c in corners]
        
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        return (min(xs), min(ys), max(xs), max(ys))

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

        # Draw hatching
        if hatching:
            # Define clip rectangle in local coordinates
            clip_local = [
                (pos[0] - mm(supportBasicLength)/2, base_y),
                (pos[0] + mm(supportBasicLength)/2, base_y),
                (pos[0] + mm(supportBasicLength)/2, base_y + mm(supportBasicHeight)),
                (pos[0] - mm(supportBasicLength)/2, base_y + mm(supportBasicHeight))
            ]
            # Rotate the clip rectangle corners
            clip_rotated = self._rot_many(clip_local, pos, rot)
            self._draw_ground_hatching(d, clip_rotated, 180 - hatchingAngle + rot, hatchingLength)

    def _s3(self, d, pos, rot, hatching=True):
        top_y = pos[1]
        d.line([
            self._rot((pos[0]+mm(supportBasicLength)/2, top_y), pos, rot),
            self._rot((pos[0]-mm(supportBasicLength)/2, top_y), pos, rot)
        ], fill="black", width=self.line_width)
        
        # Draw hatching
        if hatching:
            clip_local = [
                (pos[0] - mm(supportBasicLength)/2, top_y),
                (pos[0] + mm(supportBasicLength)/2, top_y),
                (pos[0] + mm(supportBasicLength)/2, top_y + mm(supportBasicHeight)),
                (pos[0] - mm(supportBasicLength)/2, top_y + mm(supportBasicHeight))
            ]
            clip_rotated = self._rot_many(clip_local, pos, rot)
            # Adjust hatching angle by rotation
            self._draw_ground_hatching(d, clip_rotated, 180 - hatchingAngle + rot, hatchingLength)

    # roller (triangle + gap line)
    def _s2(self, d, pos, rot):
        # roller (triangle + gap line)
        self._s1(d, pos, rot, hatching=False)
        y_gap = pos[1] + mm(supportHeight) + mm(supportGap)
        
        # Draw gap line with rotation
        g_left = self._rot((pos[0] + mm(supportBasicLength)/2, y_gap), pos, rot)
        g_right = self._rot((pos[0] - mm(supportBasicLength)/2, y_gap), pos, rot)
        d.line([g_left, g_right], fill="black", width=self.line_width)
        
        # Draw hatching with rotation
        clip_local = [
            (pos[0] - mm(supportBasicLength)/2, y_gap),
            (pos[0] + mm(supportBasicLength)/2, y_gap),
            (pos[0] + mm(supportBasicLength)/2, y_gap + mm(supportBasicHeight)),
            (pos[0] - mm(supportBasicLength)/2, y_gap + mm(supportBasicHeight))
        ]
        clip_rotated = self._rot_many(clip_local, pos, rot)
        #self._draw_ground_hatching(d, clip_rotated, 180 - hatchingAngle + rot, hatchingLength)

    def _s4(self, d, pos, rot):
        self._s3(d, pos, rot, hatching=False)
        gap_y = pos[1] + mm(supportGap)
        
        # Draw gap line with rotation
        g_left = self._rot((pos[0] + mm(supportBasicLength)/2, gap_y), pos, rot)
        g_right = self._rot((pos[0] - mm(supportBasicLength)/2, gap_y), pos, rot)
        d.line([g_left, g_right], fill="black", width=self.line_width)
        
        # Draw hatching with rotation
        clip_local = [
            (pos[0] - mm(supportBasicLength)/2, gap_y),
            (pos[0] + mm(supportBasicLength)/2, gap_y),
            (pos[0] + mm(supportBasicLength)/2, gap_y + mm(supportBasicHeight)),
            (pos[0] - mm(supportBasicLength)/2, gap_y + mm(supportBasicHeight))
        ]
        clip_rotated = self._rot_many(clip_local, pos, rot)
        self._draw_ground_hatching(d, clip_rotated, 180 - hatchingAngle + rot, hatchingLength)

    # FEDER support
    def _s5(self, d, pos, rot):
        total = mm(FEDERLength)
        pre = mm(FEDERPreLength)
        post = mm(FEDERPostLength)
        usable = total - pre - post
        cycles = 4
        amp = mm(FEDERAmplitude)

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

        # torsion FEDER
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
        """Draw diagonal hatching clipped to an arbitrary quadrilateral (clip_rect).
        angle_deg: hatch line angle in degrees (0 = along +x). spacing_mm: spacing in mm.
        """
        # convert spacing to pixels
        step = mm(spacing_mm)
        if step <= 0:
            return

        # Get bounding box of clip polygon
        xs = [p[0] for p in clip_rect]
        ys = [p[1] for p in clip_rect]
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)

        # Direction vector for hatching lines
        angle_rad = math.radians(angle_deg)
        dx = math.cos(angle_rad)
        dy = math.sin(angle_rad)
        
        # Perpendicular direction for stepping between lines
        perp_dx = -dy
        perp_dy = dx

        # Diagonal length of bounding box to ensure coverage
        diag = math.hypot(xmax - xmin, ymax - ymin)
        
        # Number of lines needed
        n_lines = int(diag / step) + 4
        
        # Starting point (offset from center of bbox in perpendicular direction)
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        start_offset = -diag / 2
        
        for i in range(n_lines):
            offset = start_offset + i * step
            
            # Base point for this line (center + perpendicular offset)
            base_x = cx + perp_dx * offset
            base_y = cy + perp_dy * offset
            
            # Two points far along the line direction
            p1 = (base_x - dx * diag, base_y - dy * diag)
            p2 = (base_x + dx * diag, base_y + dy * diag)
            
            # Clip line segment to polygon
            clipped_segments = self._clip_line_to_polygon(p1, p2, clip_rect)
            
            # Draw all clipped segments
            for seg_start, seg_end in clipped_segments:
                d.line([seg_start, seg_end], fill="black", width=LINE_SMALL)

    def _clip_line_to_polygon(self, p1: Tuple[float, float], p2: Tuple[float, float], 
                          polygon: List[Tuple[float, float]]) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Clip a line segment to a convex polygon.
        Returns list of clipped line segments (may be empty if line is outside polygon)."""
        
        def line_intersection(p1, p2, p3, p4):
            """Find intersection point of two line segments (p1-p2) and (p3-p4).
            Returns (x, y, t, u) where t is parameter along p1-p2, u along p3-p4, or None if parallel."""
            x1, y1 = p1
            x2, y2 = p2
            x3, y3 = p3
            x4, y4 = p4
            
            denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(denom) < 1e-10:
                return None
            
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
            u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
            
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return (x, y, t, u)
        
        # Collect all valid intersection points with polygon edges
        intersections = []
        
        for i in range(len(polygon)):
            edge_start = polygon[i]
            edge_end = polygon[(i + 1) % len(polygon)]
            
            result = line_intersection(p1, p2, edge_start, edge_end)
            if result:
                x, y, t, u = result
                # Check if intersection is within BOTH line segment AND polygon edge
                if 0 <= t <= 1 and 0 <= u <= 1:
                    intersections.append((t, (x, y)))
        
        # Need exactly 2 intersections for a valid clipped segment
        if len(intersections) != 2:
            return []
        
        # Sort by parameter t along the line
        intersections.sort(key=lambda item: item[0])
        
        # Return the single clipped segment
        return [(intersections[0][1], intersections[1][1])]


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
        if self.ht == HingeType.VOLLGELENK:
            d.ellipse((pos[0]-r,pos[1]-r,pos[0]+r,pos[1]+r), fill="white", outline="black", width=self.line_width)

        elif self.ht == HingeType.HALBGELENK and p_init and p_end:
            # circle
            d.ellipse((pos[0]-r,pos[1]-r,pos[0]+r,pos[1]+r), fill="white", outline="black", width=self.line_width)
            # thick bars (approx hugeLine)
            self._radial_bar(d, pos, p_init, r)
            self._radial_bar(d, pos, p_end, r)

        elif self.ht == HingeType.SCHUBGELENK:
            gap = mm(supportGap)/2
            L = mm(supportBasicLength)
            # two vertical bars and a small white core
            d.ellipse((pos[0]-gap,pos[1]-gap,pos[0]+gap,pos[1]+gap), fill="white", outline="black", width=LINE_SMALL)
            d.line([(pos[0]-gap, pos[1]-L/2),(pos[0]-gap,pos[1]+L/2)], fill="black", width=self.line_width)
            d.line([(pos[0]+gap, pos[1]-L/2),(pos[0]+gap,pos[1]+L/2)], fill="black", width=self.line_width)

        elif self.ht == HingeType.NORMALKRAFTGELENK:
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

        elif self.ht == HingeType.BIEGESTEIFE_ECKE and p_init and p_end:
            # filled triangle
            a = self._point_along(pos, p_init, mm(hingeCornerLength))
            b = self._point_along(pos, p_end, mm(hingeCornerLength))
            d.polygon([pos, a, b], fill="black")
            d.ellipse((pos[0]-LINE_HUGE/2,pos[1]-LINE_HUGE/2,pos[0]+LINE_HUGE/2,pos[1]+LINE_HUGE/2),
                      fill="black")
    
    def get_bbox(self, pos: Tuple[float, float], rotation: float = 0,
                 p_init: Optional[Tuple[float, float]] = None,
                 p_end: Optional[Tuple[float, float]] = None) -> Tuple[float, float, float, float]:
        """Calculate axis-aligned bounding box for hinge symbol.
        Returns (min_x, min_y, max_x, max_y) in pixel coordinates."""
        r = mm(hingeRadius)
        
        if self.ht == HingeType.VOLLGELENK:
            # Simple circle
            return (pos[0] - r, pos[1] - r, pos[0] + r, pos[1] + r)
        
        elif self.ht == HingeType.HALBGELENK:
            # Circle + radial bars
            if p_init and p_end:
                corners = [
                    (pos[0] - r, pos[1] - r),
                    (pos[0] + r, pos[1] + r),
                    self._point_along(pos, p_init, r),
                    self._point_along(pos, p_end, r)
                ]
            else:
                corners = [(pos[0] - r, pos[1] - r), (pos[0] + r, pos[1] + r)]
        
        elif self.ht == HingeType.SCHUBGELENK:
            # Two vertical bars
            gap = mm(supportGap) / 2
            L = mm(supportBasicLength)
            corners = [
                (pos[0] - gap, pos[1] - L/2),
                (pos[0] + gap, pos[1] + L/2)
            ]

        elif self.ht == HingeType.NORMALKRAFTGELENK:
            # Rectangle
            w = mm(hingeAxialLength)
            h = mm(hingeAxialHeight)
            corners = [
                (pos[0] - w/3, pos[1] - h/2),
                (pos[0] + 2*w/3, pos[1] + h/2)
            ]
        
        elif self.ht == HingeType.BIEGESTEIFE_ECKE:
            # Triangle
            if p_init and p_end:
                a = self._point_along(pos, p_init, mm(hingeCornerLength))
                b = self._point_along(pos, p_end, mm(hingeCornerLength))
                corners = [pos, a, b]
            else:
                # Fallback
                L = mm(hingeCornerLength)
                corners = [(pos[0] - L, pos[1] - L), (pos[0] + L, pos[1] + L)]
        else:
            # Default fallback
            corners = [(pos[0] - r, pos[1] - r), (pos[0] + r, pos[1] + r)]
        
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        return (min(xs), min(ys), max(xs), max(ys))

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
        if self.lt == LoadType.EINZELLAST:
            self._single(d, pos, rotation_deg,
                         length if length is not None else forceLength,
                         distance if distance is not None else forceDistance)
        else:
            self._moment(d, pos,
                         distance if distance is not None else momentDistance,
                         arc_angle if arc_angle is not None else momentAngleDefault,
                         rotation_deg,
                         clockwise=(self.lt == LoadType.MOMENT_UHRZEIGER))

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
    
    def get_bbox(self, pos: Tuple[float, float], rotation_deg: float = 0,
                 length: Optional[float] = None,
                 distance: Optional[float] = None,
                 arc_angle: Optional[float] = None) -> Tuple[float, float, float, float]:
        """Calculate axis-aligned bounding box for load symbol.
        Returns (min_x, min_y, max_x, max_y) in pixel coordinates."""
        
        if self.lt == LoadType.EINZELLAST:
            # Arrow from distance to distance+length
            L_mm = length if length is not None else forceLength
            D_mm = distance if distance is not None else forceDistance
            ang = math.radians(rotation_deg)
            
            start = (pos[0] + mm(D_mm) * math.cos(ang),
                    pos[1] - mm(D_mm) * math.sin(ang))
            end = (start[0] + mm(L_mm) * math.cos(ang),
                  start[1] - mm(L_mm) * math.sin(ang))
            
            # Arrow head adds small extra extent
            arrow_size = mm(2.2)
            corners = [start, end,
                      (start[0] - arrow_size, start[1] - arrow_size),
                      (start[0] + arrow_size, start[1] + arrow_size)]
        
        else:
            # Moment arc (clockwise or counter)
            radius_mm = distance if distance is not None else momentDistance
            angle_deg_arc = arc_angle if arc_angle is not None else momentAngleDefault
            r_px = mm(radius_mm)
            
            base_rot = math.radians(rotation_deg)
            steps = max(10, int(angle_deg_arc / 6))
            angle_list = [i * angle_deg_arc / steps for i in range(steps + 1)]
            
            corners = []
            for a in angle_list:
                a_rad = math.radians(a)
                x_local = r_px * math.cos(a_rad)
                y_local = -r_px * math.sin(a_rad)
                x = pos[0] + x_local * math.cos(base_rot) - y_local * math.sin(base_rot)
                y = pos[1] + x_local * math.sin(base_rot) + y_local * math.cos(base_rot)
                corners.append((x, y))
            
            # Add arrow head extent
            arrow_size = mm(2.2)
            corners.extend([
                (pos[0] - r_px - arrow_size, pos[1] - r_px - arrow_size),
                (pos[0] + r_px + arrow_size, pos[1] + r_px + arrow_size)
            ])
        
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        return (min(xs), min(ys), max(xs), max(ys))

    def _arrow_head(self, d, tip, ang, size_px=mm(2.2)):
        spread = math.radians(22)
        p1 = (tip[0] + size_px*math.cos(ang+spread),
              tip[1] + size_px*math.sin(ang+spread))
        p2 = (tip[0] + size_px*math.cos(ang-spread),
              tip[1] + size_px*math.sin(ang-spread))
        d.polygon([tip, p1, p2], fill="black")

