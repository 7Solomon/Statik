import copy
from dataclasses import replace
from typing import List, Optional, Tuple

from src.models.image_models import ImageLoad, ImageNode, ImageSystem
from src.plugins.generator.image.placement import compute_placements


class GeometryProcessor:
    @staticmethod
    def get_structure_bounds_with_symbols(
        structure: ImageSystem,
        load_arrow_length_px: float = 40.0,
    ) -> Tuple[float, float, float, float]:
        """Extent of everything that will be inked: members plus every symbol.

        Uses the same placement list as the renderer, so a symbol can no longer
        be missing from the bounds (hinges used to be, which is why they clipped
        at the frame edge).
        """
        if not structure or not structure.nodes:
            return (0.0, 0.0, 0.0, 0.0)

        bounds: List[Tuple[float, float, float, float]] = []

        # Members / bare nodes. Members are straight lines between nodes, so the
        # node positions alone cover them.
        for node in structure.nodes:
            pad = 3.0
            bounds.append((node.pixel_x - pad, node.pixel_y - pad,
                           node.pixel_x + pad, node.pixel_y + pad))

        for placement in compute_placements(structure, load_arrow_length_px):
            box = placement.bbox()
            if box is not None:
                bounds.append(box)

        return (
            min(b[0] for b in bounds),
            min(b[1] for b in bounds),
            max(b[2] for b in bounds),
            max(b[3] for b in bounds),
        )

    @staticmethod
    def normalize_coordinates(
        structure: ImageSystem,
        target_size: Tuple[int, int],
        margin: float = 0.1,
        in_place: bool = False,
        load_arrow_length_px: float = 40.0,
    ) -> ImageSystem:
        """Fit the structure inside `target_size`, leaving `margin` free at each edge.

        Runs twice on purpose. Symbols are drawn at a fixed pixel size while node
        positions get scaled, so the first pass' bounds - which include symbol
        extents measured *before* scaling - under-budget the symbols whenever the
        structure shrinks. The second pass measures the already-scaled system and
        corrects, which is what keeps supports from being clipped at the frame.
        """
        if not structure or not structure.nodes:
            return structure

        result = structure if in_place else copy.deepcopy(structure)
        tgt_w, tgt_h = target_size

        for _ in range(2):
            min_x, min_y, max_x, max_y = GeometryProcessor.get_structure_bounds_with_symbols(
                result, load_arrow_length_px=load_arrow_length_px
            )
            width = max_x - min_x
            height = max_y - min_y
            if width <= 0 or height <= 0:
                return result

            margin_x = min(tgt_w * margin, tgt_w * 0.4)
            margin_y = min(tgt_h * margin, tgt_h * 0.4)
            scale = min((tgt_w - 2 * margin_x) / width, (tgt_h - 2 * margin_y) / height)

            struct_cx = (min_x + max_x) / 2
            struct_cy = (min_y + max_y) / 2
            center_x, center_y = tgt_w / 2, tgt_h / 2

            def transform(x, y):
                return (center_x + (x - struct_cx) * scale,
                        center_y + (y - struct_cy) * scale)

            for node in result.nodes:
                node.pixel_x, node.pixel_y = transform(node.pixel_x, node.pixel_y)
            for load in result.loads:
                if not load.node_id:
                    load.pixel_x, load.pixel_y = transform(load.pixel_x, load.pixel_y)

            # Already inside the frame with room to spare - a second pass would
            # only nudge it by rounding error.
            if abs(scale - 1.0) < 0.02:
                break

        return result

    @staticmethod
    def validate_bounds(
        structure: ImageSystem,
        image_size: Tuple[int, int],
        padding: float = 0.0,
        load_arrow_length_px: float = 40.0,
    ) -> bool:
        """True when every inked pixel lands inside the frame."""
        if not structure or not structure.nodes:
            return True

        w, h = image_size
        min_x, min_y, max_x, max_y = GeometryProcessor.get_structure_bounds_with_symbols(
            structure, load_arrow_length_px=load_arrow_length_px
        )
        return (min_x >= padding and min_y >= padding
                and max_x <= w - padding and max_y <= h - padding)
