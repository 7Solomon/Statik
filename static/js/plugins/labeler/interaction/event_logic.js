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

        console.log("Rotation Mode Started");
        document.body.style.cursor = "ns-resize";
    }
}

// --- 2. MOUSE MOVE (Update Rotation) ---
export function handleMouseMove(raw, interactionState) {
    if (interactionState.isRotating) {
        const deltaY = raw.y - interactionState.initialMouseY;

        let rawRotation = interactionState.initialRotation + deltaY;

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
        window.updateRotation(0);
    }
}

// --- CORE ACTION LOGIC ---
function executeStandardClick(snapped, raw, currentTool, currentRotation, interactionState, canvas, SYMBOL_DEFINITIONS) {

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
                interactionState.dragStartNodeId = nodeId;
            } else {
                // Connection is handled by main loop / drag logic usually, 
                // but if we clicked a node to finish, we can ensure it's processed.
                // (The interactionHandler usually handles the addMember call on MouseUp if dragging)
            }
        } else if (currentTool.category === 'support' || currentTool.category === 'hinge') {
            applySymbolToNode(nodeId, currentTool.name, currentRotation, SYMBOL_DEFINITIONS);
        } else if (currentTool.category === 'load') {
            Data.addLoad({ type: 'node', id: nodeId }, currentTool.name, 10, currentRotation);
        }
    }

    // 3. CLICK ON EMPTY SPACE
    else {
        // *** MEMBER FIX: If we are finishing a connection, DO NOT create a new node here ***
        if (currentTool.category === 'connection' && interactionState.dragStartNodeId !== null) {
            // Handeler.js handleMouseUp logic takes care of connecting 
            // dragStartNodeId to the current snapped location (creating a node if needed).
            return;
        }

        // Load on Member?
        if (currentTool.category === 'load') {
            const memberId = Utils.findMemberAt(raw.x, raw.y, canvas);
            if (memberId !== null) {
                const t = Utils.calculateMemberT(memberId, snapped.realX, snapped.realY);
                Data.addLoad({ type: 'member', id: memberId, t: t }, currentTool.name, 10, currentRotation);
                return;
            }
        }

        // Create Node (Only if we aren't dragging a connection)
        const newNode = Data.addNode(snapped.realX, snapped.realY);

        if (currentTool.category === 'support' || currentTool.category === 'hinge') {
            applySymbolToNode(newNode.id, currentTool.name, currentRotation, SYMBOL_DEFINITIONS);
        } else if (currentTool.category === 'load') {
            Data.addLoad({ type: 'node', id: newNode.id }, currentTool.name, 10, currentRotation);
        } else if (currentTool.category === 'connection') {
            if (interactionState.dragStartNodeId === null) {
                interactionState.dragStartNodeId = newNode.id;
            }
        }
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
