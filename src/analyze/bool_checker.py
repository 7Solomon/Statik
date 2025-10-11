from typing import List, Iterable, Optional, Sequence

from src.analyze.geometrie import concurrency_point_2d
from data.analyze_custome_class import Bearing, Joint

MOMENT_VEC = (0, 0, 1)
X_VEC = (1, 0, 0)
Y_VEC = (0, 1, 0)

def has_full_xyM(vectors: Iterable[tuple[float,float,float]]) -> bool:
    vecs = set(vectors)
    return X_VEC in vecs and Y_VEC in vecs and MOMENT_VEC in vecs


def has_combined_xyM(vectors: Iterable[(Bearing)]) -> bool:
    ves = [_[0].vector for _ in vectors]
    pos = [_[1] for _ in vectors]
    if has_full_xyM(ves):
        return True
    if len(ves) > 2:
        point = concurrency_point_2d(pos, ves)
        #print(f"Concurrent point: {point}")
        if point is None:
            return True
    return False
    
    
