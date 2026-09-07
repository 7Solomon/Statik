from PIL import Image, ImageDraw
from typing import Tuple, Union, Optional

from src.models.image_models import ImageSystem, ImageNode, ImageMember, ImageLoad
from src.plugins.generator.image.annotations import AnnotationRenderer
from src.plugins.generator.image.placement import (
    coerce_load,
    coerce_support,
    compute_placements,
)
from src.plugins.generator.image.style import RenderStyle
from src.plugins.generator.image.stanli_symbols import (
    DETECTABLE_HINGES,
    DETECTABLE_LOADS,
    DETECTABLE_SUPPORTS,
    BeamType,
    HingeType,
    LoadType,
    StanliBeam,
    StanliHinge,
    StanliLoad,
    StanliSupport,
    SupportType,
)

class StanliRenderer:
    """Renderer for ImageSystem (pixel-space)."""

    def __init__(self, config):
        self.image_size = config.image_size
        self.background_color = config.background_color
        self.load_arrow_length_px = getattr(config, "load_arrow_length_px", 40.0)

    def create_image(self, style: Optional[RenderStyle] = None) -> Image.Image:
        paper = style.paper if style else self.background_color
        return Image.new('RGB', self.image_size, tuple(paper))

    def render_structure(self, system: ImageSystem) -> Image.Image:
        style = getattr(system, 'style', None)
        img = self.create_image(style)
        draw = ImageDraw.Draw(img)

        self.draw_members(draw, system, style)
        # Symbols come from the same placement list the label writer uses, so a
        # rendered symbol and its YOLO box can never disagree.
        placements = compute_placements(system, self.load_arrow_length_px)
        for placement in placements:
            placement.draw(draw)

        # Annotation goes on last and is never labelled - see annotations.py.
        if style is not None:
            AnnotationRenderer(style).draw(draw, system, placements, self.image_size)
        return img

    def draw_members(self, draw: ImageDraw.Draw, system: ImageSystem,
                     style: Optional[RenderStyle] = None):
        nodes = {n.id: n for n in getattr(system, 'nodes', [])}
        for member in getattr(system, 'members', []):
            n1 = nodes.get(member.start_node_id)
            n2 = nodes.get(member.end_node_id)
            if not n1 or not n2:
                continue
            btype = getattr(member, 'beam_type', None) or BeamType.FACHWERK
            if isinstance(btype, str):
                btype = self._safe_beam_enum(btype)
            beam = StanliBeam(btype).apply_style(style)
            beam.draw(draw, (n1.pixel_x, n1.pixel_y), (n2.pixel_x, n2.pixel_y))

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------

    def _safe_beam_enum(self, beam_str: str) -> BeamType:
        try:
            return BeamType[str(beam_str).split(".")[-1].upper()]
        except KeyError:
            return BeamType.FACHWERK

    def _safe_support_enum(self, support_str: str) -> SupportType:
        """Convert ANY support string -> valid SupportType."""
        return coerce_support(support_str) or SupportType.FREIES_ENDE

    def _safe_load_enum(self, load_str: str) -> LoadType:
        """Convert ANY load string -> valid LoadType."""
        return coerce_load(load_str) or LoadType.EINZELLAST

    # ---------------------------------------------------------
    # DRAWING WRAPPERS
    # ---------------------------------------------------------

    def draw_beam(self, draw: ImageDraw.Draw, beam_type: BeamType, 
                  start_pos: Tuple[float, float], end_pos: Tuple[float, float], 
                  rounded_start: bool = False, rounded_end: bool = False):
        beam = StanliBeam(beam_type)
        beam.draw(draw, start_pos, end_pos, rounded_start, rounded_end)

    def draw_support(self, draw: ImageDraw.Draw, support_type: SupportType, 
                     position: Tuple[float, float], rotation: float = 0.0):
        StanliSupport(support_type).draw(draw, position, rotation)

    def draw_hinge(self, draw: ImageDraw.Draw, hinge_type: HingeType, 
                   position: Tuple[float, float], rotation: float = 0.0):
        StanliHinge(hinge_type).draw(draw, position, rotation)

    def draw_load(self, draw: ImageDraw.Draw, load_type: LoadType, 
                  position: Tuple[float, float], rotation: float = 0.0, 
                  length: float = 40.0, distance: float = 0.0):
        StanliLoad(load_type).draw(draw, position, rotation, length, distance)

    # ---------------------------------------------------------
    # DEBUG / GALLERY
    # ---------------------------------------------------------

    def show_symbol_galleries(self):
        """Interactive single-window gallery to switch categories."""
        import matplotlib.pyplot as plt

        tile_size = (220, 220)
        center = (tile_size[0] // 2, tile_size[1] // 2)

        def new_img():
            return Image.new('RGB', tile_size, self.background_color)

        def draw_support_symbol(img, enum_member):
            d = ImageDraw.Draw(img)
            d.line([(20, center[1]), (tile_size[0] - 20, center[1])], fill=(0, 0, 0), width=2)
            self.draw_support(d, enum_member, center, rotation=0)

        def draw_hinge_symbol(img, enum_member):
            d = ImageDraw.Draw(img)
            # Release symbols are oriented along their member, so show the member.
            start = (30, center[1])
            end = (tile_size[0] - 30, center[1])
            d.line([start, end], fill=(0, 0, 0), width=2)
            self.draw_hinge(d, enum_member, center, rotation=0)

        def draw_beam_symbol(img, enum_member):
            d = ImageDraw.Draw(img)
            self.draw_beam(d, enum_member, (25, center[1]), (tile_size[0] - 25, center[1]),
                           rounded_start=True, rounded_end=True)

        def draw_load_symbol(img, enum_member):
            d = ImageDraw.Draw(img)
            if enum_member.name.startswith("MOMENT"):
                self.draw_load(d, enum_member, center, rotation=0, length=90)
            else:
                self.draw_load(d, enum_member, center, rotation=270, length=110)

        categories = [
            ("Supports", list(DETECTABLE_SUPPORTS), draw_support_symbol),
            ("Hinges",   list(DETECTABLE_HINGES),   draw_hinge_symbol),
            ("Beams",    list(BeamType),            draw_beam_symbol),
            ("Loads",    list(DETECTABLE_LOADS),    draw_load_symbol),
        ]

        state = {"cat": 0}

        max_items = max(len(members) for _, members, _ in categories)
        cols = 4
        rows = (max_items + cols - 1) // cols
        if rows == 0: rows = 1

        fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.3, rows * 2.3))
        fig.canvas.manager.set_window_title("Stanli Symbols Gallery")

        if hasattr(axes, 'flatten'):
            axes_flat = axes.flatten()
        else:
            axes_flat = [axes] if not isinstance(axes, list) else axes

        def render():
            cat_name, members, drawer = categories[state["cat"]]
            for ax in axes_flat:
                ax.clear()
                ax.axis("off")
            for i, m in enumerate(members):
                if i >= len(axes_flat): break
                img = new_img()
                drawer(img, m)
                axes_flat[i].imshow(img)
                axes_flat[i].set_title(m.name, fontsize=8)
            fig.suptitle(
                f"{cat_name} ({state['cat']+1}/{len(categories)})  |  "
                "Keys: <-/-> or A/D switch category, 1-4 jump, Q quit",
                fontsize=11
            )
            fig.canvas.draw_idle()

        def change_category(delta):
            state["cat"] = (state["cat"] + delta) % len(categories)
            render()

        def set_category(idx):
            state["cat"] = idx % len(categories)
            render()

        def on_key(e):
            k = e.key.lower()
            if k in ("q", "escape"):
                plt.close(fig)
                return
            if k in ("right", "d"):
                change_category(1)
            elif k in ("left", "a"):
                change_category(-1)
            elif k in ("1", "2", "3", "4"):
                set_category(int(k) - 1)

        fig.canvas.mpl_connect("key_press_event", on_key)
        render()
        plt.tight_layout()
        plt.show()

# Helper for external usage
def render_structure_to_image(system: ImageSystem, image_size: Tuple[int, int] = (800, 600)) -> Image.Image:
    class SimpleConfig:
        def __init__(self):
            self.image_size = image_size
            self.background_color = (255, 255, 255)
            self.load_arrow_length_px = 40.0
    
    return StanliRenderer(SimpleConfig()).render_structure(system)
