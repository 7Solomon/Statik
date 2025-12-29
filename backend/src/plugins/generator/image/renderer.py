from PIL import Image, ImageDraw
from typing import Tuple
import matplotlib.pyplot as plt

from src.models.image_models import ImageSystem, ImageNode, ImageMember, ImageLoad

from src.plugins.generator.image.stanli_symbols import (
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
        self.symbols = {
            'beams': {},
            'supports': {},
            'hinges': {},
            'loads': {},
        }

    def create_image(self) -> Image.Image:
        return Image.new('RGB', self.image_size, self.background_color)

    def render_structure(self, system: ImageSystem) -> Image.Image:
        img = self.create_image()
        draw = ImageDraw.Draw(img)

        # 1. BEAMS (safe)
        for member in getattr(system, 'members', []):
            try:
                n1 = next((n for n in getattr(system, 'nodes', []) if n.id == member.start_node_id), None)
                n2 = next((n for n in getattr(system, 'nodes', []) if n.id == member.end_node_id), None)
                if n1 and n2:
                    self.draw_beam(draw, BeamType.FACHWERK, 
                                (n1.pixel_x, n1.pixel_y), 
                                (n2.pixel_x, n2.pixel_y))
            except:
                continue

        # 2. SUPPORTS (bulletproof enum mapping)
        for node in getattr(system, 'nodes', []):
            support_type = getattr(node, "support_type", "free")
            if support_type and support_type != "free":
                try:
                    stype = self._safe_support_enum(support_type)
                    self.draw_support(draw, stype, (node.pixel_x, node.pixel_y))
                except:
                    pass  # Skip bad supports

        # 3. LOADS (bulletproof enum mapping)
        for load in getattr(system, 'loads', []):
            try:
                node = next((n for n in getattr(system, 'nodes', []) if n.id == load.node_id), None) if load.node_id else None
                pos = (node.pixel_x, node.pixel_y) if node else (load.pixel_x, load.pixel_y)
                
                ltype = self._safe_load_enum(getattr(load, "load_type", "EINZELLAST"))
                angle = getattr(load, "angle_deg", 270.0)
                
                self.draw_load(draw, ltype, pos, angle)
            except:
                pass  # Skip bad loads

        return img

    def _safe_support_enum(self, support_str: str) -> SupportType:
        """Convert ANY support string → valid SupportType."""
        mapping = {
            'fixed': SupportType.FESTE_EINSPANNUNG,
            'pinned': SupportType.FESTLAGER,
            'roller': SupportType.LOSLAGER,
            'festlager': SupportType.FESTLAGER,
            'loslager': SupportType.LOSLAGER,
            'feste_einspannung': SupportType.FESTE_EINSPANNUNG,
            'gleitlager': SupportType.GLEITLAGER,
        }
        key = support_str.lower()
        return mapping.get(key, SupportType.FESTLAGER)  # FESTLAGER as default

    def _safe_load_enum(self, load_str: str) -> LoadType:
        """Convert ANY load string → valid LoadType."""
        mapping = {
            'force_point': LoadType.EINZELLAST,
            'force': LoadType.EINZELLAST,
            'moment': LoadType.MOMENT_UHRZEIGER,
            'einzelLast': LoadType.EINZELLAST,
        }
        key = load_str.lower()
        return mapping.get(key, LoadType.EINZELLAST)  # EINZELLAST as default


    # --------- Primitive wrappers around Stanli symbols ----------

    def draw_beam(
        self,
        draw: ImageDraw.Draw,
        beam_type: BeamType,
        start_pos: Tuple[float, float],
        end_pos: Tuple[float, float],
        rounded_start: bool = False,
        rounded_end: bool = False,
    ):
        beam = StanliBeam(beam_type)
        beam.draw(draw, start_pos, end_pos, rounded_start, rounded_end)

    def draw_support(
        self,
        draw: ImageDraw.Draw,
        support_type: SupportType,
        position: Tuple[float, float],
        rotation: float = 0.0,
    ):
        support = StanliSupport(support_type)
        support.draw(draw, position, rotation)

    def draw_hinge(
        self,
        draw: ImageDraw.Draw,
        hinge_type: HingeType,
        position: Tuple[float, float],
        rotation: float = 0.0,
    ):
        hinge = StanliHinge(hinge_type)
        hinge.draw(draw, position)

    def draw_load(
        self,
        draw: ImageDraw.Draw,
        load_type: LoadType,
        position: Tuple[float, float],
        rotation: float = 0.0,
        length: float = 40.0,
        distance: float = 0.0,
    ):
        load = StanliLoad(load_type)
        load.draw(draw, position, rotation, length, distance)

  
    def show_symbol_galleries(self):
        """Interactive single-window gallery to switch categories."""

        tile_size = (220, 220)
        center = (tile_size[0] // 2, tile_size[1] // 2)

        def new_img():
            return Image.new('RGB', tile_size, self.background_color)

        def draw_support_symbol(img, enum_member):
            d = ImageDraw.Draw(img)
            self.draw_support(d, enum_member, center, rotation=0, size=80)

        def draw_hinge_symbol(img, enum_member):
            d = ImageDraw.Draw(img)
            start = (30, center[1])
            end = (tile_size[0] - 30, center[1])
            d.line([start, end], fill=(0, 0, 0), width=3)
            self.draw_hinge(d, enum_member, center, rotation=0,
                            start_point=start, end_point=end,
                            orientation=0, size=60)

        def draw_beam_symbol(img, enum_member):
            d = ImageDraw.Draw(img)
            self.draw_beam(d, enum_member, (25, center[1]), (tile_size[0] - 25, center[1]),
                           rounded_start=True, rounded_end=True, width=16)

        def draw_load_symbol(img, enum_member):
            d = ImageDraw.Draw(img)
            if enum_member.name.startswith("MOMENT"):
                self.draw_load(d, enum_member, center, rotation=0, length=90)
            else:
                self.draw_load(d, enum_member, center, rotation=270, length=110)

        categories = [
            ("Supports", list(SupportType), draw_support_symbol),
            ("Hinges",   list(HingeType),   draw_hinge_symbol),
            ("Beams",    list(BeamType),    draw_beam_symbol),
            ("Loads",    list(LoadType),    draw_load_symbol),
        ]

        state = {"cat": 0}

        # Single persistent figure sized for the largest category
        max_items = max(len(members) for _, members, _ in categories)
        cols = 4
        rows = (max_items + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.3, rows * 2.3))
        fig.canvas.manager.set_window_title("Stanli Symbols Gallery")
        axes_flat = axes.flatten()

        def render():
            cat_name, members, drawer = categories[state["cat"]]

            # Clear all
            for ax in axes_flat:
                ax.clear()
                ax.axis("off")

            # Draw current category symbols
            for i, m in enumerate(members):
                img = new_img()
                drawer(img, m)
                axes_flat[i].imshow(img)
                axes_flat[i].set_title(m.name, fontsize=8)
                axes_flat[i].axis("off")

            fig.suptitle(
                f"{cat_name} ({state['cat']+1}/{len(categories)})  |  "
                "Keys: ←/→ or A/D switch category, 1-4 jump, Q quit",
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


def render_structure_to_image(system: ImageSystem,
                              image_size: Tuple[int, int] = (800, 600)) -> Image.Image:
    """Render an ImageSystem to PIL Image using StanliRenderer."""
    class SimpleConfig:
        def __init__(self):
            self.image_size = image_size
            self.background_color = (255, 255, 255)
            self.beam_width = 4
            self.support_size = 25
            self.node_radius = 8
            self.node_color = (50, 50, 200)

    config = SimpleConfig()
    renderer = StanliRenderer(config)
    return renderer.render_structure(system)
