import random
from typing import Tuple
import numpy as np
from PIL import Image, ImageFilter
from dataclasses import replace

from src.models.image_models import ImageSystem, ImageNode, ImageLoad
from src.plugins.generator.geometry import GeometryProcessor


class ImageAugmenter:
    """Applies various augmentations to images and updates ImageSystem accordingly."""
    
    def __init__(self, config):
        self.config = config
        self.geometry_processor = GeometryProcessor()
    
    def augment(self, image: Image.Image, system: ImageSystem) -> Tuple[Image.Image, ImageSystem]:
        """Apply all enabled augmentations."""
        if self.config.enable_rotation:
            image, system = self._apply_rotation(image, system)
        
        if self.config.enable_perspective:
            system = self.geometry_processor.apply_perspective_transform(
                system, self.config.perspective_strength, self.config.image_size
            )
        
        if self.config.enable_blur:
            image = self._apply_blur(image)
        
        if self.config.enable_noise:
            image = self._apply_noise(image)
        
        return image, system
    
    def _apply_rotation(self, image: Image.Image, system: ImageSystem) -> Tuple[Image.Image, ImageSystem]:
        """Rotate image and update node & load pixel coordinates."""
        angle = random.randint(*self.config.rotation_range)

        # PIL rotates CCW for positive angle, about the image center
        rotated_image = image.rotate(angle, fillcolor=self.config.background_color)

        W, H = image.size
        center_x, center_y = W / 2.0, H / 2.0

        angle_rad = np.radians(angle)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        def rot(x: float, y: float) -> Tuple[float, float]:
            x_c = x - center_x
            y_c = y - center_y
            new_x = x_c * cos_a + y_c * sin_a + center_x
            new_y = -x_c * sin_a + y_c * cos_a + center_y
            return new_x, new_y

        # Rotate nodes
        new_nodes = []
        for n in system.nodes:
            nx, ny = rot(n.pixel_x, n.pixel_y)
            current_rot = getattr(n, "rotation", 0.0) or 0.0
            new_rot = (current_rot + angle) % 360
            
            new_nodes.append(replace(n, pixel_x=nx, pixel_y=ny, rotation=new_rot))

        # Rotate loads that store explicit pixel positions
        new_loads = []
        for l in system.loads:
            if hasattr(l, "pixel_x"):
                lx, ly = rot(l.pixel_x, l.pixel_y)
                # Update angle_deg if present
                if hasattr(l, "angle_deg"):
                    new_angle = (getattr(l, "angle_deg", 0.0) + angle) % 360
                    new_loads.append(replace(l, pixel_x=lx, pixel_y=ly, angle_deg=new_angle))
                else:
                    new_loads.append(replace(l, pixel_x=lx, pixel_y=ly))
            else:
                new_loads.append(l)

        rotated_system = replace(system, nodes=new_nodes, loads=new_loads)
        return rotated_image, rotated_system
    
    def _apply_blur(self, image: Image.Image) -> Image.Image:
        kernel_size = random.choice(self.config.blur_kernels)
        return image.filter(ImageFilter.GaussianBlur(radius=max(0.3, kernel_size / 3.0)))

    def _apply_noise(self, image: Image.Image) -> Image.Image:
        img_array = np.array(image)
        noise = np.random.normal(0, self.config.noise_intensity * 255, img_array.shape)
        noisy_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy_array)
