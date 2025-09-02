from typing import List, Iterable
from data.custome_class_definitions import Joint

MOMENT_VEC = (0, 0, 1)
X_VEC = (1, 0, 0)
Y_VEC = (0, 1, 0)

def has_full_xyzM(vectors: Iterable[tuple[float,float,float]]) -> bool:
    vecs = set(vectors)
    return X_VEC in vecs and Y_VEC in vecs and MOMENT_VEC in vecs