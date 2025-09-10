# stanli_symbols.py
"""
Faithful recreation of stanli structural analysis symbols for PIL rendering
Based on the official stanli documentation from CTAN
"""

import math
import numpy as np
from PIL import Image, ImageDraw
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class BeamType(Enum):
    BENDING_WITH_FIBER = 1  # Type 1: bending beam with characteristic fiber
    TRUSS = 2              # Type 2: truss rod
    HIDDEN = 3             # Type 3: hidden bar (dashed)
    BENDING_NO_FIBER = 4   # Type 4: bending beam without characteristic fiber

class SupportType(Enum):
    FIXED_BEARING = 1      # Type 1: fixed bearing (two rollers)
    FLOATING_BEARING = 2   # Type 2: floating bearing (one roller)
    FIXED_SUPPORT = 3      # Type 3: fixed support (triangle with hatching)
    SUPPORT = 4            # Type 4: support (single direction)
    SPRING = 5             # Type 5: spring
    TORSION_SPRING = 6     # Type 6: torsion spring

class HingeType(Enum):
    FULL_JOINT = 1         # Type 1: full joint (circle)
    HALF_JOINT = 2         # Type 2: half joint (half circle)
    SHEAR_JOINT = 3        # Type 3: shear joint (parallel lines)
    NORMAL_FORCE_JOINT = 4 # Type 4: normal force joint (perpendicular lines)
    STIFF_CORNER = 5       # Type 5: stiff corner

class LoadType(Enum):
    SINGLE_LOAD = 1        # Type 1: single force
    MOMENT_CLOCKWISE = 2   # Type 2: moment clockwise
    MOMENT_COUNTER = 3     # Type 3: moment counter clockwise

class LineLoadType(Enum):
    NORMAL_TO_BEAM = 1     # Type 1: normal to beam axis
    PARALLEL_TO_Y = 2      # Type 2: parallel to y-axis
    PROJECTED_ON_BEAM = 3  # Type 3: projected on beam
    ALONG_BEAM_AXIS = 4    # Type 4: along beam axis

@dataclass
class StanliSymbol:
    """Base class for stanli symbols with precise geometric definitions"""
    scale: float = 1.0
    line_width: float = 1.0
    
    def draw(self, draw: ImageDraw.Draw, position: Tuple[float, float], 
             rotation: float = 0, **kwargs):
        """Override in subclasses"""
        pass

class StanliBeam(StanliSymbol):
    """Accurate beam representations from stanli"""
    
    def __init__(self, beam_type: BeamType, width: float = 3.0):
        super().__init__()
        self.beam_type = beam_type
        self.width = width
    
    def draw(self, draw: ImageDraw.Draw, start_pos: Tuple[float, float], 
             end_pos: Tuple[float, float], rounded_start: bool = False, 
             rounded_end: bool = False, **kwargs):
        
        x1, y1 = start_pos
        x2, y2 = end_pos
        
        if self.beam_type == BeamType.HIDDEN:
            # Dashed line for hidden beams
            self._draw_dashed_line(draw, start_pos, end_pos)
        else:
            # Calculate beam geometry
            length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            if length == 0:
                return
                
            # Unit vector along beam
            ux, uy = (x2-x1)/length, (y2-y1)/length
            # Perpendicular unit vector
            vx, vy = -uy, ux
            
            # Half width offset
            hw = self.width / 2
            
            # Beam corners
            corners = [
                (x1 + vx*hw, y1 + vy*hw),  # Top left
                (x2 + vx*hw, y2 + vy*hw),  # Top right
                (x2 - vx*hw, y2 - vy*hw),  # Bottom right
                (x1 - vx*hw, y1 - vy*hw),  # Bottom left
            ]
            
            # Draw main beam
            draw.polygon(corners, outline=(0,0,0), width=int(self.line_width))
            
            # Draw characteristic fiber for bending beams
            if self.beam_type == BeamType.BENDING_WITH_FIBER:
                fiber_y = y1 - vy*hw + vy*0.3  # Slightly inside bottom edge
                fiber_end_y = y2 - vy*hw + vy*0.3
                draw.line([(x1, fiber_y), (x2, fiber_end_y)], 
                         fill=(0,0,0), width=int(self.line_width))
            
            # Handle rounded ends
            if rounded_start:
                self._draw_rounded_end(draw, (x1, y1), -ux, -uy, hw)
            if rounded_end:
                self._draw_rounded_end(draw, (x2, y2), ux, uy, hw)
    
    def _draw_dashed_line(self, draw: ImageDraw.Draw, start: Tuple[float, float], 
                         end: Tuple[float, float]):
        """Draw dashed line for hidden beams"""
        x1, y1 = start
        x2, y2 = end
        length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        
        if length == 0:
            return
            
        dash_length = 8
        gap_length = 4
        total_dash = dash_length + gap_length
        
        num_dashes = int(length / total_dash)
        
        ux, uy = (x2-x1)/length, (y2-y1)/length
        
        for i in range(num_dashes + 1):
            start_offset = i * total_dash
            end_offset = min(start_offset + dash_length, length)
            
            dash_start = (x1 + start_offset*ux, y1 + start_offset*uy)
            dash_end = (x1 + end_offset*ux, y1 + end_offset*uy)
            
            draw.line([dash_start, dash_end], fill=(0,0,0), width=int(self.line_width))
    
    def _draw_rounded_end(self, draw: ImageDraw.Draw, center: Tuple[float, float],
                         ux: float, uy: float, half_width: float):
        """Draw rounded beam end"""
        cx, cy = center
        r = half_width
        bbox = [cx-r, cy-r, cx+r, cy+r]
        draw.ellipse(bbox, outline=(0,0,0), width=int(self.line_width))

