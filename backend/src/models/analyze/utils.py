"""Small value types shared by every other model module."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Vec2:
    x: float
    y: float

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y])
