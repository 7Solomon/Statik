import type { Vec2, Node, Scheibe } from "~/types/model";

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


export function isPointInsideScheibe(pos: Vec2, scheibe: Scheibe): boolean {
    const { corner1, corner2, shape } = scheibe;

    switch (shape) {
        case 'rectangle':
            return isPointInRectangle(pos, corner1, corner2);

        case 'circle':
            return isPointInCircle(pos, corner1, corner2);

        case 'triangle':
            return isPointInTriangle(pos, corner1, corner2);

        case 'polygon':
            if (scheibe.additionalPoints && scheibe.additionalPoints.length >= 3) {
                return isPointInPolygon(pos, scheibe.additionalPoints);
            }
            return false;

        default:
            return false;
    }
}

function isPointInRectangle(pos: Vec2, corner1: Vec2, corner2: Vec2): boolean {
    const minX = Math.min(corner1.x, corner2.x);
    const maxX = Math.max(corner1.x, corner2.x);
    const minY = Math.min(corner1.y, corner2.y);
    const maxY = Math.max(corner1.y, corner2.y);

    return pos.x >= minX && pos.x <= maxX && pos.y >= minY && pos.y <= maxY;
}

function isPointInCircle(pos: Vec2, corner1: Vec2, corner2: Vec2): boolean {
    const centerX = (corner1.x + corner2.x) / 2;
    const centerY = (corner1.y + corner2.y) / 2;
    const radius = Math.max(Math.abs(corner2.x - corner1.x), Math.abs(corner2.y - corner1.y)) / 2;

    const distFromCenter = Math.hypot(pos.x - centerX, pos.y - centerY);
    return distFromCenter <= radius;
}

function isPointInTriangle(pos: Vec2, corner1: Vec2, corner2: Vec2): boolean {
    const x1 = Math.min(corner1.x, corner2.x);
    const x2 = Math.max(corner1.x, corner2.x);
    const y1 = Math.min(corner1.y, corner2.y);
    const y2 = Math.max(corner1.y, corner2.y);
    const centerX = (x1 + x2) / 2;

    // Triangle vertices
    const v1 = { x: centerX, y: y1 };  // Top
    const v2 = { x: x1, y: y2 };       // Bottom-left
    const v3 = { x: x2, y: y2 };       // Bottom-right

    // Barycentric coordinate test
    const d1 = sign(pos, v1, v2);
    const d2 = sign(pos, v2, v3);
    const d3 = sign(pos, v3, v1);

    const hasNeg = (d1 < 0) || (d2 < 0) || (d3 < 0);
    const hasPos = (d1 > 0) || (d2 > 0) || (d3 > 0);

    return !(hasNeg && hasPos);
}

function sign(p1: Vec2, p2: Vec2, p3: Vec2): number {
    return (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y);
}

function isPointInPolygon(pos: Vec2, vertices: Vec2[]): boolean {
    let inside = false;

    for (let i = 0, j = vertices.length - 1; i < vertices.length; j = i++) {
        const xi = vertices[i].x, yi = vertices[i].y;
        const xj = vertices[j].x, yj = vertices[j].y;

        const intersect = ((yi > pos.y) !== (yj > pos.y))
            && (pos.x < (xj - xi) * (pos.y - yi) / (yj - yi) + xi);

        if (intersect) inside = !inside;
    }

    return inside;
}

/**
 * Get all nodes that are inside a Scheibe
 */
export function getNodesInsideScheibe(scheibe: Scheibe, nodes: Node[]): Node[] {
    return nodes.filter(node => isPointInsideScheibe(node.position, scheibe));
}

/**
 * Find all Scheiben that contain a given point
 */
export function getScheibenContainingPoint(pos: Vec2, scheiben: Scheibe[]): Scheibe[] {
    return scheiben.filter(scheibe => isPointInsideScheibe(pos, scheibe));
}