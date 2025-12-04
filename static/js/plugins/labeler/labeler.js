import { GridSystem } from './gridSystem.js';

// --- State ---
let nodes = [];
let members = [];
let currentTool = 'node';
let currentSupport = 'none';
let hoveredNodeId = null;
let dragStartNodeId = null;
let gridSizeReal = 1.0;
let showGrid = true;

const SUPPORT_IMAGES = {};
let canvas, ctx, rect;

// Configuration
const NODE_RADIUS_PX = 6;
const SNAP_RADIUS_PX = 15;
const COLORS = {
    node: '#1e293b',
    nodeHover: '#3b82f6',
    member: '#334155',
    memberDrag: '#94a3b8',
    support: '#ef4444',
    grid: '#e2e8f0',
    axis: '#94a3b8'
};

// --- Initialization ---
export function initLabeler() {
    canvas = document.getElementById('structure-canvas');
    const container = document.getElementById('canvas-container');

    // FIX 2: Guard clause for missing HTML elements
    if (!canvas || !container) {
        console.error("Canvas or Container not found in DOM");
        return;
    }

    ctx = canvas.getContext('2d');

    const input = document.getElementById('grid-size-input');
    if (input) gridSizeReal = parseFloat(input.value) || 1.0;

    const resizeObserver = new ResizeObserver(() => {
        resizeCanvas();
        render();
    });
    resizeObserver.observe(container);

    resizeCanvas();
    loadSymbolImages();
    setupEvents();
    render();
}

function setupEvents() {
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mouseup', handleMouseUp);
    canvas.addEventListener('mouseleave', () => {
        dragStartNodeId = null;
        render();
    });
}

function resizeCanvas() {
    const container = document.getElementById('canvas-container');
    if (container) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        rect = canvas.getBoundingClientRect();
    }
}

// --- Helpers (Using GridSystem) ---

function getSnappedPos(pixelX, pixelY) {
    // 1. Snap to Nodes
    for (let n of nodes) {
        const p = GridSystem.toPixel(n.x, n.y, canvas, gridSizeReal);
        const dist = Math.hypot(p.x - pixelX, p.y - pixelY);
        if (dist <= SNAP_RADIUS_PX) {
            return { x: p.x, y: p.y, nodeId: n.id, isNode: true, realX: n.x, realY: n.y };
        }
    }

    // 2. Snap to Grid
    if (showGrid) {
        const real = GridSystem.toReal(pixelX, pixelY, canvas, gridSizeReal);
        const snapRealX = Math.round(real.x / gridSizeReal) * gridSizeReal;
        const snapRealY = Math.round(real.y / gridSizeReal) * gridSizeReal;
        const snapPixel = GridSystem.toPixel(snapRealX, snapRealY, canvas, gridSizeReal);

        return {
            x: snapPixel.x,
            y: snapPixel.y,
            nodeId: null,
            isNode: false,
            realX: snapRealX,
            realY: snapRealY
        };
    }

    const real = GridSystem.toReal(pixelX, pixelY, canvas, gridSizeReal);
    return { x: pixelX, y: pixelY, nodeId: null, isNode: false, realX: real.x, realY: real.y };
}

// --- Rendering ---

function render(mouseInfo = null) {
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 1. Draw Grid
    if (showGrid) {
        GridSystem.draw(ctx, canvas, gridSizeReal, COLORS);
    }

    // 2. Draw Members
    ctx.lineWidth = 3;
    ctx.strokeStyle = COLORS.member;
    ctx.beginPath();
    members.forEach(m => {
        const n1 = nodes.find(n => n.id === m.startNodeId);
        const n2 = nodes.find(n => n.id === m.endNodeId);
        if (n1 && n2) {
            const p1 = GridSystem.toPixel(n1.x, n1.y, canvas, gridSizeReal);
            const p2 = GridSystem.toPixel(n2.x, n2.y, canvas, gridSizeReal);
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
        }
    });
    ctx.stroke();

    // 3. Ghost Line
    if (dragStartNodeId !== null && mouseInfo) {
        const n1 = nodes.find(n => n.id === dragStartNodeId);
        if (n1) {
            const p1 = GridSystem.toPixel(n1.x, n1.y, canvas, gridSizeReal);
            ctx.lineWidth = 2;
            ctx.strokeStyle = COLORS.memberDrag;
            ctx.setLineDash([5, 5]);
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(mouseInfo.x, mouseInfo.y);
            ctx.stroke();
            ctx.setLineDash([]);
        }
    }

    // 4. Draw Nodes
    nodes.forEach(n => {
        const p = GridSystem.toPixel(n.x, n.y, canvas, gridSizeReal);
        const isHovered = (n.id === hoveredNodeId);

        ctx.fillStyle = isHovered ? COLORS.nodeHover : COLORS.node;
        ctx.beginPath();
        ctx.arc(p.x, p.y, isHovered ? NODE_RADIUS_PX + 2 : NODE_RADIUS_PX, 0, Math.PI * 2);
        ctx.fill();

        drawSupport(p.x, p.y, n.support);
    });

    // 5. Highlight Grid Point
    if (mouseInfo && !mouseInfo.isNode && mouseInfo.realX !== undefined) {
        ctx.fillStyle = 'rgba(59, 130, 246, 0.3)';
        ctx.beginPath();
        ctx.arc(mouseInfo.x, mouseInfo.y, 4, 0, Math.PI * 2);
        ctx.fill();
    }
}

