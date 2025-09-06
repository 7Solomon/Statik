
from typing import Optional, Sequence


def concurrency_point_2d(positions: Sequence[tuple[float,float]],
                          vectors: Sequence[tuple[float,float,float]],
                          tol: float = 1e-9) -> Optional[tuple[float,float]]:
    """
    Returns (x,y) if all (non zero, non parallel conflicting) lines p + t*v are concurrent, else None.
    A line uses only the first two components (x,y) of the vector.
    """
    # Collect usable lines (ignore zero in-plane direction)
    lines = []
    for (px, py), (vx, vy, _) in zip(positions, vectors):
        if abs(vx) < tol and abs(vy) < tol:
            continue  # skip zero direction
        lines.append(((px, py), (vx, vy)))
    if len(lines) <= 1:
        return None  # Need at least two directions to define a unique point

    # Find intersection candidate from first non-parallel pair
    base_point = None
    for i in range(len(lines)):
        p1, v1 = lines[i]
        for j in range(i+1, len(lines)):
            p2, v2 = lines[j]
            det = v1[0]*v2[1] - v1[1]*v2[0]
            if abs(det) < tol:
                # Parallel (could be coincident) -> skip for now
                continue
            # Solve p1 + t v1 = p2 + s v2  =>  t v1 - s v2 = (p2 - p1)
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            t = (dx * v2[1] - dy * v2[0]) / det
            cand = (p1[0] + t * v1[0], p1[1] + t * v1[1])
            base_point = cand
            break
        if base_point:
            break

    if base_point is None:
        # All usable lines parallel; either none or infinite intersection -> treat as not concurrent
        return None

    bx, by = base_point
    # Verify all lines pass through candidate
    for (p, v) in lines:
        vx, vy = v
        # Vector from point on line to candidate
        dx = bx - p[0]
        dy = by - p[1]
        # Check if (dx,dy) is colinear with (vx,vy)
        if abs(vx) >= abs(vy):
            if abs(vx) < tol:
                # Line is vertical (vx ~ 0); require dx ~ 0
                if abs(dx) > tol:
                    return None
            else:
                ratio = dx / vx
                if abs(p[1] + ratio * vy - by) > tol:
                    return None
        else:
            if abs(vy) < tol:
                if abs(dy) > tol:
                    return None
            else:
                ratio = dy / vy
                if abs(p[0] + ratio * vx - bx) > tol:
                    return None
    return base_point