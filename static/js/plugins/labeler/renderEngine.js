// renderEngine.js
import { GridSystem } from './gridSystem.js';
import { SystemState } from './structureData.js';

// Constants
const COLORS = {
    node: '#1e293b',
    nodeHover: '#3b82f6',
    member: '#334155',
    memberDrag: '#94a3b8',
    grid: '#e2e8f0',
    axis: '#94a3b8'
};

const SYMBOL_CACHE = {};
let SYMBOL_DEFINITIONS = {};

// Setup definitions (call this from main init)
export function setSymbolDefinitions(defs) {
    SYMBOL_DEFINITIONS = defs;
}

function getSymbolImage(name, rotation, onLoaded) {
    const r = Math.round(rotation * 100) / 100;
    const key = `${name}_${r}`;

    if (SYMBOL_CACHE[key]) return SYMBOL_CACHE[key];

    const img = new Image();
    img.onload = onLoaded; // Callback to re-render when loaded
    img.src = `/symbols/get/${name}?rotation=${r}`;
    SYMBOL_CACHE[key] = img;
    return img;
}

export function renderScene(ctx, canvas, interactionState) {
    if (!ctx) return;
    const { width, height } = canvas;
    const { hoveredNodeId, dragStartNodeId, mousePos } = interactionState;

    ctx.clearRect(0, 0, width, height);

    // 1. Draw Grid
    if (interactionState.showGrid) {
        GridSystem.draw(ctx, canvas, SystemState.gridSize, COLORS);
    }

    // 2. Draw Members
    ctx.lineWidth = 3;
    ctx.strokeStyle = COLORS.member;
    ctx.beginPath();
    SystemState.members.forEach(m => {
        const n1 = SystemState.nodes.find(n => n.id === m.startNodeId);
        const n2 = SystemState.nodes.find(n => n.id === m.endNodeId);
        if (n1 && n2) {
            const p1 = GridSystem.toPixel(n1.x, n1.y, canvas, SystemState.gridSize);
            const p2 = GridSystem.toPixel(n2.x, n2.y, canvas, SystemState.gridSize);
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
        }
    });
    ctx.stroke();

    // 3. Draw Ghost Line (Dragging)
    if (dragStartNodeId !== null && mousePos) {
        const n1 = SystemState.nodes.find(n => n.id === dragStartNodeId);
        if (n1) {
            const p1 = GridSystem.toPixel(n1.x, n1.y, canvas, SystemState.gridSize);
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

    // 4. Draw Nodes & Symbols
    SystemState.nodes.forEach(n => {
        const p = GridSystem.toPixel(n.x, n.y, canvas, SystemState.gridSize);
        const isHovered = (n.id === hoveredNodeId);

        // Draw Symbol
        if (n.symbolType && n.symbolType !== 'none' && SYMBOL_DEFINITIONS[n.symbolType]) {
            const def = SYMBOL_DEFINITIONS[n.symbolType];
            const img = getSymbolImage(n.symbolType, n.rotation, () => {
                // If image loads late, trigger a re-render via callback
                // Note: You might need to pass a generic 'requestRender' function to this module
            });

            if (img.complete && img.naturalWidth > 0) {
                const scale = 0.5;
                const anchorX = def.anchor ? def.anchor[0] : 50;
                const anchorY = def.anchor ? def.anchor[1] : 30;
                ctx.drawImage(img, p.x - (anchorX * scale), p.y - (anchorY * scale), img.width * scale, img.height * scale);
            }
        }

        // Draw Node Dot
        ctx.fillStyle = isHovered ? COLORS.nodeHover : COLORS.node;
        ctx.beginPath();
        ctx.arc(p.x, p.y, isHovered ? 8 : 6, 0, Math.PI * 2);
        ctx.fill();
    });

    // 5. Highlight Snap Candidate
    if (mousePos && !mousePos.isNode && mousePos.realX !== undefined) {
        ctx.fillStyle = 'rgba(59, 130, 246, 0.3)';
        ctx.beginPath();
        ctx.arc(mousePos.x, mousePos.y, 4, 0, Math.PI * 2);
        ctx.fill();
    }
}
