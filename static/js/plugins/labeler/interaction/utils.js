import { GridSystem } from '../gridSystem.js';
import * as Data from '../structureData.js';

export function getMousePos(evt, canvas) {
    const rect = canvas.getBoundingClientRect();
    return { x: evt.clientX - rect.left, y: evt.clientY - rect.top };
}

export function getSnappedPos(px, py, canvas, showGrid) {
    const nodes = Data.SystemState.nodes;
    const gridSize = Data.SystemState.gridSize;

    // 1. Snap to Node (Priority)
    for (let n of nodes) {
        const p = GridSystem.toPixel(n.x, n.y, canvas, gridSize);
        // Snap radius 15px
        if (Math.hypot(p.x - px, p.y - py) <= 15) {
            return { x: p.x, y: p.y, nodeId: n.id, isNode: true, realX: n.x, realY: n.y };
        }
    }

    // 2. Snap to Grid
    if (showGrid) {
        const real = GridSystem.toReal(px, py, canvas, gridSize);
        const snapRealX = Math.round(real.x / gridSize) * gridSize;
        const snapRealY = Math.round(real.y / gridSize) * gridSize;
        const snapPixel = GridSystem.toPixel(snapRealX, snapRealY, canvas, gridSize);
        return { x: snapPixel.x, y: snapPixel.y, nodeId: null, isNode: false, realX: snapRealX, realY: snapRealY };
    }

    // 3. No Snap
    const real = GridSystem.toReal(px, py, canvas, gridSize);
    return { x: px, y: py, nodeId: null, isNode: false, realX: real.x, realY: real.y };
}

export function findMemberAt(px, py, canvas) {
    const threshold = 10; // px tolerance
    for (let m of Data.SystemState.members) {
        const n1 = Data.SystemState.nodes.find(n => n.id === m.startNodeId);
        const n2 = Data.SystemState.nodes.find(n => n.id === m.endNodeId);
        if (!n1 || !n2) continue;

        const p1 = GridSystem.toPixel(n1.x, n1.y, canvas, Data.SystemState.gridSize);
        const p2 = GridSystem.toPixel(n2.x, n2.y, canvas, Data.SystemState.gridSize);

        const dist = pointToSegmentDistance(px, py, p1.x, p1.y, p2.x, p2.y);
        if (dist < threshold) return m.id;
    }
    return null;
}

// Internal Helper
function pointToSegmentDistance(x, y, x1, y1, x2, y2) {
    const A = x - x1;
    const B = y - y1;
    const C = x2 - x1;
    const D = y2 - y1;
    const dot = A * C + B * D;
    const len_sq = C * C + D * D;
    let param = -1;

    if (len_sq !== 0) param = dot / len_sq;

    let xx, yy;
    if (param < 0) {
        xx = x1;
        yy = y1;
    } else if (param > 1) {
        xx = x2;
        yy = y2;
    } else {
        xx = x1 + param * C;
        yy = y1 + param * D;
    }

    const dx = x - xx;
    const dy = y - yy;
    return Math.sqrt(dx * dx + dy * dy);
}

// Calculate relative position 't' (0..1) of a point projected onto a member
export function calculateMemberT(memberId, rawX, rawY) {
    const m = Data.SystemState.members.find(x => x.id === memberId);
    if (!m) return 0.5;

    const n1 = Data.SystemState.nodes.find(n => n.id === m.startNodeId);
    const n2 = Data.SystemState.nodes.find(n => n.id === m.endNodeId);
    if (!n1 || !n2) return 0.5;

    const dx = n2.x - n1.x;
    const dy = n2.y - n1.y;
    const len2 = dx * dx + dy * dy;

    if (len2 === 0) return 0;

    // Project rawX/Y (which must be in REAL coords) onto line
    // If rawX/Y are pixels, convert first!
    // But usually rawX is from snapped.realX
    // NOTE: rawX passed here should be REAL coordinates

    let t = ((rawX - n1.x) * dx + (rawY - n1.y) * dy) / len2;
    return Math.max(0, Math.min(1, t));
}

export async function loadDefinitions(SYMBOL_DEFINITIONS, Renderer) {
    try {
        const res = await fetch('/symbols/definitions');
        if (res.ok) {
            SYMBOL_DEFINITIONS = await res.json();
            Renderer.setSymbolDefinitions(SYMBOL_DEFINITIONS);
        }
    } catch (e) {
        console.error("Could not load definitions", e);
    }
}

export function handleResize(container, canvas) {
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    triggerRender();
}
