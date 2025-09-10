import random
import math
from tkinter import Image
from typing import List, Tuple, Optional

from data.generator_class import Beam, Hinge, Node, Load, Structure, SupportType
from src.generator.image.stanli_symbols import BeamType, SupportType as SymbolSupportType, HingeType, LoadType
from src.generator.image.renderer import StanliRenderer



class StructuralSystemGenerator:
    """Generates realistic structural systems"""
    
    def __init__(self):
        self.grid_spacing = 80.0
        self.structure_types = [
            'simple_beam', 'cantilever', 'simple_truss', 
            'frame', 'arch', 'continuous_beam',
            'component_frame'  # new
        ]
        # Probabilities / tunables for component strategy
        self.max_stories = 4
        self.max_bays = 5
        self.p_add_story = 0.55
        self.p_add_bay = 0.65
        self.p_pitched_roof = 0.35
        self.p_horizontal_load = 0.25
        self.p_moment_load = 0.15
        self.p_distributed_load = 0.30
        self.distributed_points = (3, 6)
        self.p_internal_hinge_continuous = 0.40  # Gerber style
        self.p_beam_overhang = 0.35
        self.support_orientation_mode = 'auto'  # 'vertical' | 'beam_aligned' | 'auto' | 'random'
        self.support_random_jitter_deg = 10.0

    # --- new helper ---
    def _assign_support_rotations(self, nodes: List[Node], beams: List[Beam]) -> None:
        """Assign node.rotation for supports (and optionally all nodes)."""
        # Build adjacency
        connected: dict[int, list[float]] = {n.id: [] for n in nodes}
        for b in beams:
            n1 = next(nd for nd in nodes if nd.id == b.node1_id)
            n2 = next(nd for nd in nodes if nd.id == b.node2_id)
            dx = n2.position[0] - n1.position[0]
            dy = n2.position[1] - n1.position[1]
            angle = math.degrees(math.atan2(dy, dx))  # beam axis angle
            connected[n1.id].append(angle)
            connected[n2.id].append(angle)

        for n in nodes:
            if self.support_orientation_mode == 'vertical':
                n.rotation = 0.0
                continue
            if self.support_orientation_mode == 'random':
                base = 0.0
                n.rotation = base + random.uniform(-self.support_random_jitter_deg, self.support_random_jitter_deg)
                continue

            angles = connected.get(n.id, [])
            if not angles:
                n.rotation = 0.0
                continue

            # Average direction
            sx = sum(math.cos(math.radians(a)) for a in angles)
            sy = sum(math.sin(math.radians(a)) for a in angles)
            avg_angle = math.degrees(math.atan2(sy, sx))

            if self.support_orientation_mode == 'beam_aligned':
                n.rotation = avg_angle
            elif self.support_orientation_mode == 'auto':
                # If beams nearly horizontal keep vertical support, else align
                if any(abs(a) > 15 and abs(a - 180) > 15 for a in angles):
                    n.rotation = avg_angle
                else:
                    n.rotation = 0.0

            # Optional small jitter
            n.rotation += random.uniform(-self.support_random_jitter_deg/2,
                                         self.support_random_jitter_deg/2)

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
        elif structure_type == 'continuous_beam':
            return self._generate_continuous_beam(image_size)
        else:
            return self._generate_component_frame(image_size)
    
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
        """
        Generate a beam with randomized end conditions (simple, propped, or fixed).
        """
        # Overhang logic
        base_span = random.uniform(4, 6) * self.grid_spacing
        left_overhang = right_overhang = 0.0
        if random.random() < self.p_beam_overhang:
            left_overhang = random.uniform(0.3, 1.0) * self.grid_spacing
        if random.random() < self.p_beam_overhang:
            right_overhang = random.uniform(0.3, 1.0) * self.grid_spacing
        
        local_coords = [(-left_overhang, 0), (base_span + right_overhang, 0)]
        centered_coords = self._get_centered_coords(local_coords, image_size)
        
        nodes = [Node(0, centered_coords[0]), Node(1, centered_coords[1])]
        beams = [Beam(0, 0, 1, BeamType.BENDING_WITH_FIBER)]
        hinges = []
        
        support_conditions = random.choice(['simple', 'propped', 'fixed'])
        if support_conditions == 'simple':
            nodes[0].support_type = SupportType.FIXED_BEARING
            nodes[1].support_type = SupportType.FLOATING_BEARING
            #hinges.extend([Hinge(0, 0, HingeType.FULL_JOINT), Hinge(1, 1, HingeType.FULL_JOINT)])
        elif support_conditions == 'propped':
            nodes[0].support_type = SupportType.FIXED_SUPPORT
            nodes[1].support_type = SupportType.FLOATING_BEARING
            hinges.append(Hinge(0, 1, HingeType.FULL_JOINT))
        else:
            nodes[0].support_type = SupportType.FIXED_SUPPORT
            nodes[1].support_type = SupportType.FIXED_SUPPORT
        
        loads = self._generate_point_and_distributed_loads(nodes, beams, allow_horizontal=True, allow_moments=True)
        self._assign_support_rotations(nodes, beams)
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

        hinges = [] 

        loads = [
            Load(0, 1, LoadType.SINGLE_LOAD, 270)
        ]

        self._assign_support_rotations(nodes, beams)
        return Structure(nodes, beams, hinges, loads)

    def _generate_simple_truss(self, image_size: Tuple[int, int]) -> Structure:
        """Generate a simple truss (Pratt / Howe / Warren)"""
        truss_type = random.choice(['pratt', 'howe', 'warren'])
        span = random.uniform(5, 7) * self.grid_spacing
        height = random.uniform(2, 3) * self.grid_spacing
        num_panels = random.randint(4, 6)

        nodes = []
        local_coords = []

        # Bottom chord
        for i in range(num_panels + 1):
            x = i * span / num_panels
            local_coords.append((x, 0))

        if truss_type in ('pratt', 'howe'):
            # Top chord nodes between bottom chord joints
            for i in range(num_panels):
                x = (i + 0.5) * span / num_panels
                local_coords.append((x, height))
        elif truss_type == 'warren':
            # Alternate up/down to form triangles
            for i in range(1, num_panels):
                x = i * span / num_panels
                y = height if i % 2 else height * 0.15
                local_coords.append((x, y))

        centered = self._get_centered_coords(local_coords, image_size)
        total_nodes = len(centered)

        # Identify sets
        bottom_count = num_panels + 1
        bottom_indices = list(range(bottom_count))
        top_indices = list(range(bottom_count, total_nodes))

        for i, c in enumerate(centered):
            support_type = None
            if i == 0:
                support_type = SupportType.FIXED_BEARING
            elif i == bottom_count - 1:
                support_type = SupportType.FLOATING_BEARING
            nodes.append(Node(i, c, support_type))

        beams = []
        bid = 0
        # Bottom chord
        for i in range(bottom_count - 1):
            beams.append(Beam(bid, bottom_indices[i], bottom_indices[i + 1], BeamType.TRUSS)); bid += 1

        if truss_type in ('pratt', 'howe'):
            # Top chord sequential
            for i in range(len(top_indices) - 1):
                beams.append(Beam(bid, top_indices[i], top_indices[i + 1], BeamType.TRUSS)); bid += 1
            # Verticals / diagonals
            for i, top_idx in enumerate(top_indices):
                # Vertical to nearest bottom nodes
                left_bottom = bottom_indices[i]
                right_bottom = bottom_indices[i + 1]
                beams.append(Beam(bid, left_bottom, top_idx, BeamType.TRUSS)); bid += 1
                beams.append(Beam(bid, right_bottom, top_idx, BeamType.TRUSS)); bid += 1

            # Diagonals direction depends on type
            # Simplified approach: connect alternating bottoms to adjacent top
            for i in range(len(top_indices) - 1):
                if truss_type == 'pratt':
                    beams.append(Beam(bid, bottom_indices[i + 1], top_indices[i], BeamType.TRUSS)); bid += 1
                else:  # howe
                    beams.append(Beam(bid, bottom_indices[i], top_indices[i], BeamType.TRUSS)); bid += 1
        else:  # Warren
            # Connect zig-zag
            chain = bottom_indices + top_indices
            # Simpler approach: connect consecutive nodes across chords by geometry
            # Connect bottom to alternating top to form triangles
            for i in range(bottom_count - 1):
                if i < len(top_indices):
                    beams.append(Beam(bid, bottom_indices[i], top_indices[i], BeamType.TRUSS)); bid += 1
                if i - 1 >= 0 and i - 1 < len(top_indices):
                    beams.append(Beam(bid, bottom_indices[i + 1], top_indices[i - 1], BeamType.TRUSS)); bid += 1

        hinges = [Hinge(i, i, HingeType.FULL_JOINT) for i in range(len(nodes))]
        loads = self._generate_point_and_distributed_loads(nodes, beams, vertical_only=True)
        self._assign_support_rotations(nodes, beams)
        return Structure(nodes, beams, hinges, loads)
    
        
    def _generate_frame(self, image_size: Tuple[int, int]) -> Structure:
        """Original simple single-bay frame retained (could call component version)."""
        width = random.uniform(4, 6) * self.grid_spacing
        height = random.uniform(3, 4) * self.grid_spacing
        
        local_coords = [
            (0, 0), (width, 0), (0, height), (width, height)
        ]
        centered_coords = self._get_centered_coords(local_coords, image_size)
        
        nodes = [
            Node(0, centered_coords[0]), Node(1, centered_coords[1]),
            Node(2, centered_coords[2]), Node(3, centered_coords[3])
        ]
        
        beams = [
            Beam(0, 0, 2, BeamType.BENDING_WITH_FIBER),
            Beam(1, 1, 3, BeamType.BENDING_WITH_FIBER),
            Beam(2, 2, 3, BeamType.BENDING_WITH_FIBER),
        ]
        
        hinges = [
            # Stiff corners are always present for a rigid frame
            Hinge(0, 2, HingeType.STIFF_CORNER, start_node_id=0, end_node_id=3),
            Hinge(1, 3, HingeType.STIFF_CORNER, start_node_id=1, end_node_id=2)
        ]
        
        base_supports = [SupportType.FIXED_SUPPORT, SupportType.FIXED_BEARING]
        
        # Left support (Node 0)
        left_support = random.choice(base_supports)
        nodes[0].support_type = left_support
        if left_support == SupportType.FIXED_BEARING:
            hinges.append(Hinge(len(hinges), 0, HingeType.FULL_JOINT))

        # Right support (Node 1)
        right_support = random.choice(base_supports)
        nodes[1].support_type = right_support
        if right_support == SupportType.FIXED_BEARING:
            hinges.append(Hinge(len(hinges), 1, HingeType.FULL_JOINT))
            
        loads = [
            Load(0, 2, LoadType.SINGLE_LOAD, 0),
            Load(1, 3, LoadType.SINGLE_LOAD, 270)
        ]
        
        self._assign_support_rotations(nodes, beams)
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
        
        self._assign_support_rotations(nodes, beams)
        return Structure(nodes, beams, hinges, loads)

    def _generate_continuous_beam(self, image_size: Tuple[int, int]) -> Structure:
        """Generate a continuous beam over multiple supports (optionally Gerber)."""
        num_spans = random.randint(2, 4)
        span_length = random.uniform(3, 4) * self.grid_spacing

        # Optional internal hinge (Gerber) near one interior support
        insert_internal_hinge = num_spans >= 3 and random.random() < self.p_internal_hinge_continuous

        # Optional overhangs
        left_overhang = right_overhang = 0.0
        if random.random() < self.p_beam_overhang:
            left_overhang = random.uniform(0.5, 1.0) * self.grid_spacing
        if random.random() < self.p_beam_overhang:
            right_overhang = random.uniform(0.5, 1.0) * self.grid_spacing

        local_coords = [(-left_overhang, 0)]
        for i in range(1, num_spans + 1):
            local_coords.append((i * span_length, 0))
        local_coords.append((num_spans * span_length + right_overhang, 0))

        centered_coords = self._get_centered_coords(local_coords, image_size)

        nodes = []
        for i, coord in enumerate(centered_coords):
            if i == 0:
                st = SupportType.FIXED_BEARING
            elif i == len(centered_coords) - 1:
                st = SupportType.FLOATING_BEARING
            else:
                st = SupportType.FIXED_BEARING
            nodes.append(Node(i, coord, st))

        beams = []
        hinges = []
        beam_id = 0

        internal_hinge_node: Optional[int] = None
        if insert_internal_hinge:
            # Pick an interior support (avoid ends)
            internal_hinge_node = random.randint(2, len(nodes) - 3)
            hinges.append(Hinge(len(hinges), internal_hinge_node, HingeType.FULL_JOINT))

        # Create beam segments; if internal hinge -> still continuous visually but determinate segments
        for i in range(len(nodes) - 1):
            beams.append(Beam(beam_id, i, i + 1, BeamType.BENDING_WITH_FIBER))
            beam_id += 1

        # End hinges (if supports not fixed)
        hinges.append(Hinge(len(hinges), 0, HingeType.FULL_JOINT))
        hinges.append(Hinge(len(hinges), len(nodes) - 1, HingeType.FULL_JOINT))

        loads = self._generate_point_and_distributed_loads(nodes, beams, allow_horizontal=True, allow_moments=True)
        self._assign_support_rotations(nodes, beams)
        return Structure(nodes, beams, hinges, loads)
    
    def _generate_component_frame(self, image_size: Tuple[int, int]) -> Structure:
        """LEGO style multi-story multi-bay frame with optional pitched roof."""
        # Decide bays & stories
        bays = 1
        while bays < self.max_bays and random.random() < self.p_add_bay:
            bays += 1
        stories = 1
        while stories < self.max_stories and random.random() < self.p_add_story:
            stories += 1

        bay_width = random.uniform(2.5, 3.5) * self.grid_spacing
        story_height = random.uniform(2.5, 3.5) * self.grid_spacing

        # Generate node grid
        nodes: List[Node] = []
        local_coords: List[Tuple[float, float]] = []
        for s in range(stories + 1):
            y = s * story_height
            for b in range(bays + 1):
                x = b * bay_width
                local_coords.append((x, y))

        # Pitched roof (adjust top line)
        pitched = (stories >= 2 and random.random() < self.p_pitched_roof)
        if pitched:
            ridge_offset = (bays * bay_width) / 2
            for b in range(bays + 1):
                # index of top level node before centering
                idx = (stories) * (bays + 1) + b
                x, y = local_coords[idx]
                # simple triangular pitch
                distance = abs(x - ridge_offset)
                max_rise = story_height * random.uniform(0.3, 0.6)
                local_coords[idx] = (x, y + max(0, max_rise - (distance / ridge_offset) * max_rise))

        centered = self._get_centered_coords(local_coords, image_size)

        # Create nodes with supports at base
        for i, c in enumerate(centered):
            row = i // (bays + 1)
            support_type = None
            if row == 0:
                # Alternate fixed / bearing for base realism
                support_type = random.choice([SupportType.FIXED_SUPPORT, SupportType.FIXED_BEARING, SupportType.FLOATING_BEARING])
            nodes.append(Node(i, c, support_type))

        beams: List[Beam] = []
        hinges: List[Hinge] = []
        beam_id = 0

        def node_index(b, s):
            return s * (bays + 1) + b

        # Columns
        for b in range(bays + 1):
            for s in range(stories):
                n1 = node_index(b, s)
                n2 = node_index(b, s + 1)
                beams.append(Beam(beam_id, n1, n2, BeamType.BENDING_WITH_FIBER)); beam_id += 1

        # Beams / floor girders
        for s in range(1, stories + 1):
            for b in range(bays):
                n1 = node_index(b, s)
                n2 = node_index(b + 1, s)
                beams.append(Beam(beam_id, n1, n2, BeamType.BENDING_WITH_FIBER)); beam_id += 1

        # Add roof ridge beam if pitched
        if pitched:
            top_row = stories
            # optionally add diagonals (gable bracing)
            for b in range(bays):
                n1 = node_index(b, top_row)
                n2 = node_index(b + 1, top_row)
                # already added as beam above; optionally add hinge or change type
            # Optional top bracing (triangulation)
            if bays >= 2 and random.random() < 0.5:
                for b in range(bays - 1):
                    beams.append(Beam(beam_id, node_index(b, top_row), node_index(b + 2, top_row), BeamType.BENDING_WITH_FIBER)); beam_id += 1

        # Hinges at base bearings, some random beam-column joints
        for n in nodes:
            if n.support_type in (SupportType.FIXED_BEARING, SupportType.FLOATING_BEARING):
                hinges.append(Hinge(len(hinges), n.id, HingeType.FULL_JOINT))
        # Random internal hinges to create partial releases
        for _ in range(random.randint(0, bays)):
            bcol = random.randint(0, bays)
            s = random.randint(1, stories - 1) if stories > 1 else 0
            n = node_index(bcol, s)
            hinges.append(Hinge(len(hinges), n, HingeType.FULL_JOINT))

        loads = self._generate_point_and_distributed_loads(nodes, beams, allow_horizontal=True, allow_moments=True)
        self._assign_support_rotations(nodes, beams)

        return Structure(nodes, beams, hinges, loads)
    
    def _generate_point_and_distributed_loads(self, nodes: List[Node], beams: List[Beam],
                                              vertical_only: bool = False,
                                              allow_horizontal: bool = False,
                                              allow_moments: bool = False) -> List[Load]:
        """Create varied loads: vertical, horizontal, moments, pseudo-distributed."""
        loads: List[Load] = []
        load_id = 0

        # Node candidate list (exclude maybe base in some cases)
        for n in nodes:
            if random.random() < 0.35:
                angle = 270  # vertical downward
                if allow_horizontal and not vertical_only and random.random() < self.p_horizontal_load:
                    angle = random.choice([0, 180])  # horizontal
                loads.append(Load(load_id, n.id, LoadType.SINGLE_LOAD, angle))
                load_id += 1

            # Optional moment load (if enum provides)
            if allow_moments and random.random() < self.p_moment_load:
                moment_type = getattr(LoadType, 'MOMENT_CLOCKWISE', None)
                if moment_type:
                    loads.append(Load(load_id, n.id, moment_type, 0))
                    load_id += 1

        # Pseudo distributed: pick some beams and sprinkle loads
        if random.random() < self.p_distributed_load and beams:
            num_beams = max(1, len(beams) // 3)
            candidate_beams = random.sample(beams, num_beams)
            for b in candidate_beams:
                n1 = next(nd for nd in nodes if nd.id == b.node1_id)
                n2 = next(nd for nd in nodes if nd.id == b.node2_id)
                count = random.randint(*self.distributed_points)
                for i in range(1, count - 1):
                    t = i / (count - 1)
                    x = n1.position[0] + t * (n2.position[0] - n1.position[0])
                    y = n1.position[1] + t * (n2.position[1] - n1.position[1])
                    # Create synthetic intermediate node for load application
                    new_node_id = len(nodes)
                    nodes.append(Node(new_node_id, (x, y)))
                    angle = 270
                    loads.append(Load(load_id, new_node_id, LoadType.SINGLE_LOAD, angle))
                    load_id += 1
        return loads