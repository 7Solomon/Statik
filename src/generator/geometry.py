import numpy as np
from typing import Tuple

from models.generator_class import Structure, Node
from src.generator.image.stanli_symbols import StanliSupport, StanliHinge, StanliLoad

# Maximum symbol extents (in mm, converted to pixels in normalization)
MAX_SUPPORT_EXTENT_MM = 25.0  # Largest support (FEDER + hatching)
MAX_LOAD_EXTENT_MM = 15.0     # Load arrows
MAX_HINGE_EXTENT_MM = 8.0     # Hinge circles
PX_PER_MM = 4.0

def mm(x: float) -> float:
    return x * PX_PER_MM


class GeometryProcessor:
    """Handles coordinate transformations and geometric operations on Structure objects."""

    @staticmethod
    def get_structure_bounds_with_symbols(structure: Structure) -> Tuple[float, float, float, float]:
        """
        Calculate the true bounding box of the structure including all rendered symbols.
        Returns (min_x, min_y, max_x, max_y) in pixel coordinates.
        """
        if not structure or not structure.nodes:
            return (0, 0, 0, 0)
        
        all_bounds = []
        
        # Get bounds for each node (considering support symbols)
        for node in structure.nodes:
            if node.support_type:
                # Get actual support symbol bounding box
                support_symbol = StanliSupport(node.support_type)
                rotation = getattr(node, 'rotation', 0.0)
                bbox = support_symbol.get_bbox(node.position, rotation)
                all_bounds.append(bbox)
            else:
                # Just the node position (with small padding for visual node dot)
                x, y = node.position
                padding = 5.0  # pixels for node dots
                all_bounds.append((x - padding, y - padding, x + padding, y + padding))
        
        # Get bounds for hinges
        for hinge in getattr(structure, 'hinges', []):
            node = structure.get_node_by_id(hinge.node_id)
            if not node:
                continue
            
            # Find connected nodes for hinges that need them
            p_init = None
            p_end = None
            for beam in structure.beams:
                if beam.node1_id == hinge.node_id:
                    p_end_node = structure.get_node_by_id(beam.node2_id)
                    if p_end_node:
                        p_end = p_end_node.position
                elif beam.node2_id == hinge.node_id:
                    p_init_node = structure.get_node_by_id(beam.node1_id)
                    if p_init_node:
                        p_init = p_init_node.position
            
            hinge_symbol = StanliHinge(hinge.hinge_type)
            rotation = getattr(hinge, 'rotation', 0.0)
            bbox = hinge_symbol.get_bbox(node.position, rotation, p_init, p_end)
            all_bounds.append(bbox)
        
        # Get bounds for loads
        for load in getattr(structure, 'loads', []):
            node = structure.get_node_by_id(load.node_id)
            if not node:
                continue
            
            load_symbol = StanliLoad(load.load_type)
            rotation = getattr(load, 'rotation', 0.0)
            length = getattr(load, 'length', None)
            distance = getattr(load, 'distance', None)
            arc_angle = getattr(load, 'arc_angle', None)
            
            bbox = load_symbol.get_bbox(node.position, rotation, length, distance, arc_angle)
            all_bounds.append(bbox)
        
        # Combine all bounding boxes
        if not all_bounds:
            # Fallback to node positions only
            positions = [n.position for n in structure.nodes]
            x_vals = [p[0] for p in positions]
            y_vals = [p[1] for p in positions]
            return (min(x_vals), min(y_vals), max(x_vals), max(y_vals))
        
        min_x = min(bbox[0] for bbox in all_bounds)
        min_y = min(bbox[1] for bbox in all_bounds)
        max_x = max(bbox[2] for bbox in all_bounds)
        max_y = max(bbox[3] for bbox in all_bounds)
        
        return (min_x, min_y, max_x, max_y)

    @staticmethod
    def normalize_coordinates(
        structure: Structure,
        target_size: Tuple[int, int],
        margin: float = 0.1,
        in_place: bool = False
    ) -> Structure:
        """
        Normalize node coordinates to fit inside target_size (width, height) with margin.
        Now uses actual symbol bounds instead of estimated padding.
        """
        if not structure or not structure.nodes:
            return structure

        # Get actual bounds including all symbols
        min_x, min_y, max_x, max_y = GeometryProcessor.get_structure_bounds_with_symbols(structure)

        width = max_x - min_x
        height = max_y - min_y

        # Guard against degenerate extents
        if width == 0 or height == 0:
            if in_place:
                return structure
            return Structure(
                nodes=[Node(id=n.id, position=n.position, support_type=n.support_type) for n in structure.nodes],
                beams=structure.beams,
                hinges=structure.hinges,
                loads=structure.loads
            )

        tgt_w, tgt_h = target_size
        
        # User-specified margin
        margin_x = tgt_w * margin
        margin_y = tgt_h * margin
        
        # Ensure margins don't exceed half the image size
        margin_x = min(margin_x, tgt_w * 0.4)
        margin_y = min(margin_y, tgt_h * 0.4)

        scale_x = (tgt_w - 2 * margin_x) / width
        scale_y = (tgt_h - 2 * margin_y) / height
        scale = min(scale_x, scale_y)

        center_x = tgt_w / 2
        center_y = tgt_h / 2
        struct_cx = (min_x + max_x) / 2
        struct_cy = (min_y + max_y) / 2

        def transform(pos):
            x, y = pos
            new_x = center_x + (x - struct_cx) * scale
            new_y = center_y + (y - struct_cy) * scale
            return (new_x, new_y)

        if in_place:
            for node in structure.nodes:
                node.position = transform(node.position)
            return structure

        new_nodes = [
            Node(id=n.id, position=transform(n.position), support_type=n.support_type, rotation=getattr(n, 'rotation', 0.0))
            for n in structure.nodes
        ]

        return Structure(
            nodes=new_nodes,
            beams=structure.beams,
            hinges=structure.hinges,
            loads=structure.loads
        )

    @staticmethod
    def apply_perspective_transform(
        structure: Structure,
        strength: float,
        image_size: Tuple[int, int],
        in_place: bool = False
    ) -> Structure:
        """
        Apply a simple pseudo‑perspective horizontal squeeze dependent on vertical position.
        This keeps topology (IDs) intact. Hinges / loads remain attached via node IDs.
        """
        if strength <= 0 or not structure.nodes:
            return structure

        img_w, img_h = image_size
        max_factor = max(0.0, 1.0 - strength * 0.1)

        def transform(pos):
            x, y = pos
            t = y / img_h  # 0 at top, 1 at bottom
            # Interpolate squeeze across height
            x_factor = 1.0 - (1.0 - max_factor) * t
            return (x * x_factor, y)

        if in_place:
            for node in structure.nodes:
                node.position = transform(node.position)
            return structure

        new_nodes = [
            Node(id=n.id, position=transform(n.position), support_type=n.support_type, rotation=getattr(n, 'rotation', 0.0))
            for n in structure.nodes
        ]

        return Structure(
            nodes=new_nodes,
            beams=structure.beams,
            hinges=structure.hinges,
            loads=structure.loads
        )
    
    @staticmethod
    def validate_bounds(
        structure: Structure,
        image_size: Tuple[int, int],
        padding: float = 10.0
    ) -> bool:
        """
        Check if all structure elements (including symbols) are within image bounds.
        Returns True if all elements are valid, False otherwise.
        """
        if not structure or not structure.nodes:
            return True
        
        w, h = image_size
        
        # Get actual bounds including symbols
        min_x, min_y, max_x, max_y = GeometryProcessor.get_structure_bounds_with_symbols(structure)
        
        # Check if bounds exceed image with padding
        if min_x < padding or max_x > w - padding:
            return False
        if min_y < padding or max_y > h - padding:
            return False
        
        return True
