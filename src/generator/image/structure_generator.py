import random
import math
from typing import List, Tuple, Optional

from data.generator_class import Beam, Hinge, Node, Load, Structure, SupportType
from src.generator.image.stanli_symbols import BeamType, SupportType, HingeType, LoadType
from src.generator.image.renderer import StanliRenderer



class StructuralSystemGenerator:
    """Generates realistic structural systems"""
    
    def __init__(self):
        self.grid_spacing = 80.0
        self.structure_types = [
            "simple_beam",
            "cantilever",
            "continuous_beam",
            "frame",
            "hinge_triangle"
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

    def _count_support_reactions(self, nodes: List[Node]) -> int:
        """Count total number of reaction forces from supports."""
        reaction_count = 0
        for n in nodes:
            if not n.support_type:
                continue
            if n.support_type == SupportType.FESTE_EINSPANNUNG:
                reaction_count += 3  # Fx, Fy, M
            elif n.support_type in (SupportType.FESTLAGER, SupportType.LOSLAGER):
                reaction_count += 2  # Fx, Fy (or Fy and constrained direction)
            elif n.support_type == SupportType.GLEITLAGER:
                reaction_count += 1  # One direction only
            elif n.support_type in (SupportType.FEDER, SupportType.TORSIONSFEDER):
                reaction_count += 1  # Elastic constraint
        return reaction_count
    
    def _ensure_stable_supports(self, nodes: List[Node]) -> None:
        """Ensure structure has at least one fixed support or equivalent."""
        has_fixed = any(n.support_type == SupportType.FESTE_EINSPANNUNG for n in nodes)
        support_nodes = [n for n in nodes if n.support_type]
        
        if not support_nodes:
            # No supports at all - add one fixed support
            if nodes:
                nodes[0].support_type = SupportType.FESTE_EINSPANNUNG
            return
        
        # Ensure at least 3 reactions total for 2D stability
        reactions = self._count_support_reactions(nodes)
        
        if reactions < 3:
            # Upgrade supports to ensure stability
            for n in support_nodes:
                if reactions >= 3:
                    break
                if n.support_type == SupportType.LOSLAGER:
                    n.support_type = SupportType.FESTLAGER
                    reactions += 0  # Already counted 2
                elif n.support_type == SupportType.GLEITLAGER:
                    n.support_type = SupportType.FESTLAGER
                    reactions += 1
        
        # Avoid all floating bearings (mechanism)
        if not has_fixed and all(n.support_type == SupportType.LOSLAGER for n in support_nodes):
            # Convert first support to fixed bearing
            support_nodes[0].support_type = SupportType.FESTLAGER


    def _assign_support_rotations(self, nodes: List[Node], beams: List[Beam]) -> None:
        """Assign node.rotation for supports to point OUTWARD from structure."""
        # Build adjacency map: node_id -> list of (connected_node_id, beam_angle)
        connected: dict[int, list[Tuple[int, float]]] = {n.id: [] for n in nodes}
        node_map = {n.id: n for n in nodes}
        
        for b in beams:
            n1 = node_map[b.node1_id]
            n2 = node_map[b.node2_id]
            
            # Angle FROM n1 TO n2
            dx = n2.position[0] - n1.position[0]
            dy = n2.position[1] - n1.position[1]
            angle_to_n2 = math.degrees(math.atan2(dy, dx))
            angle_to_n1 = (angle_to_n2 + 180) % 360
            
            connected[n1.id].append((n2.id, angle_to_n2))
            connected[n2.id].append((n1.id, angle_to_n1))

        for n in nodes:
            # Only assign rotation to nodes with supports
            if not n.support_type:
                n.rotation = 0.0
                continue
            
            # Mode-based rotation assignment
            if self.support_orientation_mode == 'vertical':
                n.rotation = 0.0
                continue
            
            if self.support_orientation_mode == 'random':
                n.rotation = random.uniform(0, 360)
                continue
            
            # Auto or beam_aligned modes
            connections = connected.get(n.id, [])
            
            if not connections:
                # Isolated node - point downward
                n.rotation = 0.0
                continue
            
            if len(connections) == 1:
                # Single connection - support points AWAY from beam
                _, beam_angle = connections[0]
                # Support extends perpendicular and away from structure
                # If beam goes right (0°), support points down (90°)
                # If beam goes up (90°), support points left (180°)
                outward_angle = (beam_angle + 180) % 360
                n.rotation = outward_angle
                
            else:
                # Multiple connections - calculate centroid of neighbors
                neighbor_positions = []
                for neighbor_id, _ in connections:
                    if neighbor_id in node_map:
                        neighbor_positions.append(node_map[neighbor_id].position)
                
                if neighbor_positions:
                    # Average position of neighbors (structure centroid direction)
                    avg_x = sum(p[0] for p in neighbor_positions) / len(neighbor_positions)
                    avg_y = sum(p[1] for p in neighbor_positions) / len(neighbor_positions)
                    
                    # Vector FROM neighbors centroid TO current node (outward direction)
                    dx = n.position[0] - avg_x
                    dy = n.position[1] - avg_y
                    
                    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                        # Degenerate case - use average beam direction
                        angles = [angle for _, angle in connections]
                        sx = sum(math.cos(math.radians(a)) for a in angles)
                        sy = sum(math.sin(math.radians(a)) for a in angles)
                        avg_angle = math.degrees(math.atan2(sy, sx))
                        n.rotation = (avg_angle + 180) % 360
                    else:
                        # Support points away from structure center
                        outward_angle = math.degrees(math.atan2(dy, dx))
                        n.rotation = outward_angle
                else:
                    n.rotation = 0.0
            
            # Special handling for specific support types
            if self.support_orientation_mode == 'auto':
                # For bottom supports (y near max), prefer vertical
                # For side supports, keep calculated angle
                connections_angles = [angle for _, angle in connections]
                
                # If all beams are nearly horizontal, use vertical support
                if all(abs(a % 180) < 15 or abs(a % 180 - 180) < 15 for a in connections_angles):
                    n.rotation = 0.0
            
            # Add small jitter for realism
            jitter = random.uniform(-self.support_random_jitter_deg / 2,
                                   self.support_random_jitter_deg / 2)
            n.rotation = (n.rotation + jitter) % 360

    def generate_structure(self, image_size: Tuple[int, int] = (800, 600)) -> Structure:
        """Generate a random structural system"""
        structure_type = random.choice(self.structure_types)
        
        if structure_type == 'simple_beam':
            return self._generate_simple_beam(image_size)
        elif structure_type == 'cantilever':
            return self._generate_cantilever(image_size)
        elif structure_type == 'simple_FACHWERK':
            return self._generate_simple_FACHWERK(image_size)
        elif structure_type == 'frame':
            return self._generate_frame(image_size)
        elif structure_type == 'continuous_beam':
            return self._generate_continuous_beam(image_size)
        elif structure_type == 'hinge_triangle':
            return self._generate_hinge_triangle(image_size)
        else:
            return self._generate_component_frame(image_size)
    
    def _get_centered_coords(self, local_coords: List[Tuple[float, float]], 
                           image_size: Tuple[int, int]) -> List[Tuple[float, float]]:
        """
        Return coordinates as-is. Normalization is handled by GeometryProcessor.
        This method kept for backward compatibility but no longer does centering.
        """
        return local_coords
    def _align_support_rotation(self, node, neighbor):
        dx = neighbor.position[0] - node.position[0]
        dy = neighbor.position[1] - node.position[1]
        angle = math.degrees(math.atan2(dy, dx))
        return (angle + 90) % 360

        
    def _generate_simple_beam(self, image_size):
        L = random.randint(3, 8) * self.grid_spacing
        coords = [(0, 0), (L, 0)]
        centered = self._get_centered_coords(coords, image_size)

        nodes = [Node(i, xy) for i, xy in enumerate(centered)]
        beams = [Beam(0, 0, 1, BeamType.BIEGUNG_MIT_FASER)]

        # Supports at boundaries - ensure stability
        nodes[0].support_type = SupportType.FESTLAGER
        nodes[1].support_type = SupportType.LOSLAGER
        
        # Validate and fix if needed
        self._ensure_stable_supports(nodes)

        # Loads
        loads = self._generate_point_and_distributed_loads(nodes, beams)
        
        # Assign support rotations
        self._assign_support_rotations(nodes, beams)

        return Structure(nodes, beams, [], loads)

    
    def _generate_cantilever(self, image_size: Tuple[int, int]) -> Structure:
        """Generate a cantilever beam"""
        length = random.uniform(3, 5) * self.grid_spacing

        local_coords = [(0, 0), (length, 0)]
        centered_coords = self._get_centered_coords(local_coords, image_size)

        nodes = [
            Node(0, centered_coords[0], SupportType.FESTE_EINSPANNUNG),
            Node(1, centered_coords[1])
        ]

        beams = [
            Beam(0, 0, 1, BeamType.BIEGUNG_MIT_FASER)
        ]

        hinges = [] 

        loads = [
            Load(0, 1, LoadType.EINZELLAST, 270)
        ]

        self._assign_support_rotations(nodes, beams)
        return Structure(nodes, beams, hinges, loads)

    def _generate_simple_FACHWERK(self, image_size: Tuple[int, int]) -> Structure:
        """Generate a simple FACHWERK (Pratt / Howe / Warren)"""
        FACHWERK_type = random.choice(['pratt', 'howe', 'warren'])
        span = random.uniform(5, 7) * self.grid_spacing
        height = random.uniform(2, 3) * self.grid_spacing
        num_panels = random.randint(4, 6)

        nodes = []
        local_coords = []

        # Bottom chord
        for i in range(num_panels + 1):
            x = i * span / num_panels
            local_coords.append((x, 0))

        if FACHWERK_type in ('pratt', 'howe'):
            # Top chord nodes between bottom chord joints
            for i in range(num_panels):
                x = (i + 0.5) * span / num_panels
                local_coords.append((x, height))
        elif FACHWERK_type == 'warren':
            # Warren FACHWERK: alternating peak nodes only
            for i in range(1, num_panels):
                x = i * span / num_panels
                y = height if i % 2 == 1 else 0  # Alternate high/low
                if y > 0:  # Only add if it's a peak node
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
                support_type = SupportType.FESTLAGER
            elif i == bottom_count - 1:
                support_type = SupportType.LOSLAGER
            nodes.append(Node(i, c, support_type))

        beams = []
        bid = 0
        # Bottom chord
        for i in range(bottom_count - 1):
            beams.append(Beam(bid, bottom_indices[i], bottom_indices[i + 1], BeamType.FACHWERK)); bid += 1

        if FACHWERK_type in ('pratt', 'howe'):
            # Top chord sequential
            for i in range(len(top_indices) - 1):
                beams.append(Beam(bid, top_indices[i], top_indices[i + 1], BeamType.FACHWERK)); bid += 1
            # Verticals / diagonals
            for i, top_idx in enumerate(top_indices):
                # Vertical to nearest bottom nodes
                left_bottom = bottom_indices[i]
                right_bottom = bottom_indices[i + 1]
                beams.append(Beam(bid, left_bottom, top_idx, BeamType.FACHWERK)); bid += 1
                beams.append(Beam(bid, right_bottom, top_idx, BeamType.FACHWERK)); bid += 1

            # Diagonals direction depends on type
            # Simplified approach: connect alternating bottoms to adjacent top
            for i in range(len(top_indices) - 1):
                if FACHWERK_type == 'pratt':
                    beams.append(Beam(bid, bottom_indices[i + 1], top_indices[i], BeamType.FACHWERK)); bid += 1
                else:  # howe
                    beams.append(Beam(bid, bottom_indices[i], top_indices[i], BeamType.FACHWERK)); bid += 1
        else:  # Warren
            # Warren FACHWERK: proper triangular connections
            for i in range(len(top_indices)):
                top_idx = top_indices[i]
                # Connect to surrounding bottom nodes to form triangles
                if i < len(bottom_indices) - 1:
                    beams.append(Beam(bid, bottom_indices[i], top_idx, BeamType.FACHWERK)); bid += 1
                if i + 1 < len(bottom_indices):
                    beams.append(Beam(bid, bottom_indices[i + 1], top_idx, BeamType.FACHWERK)); bid += 1

        hinges = [Hinge(i, i, HingeType.VOLLGELENK) for i in range(len(nodes))]
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
            Beam(0, 0, 2, BeamType.BIEGUNG_MIT_FASER),
            Beam(1, 1, 3, BeamType.BIEGUNG_MIT_FASER),
            Beam(2, 2, 3, BeamType.BIEGUNG_MIT_FASER),
        ]
        
        hinges = [
            # Stiff corners are always present for a rigid frame
            Hinge(0, 2, HingeType.BIEGESTEIFE_ECKE, start_node_id=0, end_node_id=3),
            Hinge(1, 3, HingeType.BIEGESTEIFE_ECKE, start_node_id=1, end_node_id=2)
        ]
        
        base_supports = [SupportType.FESTE_EINSPANNUNG, SupportType.FESTLAGER]
        
        # Left support (Node 0)
        left_support = random.choice(base_supports)
        nodes[0].support_type = left_support
        if left_support == SupportType.FESTLAGER:
            hinges.append(Hinge(len(hinges), 0, HingeType.VOLLGELENK))

        # Right support (Node 1)
        right_support = random.choice(base_supports)
        nodes[1].support_type = right_support
        if right_support == SupportType.FESTLAGER:
            hinges.append(Hinge(len(hinges), 1, HingeType.VOLLGELENK))
            
        loads = [
            Load(0, 2, LoadType.EINZELLAST, 0),
            Load(1, 3, LoadType.EINZELLAST, 270)
        ]
        
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
                st = SupportType.FESTLAGER
            elif i == len(centered_coords) - 1:
                st = SupportType.LOSLAGER
            else:
                st = SupportType.FESTLAGER
            nodes.append(Node(i, coord, st))

        beams = []
        hinges = []
        beam_id = 0

        internal_hinge_node: Optional[int] = None
        if insert_internal_hinge:
            # Pick an interior support (avoid ends)
            internal_hinge_node = random.randint(2, len(nodes) - 3)
            hinges.append(Hinge(len(hinges), internal_hinge_node, HingeType.VOLLGELENK))

        # Create beam segments; if internal hinge -> still continuous visually but determinate segments
        for i in range(len(nodes) - 1):
            beams.append(Beam(beam_id, i, i + 1, BeamType.BIEGUNG_MIT_FASER))
            beam_id += 1

        # End hinges (only if supports are bearings, not fixed)
        if nodes[0].support_type == SupportType.FESTLAGER:
            hinges.append(Hinge(len(hinges), 0, HingeType.VOLLGELENK))
        if nodes[-1].support_type in (SupportType.FESTLAGER, SupportType.LOSLAGER):
            hinges.append(Hinge(len(hinges), len(nodes) - 1, HingeType.VOLLGELENK))

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
                support_type = random.choice([SupportType.FESTE_EINSPANNUNG, SupportType.FESTLAGER, SupportType.LOSLAGER])
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
                beams.append(Beam(beam_id, n1, n2, BeamType.BIEGUNG_MIT_FASER)); beam_id += 1

        # Beams / floor girders
        for s in range(1, stories + 1):
            for b in range(bays):
                n1 = node_index(b, s)
                n2 = node_index(b + 1, s)
                beams.append(Beam(beam_id, n1, n2, BeamType.BIEGUNG_MIT_FASER)); beam_id += 1

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
                    beams.append(Beam(beam_id, node_index(b, top_row), node_index(b + 2, top_row), BeamType.BIEGUNG_MIT_FASER)); beam_id += 1

        # Hinges at base bearings, some random beam-column joints
        for n in nodes:
            if n.support_type in (SupportType.FESTLAGER, SupportType.LOSLAGER):
                hinges.append(Hinge(len(hinges), n.id, HingeType.VOLLGELENK))
        # Random internal hinges to create partial releases
        for _ in range(random.randint(0, bays)):
            bcol = random.randint(0, bays)
            s = random.randint(1, stories - 1) if stories > 1 else 0
            n = node_index(bcol, s)
            hinges.append(Hinge(len(hinges), n, HingeType.VOLLGELENK))

        loads = self._generate_point_and_distributed_loads(nodes, beams, allow_horizontal=True, allow_moments=True)
        self._assign_support_rotations(nodes, beams)

        return Structure(nodes, beams, hinges, loads)
    def _generate_hinge_triangle(self, image_size):
        side = 3 * self.grid_spacing
        h = math.sqrt(3)/2 * side
        coords = [(0,0), (side,0), (side/2,h)]
        centered = self._get_centered_coords(coords, image_size)

        nodes = [Node(i, xy) for i, xy in enumerate(centered)]
        beams = [
            Beam(0, 0, 1, BeamType.BIEGUNG_MIT_FASER),
            Beam(1, 1, 2, BeamType.BIEGUNG_MIT_FASER),
            Beam(2, 2, 0, BeamType.BIEGUNG_MIT_FASER)
        ]
        hinges = [Hinge(i, i, HingeType.VOLLGELENK) for i in range(3)]

        # Attach supports at 2-3 vertices only (never just 1 for stability)
        num_supports = random.randint(2, 3)  # Changed from (1,2) to (2,3)
        support_nodes = random.sample(nodes, num_supports)
        for n in support_nodes:
            n.support_type = random.choice([SupportType.FESTLAGER, SupportType.FESTE_EINSPANNUNG])
            n.rotation = 270  # downward by default

        loads = self._generate_point_and_distributed_loads(nodes, beams)
        return Structure(nodes, beams, hinges, loads)

    
    def _generate_point_and_distributed_loads(self, nodes: List[Node], beams: List[Beam],
                                              vertical_only: bool = False,
                                              allow_horizontal: bool = False,
                                              allow_moments: bool = False) -> List[Load]:
        """Create structurally realistic loads based on node classification."""
        loads: List[Load] = []
        load_id = 0
        node_map = {n.id: n for n in nodes}
        
        # Build connectivity information
        node_connections = {n.id: [] for n in nodes}
        for b in beams:
            node_connections[b.node1_id].append(b.node2_id)
            node_connections[b.node2_id].append(b.node1_id)
        
        # Classify nodes by type
        support_nodes = set()
        free_end_nodes = set()
        joint_nodes = set()
        midspan_nodes = set()
        
        for n in nodes:
            num_connections = len(node_connections[n.id])
            
            if n.support_type:
                support_nodes.add(n.id)
            elif num_connections == 1:
                free_end_nodes.add(n.id)
            elif num_connections >= 3:
                joint_nodes.add(n.id)
            elif num_connections == 2:
                midspan_nodes.add(n.id)
        
        # Classify beams by orientation (vertical, horizontal, or inclined)
        horizontal_beams = []
        vertical_beams = []
        inclined_beams = []
        
        for b in beams:
            n1 = node_map[b.node1_id]
            n2 = node_map[b.node2_id]
            dx = abs(n2.position[0] - n1.position[0])
            dy = abs(n2.position[1] - n1.position[1])
            
            angle = math.degrees(math.atan2(dy, dx))
            if angle < 15:  # Nearly horizontal
                horizontal_beams.append(b)
            elif angle > 75:  # Nearly vertical
                vertical_beams.append(b)
            else:
                inclined_beams.append(b)
        
        # RULE 1: Never place loads on support nodes
        loadable_nodes = [n for n in nodes if n.id not in support_nodes]
        
        # RULE 2: Place vertical loads on horizontal beams (most common)
        if not vertical_only or True:  # Always consider vertical loads
            # Load at joint nodes on horizontal members (beam-column intersections)
            for node_id in joint_nodes:
                if node_id in support_nodes:
                    continue
                # Check if any horizontal beam connects here
                connected_beams = [b for b in beams 
                                 if (b.node1_id == node_id or b.node2_id == node_id)]
                has_horizontal = any(b in horizontal_beams for b in connected_beams)
                
                if has_horizontal and random.random() < 0.5:
                    loads.append(Load(load_id, node_id, LoadType.EINZELLAST, 270))
                    load_id += 1
            
            # Load at midspan of horizontal beams
            for node_id in midspan_nodes:
                if node_id in support_nodes:
                    continue
                connected_beams = [b for b in beams 
                                 if (b.node1_id == node_id or b.node2_id == node_id)]
                if any(b in horizontal_beams for b in connected_beams) and random.random() < 0.4:
                    loads.append(Load(load_id, node_id, LoadType.EINZELLAST, 270))
                    load_id += 1
        
        # RULE 3: Horizontal loads on column tops or free cantilever ends
        if allow_horizontal and not vertical_only:
            # Free end nodes (cantilevers, column tops)
            for node_id in free_end_nodes:
                if random.random() < self.p_horizontal_load:
                    # Determine direction based on connected beam orientation
                    connected = node_connections[node_id]
                    if connected:
                        neighbor = node_map[connected[0]]
                        current = node_map[node_id]
                        dx = current.position[0] - neighbor.position[0]
                        # Load points away from structure
                        angle = 0 if dx > 0 else 180
                    else:
                        angle = random.choice([0, 180])
                    
                    loads.append(Load(load_id, node_id, LoadType.EINZELLAST, angle))
                    load_id += 1
            
            # Top nodes of vertical members (columns)
            for b in vertical_beams:
                # Find the top node (larger Y in screen coords = lower position, so smaller Y is top)
                n1 = node_map[b.node1_id]
                n2 = node_map[b.node2_id]
                top_node_id = b.node1_id if n1.position[1] < n2.position[1] else b.node2_id
                
                if top_node_id not in support_nodes and random.random() < self.p_horizontal_load * 0.5:
                    angle = random.choice([0, 180])
                    loads.append(Load(load_id, top_node_id, LoadType.EINZELLAST, angle))
                    load_id += 1
        
        # RULE 4: Moment loads at specific locations (rare, structural significance)
        if allow_moments:
            # Moments at free cantilever ends
            for node_id in free_end_nodes:
                if random.random() < self.p_moment_load:
                    moment_type = random.choice([LoadType.MOMENT_UHRZEIGER, LoadType.MOMENT_GEGEN_UHRZEIGER])
                    loads.append(Load(load_id, node_id, moment_type, 0))
                    load_id += 1
        
        # RULE 5: Distributed loads (create intermediate points on beams)
        nodes_copy = nodes.copy()
        if random.random() < self.p_distributed_load and horizontal_beams:
            # Only apply distributed loads to horizontal beams
            num_beams = min(2, max(1, len(horizontal_beams) // 2))
            candidate_beams = random.sample(horizontal_beams, num_beams)
            
            for b in candidate_beams:
                n1 = node_map[b.node1_id]
                n2 = node_map[b.node2_id]
                count = random.randint(*self.distributed_points)
                
                for i in range(1, count - 1):
                    t = i / (count - 1)
                    x = n1.position[0] + t * (n2.position[0] - n1.position[0])
                    y = n1.position[1] + t * (n2.position[1] - n1.position[1])
                    
                    # Create intermediate node
                    new_node_id = len(nodes_copy)
                    new_node = Node(new_node_id, (x, y))
                    nodes_copy.append(new_node)
                    
                    # Vertical load
                    loads.append(Load(load_id, new_node_id, LoadType.EINZELLAST, 270))
                    load_id += 1
        
        # Update nodes list with new distributed load points
        nodes.extend(nodes_copy[len(nodes):])
        
        return loads
