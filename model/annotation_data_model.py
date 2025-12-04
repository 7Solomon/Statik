from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Set

# Define available point types (key -> (label, color))
POINT_TYPES: Dict[str, Tuple[str, str]] = {
    "node": ("Node", "#ff5252"),
    "support": ("Support", "#3cb44b"),
    "load": ("Load", "#3c7bff"),
    "joint": ("Joint", "#ffa500"),
}

@dataclass
class AnnotationPoint:
    id: int
    
    type_key: str
    pixel: Tuple[int, int]

class AnnotationModel:
    def __init__(self):
        self.points: List[AnnotationPoint] = []
        self.connections: Set[Tuple[int, int]] = set()
        
        self._next_id = 1
        self.on_changed = None

    def add_point(self, pixel: Tuple[int, int], type_key: str) -> AnnotationPoint:
        p = AnnotationPoint(id=self._next_id, type_key=type_key, pixel=pixel)
        self._next_id += 1
        self.points.append(p)
        self._emit()
        return p

    def remove_point(self, pid: int):
        before = len(self.points)
        self.points = [p for p in self.points if p.id != pid]
        if len(self.points) != before:
            # remove connections referencing pid
            self.connections = {c for c in self.connections if pid not in c}
            self._emit()

    def toggle_connection(self, a: int, b: int):
        if a == b:
            return
        edge = tuple(sorted((a, b)))
        if edge in self.connections:
            self.connections.remove(edge)
        else:
            self.connections.add(edge)
        self._emit()

    def find_point(self, pid: int) -> Optional[AnnotationPoint]:
        return next((p for p in self.points if p.id == pid), None)

    def clear(self):
        self.points.clear()
        self.connections.clear()
        self._emit()

    def _emit(self):
        if self.on_changed:
            self.on_changed()
