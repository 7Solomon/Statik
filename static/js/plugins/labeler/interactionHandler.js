import { GridSystem } from './gridSystem.js';
import * as Data from './structureData.js';
import * as Renderer from './renderEngine.js';
import { initSystemView, runAnalysis } from './analysisHandler.js';


import './fileManager.js';
// --- State ---
let canvas, ctx;
let currentTool = { category: 'connection', name: 'member' };
let currentRotation = 0;
let interactionState = {
    hoveredNodeId: null,
    dragStartNodeId: null,
    mousePos: null, // { x, y, realX, realY, nodeId, isNode }
    showGrid: true
};
let SYMBOL_DEFINITIONS = {};
let resizeObserver;

export function triggerRender() {
    Renderer.renderScene(ctx, canvas, interactionState);
}

// --- Initialization  ---
export async function initLabeler() {
    // 1. Load Definitions
    await loadDefinitions();

    // 2. Setup DOM
    canvas = document.getElementById('structure-canvas');
    const container = document.getElementById('canvas-container');

    if (!canvas || !container) {
        console.error("Labeler: Canvas or Container not found");
        return;
    }

    ctx = canvas.getContext('2d');

    // 3. Setup Resizing
    resizeObserver = new ResizeObserver(() => {
        handleResize(container);
    });
    resizeObserver.observe(container);
    handleResize(container); // Initial size

    // 4. Setup Events
    setupEvents();

    // 5. Expose Global Functions for HTML Buttons
    exposeGlobalFunctions();

    // 6. Initial Render
    triggerRender();

    initSystemView();
    // 7. Restore UI State (Optional: Highlight default button)
    window.setTool('connection', 'member');
}

