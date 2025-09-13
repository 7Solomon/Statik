from PIL import Image, ImageDraw
import numpy as np
from typing import Optional, Tuple, List
import matplotlib.pyplot as plt

from data.generator_class import Structure
from src.generator.image.stanli_symbols import BeamType, HingeType, LoadType, StanliBeam, StanliHinge, StanliLoad, StanliSupport, SupportType

class StanliRenderer:
    """Main renderer for stanli symbols"""
    
    def __init__(self, config):
        self.config = config
        self.image_size = config.image_size
        self.background_color = config.background_color
        self.symbols = {
            'beams': {},
            'supports': {},
            'hinges': {},
            'loads': {}
        }
    
    def create_image(self) -> Image.Image:
        """Create new image for drawing"""
        return Image.new('RGB', self.image_size, self.background_color)
    
    def render_structure(self, structure: Structure) -> Image.Image:
        """Main method expected by the pipeline - renders complete structure"""
        img = self.create_image()
        draw = ImageDraw.Draw(img)
        
        # Draw beams first
        for beam in structure.beams:
            node1 = structure.get_node_by_id(beam.node1_id)
            node2 = structure.get_node_by_id(beam.node2_id)
            
            if node1 and node2:
                self.draw_beam(
                    draw, beam.beam_type, 
                    node1.position, node2.position,
                    beam.rounded_start, beam.rounded_end,
                )

        # Draw hinges
        for hinge in structure.hinges:
            node = structure.get_node_by_id(hinge.node_id)
            if node:
                start_node = None
                end_node = None
                
                if hinge.start_node_id is not None:
                    start_node_obj = structure.get_node_by_id(hinge.start_node_id)
                    start_node = start_node_obj.position if start_node_obj else None
                
                if hinge.end_node_id is not None:
                    end_node_obj = structure.get_node_by_id(hinge.end_node_id)
                    end_node = end_node_obj.position if end_node_obj else None
                
                self.draw_hinge(
                    draw, hinge.hinge_type, node.position, 
                    hinge.rotation,
                )
        
        # Draw supports
        for node in structure.nodes:
            if node.support_type:
                support_rotation = getattr(node, 'rotation', 0) or 0

                self.draw_support(
                    draw, node.support_type, node.position, 
                    support_rotation,
                )
        
        
        # Draw loads
        for load in structure.loads:
            node = structure.get_node_by_id(load.node_id)
            if node:
                self.draw_load(
                    draw, load.load_type, node.position, 
                    load.rotation, 40.0 * load.magnitude
                )
        
        return img

    def draw_beam(self, draw: ImageDraw.Draw, beam_type: BeamType,
                  start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                  rounded_start: bool = False, rounded_end: bool = False,
                  #width: float = 4.0
                  ):
        """Draw beam of specified type"""
        beam = StanliBeam(beam_type)
        beam.draw(draw, start_pos, end_pos, rounded_start, rounded_end)
    
    def draw_support(self, draw: ImageDraw.Draw, support_type: SupportType,
                position: Tuple[float, float], rotation: float = 0,
                #size: float = 25.0
                ):
        """Draw support of specified type"""
        support = StanliSupport(support_type)
        support.draw(draw, position, rotation)
    
    def draw_hinge(self, draw: ImageDraw.Draw, hinge_type: HingeType,
                   position: Tuple[float, float], rotation: float = 0,
                   #start_point: Optional[Tuple[float, float]] = None,
                   #end_point: Optional[Tuple[float, float]] = None,
                   #orientation: int = 0, size: float = 15.0
                   ):
        """Draw hinge/joint of specified type"""
        hinge = StanliHinge(hinge_type)
        hinge.draw(draw, position)
    
    def draw_load(self, draw: ImageDraw.Draw, load_type: LoadType,
                  position: Tuple[float, float], rotation: float = 0,
                  length: float = 40.0, distance: float = 0
                  ):
        """Draw load of specified type"""
        load = StanliLoad(load_type)
        load.draw(draw, position, rotation, length, distance)
    
    ####
    ## DEBUG
    ####

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



###
# For debug
###

def render_structure_to_image(structure: Structure, 
                            image_size: Tuple[int, int] = (800, 600)) -> Image.Image:
    """Render a structure to PIL Image using StanliRenderer"""
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
    return renderer.render_structure(structure)