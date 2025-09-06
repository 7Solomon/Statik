import numpy as np
from typing import Tuple

from data.generator_class import Structure, Node


class GeometryProcessor:
    """Handles coordinate transformations and geometric operations on Structure objects."""

    @staticmethod
    def normalize_coordinates(
        structure: Structure,
        target_size: Tuple[int, int],
        margin: float = 0.1,
        in_place: bool = False
    ) -> Structure:
        """
        Normalize node coordinates to fit inside target_size (width, height) with a margin.
        Only node positions are changed; beams, hinges, loads are preserved.
        """
        if not structure or not structure.nodes:
            return structure

        positions = [n.position for n in structure.nodes]
        x_vals = [p[0] for p in positions]
        y_vals = [p[1] for p in positions]

        min_x, max_x = min(x_vals), max(x_vals)
        min_y, max_y = min(y_vals), max(y_vals)

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
        margin_x = tgt_w * margin
        margin_y = tgt_h * margin

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
            Node(id=n.id, position=transform(n.position), support_type=n.support_type)
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
            Node(id=n.id, position=transform(n.position), support_type=n.support_type)
            for n in structure.nodes
        ]

        return Structure(
            nodes=new_nodes,
            beams=structure.beams,
            hinges=structure.hinges,
            loads=structure.loads
        )