async function loadDefinitions() {
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

function handleResize(container) {
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    triggerRender();
}


function updateRotationPreview() {
    const img = document.getElementById('rotation-preview');
    if (!img) return;

    let symbolName = 'festlager';
    if (currentTool.category === 'support' || currentTool.category === 'hinge') {
        symbolName = currentTool.name;
    }

    const r = Math.round(currentRotation);
    img.src = `/symbols/get/${symbolName}?rotation=${r}`;
}

// --- Global Exports for HTML ---
function exposeGlobalFunctions() {
    window.setTool = (cat, name) => {
        currentTool = { category: cat, name: name };
        updateUIButtons();
    };

    window.updateRotation = (deg) => {
        currentRotation = parseFloat(deg) || 0;
        const display = document.getElementById('rotation-display');
        if (display) display.innerText = currentRotation.toFixed(0);
        updateRotationPreview();
    };


    window.selectPresetRotation = (angle) => {
        angle = parseFloat(angle) || 0;
        window.updateRotation(angle);

        const custom = document.getElementById('rotation-custom');
        if (custom) custom.value = angle;

        document.querySelectorAll('#rotation-presets .rot-btn').forEach(btn => {
            btn.classList.remove('bg-blue-500', 'text-white', 'border-blue-500');
            btn.classList.add('bg-slate-50', 'text-slate-700', 'border-slate-300');
            const a = parseFloat(btn.dataset.angle);
            if (a === angle) {
                btn.classList.remove('bg-slate-50', 'border-slate-300', 'text-slate-700');
                btn.classList.add('bg-blue-500', 'text-white', 'border-blue-500');
            }
        });

        updateRotationPreview();
    };

    window.selectCustomRotation = (val) => {
        const angle = Math.max(0, Math.min(360, parseFloat(val) || 0));
        window.updateRotation(angle);

        document.querySelectorAll('#rotation-presets .rot-btn').forEach(btn => {
            btn.classList.remove('bg-blue-500', 'text-white', 'border-blue-500');
            btn.classList.add('bg-slate-50', 'text-slate-700', 'border-slate-300');
        });

        updateRotationPreview();
    };

    window.updateGridSize = (val) => {
        Data.SystemState.gridSize = parseFloat(val) || 1.0;
        triggerRender();
    };

    window.toggleGrid = () => {
        interactionState.showGrid = !interactionState.showGrid;
        triggerRender();
    };

    window.clearCanvas = () => {
        if (confirm("Alles löschen?")) {
            Data.clearSystem();
            triggerRender();
        }
    };

    window.toggleSystemView = () => {
        const body = document.getElementById('system-view-body');
        if (!body) return;
        const hidden = body.classList.toggle('hidden');
        const btn = document.querySelector('#system-view-panel button[onclick="toggleSystemView()"]');
        if (btn) btn.textContent = hidden ? 'Expand' : 'Collapse';
    };


}

function updateUIButtons() {
    // Reset all buttons
    document.querySelectorAll('.tool-btn').forEach(b => {
        b.classList.remove('border-blue-500', 'bg-blue-50', 'ring-2', 'border-red-400', 'bg-red-50', 'border-green-400');
        b.classList.add('border-slate-200');
    });

    // Highlight active
    const btnId = `btn-${currentTool.category}-${currentTool.name}`;
    const btn = document.getElementById(btnId);
    if (btn) {
        btn.classList.remove('border-slate-200');
        if (currentTool.category === 'delete') {
            btn.classList.add('border-red-400', 'bg-red-50', 'ring-2');
        } else {
            btn.classList.add('border-blue-500', 'bg-blue-50', 'ring-2');
        }
    }
}

// --- Interaction Logic ---

function handleMouseDown(e) {
    const raw = getMousePos(e);
    const snapped = getSnappedPos(raw.x, raw.y);

    // CASE: DELETE TOOL
    if (currentTool.category === 'delete') {
        if (snapped.nodeId !== null) {
            Data.deleteNode(snapped.nodeId);
        } else {
            const memberId = findMemberAt(raw.x, raw.y);
            if (memberId !== null) Data.deleteMember(memberId);
        }
        triggerRender();
        return;
    }

    // CASE: EXISTING NODE CLICK
    if (snapped.nodeId !== null) {
        if (currentTool.category === 'connection') {
            interactionState.dragStartNodeId = snapped.nodeId;
        } else if (currentTool.category === 'support' || currentTool.category === 'hinge') {
            applySymbolToNode(snapped.nodeId);
        }
    }
    // CASE: EMPTY SPACE CLICK
    else {
        // Create Node immediately
        const newNode = Data.addNode(snapped.realX, snapped.realY);

        if (currentTool.category === 'support' || currentTool.category === 'hinge') {
            // Apply symbol to the new node
            applySymbolToNode(newNode.id);
        } else if (currentTool.category === 'connection') {
            // Start dragging from new node
            interactionState.dragStartNodeId = newNode.id;
        }
    }

    triggerRender();
}

function handleMouseUp(e) {
    if (interactionState.dragStartNodeId !== null) {
        const raw = getMousePos(e);
        const snapped = getSnappedPos(raw.x, raw.y);

        if (snapped.nodeId !== null && snapped.nodeId !== interactionState.dragStartNodeId) {
            // Connect to existing
            Data.addMember(interactionState.dragStartNodeId, snapped.nodeId);
        } else if (snapped.nodeId === null) {
            // Create end node and connect
            const newNode = Data.addNode(snapped.realX, snapped.realY);
            Data.addMember(interactionState.dragStartNodeId, newNode.id);
        }
    }

    interactionState.dragStartNodeId = null;
    triggerRender();
}

function handleMouseMove(e) {
    const raw = getMousePos(e);
    const snapped = getSnappedPos(raw.x, raw.y);

    // Update Coord Display
    const cx = document.getElementById('coord-x');
    const cy = document.getElementById('coord-y');
    if (cx && cy) {
        cx.textContent = snapped.realX.toFixed(2);
        cy.textContent = snapped.realY.toFixed(2);
    }

    interactionState.mousePos = snapped;
    interactionState.hoveredNodeId = snapped.nodeId;

    triggerRender();
}

// --- Helpers ---

function applySymbolToNode(nodeId) {
    const def = SYMBOL_DEFINITIONS[currentTool.name];
    if (!def && currentTool.name !== 'none') return;

    // Default if def not found but we have a name (fallback)
    const fixData = def ? {
        fix_x: def.fix_x || false,
        fix_y: def.fix_y || false,
        fix_m: def.fix_m || false,
        category: def.category
    } : { fix_x: false, fix_y: false, fix_m: false };

    Data.updateNodeSymbol(nodeId, currentTool.name, currentRotation, fixData);
}

function getMousePos(evt) {
    const rect = canvas.getBoundingClientRect();
    return { x: evt.clientX - rect.left, y: evt.clientY - rect.top };
}

function getSnappedPos(px, py) {
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
    if (interactionState.showGrid) {
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

// Math for detecting clicks on members
function findMemberAt(px, py) {
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

function setupEvents() {
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mouseup', handleMouseUp);
    canvas.addEventListener('mouseleave', () => {
        interactionState.dragStartNodeId = null;
        triggerRender();
    });
}
