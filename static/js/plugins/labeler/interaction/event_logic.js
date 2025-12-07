// event_logic.js

import * as Data from '../structureData.js';
import * as Utils from './utils.js';

// --- 1. MOUSE DOWN (Start Rotation or Drag) ---
export function handleMouseDown(snapped, raw, interactionState, currentRotation, currentTool) {
    // Store the position where the mouse was PRESSED. 
    // We will use this as the placement target even if the mouse moves to rotate.
    interactionState.placementOrigin = snapped;

    // Check if this is a tool that should rotate (Supports, Hinges, Loads)
    // And ensure we are NOT in the middle of a connection drag
    const isRotationalTool = ['support', 'hinge', 'load'].includes(currentTool.category);

    if (isRotationalTool) {
        // --- START ROTATION MODE IMMEDIATELY ---
        interactionState.isRotating = true;
        interactionState.initialMouseY = raw.y; // Pixel Y
        interactionState.initialRotation = currentRotation; // Current Tool Rotation

        //console.log("Rotation Mode Started");
        document.body.style.cursor = "ns-resize";
    }
}

// --- 2. MOUSE MOVE (Update Rotation) ---
export function handleMouseMove(raw, interactionState) {
    if (interactionState.isRotating) {
        const deltaY = raw.y - interactionState.initialMouseY;

        let rawRotation = interactionState.initialRotation - deltaY;

        // Normalize to 0-360
        rawRotation = (rawRotation % 360 + 360) % 360;

        const snapStep = 45;
        let newRotation = Math.round(rawRotation / snapStep) * snapStep;

        newRotation = newRotation % 360;
        // -------------------------------------

        if (window.updateRotation) window.updateRotation(newRotation);
        return true;
    }
}

// --- 3. MOUSE UP (Confirm Placement) ---
export function handleMouseUp(snapped, raw, currentTool, currentRotation, interactionState, canvas, SYMBOL_DEFINITIONS) {

    // Determine the actual target coordinate.
    // If we were rotating, 'snapped' is where we released the mouse (wrong spot).
    // We want 'placementOrigin' (where we pressed the mouse).
    const targetPos = (interactionState.isRotating && interactionState.placementOrigin)
        ? interactionState.placementOrigin
        : snapped;

    // Cleanup Rotation State
    if (interactionState.isRotating) {
        interactionState.isRotating = false;
        document.body.style.cursor = "default";
    }

    // Execute Action at the Target Position
    executeStandardClick(targetPos, raw, currentTool, currentRotation, interactionState, canvas, SYMBOL_DEFINITIONS);

    // RESET
    if (window.updateRotation) {
        if (currentTool['category'] === 'load' && currentTool['name'] === 'force') {
            window.updateRotation(90);
        } else { window.updateRotation(0); }
    }
}

// --- CORE ACTION LOGIC ---
async function executeStandardClick(snapped, raw, currentTool, currentRotation, interactionState, canvas, SYMBOL_DEFINITIONS) {

    // 1. DELETE TOOL
    if (currentTool.category === 'delete') {
        if (snapped.nodeId !== null) {
            Data.deleteNode(snapped.nodeId);
            Data.deleteLoadsOnNode(snapped.nodeId);
        } else {
            const memberId = Utils.findMemberAt(raw.x, raw.y, canvas);
            if (memberId !== null) Data.deleteMember(memberId);
        }
        return;
    }

    // 2. CLICK ON EXISTING NODE
    if (snapped.nodeId !== null) {
        const nodeId = snapped.nodeId;

        if (currentTool.category === 'connection') {
            if (interactionState.dragStartNodeId === null) {
                // START DRAG
                interactionState.dragStartNodeId = nodeId;
            } else {
                // END DRAG (Connect Start -> Clicked Node)
                // NEW: Pass currentTool.name (e.g., 'normal', 'truss')
                Data.addMember(interactionState.dragStartNodeId, nodeId, currentTool.name);
                interactionState.dragStartNodeId = null;
            }
        }
        else if (currentTool.category === 'support' || currentTool.category === 'hinge') {
            applySymbolToNode(nodeId, currentTool.name, currentRotation, SYMBOL_DEFINITIONS);
        }
        else if (currentTool.category === 'load') {
            if (currentTool.name === 'force') {
                const mag = await askForMagnitude(10);
                Data.addLoad({ type: 'node', id: nodeId }, currentTool.name, mag, currentRotation);
                return;
            } else if (currentTool.name === 'distributed') {
                const params = await askForDistributedParams();

                if (params) {
                    Data.addLoad(
                        { type: 'member', id: memberId }, // Target
                        'distributed',                    // Type Name
                        params.mag,                       // Magnitude
                        0,                                // Rotation (usually 0 for local perpendicular)
                        { tStart: params.t0, tEnd: params.t1 } // Extra Data
                    );
                    // Force re-render after async add
                    if (window.triggerRender) window.triggerRender();
                }
                return;
            } else if (currentTool.name === 'moment') {
                const mag = await askForMagnitude(10);
                Data.addLoad({ type: 'node', id: nodeId }, currentTool.name, mag, currentRotation);
                return
            }
            return;
        }
    }

    // 3. CLICK ON EMPTY SPACE
    // ... inside executeStandardClick ...

    // 3. CLICK ON EMPTY SPACE (Potential Member Click)
    else {
        // First: Check if we clicked on a MEMBER (Beam)
        const memberId = Utils.findMemberAt(raw.x, raw.y, canvas);

        if (memberId !== null) {
            // --- DISTRIBUTED LOAD LOGIC ---
            if (currentTool.category === 'load' && currentTool.name === 'distributed') {
                const params = await askForDistributedParams(); // Open Modal

                if (params) {
                    Data.addLoad(
                        { type: 'member', id: memberId },
                        'distributed',
                        params.mag,
                        0, // Rotation 0 usually means perpendicular to beam
                        { tStart: params.t0, tEnd: params.t1 }
                    );
                    if (window.triggerRender) window.triggerRender();
                }
                return; // Stop here, don't create a node
            }

            // --- POINT LOAD ON MEMBER LOGIC ---
            if (currentTool.category === 'load' && (currentTool.name === 'point' || currentTool.name === 'force')) {
                const mag = await askForMagnitude(10);
                if (mag !== null) {
                    const t = Utils.calculateMemberT(memberId, snapped.realX, snapped.realY);
                    Data.addLoad({ type: 'member', id: memberId, t: t }, 'force', mag, currentRotation);
                }
                return;
            }
        }
        const newNode = Data.addNode(snapped.realX, snapped.realY);

        if (currentTool.category === 'connection') {  // DONT KNOW ABTOHT THIS SHIT HERE, could be stupdid
            if (interactionState.dragStartNodeId === null) {
                // Start dragging from this new node
                interactionState.dragStartNodeId = newNode.id;
            } else {
                // Finish connection to this new node
                Data.addMember(interactionState.dragStartNodeId, newNode.id, currentTool.name);
                interactionState.dragStartNodeId = null;
            }
        }
        else if (currentTool.category === 'support' || currentTool.category === 'hinge') {
            applySymbolToNode(newNode.id, currentTool.name, currentRotation, SYMBOL_DEFINITIONS);
        }
        // NO PLACEMENT IN EMPTY SPACE OF LOADS
        //else if (currentTool.category === 'load') {
        //    // Optional: Allow placing point loads on new nodes in empty space
        //    if (currentTool.name === 'force') {
        //        // We need to handle async here too if you want the modal
        //        askForMagnitude(10).then(mag => {
        //            if (mag !== null) Data.addLoad({ type: 'node', id: newNode.id }, 'force', mag, currentRotation);
        //        });
        //    }
        //}
    }
}



