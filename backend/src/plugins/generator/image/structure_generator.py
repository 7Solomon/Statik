import random
import uuid
import math
from typing import List, Tuple

from src.models.image_models import ImageSystem, ImageNode, ImageMember, ImageLoad

class RandomStructureGenerator:
    """
    Generates ImageSystems with random pixel coordinates.
    Optimized for creating diverse visual training data for YOLO.
    """
    
    def __init__(self, width: int = 800, height: int = 600, padding: int = 50):
        self.width = width
        self.height = height
        self.padding = padding

    def generate(self) -> ImageSystem:
        system = ImageSystem(width=self.width, height=self.height)
        
        # 1. Generate Nodes (Splatter)
        # We define "layers" or "grid-like" structures sometimes, and pure random others
        strategy = random.choice(['random', 'grid', 'truss_like'])
        
        if strategy == 'grid':
            system.nodes = self._generate_grid_nodes()
        else:
            system.nodes = self._generate_random_nodes()

        # 2. Connect Nodes (Members)
        system.members = self._connect_nodes(system.nodes)
        
        # 3. Add Loads (Visuals)
        system.loads = self._add_random_loads(system.nodes, system.members)
        
        return system

    def _generate_random_nodes(self) -> List[ImageNode]:
        nodes = []
        num_nodes = random.randint(3, 8)
        
        support_types = ['FESTLAGER', 'LOSLAGER', 'FESTE_EINSPANNUNG', 'GLEITLAGER']

        for _ in range(num_nodes):
            x = random.randint(self.padding, self.width - self.padding)
            y = random.randint(self.padding, self.height - self.padding)
            
            # 30% chance of being a support
            support = 'free'
            if random.random() < 0.3:
                support = random.choice(support_types)  
            
            nodes.append(ImageNode(
                id=str(uuid.uuid4()),
                pixel_x=float(x),
                pixel_y=float(y),
                support_type=support
            ))
        return nodes

    def _generate_grid_nodes(self) -> List[ImageNode]:
        """Creates nicer looking orthogonal structures"""
        nodes = []
        cols = random.randint(2, 4)
        rows = random.randint(1, 2)
        
        step_x = (self.width - 2*self.padding) // cols
        step_y = (self.height - 2*self.padding) // (rows + 1)
        
        start_x = self.padding + step_x // 2
        start_y = self.height - self.padding - (step_y * rows)

        for r in range(rows + 1):
            for c in range(cols + 1):
                # Jitter positions slightly so it's not "perfect" (better for AI training)
                jitter = random.randint(-10, 10)
                
                x = start_x + c * step_x + jitter
                y = start_y + r * step_y + jitter
                
                # Bottom row often supports
                support = 'free'
                if r == rows: 
                    support = random.choice(['FESTLAGER', 'LOSLAGER', 'FESTE_EINSPANNUNG'])

                nodes.append(ImageNode(
                    id=str(uuid.uuid4()),
                    pixel_x=float(x),
                    pixel_y=float(y),
                    support_type=support
                ))
        return nodes

    def _connect_nodes(self, nodes: List[ImageNode]) -> List[ImageMember]:
        members = []
        # Simple logic: Connect nearest neighbors or sequential
        # This prevents "crossing" lines that look messy
        
        # Sort by X then Y
        sorted_nodes = sorted(nodes, key=lambda n: (n.pixel_x, n.pixel_y))
        
        for i in range(len(sorted_nodes)):
            # Always connect to the "next" node to form a chain
            if i < len(sorted_nodes) - 1:
                members.append(ImageMember(
                    id=str(uuid.uuid4()),
                    start_node_id=sorted_nodes[i].id,
                    end_node_id=sorted_nodes[i+1].id
                ))
            
            # Random extra connections (triangulation)
            if i < len(sorted_nodes) - 2 and random.random() > 0.5:
                members.append(ImageMember(
                    id=str(uuid.uuid4()),
                    start_node_id=sorted_nodes[i].id,
                    end_node_id=sorted_nodes[i+2].id
                ))
                
        return members

    def _add_random_loads(self, nodes: List[ImageNode], members: List[ImageMember]) -> List[ImageLoad]:
        loads = []
        load_types = ['EINZELLAST', 'MOMENT_UHRZEIGER']
        # Add 1-3 random loads
        for _ in range(random.randint(1, 3)):
            target_node = random.choice(nodes)
            
            # Visual angle for the arrow
            angle = random.choice([0, 90, 180, 270, 45])
            
            loads.append(ImageLoad(
                id=str(uuid.uuid4()),
                node_id=target_node.id,
                pixel_x=target_node.pixel_x,
                pixel_y=target_node.pixel_y,
                angle_deg=angle,
                load_type=random.choice(load_types),
                label_text=f"{random.randint(5, 50)}kN"
            ))
        return loads