class StanliSupport(StanliSymbol):
    """Accurate support symbols from stanli documentation"""
    
    def __init__(self, support_type: SupportType, size: float = 20.0):
        super().__init__()
        self.support_type = support_type
        self.size = size
    
    def draw(self, draw: ImageDraw.Draw, position: Tuple[float, float], 
            rotation: float = 0, hinge_radius: Optional[float] = None, **kwargs):

        x, y = position
        s = self.size

        if hinge_radius is not None:
            # Offset distance so triangle peak touches hinge circle edge
            offset_distance = s / 2 + hinge_radius
            
            cos_r = math.cos(math.radians(rotation))
            sin_r = math.sin(math.radians(rotation))
            
            # Offset downward (positive Y) by default, then rotate
            offset_x = offset_distance * sin_r
            offset_y = offset_distance * cos_r
            
            x += offset_x
            y += offset_y
        
        # Apply rotation
        cos_r = math.cos(math.radians(rotation))
        sin_r = math.sin(math.radians(rotation))
        
        def rotate_point(px: float, py: float) -> Tuple[float, float]:
            return (
                x + px * cos_r - py * sin_r,
                y + px * sin_r + py * cos_r
            )
        
        if self.support_type == SupportType.FIXED_BEARING:
            # Type 1: Fixed bearing - two rollers in triangle frame
            # Triangle base
            p1 = rotate_point(-s/2, s/2)
            p2 = rotate_point(s/2, s/2)
            p3 = rotate_point(0, -s/2)
            
            draw.polygon([p1, p2, p3], outline=(0,0,0), width=int(self.line_width))
            
            # Two rollers
            r1_center = rotate_point(-s/4, s/4)
            r2_center = rotate_point(s/4, s/4)
            roller_r = s/8
            
            for rc in [r1_center, r2_center]:
                bbox = [rc[0]-roller_r, rc[1]-roller_r, rc[0]+roller_r, rc[1]+roller_r]
                draw.ellipse(bbox, outline=(0,0,0), width=int(self.line_width))
        
        elif self.support_type == SupportType.FLOATING_BEARING:
            # Type 2: Floating bearing - one roller in triangle
            p1 = rotate_point(-s/2, s/2)
            p2 = rotate_point(s/2, s/2)
            p3 = rotate_point(0, -s/2)
            
            draw.polygon([p1, p2, p3], outline=(0,0,0), width=int(self.line_width))
            
            # One roller
            roller_center = rotate_point(0, s/4)
            roller_r = s/6
            bbox = [roller_center[0]-roller_r, roller_center[1]-roller_r, 
                   roller_center[0]+roller_r, roller_center[1]+roller_r]
            draw.ellipse(bbox, outline=(0,0,0), width=int(self.line_width))
        
        elif self.support_type == SupportType.FIXED_SUPPORT:
            # Type 3: Fixed support - filled triangle with hatching
            p1 = rotate_point(-s/2, s/2)
            p2 = rotate_point(s/2, s/2)
            p3 = rotate_point(0, -s/2)
            
            draw.polygon([p1, p2, p3], fill=(100,100,100), outline=(0,0,0), 
                        width=int(self.line_width))
            
            # Ground hatching lines
            for i in range(5):
                hatch_x = -s/2 + i * s/4
                h1 = rotate_point(hatch_x, s/2)
                h2 = rotate_point(hatch_x - s/6, s/2 + s/4)
                draw.line([h1, h2], fill=(0,0,0), width=int(self.line_width))
        
        elif self.support_type == SupportType.SUPPORT:
            # Type 4: Support - single direction constraint
            # Simple triangle outline pointing in constraint direction
            p1 = rotate_point(-s/3, s/2)
            p2 = rotate_point(s/3, s/2)
            p3 = rotate_point(0, -s/3)
            
            draw.polygon([p1, p2, p3], outline=(0,0,0), width=int(self.line_width))
        
        elif self.support_type == SupportType.SPRING:
            # Type 5: Spring symbol
            self._draw_spring(draw, position, rotation, s)
        
        elif self.support_type == SupportType.TORSION_SPRING:
            # Type 6: Torsion spring
            self._draw_torsion_spring(draw, position, rotation, s)
    
    def _draw_spring(self, draw: ImageDraw.Draw, center: Tuple[float, float], 
                    rotation: float, size: float):
        """Draw spring symbol with proper coil geometry"""
        x, y = center
        coils = 4
        coil_height = size / 3
        spring_length = size
        
        cos_r = math.cos(math.radians(rotation))
        sin_r = math.sin(math.radians(rotation))
        
        points = []
        for i in range(coils * 4 + 1):
            t = i / (coils * 4)
            spring_x = t * spring_length - spring_length/2
            spring_y = coil_height * math.sin(t * coils * 2 * math.pi) / 2
            
            # Rotate point
            rx = x + spring_x * cos_r - spring_y * sin_r
            ry = y + spring_x * sin_r + spring_y * cos_r
            points.append((rx, ry))
        
        # Draw spring as connected line segments
        for i in range(len(points)-1):
            draw.line([points[i], points[i+1]], fill=(0,0,0), width=int(self.line_width))
    
    def _draw_torsion_spring(self, draw: ImageDraw.Draw, center: Tuple[float, float],
                           rotation: float, size: float):
        """Draw torsion spring symbol"""
        x, y = center
        # Simplified as spiral for now
        turns = 3
        max_r = size / 3
        
        points = []
        for i in range(turns * 8):
            t = i / (turns * 8)
            angle = t * turns * 2 * math.pi + math.radians(rotation)
            r = t * max_r
            
            px = x + r * math.cos(angle)
            py = y + r * math.sin(angle)
            points.append((px, py))
        
        for i in range(len(points)-1):
            draw.line([points[i], points[i+1]], fill=(0,0,0), width=int(self.line_width))

