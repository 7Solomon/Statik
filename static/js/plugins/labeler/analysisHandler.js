import * as Data from './structureData.js';
import { renderSystemView } from './rendering/index.js';
import { showAlert } from '../../config.js';

// --- State ---
export const AnalysisState = {
    hasResult: false,
    isMechanism: false,
    dof: 0,
    nodeVelocities: {},
    memberPoles: {},
    rigidBodies: [],

    // Complete system copy for this view
    systemData: null,

    // Viewport State
    view: {
        panX: 0,
        panY: 0,
        zoom: 1.0
    },

    // Animation State
    animationTime: 0
};

let viewCanvas, viewCtx, resizeObserver;
let animationFrameId;


export function initSystemView() {
    viewCanvas = document.getElementById('system-view-canvas');
    const container = document.getElementById('system-view-container');

    if (!viewCanvas || !container) return;

    viewCtx = viewCanvas.getContext('2d');

    // Robust resize handler
    const handleResize = () => {
        viewCanvas.width = container.clientWidth;
        viewCanvas.height = container.clientHeight;

        // Center the view initially if we have data
        if (AnalysisState.systemData) centerView();
        redraw();
    };

    resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // Mouse Interaction (Pan & Zoom)
    setupInteraction(viewCanvas);

    // Start Animation Loop
    startAnimationLoop();

    // Initial call
    handleResize();
}

function redraw() {
    if (!viewCtx || !viewCanvas) return;
    // Use AnalysisState (includes systemData + view) to draw the view
    renderSystemView(viewCtx, viewCanvas, AnalysisState);
}

function setupInteraction(canvas) {
    let isDragging = false;
    let lastX = 0, lastY = 0;

    canvas.addEventListener('mousedown', (e) => {
        if (e.button === 1 || e.button === 0) { // Middle or Left mouse
            isDragging = true;
            lastX = e.clientX;
            lastY = e.clientY;
            canvas.style.cursor = 'grabbing';
        }
    });

    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const dx = e.clientX - lastX;
        const dy = e.clientY - lastY;
        lastX = e.clientX;
        lastY = e.clientY;

        AnalysisState.view.panX += dx;
        AnalysisState.view.panY += dy;
    });

    window.addEventListener('mouseup', () => {
        isDragging = false;
        canvas.style.cursor = 'default';
    });

    canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        const zoomSpeed = 0.001;
        const zoomChange = Math.exp(-e.deltaY * zoomSpeed);
        AnalysisState.view.zoom *= zoomChange;
        // Clamp zoom
        AnalysisState.view.zoom = Math.max(0.1, Math.min(AnalysisState.view.zoom, 5.0));
    });
}

function startAnimationLoop() {
    const loop = (time) => {
        AnalysisState.animationTime = time / 1000; // Seconds
        if (viewCtx && viewCanvas && AnalysisState.hasResult) {
            renderSystemView(viewCtx, viewCanvas, AnalysisState);
        }
        animationFrameId = requestAnimationFrame(loop);
    };
    animationFrameId = requestAnimationFrame(loop);
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

        // Update State (handle possible key name variations)
        AnalysisState.hasResult = true;
        AnalysisState.isMechanism = result.is_kinematic ?? result.is_mechanism ?? false;
        AnalysisState.dof = result.dof ?? 0;
        AnalysisState.nodeVelocities = result.node_velocities ?? {};
        AnalysisState.memberPoles = result.member_poles ?? {};
        AnalysisState.rigidBodies = result.rigid_bodies ?? [];

        // Store the system data returned from API or fallback to request payload
        AnalysisState.systemData = result.system ?? {
            nodes: payload.nodes || [],
            members: payload.members || [],
            gridSize: payload.gridSize ?? (Data.SystemState?.gridSize ?? 1.0)
        };

        // Auto-center view on new result
        centerView();

        // Ensure panel is open (reuse previous logic)
        const body = document.getElementById('body-system');
        if (body && body.style.display === 'none') {
            if (window.togglePanel) {
                window.togglePanel('system');
            } else {
                body.style.display = 'block';
                const arrow = document.getElementById('arrow-system');
                if (arrow) arrow.classList.add('rotate-180');
            }
        }

        redraw();
    } catch (e) {
        console.error(e);
        alert('Analysis failed (see console).');
    }
}

function centerView() {
    if (!AnalysisState.systemData || !Array.isArray(AnalysisState.systemData.nodes) || AnalysisState.systemData.nodes.length === 0) return;

    // Calculate bounding box of nodes
    const nodes = AnalysisState.systemData.nodes;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

    nodes.forEach(n => {
        minX = Math.min(minX, n.x);
        maxX = Math.max(maxX, n.x);
        minY = Math.min(minY, n.y);
        maxY = Math.max(maxY, n.y);
    });

    // Determine pixel scaling for grid units (approximate)
    const gs = AnalysisState.systemData.gridSize ?? 1.0;
    const gridSizePx = gs * 100; // 100px per grid unit default
    const contentWidth = (maxX - minX) * gridSizePx;
    const contentHeight = (maxY - minY) * gridSizePx;

    // Center point in content pixels
    const centerX = ((minX + maxX) / 2) * gridSizePx;
    const centerY = ((minY + maxY) / 2) * gridSizePx;

    // Canvas center
    const cvsCX = viewCanvas.width / 2;
    const cvsCY = viewCanvas.height / 2;

    AnalysisState.view.panX = cvsCX - centerX;
    AnalysisState.view.panY = cvsCY - centerY;
    AnalysisState.view.zoom = 0.8; // Start slightly zoomed out

    // Trigger a redraw
    redraw();
}
