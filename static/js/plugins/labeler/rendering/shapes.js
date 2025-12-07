import { SystemState } from '../structureData.js';
import { GridSystem } from '../gridSystem.js';
import { getSymbolImage } from './assets.js';
import { drawStanliDistributedLoad, drawStanliPointLoad, drawStanliMoment } from './customeShapes/loads.js';
import { drawStanliMember } from './customeShapes/members.js';

export const COLORS = {
    node: '#1e293b',
    nodeHover: '#3b82f6',
    member: '#334155',
    memberDrag: '#94a3b8',
    grid: '#e2e8f0',
    axis: '#94a3b8',
    load: '#ef4444',
    moment: '#f59e0b'
};


export function drawMembers(ctx, canvas, gridSize) {
    SystemState.members.forEach(m => {
        const n1 = SystemState.nodes.find(n => n.id === m.startNodeId);
        const n2 = SystemState.nodes.find(n => n.id === m.endNodeId);

        if (n1 && n2) {
            const p1 = GridSystem.toPixel(n1.x, n1.y, canvas, gridSize);
            const p2 = GridSystem.toPixel(n2.x, n2.y, canvas, gridSize);

            // Map your backend Enum/ID to a string style
            // Example: m.type might be 1 (Normal), 2 (Fiber), etc.
            let visualType = 'normal';
            if (m.type === 'fiber' || m.type === 1) visualType = 'fiber';
            else if (m.type === 'truss' || m.type === 2) visualType = 'truss';
            else if (m.type === 'hidden' || m.type === 3) visualType = 'hidden';

            drawStanliMember(ctx, p1, p2, visualType);
        }
    });
}

export function drawGhostMember(ctx, canvas, interactionState, gridSize) {
    const { dragStartNodeId, mousePos } = interactionState;
    if (dragStartNodeId !== null && mousePos) {
        const n1 = SystemState.nodes.find(n => n.id === dragStartNodeId);
        if (n1) {
            const p1 = GridSystem.toPixel(n1.x, n1.y, canvas, gridSize);
            ctx.lineWidth = 2;
            ctx.strokeStyle = COLORS.memberDrag;
            ctx.setLineDash([5, 5]);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(mousePos.x, mousePos.y);
            ctx.stroke();
            ctx.setLineDash([]);
        }
    }
}

export function drawNodeSymbol(ctx, pos, symbolType, rotation, SYMBOL_DEFINITIONS) {
    const def = SYMBOL_DEFINITIONS[symbolType];
    if (!def) return;
    const img = getSymbolImage(symbolType, rotation);
    if (img.complete && img.naturalWidth > 0) {
        const scale = 0.5;
        const anchorX = def.anchor ? def.anchor[0] : 50;
        const anchorY = def.anchor ? def.anchor[1] : 50;

        ctx.drawImage(
            img,
            pos.x - (anchorX * scale),
            pos.y - (anchorY * scale),
            img.width * scale,
            img.height * scale
        );
    }
}

export function drawNodes(ctx, canvas, hoveredNodeId, gridSize, SYMBOL_DEFINITIONS) {
    SystemState.nodes.forEach(n => {
        const p = GridSystem.toPixel(n.x, n.y, canvas, gridSize);
        const isHovered = (n.id === hoveredNodeId);

        if (n.symbolType && n.symbolType !== 'none') {
            drawNodeSymbol(ctx, p, n.symbolType, n.rotation, SYMBOL_DEFINITIONS);
        }

        ctx.fillStyle = isHovered ? COLORS.nodeHover : COLORS.node;
        ctx.beginPath();
        ctx.arc(p.x, p.y, isHovered ? 8 : 6, 0, Math.PI * 2);
        ctx.fill();
    });
}

export function drawLoads(ctx, canvas, gridSize, SYMBOL_DEFINITIONS) {
    if (!SystemState.loads) return;

    SystemState.loads.forEach(load => {
        let pStart = null, pEnd = null;

        // 1. Handle Node Loads (Point Forces / Moments)
        if (load.locationType === 'node') {
            const node = SystemState.nodes.find(n => n.id === load.locationId);
            if (!node) return;
            pStart = GridSystem.toPixel(node.x, node.y, canvas, gridSize);
            pEnd = pStart; // Point loads have same start/end
        }

        // 2. Handle Member Loads
        else if (load.locationType === 'member') {
            const member = SystemState.members.find(m => m.id === load.locationId);
            if (!member) return;

            const n1 = SystemState.nodes.find(n => n.id === member.startNodeId);
            const n2 = SystemState.nodes.find(n => n.id === member.endNodeId);
            if (!n1 || !n2) return;

            const lerp = (t) => ({
                x: n1.x + (n2.x - n1.x) * t,
                y: n1.y + (n2.y - n1.y) * t
            });

            // --- FIX FOR DISTRIBUTED LOADS ---
            if (load.type === 'distributed') {
                // Use the tStart/tEnd we saved in event_logic.js
                // Fallback to 0 and 1 if undefined
                const t0 = (load.tStart !== undefined) ? load.tStart : 0;
                const t1 = (load.tEnd !== undefined) ? load.tEnd : 1;

                const w1 = lerp(t0);
                const w2 = lerp(t1);

                pStart = GridSystem.toPixel(w1.x, w1.y, canvas, gridSize);
                pEnd = GridSystem.toPixel(w2.x, w2.y, canvas, gridSize);
            }
            // --- FIX FOR POINT LOADS ON MEMBER ---
            else {
                // Standard single 't'
                const w = lerp(load.t);
                pStart = GridSystem.toPixel(w.x, w.y, canvas, gridSize);
                pEnd = pStart;
            }
        }

        if (!pStart) return;

        ctx.save();
        ctx.strokeStyle = COLORS.load;
        ctx.fillStyle = COLORS.load;
        ctx.lineWidth = 2;

        if (load.type === 'distributed') {
            const angleToDraw = (load.angle !== undefined) ? load.angle : null;
            drawStanliDistributedLoad(ctx, pStart, pEnd, 15, 30, true, angleToDraw);
        }
        else if (load.type === 'force' || load.type === 'point') {
            // Use load.angle if it exists, otherwise use 270 (down)
            const angle = (load.angle !== undefined) ? load.angle : 90;
            drawStanliPointLoad(ctx, pStart.x, pStart.y, angle);
        }
        else if (load.type === 'moment') {
            drawStanliMoment(ctx, pStart.x, pStart.y, 20, true);
        }

        ctx.restore();
    });
}


//function drawArrowParams(ctx, x1, y1, x2, y2) {
//    const head = 6;
//    const dx = x2 - x1;
//    const dy = y2 - y1;
//    const angle = Math.atan2(dy, dx);
//    ctx.beginPath();
//    ctx.moveTo(x1, y1);
//    ctx.lineTo(x2, y2);
//    ctx.stroke();
//    ctx.beginPath();
//    ctx.moveTo(x2, y2);
//    ctx.lineTo(x2 - head * Math.cos(angle - Math.PI / 6), y2 - head * Math.sin(angle - Math.PI / 6));
//    ctx.lineTo(x2 - head * Math.cos(angle + Math.PI / 6), y2 - head * Math.sin(angle + Math.PI / 6));
//    ctx.fill();
//}
