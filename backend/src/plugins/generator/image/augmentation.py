"""Photometric and geometric augmentation, driven by the sample's RenderStyle.

Rotation is deliberately small. Structural drawings are gravity aligned - the
ground is at the bottom and a Festlager hangs below its node - so the old
uniform 0-360 rotation taught the model that support orientation carries no
information, throwing away the strongest cue for which side is "ground". What is
left here is drafting and scanning slop.
"""

import random
from typing import Tuple

import numpy as np
from PIL import Image, ImageFilter
from dataclasses import replace

from src.models.image_models import ImageSystem, ImageNode, ImageLoad


class ImageAugmenter:
    """Applies augmentations to images and updates the ImageSystem alongside."""

    def __init__(self, config):
        self.config = config

    def augment(self, image: Image.Image, system: ImageSystem) -> Tuple[Image.Image, ImageSystem]:
        style = getattr(system, "style", None)

        if self.config.enable_rotation:
            image, system = self._apply_rotation(image, system)

        # Photometric effects come from the per-sample style, so blur/noise/JPEG
        # vary between samples instead of being applied identically to every one.
        if style is not None:
            if style.illumination > 0:
                image = self._apply_illumination(image, style.illumination)
            if style.blur_radius > 0:
                image = image.filter(ImageFilter.GaussianBlur(radius=style.blur_radius))
            if style.noise_sigma > 0:
                image = self._apply_noise(image, style.noise_sigma)
            if style.jpeg_quality is not None:
                image = self._apply_jpeg(image, style.jpeg_quality)
            return image, system

        # No style (e.g. a system built by hand): fall back to the config flags.
        if self.config.enable_blur:
            kernel = random.choice(self.config.blur_kernels)
            image = image.filter(ImageFilter.GaussianBlur(radius=max(0.3, kernel / 3.0)))
        if self.config.enable_noise:
            image = self._apply_noise(image, self.config.noise_intensity * 255)
        return image, system

    def _apply_rotation(self, image: Image.Image, system: ImageSystem):
        """Rotate the raster and carry node/load angles along with it."""
        angle = random.uniform(*self.config.rotation_range)
        background = getattr(getattr(system, "style", None), "paper", None) or \
            self.config.background_color
        rotated_image = image.rotate(angle, fillcolor=tuple(background),
                                     resample=Image.BILINEAR)

        W, H = image.size
        center_x, center_y = W / 2.0, H / 2.0
        angle_rad = np.radians(angle)
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)

        def rot(x: float, y: float) -> Tuple[float, float]:
            x_c, y_c = x - center_x, y - center_y
            return (x_c * cos_a + y_c * sin_a + center_x,
                    -x_c * sin_a + y_c * cos_a + center_y)

        new_nodes = []
        for n in system.nodes:
            nx, ny = rot(n.pixel_x, n.pixel_y)
            new_rot = ((getattr(n, "rotation", 0.0) or 0.0) + angle) % 360
            new_nodes.append(replace(n, pixel_x=nx, pixel_y=ny, rotation=new_rot))

        new_loads = []
        for l in system.loads:
            lx, ly = rot(l.pixel_x, l.pixel_y)
            new_angle = (getattr(l, "angle_deg", 0.0) + angle) % 360
            new_loads.append(replace(l, pixel_x=lx, pixel_y=ly, angle_deg=new_angle))

        return rotated_image, replace(system, nodes=new_nodes, loads=new_loads)

    def _apply_illumination(self, image: Image.Image, strength: float) -> Image.Image:
        """A smooth brightness ramp, as from a photographed or shadowed page."""
        arr = np.asarray(image).astype(np.float32)
        h, w = arr.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w]
        ax, ay = random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0)
        ramp = 1.0 + strength * (ax * (xx / w - 0.5) + ay * (yy / h - 0.5)) * 2.0
        arr *= ramp[:, :, None]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    def _apply_noise(self, image: Image.Image, sigma: float) -> Image.Image:
        arr = np.asarray(image).astype(np.float32)
        arr += np.random.normal(0, sigma, arr.shape)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    def _apply_jpeg(self, image: Image.Image, quality: int) -> Image.Image:
        """Round-trip through JPEG so the model sees real block artefacts."""
        import io

        buf = io.BytesIO()
        image.save(buf, "JPEG", quality=quality)
        buf.seek(0)
        return Image.open(buf).convert("RGB")
