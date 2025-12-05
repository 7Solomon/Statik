import random
from typing import Tuple
import numpy as np
from PIL import Image, ImageFilter
from dataclasses import replace

from models.generator_class import Structure, Node  # Updated import
from src.plugins.generator.geometry import GeometryProcessor


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

        # PIL rotates CCW for positive angle, about the image center
        rotated_image = image.rotate(angle, fillcolor=self.config.background_color)

        W, H = image.size
        center_x, center_y = W / 2.0, H / 2.0

        # In y-down image coordinates, CCW rotation by +angle uses:
        # x' = x_c*cos + y_c*sin + cx
        # y' = -x_c*sin + y_c*cos + cy
        angle_rad = np.radians(angle)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        rotated_nodes = []
        for node in structure.nodes:
            x, y = node.position
            x_c = x - center_x
            y_c = y - center_y

            new_x = x_c * cos_a + y_c * sin_a + center_x
            new_y = -x_c * sin_a + y_c * cos_a + center_y

            n2 = replace(node, position=(new_x, new_y)) if hasattr(node, "__dict__") else Node(
                id=node.id, position=(new_x, new_y), support_type=node.support_type
            )
            # If your renderer treats positive rotation as clockwise, subtract angle here
            if hasattr(n2, "rotation"):
                setattr(n2, "rotation", (getattr(n2, "rotation", 0) - angle) % 360)
            rotated_nodes.append(n2)

        rotated_hinges = [
            replace(h, rotation=(getattr(h, "rotation", 0) - angle) % 360) if hasattr(h, "rotation") else h
            for h in (structure.hinges or [])
        ]
        rotated_loads = [
            replace(l, rotation=(getattr(l, "rotation", 0) - angle) % 360) if hasattr(l, "rotation") else l
            for l in (structure.loads or [])
        ]

        rotated_structure = Structure(
            nodes=rotated_nodes,
            beams=structure.beams,
            hinges=rotated_hinges,
            loads=rotated_loads
        )
        return rotated_image, rotated_structure
    
    def _apply_blur(self, image: Image.Image) -> Image.Image:
        kernel_size = random.choice(self.config.blur_kernels)
        return image.filter(ImageFilter.GaussianBlur(radius = max(0.3, kernel_size / 3.0)))

    def _apply_noise(self, image: Image.Image) -> Image.Image:
        img_array = np.array(image)
        noise = np.random.normal(0, self.config.noise_intensity * 255, img_array.shape)
        noisy_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy_array)
