from PIL import Image, ImageDraw
from typing import Tuple, Union, Optional
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

    def create_image(self) -> Image.Image:
        return Image.new('RGB', self.image_size, self.background_color)

    def render_structure(self, system: ImageSystem) -> Image.Image:
        img = self.create_image()
        draw = ImageDraw.Draw(img)

        # ---------------------------------------------------------
        # 1. BEAMS
        # ---------------------------------------------------------
        for member in getattr(system, 'members', []):
            try:
                n1 = next((n for n in getattr(system, 'nodes', []) if n.id == member.start_node_id), None)
                n2 = next((n for n in getattr(system, 'nodes', []) if n.id == member.end_node_id), None)
                
                if n1 and n2:
                    # Default to FACHWERK (standard line) or read from member
                    btype = BeamType.FACHWERK
                    if hasattr(member, 'beam_type') and member.beam_type:
                         # If it's a string, try to map it, otherwise assume it matches Enum
                         pass 

                    self.draw_beam(draw, btype, 
                                   (n1.pixel_x, n1.pixel_y), 
                                   (n2.pixel_x, n2.pixel_y))
            except Exception:
                continue

        # ---------------------------------------------------------
        # 2. NODES (Supports, Hinges, Connections)
        # ---------------------------------------------------------
        for node in getattr(system, 'nodes', []):
            is_occupied = False # Track if we drew something at this node

            # --- A. SUPPORTS ---
            support_val = getattr(node, "support_type", SupportType.FREIES_ENDE)
            
            # Convert string to Enum if necessary
            if isinstance(support_val, str):
                support_val = self._safe_support_enum(support_val)

            # Draw if it's a real support (not Free)
            if support_val and support_val != SupportType.FREIES_ENDE:
                try:
                    self.draw_support(draw, support_val, (node.pixel_x, node.pixel_y))
                    is_occupied = True
                except Exception:
                    pass

            # --- B. HINGES ---
            hinge_val = getattr(node, "hinge_type", None)
            if hinge_val:
                try:
                    # Convert string to Enum if necessary
                    if isinstance(hinge_val, str):
                         hinge_val = HingeType[hinge_val]
                    
                    self.draw_hinge(draw, hinge_val, (node.pixel_x, node.pixel_y))
                except Exception:
                    pass


        # ---------------------------------------------------------
        # 3. LOADS
        # ---------------------------------------------------------
        for load in getattr(system, 'loads', []):
            try:
                # Find position (Node vs Absolute)
                node = next((n for n in getattr(system, 'nodes', []) if n.id == load.node_id), None) if load.node_id else None
                pos = (node.pixel_x, node.pixel_y) if node else (load.pixel_x, load.pixel_y)
                
                # Get Enum
                load_val = getattr(load, "load_type", LoadType.EINZELLAST)
                if isinstance(load_val, str):
                    load_val = self._safe_load_enum(load_val)
                
                angle = getattr(load, "angle_deg", 270.0)
                
                self.draw_load(draw, load_val, pos, angle)
            except Exception:
                pass 

        return img

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------

    def _safe_support_enum(self, support_str: str) -> SupportType:
        """Convert ANY support string -> valid SupportType."""
        # Normalize
        key = support_str.upper()
        
        # Direct match check
        try:
            return SupportType[key]
        except KeyError:
            pass

        # Manual mappings for legacy/alternative names
        mapping = {
            'FIXED': SupportType.FESTE_EINSPANNUNG,
            'PINNED': SupportType.FESTLAGER,
            'ROLLER': SupportType.LOSLAGER,
            'FREE': SupportType.FREIES_ENDE,
            'NONE': SupportType.FREIES_ENDE,
        }
        return mapping.get(key, SupportType.FREIES_ENDE)

    def _safe_load_enum(self, load_str: str) -> LoadType:
        """Convert ANY load string -> valid LoadType."""
        key = load_str.upper()
        try:
            return LoadType[key]
        except KeyError:
            pass
            
        mapping = {
            'FORCE_POINT': LoadType.EINZELLAST,
            'FORCE': LoadType.EINZELLAST,
            'MOMENT': LoadType.MOMENT_UHRZEIGER,
            'DIST_UNIFORM': LoadType.STRECKENLAST
        }
        return mapping.get(key, LoadType.EINZELLAST)

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
        support = StanliSupport(support_type)
        support.draw(draw, position, rotation)

    def draw_hinge(self, draw: ImageDraw.Draw, hinge_type: HingeType, 
                   position: Tuple[float, float], rotation: float = 0.0):
        hinge = StanliHinge(hinge_type)
        hinge.draw(draw, position)

    def draw_load(self, draw: ImageDraw.Draw, load_type: LoadType, 
                  position: Tuple[float, float], rotation: float = 0.0, 
                  length: float = 40.0, distance: float = 0.0):
        load = StanliLoad(load_type)
        load.draw(draw, position, rotation, length, distance)

    # ---------------------------------------------------------
    # DEBUG / GALLERY
    # ---------------------------------------------------------

    def show_symbol_galleries(self):
        """Interactive single-window gallery to switch categories."""
        tile_size = (220, 220)
        center = (tile_size[0] // 2, tile_size[1] // 2)

        def new_img():
            return Image.new('RGB', tile_size, self.background_color)

        def draw_support_symbol(img, enum_member):
            if enum_member == SupportType.FREIES_ENDE: return # Skip blank
            d = ImageDraw.Draw(img)
            self.draw_support(d, enum_member, center, rotation=0)

        def draw_hinge_symbol(img, enum_member):
            d = ImageDraw.Draw(img)
            # Draw beam segment to show hinge context
            start = (30, center[1])
            end = (tile_size[0] - 30, center[1])
            d.line([start, end], fill=(0, 0, 0), width=3)
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
            ("Supports", [s for s in SupportType if s != SupportType.FREIES_ENDE], draw_support_symbol),
            ("Hinges",   list(HingeType),   draw_hinge_symbol),
            ("Beams",    list(BeamType),    draw_beam_symbol),
            ("Loads",    list(LoadType),    draw_load_symbol),
        ]

        state = {"cat": 0}

        # Matplotlib setup
        max_items = max(len(members) for _, members, _ in categories)
        cols = 4
        rows = (max_items + cols - 1) // cols
        
        # Guard against empty categories (e.g. only FREIES_ENDE)
        if rows == 0: rows = 1

        fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.3, rows * 2.3))
        fig.canvas.manager.set_window_title("Stanli Symbols Gallery")
        
        # Flatten axes handling for 1D or 2D arrays
        if hasattr(axes, 'flatten'):
            axes_flat = axes.flatten()
        else:
            axes_flat = [axes] if not isinstance(axes, list) else axes

        def render():
            cat_name, members, drawer = categories[state["cat"]]

            # Clear all
            for ax in axes_flat:
                ax.clear()
                ax.axis("off")

            # Draw current category symbols
            for i, m in enumerate(members):
                if i >= len(axes_flat): break
                img = new_img()
                drawer(img, m)
                axes_flat[i].imshow(img)
                axes_flat[i].set_title(m.name, fontsize=8)

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

# Helper for external usage
def render_structure_to_image(system: ImageSystem, image_size: Tuple[int, int] = (800, 600)) -> Image.Image:
    class SimpleConfig:
        def __init__(self):
            self.image_size = image_size
            self.background_color = (255, 255, 255)
    
    config = SimpleConfig()
    renderer = StanliRenderer(config)
    return renderer.render_structure(system)
