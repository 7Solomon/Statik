import math
import json
import os
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple

from backend.src.plugins.stanli_symbols.definitions import *

# --- 1. GEOMETRY HELPERS (Crucial for Hatching) ---

def line_intersection(p1, p2, p3, p4):
    """Find intersection of line segments p1-p2 and p3-p4"""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10: return None
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    
    if 0 <= t <= 1 and 0 <= u <= 1:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return (x, y)
    return None

def clip_line_to_polygon(p1, p2, polygon):
    """Clip segment p1-p2 to convex polygon"""
    points = []
    # Check intersection with all edges
    for i in range(len(polygon)):
        edge_start = polygon[i]
        edge_end = polygon[(i + 1) % len(polygon)]
        pt = line_intersection(p1, p2, edge_start, edge_end)
        if pt: points.append(pt)
        
    # Also check if endpoints are inside (Point in Polygon)
    # Simplified for convex box: check bounds logic or just rely on 2 intersections
    # For robust hatching of a box, usually finding 2 intersection points is enough.
    
    if len(points) == 2:
        return [(points[0], points[1])]
    return []

# --- 2. RECORDER (Outputs SVG Paths) ---
class SvgPathRecorder:
    def __init__(self):
        self.paths = []

    def line(self, xy, fill=None, width=1):
        if not xy: return
        # xy is list of tuples [(x,y), (x,y)]
        d = f"M {xy[0][0]:.2f} {xy[0][1]:.2f}"
        for p in xy[1:]:
            d += f" L {p[0]:.2f} {p[1]:.2f}"
        self.paths.append({"d": d, "type": "stroke", "width": width})

    def polygon(self, xy, fill=None, outline=None, width=1):
        if not xy: return
        d = f"M {xy[0][0]:.2f} {xy[0][1]:.2f}"
        for p in xy[1:]:
            d += f" L {p[0]:.2f} {p[1]:.2f}"
        d += " Z"
        if fill: self.paths.append({"d": d, "type": "fill", "color": "white" if fill=="white" else None})
        if outline: self.paths.append({"d": d, "type": "stroke", "width": width})

    def ellipse(self, xy, fill=None, outline=None, width=1):
        x0, y0, x1, y1 = xy
        rx = (x1 - x0)/2; ry = (y1 - y0)/2
        cx = x0 + rx; cy = y0 + ry
        d = f"M {cx-rx:.2f} {cy:.2f} A {rx:.2f} {ry:.2f} 0 1 0 {cx+rx:.2f} {cy:.2f} A {rx:.2f} {ry:.2f} 0 1 0 {cx-rx:.2f} {cy:.2f} Z"
        if fill: self.paths.append({"d": d, "type": "fill", "color": "white" if fill=="white" else None})
        if outline: self.paths.append({"d": d, "type": "stroke", "width": width})

    # --- ADD THIS MISSING METHOD ---
    def rectangle(self, xy, fill=None, outline=None, width=1):
        # xy is [left, top, right, bottom]
        x0, y0, x1, y1 = xy
        # Convert to polygon points: (x0,y0) -> (x1,y0) -> (x1,y1) -> (x0,y1)
        points = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        self.polygon(points, fill, outline, width)


# --- 4. EXECUTION ---
def run():
    print("OUTDATAD SOMEHTING WITH HINGES NOT QUIETE RIGHT")
    rec = SvgPathRecorder()
    supports = {}
    
    for st in SupportType:
        rec.paths = []
        StanliSupport(st).draw(rec, (0,0))
        supports[f"SUPPORT_{st.name}"] = rec.paths[:]
        
    hinges = {}
    for ht in HingeType:
        rec.paths = []
        StanliHinge(ht).draw(rec, (0,0))
        hinges[f"HINGE_{ht.name}"] = rec.paths[:]

    # Print JSON
    print("=== SUPPORTS ===")
    print(json.dumps(supports, indent=2))
    print("=== HINGES ===")
    print(json.dumps(hinges, indent=2))

if __name__ == "__main__":
    run()
