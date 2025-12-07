import * as Utils from './utils.js';
import * as Logic from './event_logic.js';
import * as Renderer from '../rendering/index.js';
import * as Data from '../structureData.js';
import { initSystemView } from '../analysisHandler.js';
import '../fileManager.js';

// --- State ---
let canvas, ctx;
let currentTool = { category: 'connection', name: 'member' };
let currentRotation = 0;
let renderFrameId = null;

let interactionState = {
    hoveredNodeId: null,
    dragStartNodeId: null,
    mousePos: null, // { x, y, realX, realY, nodeId, isNode }
    showGrid: true,

    // for rotation
    longPressTimer: null,
    isRotating: false,
    rotatingNodeId: null, // or rotatingLoadId
    initialMouseY: 0,
    initialRotation: 0
};
let SYMBOL_DEFINITIONS = {};
let resizeObserver;


export function triggerRender() {
    Renderer.renderScene(ctx, canvas, interactionState, currentTool, currentRotation);
}


// --- Initialization  ---
export async function initLabeler() {
    // 1. Load Definitions
    await Utils.loadDefinitions(SYMBOL_DEFINITIONS, Renderer);

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
        Utils.handleResize(container, canvas);
    });
    resizeObserver.observe(container);
    Utils.handleResize(container, canvas); // Initial size

    // 4. Setup Events
    setupEvents();

    // 5. Expose Global Functions for HTML Buttons
    exposeGlobalFunctions();

    // 6. Initial Render
    triggerRender();

    initSystemView();
    // 7. Restore UI State (Optional)
    window.setTool('connection', 'member');
}


// --- Event Logic ---

function handleMouseDown(e) {
    const raw = Utils.getMousePos(e, canvas);
    const snapped = Utils.getSnappedPos(raw.x, raw.y, canvas, interactionState.showGrid);
    Logic.handleMouseDown(snapped, raw, interactionState, currentRotation, currentTool);

    triggerRender();
}

function handleMouseMove(e) {
    const raw = Utils.getMousePos(e, canvas);

    // 1. Handle Rotation Logic First
    const didRotate = Logic.handleMouseMove(raw, interactionState);

    if (didRotate) {
        scheduleRender();
        return;
    }

    // Standard Move Logic (Hover/Snap)
    const snapped = Utils.getSnappedPos(raw.x, raw.y, canvas, interactionState.showGrid);

    // Update Coord Display
    const cx = document.getElementById('coord-x');
    const cy = document.getElementById('coord-y');
    if (cx && cy) {
        cx.textContent = snapped.realX.toFixed(2);
        cy.textContent = snapped.realY.toFixed(2);
    }

    interactionState.mousePos = snapped;
    interactionState.hoveredNodeId = snapped.nodeId;
    scheduleRender();
}

function handleMouseUp(e) {
    const raw = Utils.getMousePos(e, canvas);
    const snapped = Utils.getSnappedPos(raw.x, raw.y, canvas, interactionState.showGrid);

    // 1. Capture "Drag" state BEFORE calling Logic
    // (Logic might reset dragStartNodeId if we aren't careful, though currently it doesn't)
    const wasDragging = interactionState.dragStartNodeId !== null;

    // 2. Get Definitions
    const activeDefinitions = Renderer.getSymbolDefinitions();

    // 3. Run Event Logic (Handles Selection, Rotation, Deletion, etc.)
    Logic.handleMouseUp(
        snapped,
        raw,
        currentTool,
        currentRotation,
        interactionState,
        canvas,
        activeDefinitions
    );

    triggerRender();
}


// --- SETUP EVENTS ---
function setupEvents() {
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mouseup', handleMouseUp);
    canvas.addEventListener('mouseleave', () => {
        interactionState.dragStartNodeId = null;
        triggerRender();
    });
}


// --- UI Helpers ---

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

function updateUIButtons() {
    document.querySelectorAll('.tool-btn').forEach(b => {
        b.classList.remove('border-blue-500', 'bg-blue-50', 'ring-2', 'border-red-400', 'bg-red-50');
        b.classList.add('border-slate-200');
    });

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

// --- Global Exports ---
function exposeGlobalFunctions() {
    window.setTool = (cat, name) => {
        currentTool = { category: cat, name: name };
        if (cat === 'load' && name === 'force') {
            window.updateRotation(90);
        } else {
            window.updateRotation(0);
        }
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
    };

    window.selectCustomRotation = (val) => {
        const angle = Math.max(0, Math.min(360, parseFloat(val) || 0));
        window.updateRotation(angle);
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

    // Make render available to FileManager
    window.triggerRender = triggerRender;
}

function scheduleRender() {
    if (renderFrameId) return;

    renderFrameId = requestAnimationFrame(() => {
        triggerRender();
        renderFrameId = null;
    });
}