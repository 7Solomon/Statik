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

const BODY_COLORS = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899'];

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
export function renderSystemView(ctx, canvas, state) {
    const { width, height } = canvas;
    const { systemData, view, animationTime, isMechanism } = state;

    // 1. Clear & Setup
    ctx.clearRect(0, 0, width, height);

    if (!systemData) return;

    ctx.save(); // Save untransformed state

    // 2. Apply View Transform (Pan & Zoom)
    // We move origin to the pan location
    ctx.translate(view.panX, view.panY);
    // We Scale Zoom. 
    // CRITICAL: Scale Y by -1 to flip coordinate system so +Y is UP.
    ctx.scale(view.zoom, -view.zoom);

    // 3. Calculate Animation Factor
    const animFactor = isMechanism ? Math.sin(animationTime * 3) : 0;
    const amp = 0.5;

    // Helper: Transform grid coord (x,y) to pixel coord (in Transformed Space)
    // Since we flipped Y with scale(1, -1), we can just use normal (x,y).
    const getDeformedPos = (node) => {
        const scale = 100; // 100px per meter
        const px = node.x * scale;
        const py = node.y * scale;

        let dx = 0, dy = 0;

        let v = state.nodeVelocities[node.id] ||
            state.nodeVelocities[String(node.id)] ||
            state.nodeVelocities[node.id + ".0"];

        if (v) {
            dx = v[0] * scale * amp * animFactor;
            dy = v[1] * scale * amp * animFactor; // POSITIVE v[1] because Y is now UP
        }

        return { x: px + dx, y: py + dy, ox: px, oy: py };
    };

    // --- DRAW ORIGIN (Coordinate System) ---
    // Note: Since Y is flipped, drawing "down" means negative Y in local coords
    ctx.save();
    ctx.lineWidth = 2 / view.zoom;
    ctx.strokeStyle = '#94a3b8';

    // X-Axis
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(50, 0);
    ctx.stroke();

    // Y-Axis (draws "up" in world space)
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(0, 50);
    ctx.stroke();

    // Origin Dot
    ctx.beginPath();
    ctx.arc(0, 0, 3 / view.zoom, 0, Math.PI * 2);
    ctx.fillStyle = '#64748b';
    ctx.fill();
    ctx.restore();

    // --- DRAW MEMBERS (unchanged logic but using systemData and getDeformedPos) ---
    const bodyColorMap = {};
    state.rigidBodies.forEach((rb, i) => {
        const color = BODY_COLORS[i % BODY_COLORS.length];
        rb.member_ids.forEach(mid => bodyColorMap[mid] = color);
    });

    systemData.members.forEach(m => {
        const n1 = systemData.nodes.find(n => n.id == m.startNodeId);
        const n2 = systemData.nodes.find(n => n.id == m.endNodeId);
        if (!n1 || !n2) return;

        const p1 = getDeformedPos(n1);
        const p2 = getDeformedPos(n2);

        // Draw Deformed State
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.strokeStyle = bodyColorMap[m.id] || '#334155';
        ctx.lineWidth = 4; // visual width (in world-space units)
        ctx.lineCap = 'round';
        ctx.stroke();

        // Draw Ghost (Original) State for mechanisms
        if (isMechanism) {
            ctx.beginPath();
            ctx.moveTo(p1.ox, p1.oy);
            ctx.lineTo(p2.ox, p2.oy);
            ctx.strokeStyle = '#cbd5e1';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            ctx.stroke();
            ctx.setLineDash([]);
        }
    });

    // --- DRAW NODES & SYMBOLS (images must be un-flipped locally) ---
    systemData.nodes.forEach(n => {
        const p = getDeformedPos(n);

        const symbolType = n.symbolType || n._visual_type || 'none';
        const rotation = (n.rotation !== undefined) ? n.rotation : (n._visual_rotation || 0);

        // Draw Symbol
        if (symbolType && symbolType !== 'none' && SYMBOL_DEFINITIONS[symbolType]) {
            const def = SYMBOL_DEFINITIONS[symbolType];
            const img = getSymbolImage(symbolType, rotation, () => { /* optional re-render callback */ });

            if (img.complete && img.naturalWidth > 0) {
                const baseScale = 0.8;
                const finalScale = baseScale / view.zoom;

                const anchorX = def.anchor ? def.anchor[0] : 50;
                const anchorY = def.anchor ? def.anchor[1] : 30;

                // Un-flip image locally: translate to position, flip Y, draw centered
                ctx.save();
                ctx.translate(p.x, p.y);
                ctx.scale(1, -1); // UN-FLIP Image so it appears upright after world flip
                ctx.drawImage(
                    img,
                    -anchorX * finalScale,
                    -anchorY * finalScale,
                    img.width * finalScale,
                    img.height * finalScale
                );
                ctx.restore();
            }
        }

        // Draw Node Dot (circle is symmetric so flip doesn't affect appearance)
        ctx.beginPath();
        ctx.arc(p.x, p.y, 6 / view.zoom, 0, Math.PI * 2);
        ctx.fillStyle = COLORS.node;
        ctx.fill();
    });

    ctx.restore();
}



function drawArrow(ctx, x1, y1, x2, y2) {
    const head = 8;
    const dx = x2 - x1, dy = y2 - y1;
    const ang = Math.atan2(dy, dx);
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - head * Math.cos(ang - Math.PI / 6), y2 - head * Math.sin(ang - Math.PI / 6));
    ctx.lineTo(x2 - head * Math.cos(ang + Math.PI / 6), y2 - head * Math.sin(ang + Math.PI / 6));
    ctx.fill();
}

export function resizeCanvasToDisplaySize(canvas) {
    // Look up the size the canvas is being displayed
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;

    // Check if the canvas is not the same size.
    if (canvas.width !== width || canvas.height !== height) {
        // Make the canvas the same size
        canvas.width = width;
        canvas.height = height;
        return true; // Return true if resized
    }
    return false;
}