class StanliHinge(StanliSymbol):
    """Accurate hinge/joint symbols from stanli"""
    
    def __init__(self, hinge_type: HingeType, size: float = 12.0):
        super().__init__()
        self.hinge_type = hinge_type
        self.size = size
    
    def draw(self, draw: ImageDraw.Draw, position: Tuple[float, float],
             rotation: float = 0, start_point: Optional[Tuple[float, float]] = None,
             end_point: Optional[Tuple[float, float]] = None, 
             orientation: int = 0, **kwargs):
        
        x, y = position
        r = self.size / 2
        
        if self.hinge_type == HingeType.FULL_JOINT:
            # Type 1: Full joint - simple circle
            bbox = [x-r, y-r, x+r, y+r]
            draw.ellipse(bbox, fill=(255,255,255), outline=(0,0,0), 
                        width=int(self.line_width))
        
        elif self.hinge_type == HingeType.HALF_JOINT:
            # Type 2: Half joint - half circle oriented along beam
            if start_point and end_point:
                self._draw_half_joint(draw, position, start_point, end_point, 
                                    orientation, r)
        
        elif self.hinge_type == HingeType.SHEAR_JOINT:
            # Type 3: Shear joint - parallel lines allowing shear
            cos_r = math.cos(math.radians(rotation))
            sin_r = math.sin(math.radians(rotation))
            
            offset = r * 0.6
            length = r * 1.2
            
            # Two parallel lines
            for dy in [-offset/2, offset/2]:
                x1 = x - length/2 * cos_r + dy * sin_r
                y1 = y - length/2 * sin_r - dy * cos_r
                x2 = x + length/2 * cos_r + dy * sin_r
                y2 = y + length/2 * sin_r - dy * cos_r
                
                draw.line([(x1, y1), (x2, y2)], fill=(0,0,0), width=int(self.line_width))
        
        elif self.hinge_type == HingeType.NORMAL_FORCE_JOINT:
            # Type 4: Normal force joint - perpendicular lines
            cos_r = math.cos(math.radians(rotation))
            sin_r = math.sin(math.radians(rotation))
            
            length = r * 1.2
            
            # Perpendicular lines
            x1 = x - length/2 * cos_r
            y1 = y - length/2 * sin_r
            x2 = x + length/2 * cos_r
            y2 = y + length/2 * sin_r
            
            draw.line([(x1, y1), (x2, y2)], fill=(0,0,0), width=int(self.line_width))
            
            x3 = x - length/2 * sin_r
            y3 = y + length/2 * cos_r
            x4 = x + length/2 * sin_r
            y4 = y - length/2 * cos_r
            
            draw.line([(x3, y3), (x4, y4)], fill=(0,0,0), width=int(self.line_width))
        
        elif self.hinge_type == HingeType.STIFF_CORNER:
            # Type 5: Stiff corner - corner reinforcement symbol
            if start_point and end_point:
                self._draw_stiff_corner(draw, position, start_point, end_point, r)
    
    def _draw_half_joint(self, draw: ImageDraw.Draw, center: Tuple[float, float],
                        start_point: Tuple[float, float], end_point: Tuple[float, float],
                        orientation: int, radius: float):
        """Draw half joint oriented along beam direction"""
        x, y = center
        x1, y1 = start_point
        x2, y2 = end_point
        
        # Calculate beam direction
        dx1, dy1 = x1 - x, y1 - y
        dx2, dy2 = x2 - x, y2 - y
        
        # Average direction for arc orientation
        avg_angle = math.atan2(dy1 + dy2, dx1 + dx2)
        
        if orientation == 0:
            # Half circle on "bottom" (characteristic fiber side)
            start_angle = math.degrees(avg_angle) - 90
            end_angle = start_angle + 180
        else:
            # Half circle on "top"
            start_angle = math.degrees(avg_angle) + 90
            end_angle = start_angle + 180
        
        bbox = [x-radius, y-radius, x+radius, y+radius]
        draw.arc(bbox, start_angle, end_angle, fill=(0,0,0), width=int(self.line_width))
    
    def _draw_stiff_corner(self, draw: ImageDraw.Draw, center: Tuple[float, float],
                          start_point: Tuple[float, float], end_point: Tuple[float, float],
                          size: float):
        """Draw stiff corner reinforcement"""
        x, y = center
        x1, y1 = start_point
        x2, y2 = end_point
        
        # Vectors from center to points
        v1x, v1y = x1 - x, y1 - y
        v2x, v2y = x2 - x, y2 - y
        
        # Normalize
        len1 = math.sqrt(v1x**2 + v1y**2)
        len2 = math.sqrt(v2x**2 + v2y**2)
        
        if len1 > 0 and len2 > 0:
            v1x, v1y = v1x/len1, v1y/len1
            v2x, v2y = v2x/len2, v2y/len2
            
            # Corner reinforcement arc
            corner_size = size * 0.8
            p1 = (x + v1x * corner_size, y + v1y * corner_size)
            p2 = (x + v2x * corner_size, y + v2y * corner_size)
            
            draw.arc([x-corner_size, y-corner_size, x+corner_size, y+corner_size],
                    math.degrees(math.atan2(v1y, v1x)), 
                    math.degrees(math.atan2(v2y, v2x)),
                    fill=(0,0,0), width=int(self.line_width*2))

