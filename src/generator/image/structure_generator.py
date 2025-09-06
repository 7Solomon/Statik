import random
from tkinter import Image
from typing import List, Tuple

#from yaml import Node

from data.generator_class import Beam, Hinge, Node, Load, Structure
from src.generator.image.stanli_symbols import BeamType, SupportType, HingeType, LoadType
from src.generator.image.renderer import StanliRenderer



class StructuralSystemGenerator:
    """Generates realistic structural systems"""
    
    def __init__(self):
        self.grid_spacing = 80.0
        self.structure_types = [
            'simple_beam', 'cantilever', 'simple_truss', 
            'frame', 'arch', 'continuous_beam'
        ]
    
    def generate_structure(self, image_size: Tuple[int, int] = (800, 600)) -> Structure:
        """Generate a random structural system"""
        structure_type = random.choice(self.structure_types)
        
        if structure_type == 'simple_beam':
            return self._generate_simple_beam(image_size)
        elif structure_type == 'cantilever':
            return self._generate_cantilever(image_size)
        elif structure_type == 'simple_truss':
            return self._generate_simple_truss(image_size)
        elif structure_type == 'frame':
            return self._generate_frame(image_size)
        elif structure_type == 'arch':
            return self._generate_arch(image_size)
        else:  # continuous_beam
            return self._generate_continuous_beam(image_size)
    
    def _get_centered_coords(self, local_coords: List[Tuple[float, float]], 
                           image_size: Tuple[int, int]) -> List[Tuple[float, float]]:
        """Center coordinates within image bounds with margin"""
        if not local_coords:
            return []
        
        # Find bounds
        min_x = min(coord[0] for coord in local_coords)
        max_x = max(coord[0] for coord in local_coords)
        min_y = min(coord[1] for coord in local_coords)
        max_y = max(coord[1] for coord in local_coords)
        
        # Calculate dimensions
        width = max_x - min_x
        height = max_y - min_y
        
        # Add margins
        margin_x = image_size[0] * 0.1
        margin_y = image_size[1] * 0.1
        
        # Calculate scale to fit
        scale_x = (image_size[0] - 2 * margin_x) / width if width > 0 else 1
        scale_y = (image_size[1] - 2 * margin_y) / height if height > 0 else 1
        scale = min(scale_x, scale_y, 2.0)  # Max scale of 2
        
        # Center position
        center_x = image_size[0] / 2
        center_y = image_size[1] / 2
        local_center_x = (min_x + max_x) / 2
        local_center_y = (min_y + max_y) / 2
        
        # Transform coordinates
        centered_coords = []
        for x, y in local_coords:
            new_x = center_x + (x - local_center_x) * scale
            new_y = center_y + (y - local_center_y) * scale
            centered_coords.append((new_x, new_y))
        
        return centered_coords
    
    def _generate_simple_beam(self, image_size: Tuple[int, int]) -> Structure:
        """Generate a simple supported beam"""
        span = random.uniform(4, 6) * self.grid_spacing
        
        # Local coordinates
        local_coords = [(0, 0), (span, 0)]
        centered_coords = self._get_centered_coords(local_coords, image_size)
        
        nodes = [
            Node(0, centered_coords[0], SupportType.FIXED_BEARING),
            Node(1, centered_coords[1], SupportType.FLOATING_BEARING)
        ]
        
        beams = [
            Beam(0, 0, 1, BeamType.BENDING_WITH_FIBER)
        ]
        
        hinges = [
            Hinge(0, 0, HingeType.FULL_JOINT),
            Hinge(1, 1, HingeType.FULL_JOINT)
        ]
        
        # Add random load
        load_position = random.choice([0, 1])
        load_rotation = random.choice([270, 90])  # Up or down
        loads = [
            Load(0, load_position, LoadType.SINGLE_LOAD, load_rotation)
        ]
        
        return Structure(nodes, beams, hinges, loads)
    
    def _generate_cantilever(self, image_size: Tuple[int, int]) -> Structure:
        """Generate a cantilever beam"""
        length = random.uniform(3, 5) * self.grid_spacing
        
        local_coords = [(0, 0), (length, 0)]
        centered_coords = self._get_centered_coords(local_coords, image_size)
        
        nodes = [
            Node(0, centered_coords[0], SupportType.FIXED_SUPPORT),
            Node(1, centered_coords[1])
        ]
        
        beams = [
            Beam(0, 0, 1, BeamType.BENDING_WITH_FIBER)
        ]
        
        hinges = [
            Hinge(0, 0, HingeType.FULL_JOINT)
        ]
        
        # Load at free end
        loads = [
            Load(0, 1, LoadType.SINGLE_LOAD, 270)
        ]
        
        return Structure(nodes, beams, hinges, loads)
    
    def _generate_simple_truss(self, image_size: Tuple[int, int]) -> Structure:
        """Generate a simple truss"""
        span = random.uniform(5, 7) * self.grid_spacing
        height = random.uniform(2, 3) * self.grid_spacing
        num_panels = random.randint(3, 5)
        
        nodes = []
        local_coords = []
        
        # Bottom chord
        for i in range(num_panels + 1):
            x = i * span / num_panels
            local_coords.append((x, 0))
        
        # Top chord (apex at center)
        for i in range(num_panels + 1):
            x = i * span / num_panels
            # Triangular profile
            if i <= num_panels // 2:
                y = height * (i / (num_panels // 2))
            else:
                y = height * ((num_panels - i) / (num_panels // 2))
            local_coords.append((x, y))
        
        centered_coords = self._get_centered_coords(local_coords, image_size)
        
        # Create nodes
        for i, coord in enumerate(centered_coords):
            support_type = None
            if i == 0:  # Left support
                support_type = SupportType.FIXED_BEARING
            elif i == num_panels:  # Right support
                support_type = SupportType.FLOATING_BEARING
            
            nodes.append(Node(i, coord, support_type))
        
        beams = []
        beam_id = 0
        
        # Bottom chord
        for i in range(num_panels):
            beams.append(Beam(beam_id, i, i + 1, BeamType.BENDING_WITH_FIBER))
            beam_id += 1
        
        # Top chord
        for i in range(num_panels):
            top_start = num_panels + 1 + i
            top_end = num_panels + 1 + i + 1
            beams.append(Beam(beam_id, top_start, top_end, BeamType.BENDING_WITH_FIBER))
            beam_id += 1
        
        # Web members (verticals and diagonals)
        for i in range(num_panels + 1):
            bottom_node = i
            top_node = num_panels + 1 + i
            beams.append(Beam(beam_id, bottom_node, top_node, BeamType.TRUSS))
            beam_id += 1
        
        # Diagonal members
        for i in range(num_panels):
            bottom_left = i
            top_right = num_panels + 2 + i
            if top_right < len(nodes):
                beams.append(Beam(beam_id, bottom_left, top_right, BeamType.TRUSS))
                beam_id += 1
        
        # Hinges at supports and apex
        hinges = [
            Hinge(0, 0, HingeType.FULL_JOINT),
            Hinge(1, num_panels, HingeType.FULL_JOINT)
        ]
        
        # Add hinge at apex if it exists
        apex_node = num_panels + 1 + num_panels // 2
        if apex_node < len(nodes):
            hinges.append(Hinge(2, apex_node, HingeType.FULL_JOINT))
        
        # Loads on top chord
        loads = []
        load_id = 0
        for i in range(1, num_panels):  # Skip supports
            top_node = num_panels + 1 + i
            if top_node < len(nodes):
                loads.append(Load(load_id, top_node, LoadType.SINGLE_LOAD, 270))
                load_id += 1
        
        return Structure(nodes, beams, hinges, loads)
    
    def _generate_frame(self, image_size: Tuple[int, int]) -> Structure:
        """Generate a simple frame structure"""
        width = random.uniform(4, 6) * self.grid_spacing
        height = random.uniform(3, 4) * self.grid_spacing
        
        local_coords = [
            (0, 0),        # Bottom left
            (width, 0),    # Bottom right
            (0, height),   # Top left
            (width, height) # Top right
        ]
        
        centered_coords = self._get_centered_coords(local_coords, image_size)
        
        nodes = [
            Node(0, centered_coords[0], SupportType.FIXED_SUPPORT),  # Fixed base
            Node(1, centered_coords[1], SupportType.FIXED_BEARING), # Pinned base
            Node(2, centered_coords[2]),  # Top left
            Node(3, centered_coords[3])   # Top right
        ]
        
        beams = [
            Beam(0, 0, 2, BeamType.BENDING_WITH_FIBER),  # Left column
            Beam(1, 1, 3, BeamType.BENDING_WITH_FIBER),  # Right column
            Beam(2, 2, 3, BeamType.BENDING_WITH_FIBER),  # Beam
        ]
        
        hinges = [
            Hinge(0, 0, HingeType.FULL_JOINT),
            Hinge(1, 1, HingeType.FULL_JOINT),
            # Frame corners - could be rigid or hinged
            Hinge(2, 2, HingeType.STIFF_CORNER, start_node_id=0, end_node_id=3),
            Hinge(3, 3, HingeType.STIFF_CORNER, start_node_id=1, end_node_id=2)
        ]
        
        # Horizontal load on frame
        loads = [
            Load(0, 2, LoadType.SINGLE_LOAD, 0),  # Horizontal load
            Load(1, 3, LoadType.SINGLE_LOAD, 270) # Vertical load
        ]
        
        return Structure(nodes, beams, hinges, loads)
    
    def _generate_arch(self, image_size: Tuple[int, int]) -> Structure:
        """Generate a simple arch structure"""
        span = random.uniform(5, 7) * self.grid_spacing
        rise = random.uniform(1.5, 2.5) * self.grid_spacing
        num_segments = random.randint(5, 8)
        
        nodes = []
        local_coords = []
        
        # Generate arch curve
        for i in range(num_segments + 1):
            x = i * span / num_segments
            # Parabolic arch
            y = rise * (1 - ((2 * x / span - 1) ** 2))
            local_coords.append((x, y))
        
        centered_coords = self._get_centered_coords(local_coords, image_size)
        
        # Create nodes
        for i, coord in enumerate(centered_coords):
            support_type = None
            if i == 0:
                support_type = SupportType.FIXED_BEARING
            elif i == num_segments:
                support_type = SupportType.FLOATING_BEARING
            
            nodes.append(Node(i, coord, support_type))
        
        # Arch segments
        beams = []
        for i in range(num_segments):
            beams.append(Beam(i, i, i + 1, BeamType.BENDING_WITH_FIBER))
        
        # Hinges
        hinges = [
            Hinge(0, 0, HingeType.FULL_JOINT),
            Hinge(1, num_segments, HingeType.FULL_JOINT)
        ]
        
        # Add hinge at crown
        crown = num_segments // 2
        hinges.append(Hinge(2, crown, HingeType.FULL_JOINT))
        
        # Loads
        loads = []
        for i in range(1, num_segments):
            if random.random() < 0.6:  # 60% chance of load
                loads.append(Load(len(loads), i, LoadType.SINGLE_LOAD, 270))
        
        return Structure(nodes, beams, hinges, loads)
    
    def _generate_continuous_beam(self, image_size: Tuple[int, int]) -> Structure:
        """Generate a continuous beam over multiple supports"""
        num_spans = random.randint(2, 4)
        span_length = random.uniform(3, 4) * self.grid_spacing
        
        local_coords = []
        for i in range(num_spans + 1):
            x = i * span_length
            local_coords.append((x, 0))
        
        centered_coords = self._get_centered_coords(local_coords, image_size)
        
        nodes = []
        for i, coord in enumerate(centered_coords):
            support_type = None
            if i == 0 or i == len(centered_coords) - 1:
                support_type = SupportType.FLOATING_BEARING
            else:
                support_type = SupportType.FIXED_BEARING
            
            nodes.append(Node(i, coord, support_type))
        
        # Continuous beam segments
        beams = []
        for i in range(num_spans):
            beams.append(Beam(i, i, i + 1, BeamType.BENDING_WITH_FIBER))
        
        # Hinges at end supports only
        hinges = [
            Hinge(0, 0, HingeType.FULL_JOINT),
            Hinge(1, len(nodes) - 1, HingeType.FULL_JOINT)
        ]
        
        # Intermediate supports are rigid (no hinges) to show continuity
        for i in range(1, len(nodes) - 1):
            hinges.append(Hinge(len(hinges), i, HingeType.FULL_JOINT))
        
        # Distributed loads
        loads = []
        for i in range(len(nodes)):
            if random.random() < 0.5:  # 50% chance
                loads.append(Load(len(loads), i, LoadType.SINGLE_LOAD, 270))
        
        return Structure(nodes, beams, hinges, loads)