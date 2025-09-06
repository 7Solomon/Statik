import random
from typing import Tuple
import numpy as np
from PIL import Image, ImageFilter
from dataclasses import replace

from data.generator_class import Structure, Node  # Updated import
from src.generator.geometry import GeometryProcessor


class ImageAugmenter:
    """Applies various augmentations to images and updates labels accordingly"""
    
    def __init__(self, config):
        self.config = config
        self.geometry_processor = GeometryProcessor()
    
    def augment(self, image: Image.Image, structure: Structure) -> Tuple[Image.Image, Structure]:
        """Apply all enabled augmentations"""
        if self.config.enable_rotation:
            image, structure = self._apply_rotation(image, structure)
        
        if self.config.enable_perspective:
            structure = self.geometry_processor.apply_perspective_transform(
                structure, self.config.perspective_strength, self.config.image_size
            )
        
        if self.config.enable_blur:
            image = self._apply_blur(image)
        
        if self.config.enable_noise:
            image = self._apply_noise(image)
        
        return image, structure
    
    def _apply_rotation(self, image: Image.Image, structure: Structure) -> Tuple[Image.Image, Structure]:
        """Rotate image and update node coordinates (and element orientations)"""
        angle = random.randint(*self.config.rotation_range)
        
        rotated_image = image.rotate(angle, fillcolor=self.config.background_color)
        
        center_x, center_y = image.size[0] / 2, image.size[1] / 2
        angle_rad = np.radians(angle)
        
        rotated_nodes = []
        for node in structure.nodes:
            x, y = node.position
            x_c = x - center_x
            y_c = y - center_y
            new_x = x_c * np.cos(angle_rad) - y_c * np.sin(angle_rad) + center_x
            new_y = x_c * np.sin(angle_rad) + y_c * np.cos(angle_rad) + center_y
            rotated_nodes.append(Node(
                id=node.id,
                position=(new_x, new_y),
                support_type=node.support_type
            ))
        
        # Adjust rotations for hinges / loads if they have a rotation attribute (wrap 0-360)
        rotated_hinges = [
            replace(h, rotation=(h.rotation + angle) % 360) if hasattr(h, "rotation") else h
            for h in structure.hinges
        ] if structure.hinges else []
        
        rotated_loads = [
            replace(l, rotation=(l.rotation + angle) % 360) if hasattr(l, "rotation") else l
            for l in structure.loads
        ] if structure.loads else []
        
        rotated_structure = Structure(
            nodes=rotated_nodes,
            beams=structure.beams,
            hinges=rotated_hinges,
            loads=rotated_loads
        )
        return rotated_image, rotated_structure
    
    def _apply_blur(self, image: Image.Image) -> Image.Image:
        kernel_size = random.choice(self.config.blur_kernels)
        return image.filter(ImageFilter.GaussianBlur(radius=kernel_size // 2))
    
    def _apply_noise(self, image: Image.Image) -> Image.Image:
        img_array = np.array(image)
        noise = np.random.normal(0, self.config.noise_intensity * 255, img_array.shape)
        noisy_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy_array)