async function loadSymbolImages() {
    const types = ['festlager', 'loslager', 'einspannung'];
    for (const t of types) {
        const img = new Image();
        img.src = `/symbols/get/${t}`;
        img.onload = () => {
            SUPPORT_IMAGES[t] = img;
            render();
        };
        img.onerror = () => {
            console.warn(`Failed to load symbol: ${t}`);
            // Do NOT alert here either, or you get 3 alerts on load
        };
    }
}

function drawSupport(x, y, type) {
    if (type === 'none') return;

    let key = type;
    if (type === 'fest') key = 'festlager';
    if (type === 'los') key = 'loslager';

    const img = SUPPORT_IMAGES[key];
    if (img && img.complete && img.naturalHeight !== 0) {
        const anchorX = 50;
        const anchorY = 30;
        const scale = 0.5;

        ctx.drawImage(img,
            x - (anchorX * scale),
            y - (anchorY * scale),
            img.width * scale,
            img.height * scale
        );
    } else {
        // FIX 3: Fallback drawing instead of Alert
        ctx.fillStyle = '#ef4444';
        ctx.fillRect(x - 10, y + 5, 20, 10);
    }
}

// Window exports for UI buttons
window.setTool = (tool) => { currentTool = tool; updateUiState(); dragStartNodeId = null; render(); };
window.setSupportType = (type) => { currentSupport = type; updateUiState(); };
window.updateGridSize = (val) => { gridSizeReal = parseFloat(val) || 0.1; render(); };
window.toggleGrid = () => { showGrid = !showGrid; render(); };
window.clearCanvas = () => { if (confirm("Clear?")) { nodes = []; members = []; render(); } };
// --- Interaction Logic ---

function getMousePos(evt) {
    rect = canvas.getBoundingClientRect();
    return {
        x: evt.clientX - rect.left,
        y: evt.clientY - rect.top
    };
}

function handleMouseMove(e) {
    const raw = getMousePos(e);
    const snapped = getSnappedPos(raw.x, raw.y);

    // Display Coords in UI if elements exist
    const cx = document.getElementById('coord-x');
    const cy = document.getElementById('coord-y');
    if (cx && cy) {
        cx.textContent = snapped.realX.toFixed(2);
        cy.textContent = snapped.realY.toFixed(2);
    }

    const prevHover = hoveredNodeId;
    hoveredNodeId = snapped.nodeId;

    // Re-render only if state changed
    if (prevHover !== hoveredNodeId || dragStartNodeId !== null) {
        render(snapped);
    }
}

function handleMouseDown(e) {
    const raw = getMousePos(e);
    const snapped = getSnappedPos(raw.x, raw.y);

    if (currentTool === 'node') {
        if (snapped.nodeId !== null) {
            // If clicking an existing node, apply the current support type
            updateNodeSupport(snapped.nodeId);
        } else {
            // Create a new node
            const newNode = {
                id: nodes.length > 0 ? Math.max(...nodes.map(n => n.id)) + 1 : 0,
                x: snapped.realX, // Store REAL coordinates (meters)
                y: snapped.realY,
                support: 'none'
            };
            nodes.push(newNode);
        }
    } else if (currentTool === 'member') {
        if (snapped.nodeId !== null) {
            dragStartNodeId = snapped.nodeId;
        }
    }
    render();
}

function handleMouseUp(e) {
    if (currentTool === 'member' && dragStartNodeId !== null) {
        const raw = getMousePos(e);
        const snapped = getSnappedPos(raw.x, raw.y);

        if (snapped.nodeId !== null && snapped.nodeId !== dragStartNodeId) {
            // Check if member already exists
            const exists = members.some(m =>
                (m.startNodeId === dragStartNodeId && m.endNodeId === snapped.nodeId) ||
                (m.startNodeId === snapped.nodeId && m.endNodeId === dragStartNodeId)
            );

            if (!exists) {
                members.push({
                    id: members.length,
                    startNodeId: dragStartNodeId,
                    endNodeId: snapped.nodeId
                });
            }
        }
    }
    dragStartNodeId = null;
    render();
}

function updateNodeSupport(nodeId) {
    const idx = nodes.findIndex(n => n.id === nodeId);
    if (idx !== -1) {
        nodes[idx].support = currentSupport;
    }
}

function updateUiState() {
    // Reset tool buttons
    document.querySelectorAll('.tool-btn').forEach(btn => {
        btn.classList.remove('border-blue-500', 'bg-blue-50');
        btn.classList.add('border-transparent');
    });
    // Highlight active tool
    const tBtn = document.getElementById(`btn-${currentTool}`);
    if (tBtn) {
        tBtn.classList.add('border-blue-500', 'bg-blue-50');
        tBtn.classList.remove('border-transparent');
    }

    // Reset support buttons
    document.querySelectorAll('.support-btn').forEach(btn => {
        btn.classList.remove('border-blue-500', 'bg-blue-50');
        btn.classList.add('border-slate-200');
    });
    // Highlight active support
    const sBtn = document.getElementById(`btn-${currentSupport}`);
    if (sBtn) {
        sBtn.classList.remove('border-slate-200');
        sBtn.classList.add('border-blue-500', 'bg-blue-50');
    }
}

window.saveSystem = async () => {
    // System is already stored in Real units, so we can just save 'nodes'
    const systemData = { nodes, members, gridSize: gridSizeReal };
    console.log("System Data (Real Units):", systemData);

    // Optional: Send to backend
    // await fetch('/api/save', { method: 'POST', body: JSON.stringify(systemData) ... });

    alert("System saved to console!");
};
