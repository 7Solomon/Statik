import type { Vec2, Node } from "~/types/model";

export const SNAP_RADIUS_PIXELS = 15;

/**
 * Finds the nearest node within a certain pixel radius
 */
export function getNearestNode(
    mouseWorld: Vec2,
    nodes: Node[],
    zoom: number
): string | null {
    // Convert snap radius to world units (meters)
    const snapDistance = SNAP_RADIUS_PIXELS / zoom;
    let nearestId = null;
    let minDist = Infinity;

    for (const node of nodes) {
        const dx = node.position.x - mouseWorld.x;
        const dy = node.position.y - mouseWorld.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist <= snapDistance && dist < minDist) {
            minDist = dist;
            nearestId = node.id;
        }
    }

    return nearestId;
}

/**
 * Snaps a raw world position to the nearest grid line
 */
export function snapToGrid(pos: Vec2, gridSize: number): Vec2 {
    return {
        x: Math.round(pos.x / gridSize) * gridSize,
        y: Math.round(pos.y / gridSize) * gridSize
    };
}

export function pDistance(x: number, y: number, x1: number, y1: number, x2: number, y2: number) {
    var A = x - x1;
    var B = y - y1;
    var C = x2 - x1;
    var D = y2 - y1;

    var dot = A * C + B * D;
    var len_sq = C * C + D * D;
    var param = -1;
    if (len_sq != 0) //in case of 0 length line
        param = dot / len_sq;

    var xx, yy;

    if (param < 0) {
        xx = x1;
        yy = y1;
    }
    else if (param > 1) {
        xx = x2;
        yy = y2;
    }
    else {
        xx = x1 + param * C;
        yy = y1 + param * D;
    }

    var dx = x - xx;
    var dy = y - yy;
    return Math.sqrt(dx * dx + dy * dy);
}

export const projectPointToSegment = (p: { x: number, y: number }, a: { x: number, y: number }, b: { x: number, y: number }) => {
    const pax = p.x - a.x;
    const pay = p.y - a.y;
    const bax = b.x - a.x;
    const bay = b.y - a.y;
    const h = Math.min(1, Math.max(0, (pax * bax + pay * bay) / (bax * bax + bay * bay)));
    return {
        t: h,
        x: a.x + h * bax,
        y: a.y + h * bay,
        dist: Math.hypot(p.x - (a.x + h * bax), p.y - (a.y + h * bay))
    };
};