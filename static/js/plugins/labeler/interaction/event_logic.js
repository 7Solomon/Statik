import * as Data from '../structureData.js';
import * as Utils from './utils.js';


// --- 1. MOUSE DOWN (Start Rotation or Drag) ---
export function handleMouseDown(snapped, raw, interactionState, currentRotation, currentTool) {
    interactionState.placementOrigin = snapped;

    const isRotationalTool = ['support', 'hinge', 'load'].includes(currentTool.category);

    if (isRotationalTool) {
        interactionState.isRotating = true;
        interactionState.initialMouseY = raw.y;
        interactionState.initialRotation = currentRotation;
        document.body.style.cursor = "ns-resize";
    }
}

// --- 2. MOUSE MOVE (Update Rotation) ---
export function handleMouseMove(raw, interactionState) {
    if (interactionState.isRotating) {
        const deltaY = raw.y - interactionState.initialMouseY;
        let rawRotation = interactionState.initialRotation - deltaY;
        rawRotation = (rawRotation % 360 + 360) % 360;

        const snapStep = 45;
        let newRotation = Math.round(rawRotation / snapStep) * snapStep;
        newRotation = newRotation % 360;

        if (window.updateRotation) window.updateRotation(newRotation);
        return true;
    }
}

// --- 3. MOUSE UP (Confirm Placement) ---
export function handleMouseUp(snapped, raw, currentTool, currentRotation, interactionState, canvas, SYMBOL_DEFINITIONS) {
    const targetPos = (interactionState.isRotating && interactionState.placementOrigin)
        ? interactionState.placementOrigin
        : snapped;

    if (interactionState.isRotating) {
        interactionState.isRotating = false;
        document.body.style.cursor = "default";
    }

    executeStandardClick(targetPos, raw, currentTool, currentRotation, interactionState, canvas, SYMBOL_DEFINITIONS);

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
        window.triggerRender(); // Ensure render on delete
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
                // FINISH DRAG

                // Helper to safely get releases and CATEGORY from a node
                const getReleasesFromNode = (nId) => {
                    const node = Data.SystemState.nodes.find(n => n.id === nId);
                    if (!node || !node.fixData) {
                        return { m: false, n: false, q: false, category: 'free_end' };
                    }
                    console.log(node)

                    return {
                        m: !node.fixData.fix_m,
                        n: false,
                        q: false,
                        category: node.fixData.fix_m ? 'biegesteife_ecke' : 'vollgelenk'
                    };


                };

                const releases = {
                    start: getReleasesFromNode(interactionState.dragStartNodeId),
                    end: getReleasesFromNode(nodeId)
                };

                Data.addMember(interactionState.dragStartNodeId, nodeId, currentTool.name, releases);
                interactionState.dragStartNodeId = null;
            }
        }
        else if (currentTool.category === 'support') {
            const def = SYMBOL_DEFINITIONS[currentTool.name];
            const fixData = {
                fix_x_local: def.fix_x_local,
                fix_y_local: def.fix_y_local,
                fix_m: def.fix_m,
            };
            Data.updateNode(nodeId, currentTool.name, currentRotation, fixData)
        }
        else if (currentTool.category === 'hinge') {
            const connectedMembers = Data.SystemState.members.filter(m =>
                m.startNodeId === nodeId || m.endNodeId === nodeId
            );
            const def = SYMBOL_DEFINITIONS[currentTool.name];

            connectedMembers.forEach(member => {
                // Check which side of the member connects to this node
                const isStart = member.startNodeId === nodeId;

                // Create the new release object for just THIS specific end
                const newEndRelease = {
                    m: def.releases_m,
                    n: def.releases_n,
                    q: def.releases_q,
                    category: currentTool.name // 'vollgelenk', 'normalkraft_gelenk', etc.
                };

                // Update the member's releases structure properly
                const updatedReleases = {
                    ...member.releases,
                    [isStart ? 'start' : 'end']: newEndRelease
                };

                Data.updateMember(member.id, updatedReleases);
            });
        }
        else if (currentTool.category === 'load') {
            if (currentTool.name === 'force') {
                const mag = await askForMagnitude(10);
                Data.addLoad({ type: 'node', id: nodeId }, currentTool.name, mag, currentRotation);
            } else if (currentTool.name === 'moment') {
                const mag = await askForMagnitude(10);
                Data.addLoad({ type: 'node', id: nodeId }, currentTool.name, mag, currentRotation);
            }
        }
    }

    // 3. CLICK ON EMPTY SPACE
    else {
        const memberId = Utils.findMemberAt(raw.x, raw.y, canvas);
        if (memberId !== null) {
            if (currentTool.category === 'load' && currentTool.name === 'distributed') {
                const params = await askForDistributedParams();
                if (params) {
                    Data.addLoad({ type: 'member', id: memberId }, 'distributed', params.mag, 0, { tStart: params.t0, tEnd: params.t1 });
                    if (window.triggerRender) window.triggerRender();
                }
                return;
            }
            if (currentTool.category === 'load' && ['point', 'force'].includes(currentTool.name)) {
                const mag = await askForMagnitude(10);
                if (mag !== null) {
                    const t = Utils.calculateMemberT(memberId, snapped.realX, snapped.realY);
                    Data.addLoad({ type: 'member', id: memberId, t: t }, 'force', mag, currentRotation);
                }
                return;
            }
        }

        // --- CONNECTION TOOL ---
        if (currentTool.category === 'connection') {
            const vollgelenkDef = SYMBOL_DEFINITIONS['vollgelenk'];

            const defaultFixData = {
                release_m: vollgelenkDef.releases_m,
                release_n: vollgelenkDef.releases_n,
                release_q: vollgelenkDef.releases_q,
            };

            const newNode = Data.addNode(snapped.realX, snapped.realY, 'vollgelenk', 0, defaultFixData);

            if (interactionState.dragStartNodeId === null) {
                interactionState.dragStartNodeId = newNode.id;
            } else {
                // Same helper as above
                const getReleasesFromNode = (nId) => {
                    const node = Data.SystemState.nodes.find(n => n.id === nId);
                    if (!node || !node.fixData) return { m: false, n: false, q: false, category: 'biegesteife_ecke' };
                    return {
                        m: node.fixData.release_m || false,
                        n: node.fixData.release_n || false,
                        q: node.fixData.release_q || false,
                        category: node.symbolType || 'biegesteife_ecke'
                    };
                };

                const releases = {
                    start: getReleasesFromNode(interactionState.dragStartNodeId),
                    end: getReleasesFromNode(newNode.id)
                };
                Data.addMember(interactionState.dragStartNodeId, newNode.id, currentTool.name, releases);
                interactionState.dragStartNodeId = null;
            }
        }

        else if (currentTool.category === 'support') {
            const def = SYMBOL_DEFINITIONS[currentTool.name];
            const fixData = {
                fix_x_local: def.fix_x_local,
                fix_y_local: def.fix_y_local,
                fix_m: def.fix_m,
            };
            Data.addNode(snapped.realX, snapped.realY, currentTool.name, currentRotation, fixData);
        }
    }

    // Always trigger render after an action
    if (window.triggerRender) window.triggerRender();
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
