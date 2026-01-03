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
    STRECKENLAST = 4 # EXPERIMENTAL BE CAREFULL

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
hatchingLength = 1.5 

# -------------------------------------------------
# base
# -------------------------------------------------

@dataclass
class StanliSymbol:
    line_width: int = LINE_NORMAL

    def _rot(self, p, origin, angle_deg):
        a = math.radians(angle_deg)
        ox, oy = origin
        x, y = p
        return (
            ox + math.cos(a)*(x-ox) - math.sin(a)*(y-oy),
            oy + math.sin(a)*(x-ox) + math.cos(a)*(y-oy)
        )


    def _rot_many(self, pts, origin, ang):
        return [self._rot(p, origin, ang) for p in pts]

    def _get_rotated_bbox(self, local_corners: List[Tuple[float, float]], origin: Tuple[float, float], rotation: float) -> Tuple[float, float, float, float]:
        """
        Takes a list of points (defining the shape in standard orientation) relative to absolute space,
        rotates them around `origin` by `rotation`, and finds the axis-aligned bounding box.
        """
        rotated_points = self._rot_many(local_corners, origin, rotation)
        xs = [p[0] for p in rotated_points]
        ys = [p[1] for p in rotated_points]
        
        # Add a small padding (e.g. 2px) for line thickness
        pad = self.line_width + 1
        return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

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
            d.line([a, b], fill="black", width=self.line_width)
        
        if self.beam_type == BeamType.BIEGUNG_MIT_FASER:
            self._fiber(d, a, b)
            
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
        
        # Extra padding for fiber or thickness
        pad = self.line_width + 2
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

    def draw(self, d: ImageDraw.Draw, pos: Tuple[float,float], rotation: float=0):
        # We rotate the entire drawing canvas context conceptually, 
        # but here we manually calculate points relative to 'pos' and then rotate.
        
        # Helper to simplify calls
        def p(dx, dy):
            # Returns absolute point rotated around pos
            pt = (pos[0] + mm(dx), pos[1] + mm(dy))
            return self._rot(pt, pos, rotation)

        if self.st == SupportType.FESTLAGER:
            # Triangle
            top = p(0, 0)
            bl = p(-supportLength/2, supportHeight)
            br = p(supportLength/2, supportHeight)
            d.polygon([top, bl, br], outline="black", fill=None, width=self.line_width)
            # Hatching line
            hl_start = p(-supportHatchingLength/2, supportHeight)
            hl_end = p(supportHatchingLength/2, supportHeight)
            d.line([hl_start, hl_end], fill="black", width=self.line_width)
            self._hatch(d, hl_start, hl_end, rotation)

        elif self.st == SupportType.LOSLAGER:
            # Triangle
            top = p(0, 0)
            bl = p(-supportLength/2, supportHeight)
            br = p(supportLength/2, supportHeight)
            d.polygon([top, bl, br], outline="black", fill=None, width=self.line_width)
            # Gap line (offset by supportHeight + supportGap)
            y_line = supportHeight + supportGap
            hl_start = p(-supportHatchingLength/2, y_line)
            hl_end = p(supportHatchingLength/2, y_line)
            d.line([hl_start, hl_end], fill="black", width=self.line_width)
            #self._hatch(d, hl_start, hl_end, rotation)

        elif self.st == SupportType.FESTE_EINSPANNUNG:
            # Just a line + hatching perpendicular
            w2 = supportHatchingLength / 2
            start = p(-w2, 0)
            end = p(w2, 0)
            d.line([start, end], fill="black", width=self.line_width)
            self._hatch(d, start, end, rotation)

        elif self.st == SupportType.GLEITLAGER:
            # Two circles + line
            r = mm(1.5)
            c1 = p(-supportLength/2, r/PX_PER_MM) 
            c2 = p(supportLength/2, r/PX_PER_MM)
            
            # Since draw.ellipse doesn't support rotation easily for the ellipse itself (it stays axis aligned),
            # we just draw small circles at rotated positions.
            self._circle(d, c1, r)
            self._circle(d, c2, r)
            
            # Line below
            y_line = (r*2)/PX_PER_MM + supportGap 
            hl_start = p(-supportHatchingLength/2, y_line)
            hl_end = p(supportHatchingLength/2, y_line)
            d.line([hl_start, hl_end], fill="black", width=self.line_width)
            self._hatch(d, hl_start, hl_end, rotation)

    def _hatch(self, d, p1, p2, rot):
        # Simple hatching marks below line p1-p2
        # Vector along line
        dx, dy = p2[0]-p1[0], p2[1]-p1[1]
        L = math.hypot(dx, dy)
        if L == 0: return
        
        ux, uy = dx/L, dy/L
        nx, ny = -uy, ux # Normal vector (down relative to line)

        h_len = mm(supportHatchingHeight)
        step = mm(hatchingLength)
        
        # Determine number of hatches
        count = int(L / step)
        for i in range(count + 1):
            t = i * step
            # Start on line
            sx = p1[0] + ux*t
            sy = p1[1] + uy*t
            # End (angled)
            # Standard hatching is 45 deg relative to normal
            # Simplified: just go down normal + some sideways
            ex = sx + nx*h_len - ux*(h_len*0.5) 
            ey = sy + ny*h_len - uy*(h_len*0.5)
            d.line([(sx,sy), (ex,ey)], fill="black", width=1)

    def _circle(self, d, center, r):
        d.ellipse((center[0]-r, center[1]-r, center[0]+r, center[1]+r), outline="black", width=self.line_width)

    def get_bbox(self, pos: Tuple[float, float], rotation: float = 0) -> Tuple[float, float, float, float]:
        """Calculates exact bounding box including hatching."""
        
        # Dimensions in mm
        w_main = supportHatchingLength # This is usually the widest part (the ground line)
        h_main = 0.0
        
        if self.st == SupportType.FESTLAGER:
            h_main = supportHeight + supportHatchingHeight # Triangle + Hatching
        elif self.st == SupportType.LOSLAGER:
            h_main = supportHeight + supportGap + supportHatchingHeight
        elif self.st == SupportType.FESTE_EINSPANNUNG:
            h_main = supportHatchingHeight 
            # Note: Einspannung is drawn centered on line. 
            # top is at y=0, hatching goes to y=5
        elif self.st == SupportType.GLEITLAGER:
            h_main = 3.0 + supportGap + supportHatchingHeight # Circles (~3mm) + gap + hatch

        # Define points in local unrotated space (relative to pos)
        # Horizontal center is 0. Vertical starts at 0 and goes positive (down).
        
        w_px = mm(w_main)
        h_px = mm(h_main)
        
        # Most supports are centered horizontally around pos
        local_corners = [
            (pos[0] - w_px/2, pos[1]),      # Top Left (on the structure node)
            (pos[0] + w_px/2, pos[1]),      # Top Right
            (pos[0] + w_px/2, pos[1] + h_px), # Bottom Right (end of hatching)
            (pos[0] - w_px/2, pos[1] + h_px), # Bottom Left
        ]
        
        # Handle special case: Feste Einspannung hatching goes "down" from node?
        # In _s3, line is at 0, hatching is below. Correct.
        
        return self._get_rotated_bbox(local_corners, pos, rotation)