class StanliLoad(StanliSymbol):
    """Load symbols from stanli"""
    
    def __init__(self, load_type: LoadType, length: float = 30.0):
        super().__init__()
        self.load_type = load_type
        self.length = length
    
    def draw(self, draw: ImageDraw.Draw, position: Tuple[float, float],
             rotation: float = 0, length_override: Optional[float] = None,
             distance: float = 0, **kwargs):
        
        x, y = position
        arrow_length = length_override or self.length
        
        if self.load_type == LoadType.SINGLE_LOAD:
            # Type 1: Single force arrow
            self._draw_arrow(draw, position, rotation, arrow_length, distance)
        
        elif self.load_type == LoadType.MOMENT_CLOCKWISE:
            # Type 2: Clockwise moment
            self._draw_moment_arc(draw, position, rotation, arrow_length, True)
        
        elif self.load_type == LoadType.MOMENT_COUNTER:
            # Type 3: Counter-clockwise moment
            self._draw_moment_arc(draw, position, rotation, arrow_length, False)
    
    def _draw_arrow(self, draw: ImageDraw.Draw, center: Tuple[float, float],
                   rotation: float, length: float, distance: float):
        """Draw force arrow"""
        x, y = center
        
        # Arrow start point (offset by distance)
        start_x = x + distance * math.cos(math.radians(rotation + 90))
        start_y = y + distance * math.sin(math.radians(rotation + 90))
        
        # Arrow end point
        end_x = start_x + length * math.cos(math.radians(rotation))
        end_y = start_y + length * math.sin(math.radians(rotation))
        
        # Draw arrow shaft
        draw.line([(start_x, start_y), (end_x, end_y)], fill=(0,0,0), 
                 width=int(self.line_width))
        
        # Arrow head
        head_length = length * 0.3
        head_angle = 25  # degrees
        
        head1_x = end_x - head_length * math.cos(math.radians(rotation - head_angle))
        head1_y = end_y - head_length * math.sin(math.radians(rotation - head_angle))
        
        head2_x = end_x - head_length * math.cos(math.radians(rotation + head_angle))
        head2_y = end_y - head_length * math.sin(math.radians(rotation + head_angle))
        
        draw.polygon([(end_x, end_y), (head1_x, head1_y), (head2_x, head2_y)],
                    fill=(0,0,0))
    
    def _draw_moment_arc(self, draw: ImageDraw.Draw, center: Tuple[float, float],
                        rotation: float, radius: float, clockwise: bool):
        """Draw moment arc with arrow"""
        x, y = center
        
        # Draw arc
        bbox = [x-radius, y-radius, x+radius, y+radius]
        
        if clockwise:
            start_angle = rotation
            end_angle = rotation + 270
        else:
            start_angle = rotation + 270
            end_angle = rotation + 540  # More than 360 for counter-clockwise
        
        draw.arc(bbox, start_angle, end_angle, fill=(0,0,0), width=int(self.line_width))
        
        # Add arrow head at end
        arrow_angle = end_angle if clockwise else start_angle
        arrow_x = x + radius * math.cos(math.radians(arrow_angle))
        arrow_y = y + radius * math.sin(math.radians(arrow_angle))
        
        # Small arrow head
        head_size = radius * 0.2
        head_angle1 = arrow_angle + (15 if clockwise else -15)
        head_angle2 = arrow_angle + (-15 if clockwise else 15)
        
        head1_x = arrow_x + head_size * math.cos(math.radians(head_angle1))
        head1_y = arrow_y + head_size * math.sin(math.radians(head_angle1))
        
        head2_x = arrow_x + head_size * math.cos(math.radians(head_angle2))
        head2_y = arrow_y + head_size * math.sin(math.radians(head_angle2))
        
        draw.polygon([(arrow_x, arrow_y), (head1_x, head1_y), (head2_x, head2_y)],
                    fill=(0,0,0))