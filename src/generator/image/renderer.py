from PIL import Image, ImageDraw
import numpy as np
from typing import Optional, Tuple, List
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
                    width=self.config.beam_width
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
                    hinge.rotation, start_node, end_node, hinge.orientation,
                    size=self.config.node_radius * 2
                )
        
        # Draw supports
        for node in structure.nodes:
            if node.support_type:
                node_hinge = next((h for h in structure.hinges if h.node_id == node.id), None)
                hinge_radius = self.config.node_radius if node_hinge else None
                
                support_rotation = getattr(node, 'rotation', 0) or 0

                self.draw_support(
                    draw, node.support_type, node.position, 
                    support_rotation, size=self.config.support_size,
                    hinge_radius=hinge_radius
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
                  width: float = 4.0):
        """Draw beam of specified type"""
        beam = StanliBeam(beam_type, width)
        beam.draw(draw, start_pos, end_pos, rounded_start, rounded_end)
    
    def draw_support(self, draw: ImageDraw.Draw, support_type: SupportType,
                position: Tuple[float, float], rotation: float = 0,
                size: float = 25.0, hinge_radius: Optional[float] = None):
        """Draw support of specified type"""
        support = StanliSupport(support_type, size)
        support.draw(draw, position, rotation, hinge_radius=hinge_radius)
    
    def draw_hinge(self, draw: ImageDraw.Draw, hinge_type: HingeType,
                   position: Tuple[float, float], rotation: float = 0,
                   start_point: Optional[Tuple[float, float]] = None,
                   end_point: Optional[Tuple[float, float]] = None,
                   orientation: int = 0, size: float = 15.0):
        """Draw hinge/joint of specified type"""
        hinge = StanliHinge(hinge_type, size)
        hinge.draw(draw, position, rotation, start_point, end_point, orientation)
    
    def draw_load(self, draw: ImageDraw.Draw, load_type: LoadType,
                  position: Tuple[float, float], rotation: float = 0,
                  length: float = 40.0, distance: float = 0):
        """Draw load of specified type"""
        load = StanliLoad(load_type, length)
        load.draw(draw, position, rotation, length, distance)





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