// Helper
function applySymbolToNode(nodeId, symbolName, rotation, SYMBOL_DEFINITIONS) {
    const def = SYMBOL_DEFINITIONS[symbolName];
    if (!def && symbolName !== 'none') return;

    const fixData = def ? {
        fix_x: def.fix_x || false,
        fix_y: def.fix_y || false,
        fix_m: def.fix_m || false,
        category: def.category
    } : { fix_x: false, fix_y: false, fix_m: false };

    Data.updateNodeSymbol(nodeId, symbolName, rotation, fixData);
}

function askForMagnitude(defaultValue = 10) {
    return new Promise((resolve) => {
        const modal = document.getElementById('magnitude-modal');
        const input = document.getElementById('magnitude-input');
        const btnConfirm = document.getElementById('magnitude-confirm');
        const btnCancel = document.getElementById('magnitude-cancel');

        input.value = defaultValue;
        modal.classList.remove('hidden');
        input.select();

        const close = (val) => {
            modal.classList.add('hidden');
            // Remove listeners to prevent memory leaks
            btnConfirm.onclick = null;
            btnCancel.onclick = null;
            input.onkeydown = null;
            resolve(val);
        };

        btnConfirm.onclick = () => close(parseFloat(input.value) || 0);
        btnCancel.onclick = () => close(null); // Return null on cancel

        // Enter key support
        input.onkeydown = (e) => {
            if (e.key === 'Enter') close(parseFloat(input.value) || 0);
            if (e.key === 'Escape') close(null);
        };
    });
}

function askForDistributedParams() {
    return new Promise((resolve) => {
        const modal = document.getElementById('dist-load-modal');
        const iMag = document.getElementById('dist-mag');
        const iStart = document.getElementById('dist-start');
        const iEnd = document.getElementById('dist-end');
        const btnConfirm = document.getElementById('dist-confirm');
        const btnCancel = document.getElementById('dist-cancel');


        // Defaults
        iMag.value = 5;
        iStart.value = 0;
        iEnd.value = 1;

        modal.classList.remove('hidden');

        const close = (result) => {
            modal.classList.add('hidden');
            btnConfirm.onclick = null;
            btnCancel.onclick = null;
            resolve(result);
        };

        btnConfirm.onclick = () => {
            const mag = parseFloat(iMag.value) || 0;
            let t0 = parseFloat(iStart.value) || 0;
            let t1 = parseFloat(iEnd.value) || 1;

            // Validation: Ensure range is valid
            t0 = Math.max(0, Math.min(1, t0));
            t1 = Math.max(0, Math.min(1, t1));
            if (t0 > t1) [t0, t1] = [t1, t0]; // Swap if user messed up

            close({ mag, t0, t1 });
        };

        btnCancel.onclick = () => close(null);
    });
}