# -------------------------------------------------
# hinges
# -------------------------------------------------

class StanliHinge(StanliSymbol):
    def __init__(self, ht: HingeType):
        super().__init__()
        self.ht = ht

    def draw(self, d: ImageDraw.Draw, pos: Tuple[float,float], 
             rotation: float=0, start_point=None, end_point=None):
        
        r = mm(hingeRadius)
        d.ellipse((pos[0]-r, pos[1]-r, pos[0]+r, pos[1]+r), fill="white", outline="black", width=self.line_width)
        
        if self.ht == HingeType.VOLLGELENK:
            # Just the circle
            pass 
        # Add other hinge types if needed

    def get_bbox(self, pos: Tuple[float, float], rotation: float = 0) -> Tuple[float, float, float, float]:
        r = mm(hingeRadius) + self.line_width
        return (pos[0]-r, pos[1]-r, pos[0]+r, pos[1]+r)

# -------------------------------------------------
# loads
# -------------------------------------------------

class StanliLoad(StanliSymbol):
    def __init__(self, lt: LoadType):
        super().__init__()
        self.lt = lt

    def draw(self, d: ImageDraw.Draw, pos: Tuple[float,float], rotation: float=0, length: float=40.0, distance: float=0.0):
        # Length is passed in pixels from Renderer, usually
        
        def p(x, y): return self._rot((pos[0]+x, pos[1]+y), pos, rotation)

        if self.lt == LoadType.EINZELLAST:
            # Arrow pointing AT pos (usually). 
            # In structural analysis: Force -> Node.
            # Start far away, End at pos.
            
            # Adjust for distance (gap between tip and node)
            dist_px = mm(forceDistance) if distance == 0 else distance
            
            # Start point (tail) -> End point (tip near node)
            # Default rotation 270 (down). 
            # 0 deg = Right.
            
            # Local space: Tail at (-length - dist, 0), Tip at (-dist, 0) ?
            # Let's align with standard rotation:
            # If 0 deg (Right), force pushes Right. So Tail is Left, Tip is Right.
            # Tail: (-length, 0), Tip: (0, 0)
            
            # Standard renderer uses rotation=270 for Down gravity load.
            # cos(270)=0, sin(270)=-1. 
            
            # If we draw line from (0, -len) to (0,0)? That points down.
            
            # Let's stick to simple: Start -> End.
            # Start = (0, -length), End = (0, -dist) relative to pos (rotated)
            
            # Using the arguments passed:
            start_y = -length - dist_px
            end_y = -dist_px
            
            # We define points assuming rotation=0 implies UP (standard math) or RIGHT?
            # Stanli convention: 0 is Right. 
            # So a Down force (270) should come from top.
            
            # Let's define "Force pushing in direction of rotation".
            # Tip is at pos (minus gap). Tail is further back.
            
            start = self._rot((pos[0] - (length+dist_px), pos[1]), pos, rotation)
            end = self._rot((pos[0] - dist_px, pos[1]), pos, rotation)
            
            self._arrow(d, start, end)

        elif self.lt in (LoadType.MOMENT_UHRZEIGER, LoadType.MOMENT_GEGEN_UHRZEIGER):
            # Circular arrow
            # Center is pos. Radius ~ length/2 or fixed?
            r = mm(momentDistance) + 10 # approximate radius
            
            # We draw an arc
            bbox = (pos[0]-r, pos[1]-r, pos[0]+r, pos[1]+r)
            
            if self.lt == LoadType.MOMENT_UHRZEIGER:
                # Clockwise
                d.arc(bbox, start=30, end=330, fill="black", width=self.line_width)
                # Arrowhead at end (330)
                # Math required for arrowhead on arc, simplified here
            else:
                d.arc(bbox, start=30, end=330, fill="black", width=self.line_width)

    def _arrow(self, d, start, end):
        d.line([start, end], fill="black", width=self.line_width)
        # Arrowhead
        # Vector
        vx, vy = end[0]-start[0], end[1]-start[1]
        L = math.hypot(vx, vy)
        if L == 0: return
        ux, uy = vx/L, vy/L
        
        # Head size
        h_len = 10 
        h_wid = 4
        
        # Base of head
        bx = end[0] - ux*h_len
        by = end[1] - uy*h_len
        
        # Perpendicular
        px, py = -uy, ux
        
        c1 = (bx + px*h_wid, by + py*h_wid)
        c2 = (bx - px*h_wid, by - py*h_wid)
        
        d.polygon([end, c1, c2], fill="black")

    def get_bbox(self, pos: Tuple[float, float], rotation: float = 0, length: float = 40.0, distance: float = 0.0) -> Tuple[float, float, float, float]:
        if self.lt == LoadType.EINZELLAST:
            dist_px = mm(forceDistance) if distance == 0 else distance  
            
            # Define arrow corners with generous width for detection
            local_corners = [
                (-(length + dist_px), -15.0), # Top Left
                (-(length + dist_px), 15.0),  # Bottom Left
                (-dist_px, 15.0),             # Bottom Right
                (-dist_px, -15.0)             # Top Right
            ]
            return self._get_rotated_bbox(local_corners, pos, rotation)
        
        elif self.lt in (LoadType.MOMENT_UHRZEIGER, LoadType.MOMENT_GEGEN_UHRZEIGER):
            # Circular arc moment symbol
            r = mm(momentDistance) + 10  # Arc radius
            
            # Define arc angles (30 to 330 degrees = almost full circle)
            start_angle = 30
            end_angle = 330
            
            # Convert to radians
            start_rad = math.radians(start_angle)
            end_rad = math.radians(end_angle)
            
            # Calculate arc endpoints
            start_x = r * math.cos(start_rad)
            start_y = r * math.sin(start_rad)
            end_x = r * math.cos(end_rad)
            end_y = r * math.sin(end_rad)
            
            # Check which cardinal directions (0°, 90°, 180°, 270°) are crossed by the arc
            # This determines if we need to extend bbox to full radius in that direction [web:12]
            
            # Helper function to check if angle is within arc span
            def angle_in_arc(angle_deg, start_deg, end_deg):
                # Normalize angles to 0-360
                angle = angle_deg % 360
                start = start_deg % 360
                end = end_deg % 360
                
                if start <= end:
                    return start <= angle <= end
                else:  # Arc crosses 0 degrees
                    return angle >= start or angle <= end
            
            # Initialize bbox with arc endpoints
            min_x = min(start_x, end_x)
            max_x = max(start_x, end_x)
            min_y = min(start_y, end_y)
            max_y = max(start_y, end_y)
            
            # Check cardinal directions [web:12]
            if angle_in_arc(0, start_angle, end_angle):    # Right (0°)
                max_x = r
            if angle_in_arc(90, start_angle, end_angle):   # Top (90°)
                max_y = r
            if angle_in_arc(180, start_angle, end_angle):  # Left (180°)
                min_x = -r
            if angle_in_arc(270, start_angle, end_angle):  # Bottom (270°)
                min_y = -r
            
            # Add padding for arrowhead and line width
            pad = 15.0
            
            # Define corners in local space (centered at pos)
            local_corners = [
                (pos[0] + min_x - pad, pos[1] + min_y - pad),
                (pos[0] + max_x + pad, pos[1] + min_y - pad),
                (pos[0] + max_x + pad, pos[1] + max_y + pad),
                (pos[0] + min_x - pad, pos[1] + max_y + pad),
            ]
            
            # Apply rotation around pos
            return self._get_rotated_bbox(local_corners, pos, rotation)
        