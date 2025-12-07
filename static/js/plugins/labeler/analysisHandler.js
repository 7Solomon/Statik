import * as Data from './structureData.js';
import { renderSystemView } from './rendering/index.js';

// --- State ---
export const AnalysisState = {
    hasResult: false,
    isMechanism: false,
    dof: 0,

    // API Data
    modes: [],
    systemData: null,

    // Active Render Data (Swapped when dropdown changes)
    activeModeIndex: 0,
    nodeVelocities: {}, // Points to modes[i].velocities
    rigidBodies: [],    // Points to modes[i].rigid_bodies
    memberPoles: {},    // Points to modes[i].member_poles

    // Viewport & Animation
    amplitude: 0.5,
    view: { panX: 0, panY: 0, zoom: 1.0 },
    animationTime: 0
};

let viewCanvas, viewCtx, resizeObserver, animationFrameId;

export function initSystemView() {
    viewCanvas = document.getElementById('system-view-canvas');
    const container = document.getElementById('system-view-container');
    if (!viewCanvas || !container) return;

    viewCtx = viewCanvas.getContext('2d');

    // Resize Handler
    const handleResize = () => {
        viewCanvas.width = container.clientWidth;
        viewCanvas.height = container.clientHeight;
        if (AnalysisState.systemData) centerView();
        redraw();
    };

    resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    setupInteraction(viewCanvas);
    setupControls();
    startAnimationLoop();
    handleResize();
}

function setupControls() {
    // Dropdown for Modes
    const selector = document.getElementById('mode-selector');
    if (selector) {
        selector.addEventListener('change', (e) => {
            const idx = parseInt(e.target.value);
            switchMode(idx);
        });
    }

    // Slider for Amplitude
    const slider = document.getElementById('amp-slider');
    if (slider) {
        slider.addEventListener('input', (e) => {
            AnalysisState.amplitude = parseInt(e.target.value) / 100;
        });
    }
}

function switchMode(index) {
    if (!AnalysisState.modes[index]) return;

    AnalysisState.activeModeIndex = index;

    // SWAP DATA
    const m = AnalysisState.modes[index];
    AnalysisState.nodeVelocities = m.velocities;
    AnalysisState.rigidBodies = m.rigid_bodies;
    AnalysisState.memberPoles = m.member_poles;

    redraw();
}

// --- API Logic ---
export async function runAnalysis() {
    const payload = Data.getExportData();
    try {
        const res = await fetch('/analyze/system', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Analysis failed');
        const result = await res.json();

        // 1. Store Basic Info
        AnalysisState.hasResult = true;
        AnalysisState.isMechanism = result.is_kinematic;
        AnalysisState.dof = result.dof;
        AnalysisState.modes = result.modes || [];
        AnalysisState.systemData = result.system;

        // 2. Setup Dropdown
        const selector = document.getElementById('mode-selector');
        const controlsDiv = document.getElementById('view-controls');

        if (selector) {
            selector.innerHTML = '';
            AnalysisState.modes.forEach((m, i) => {
                const opt = document.createElement('option');
                opt.value = i;
                opt.text = `Mode ${i + 1}`;
                selector.appendChild(opt);
            });
        }

        // 3. Activate Mode 0
        if (AnalysisState.modes.length > 0) {
            switchMode(0);
            if (selector) selector.value = 0;
            if (controlsDiv) controlsDiv.classList.remove('hidden');
        } else {
            if (controlsDiv) controlsDiv.classList.add('hidden');
        }

        // 4. View Setup
        centerView();
        openSystemPanel();
        redraw();

    } catch (e) {
        console.error(e);
        alert('Analysis failed.');
    }
}

// --- Helpers ---

function openSystemPanel() {
    const body = document.getElementById('body-system');
    if (body && body.style.display === 'none') {
        if (window.togglePanel) window.togglePanel('system');
        else body.style.display = 'block';
    }
}

function centerView() {
    if (!AnalysisState.systemData?.nodes?.length) return;

    const nodes = AnalysisState.systemData.nodes;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodes.forEach(n => {
        minX = Math.min(minX, n.x);
        maxX = Math.max(maxX, n.x);
        minY = Math.min(minY, n.y);
        maxY = Math.max(maxY, n.y);
    });

    const scale = 100; // Base scale matches renderer
    const cx = (minX + maxX) / 2 * scale;
    const cy = (minY + maxY) / 2 * scale;

    AnalysisState.view.zoom = 0.8;
    AnalysisState.view.panX = (viewCanvas.width / 2) - (cx * 0.8);
    // Inverted Y axis correction:
    AnalysisState.view.panY = (viewCanvas.height / 2) + (cy * 0.8);

    redraw();
}

function redraw() {
    if (viewCtx && viewCanvas) {
        renderSystemView(viewCtx, viewCanvas, AnalysisState);
    }
}

function startAnimationLoop() {
    const loop = (time) => {
        AnalysisState.animationTime = time / 1000;
        if (AnalysisState.hasResult) redraw();
        animationFrameId = requestAnimationFrame(loop);
    };
    animationFrameId = requestAnimationFrame(loop);
}

function setupInteraction(canvas) {
    let isDragging = false, lastX = 0, lastY = 0;
    canvas.addEventListener('mousedown', e => {
        isDragging = true; lastX = e.clientX; lastY = e.clientY;
    });
    window.addEventListener('mousemove', e => {
        if (!isDragging) return;
        AnalysisState.view.panX += e.clientX - lastX;
        AnalysisState.view.panY += e.clientY - lastY;
        lastX = e.clientX; lastY = e.clientY;
    });
    window.addEventListener('mouseup', () => isDragging = false);
    canvas.addEventListener('wheel', e => {
        e.preventDefault();
        AnalysisState.view.zoom *= Math.exp(-e.deltaY * 0.001);
    });
}
