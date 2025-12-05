// structureData.js

export const SystemState = {
    nodes: [],
    members: [],
    gridSize: 1.0
};

// --- Node Management ---

export function addNode(x, y, symbolType = 'none', rotation = 0, fixData = {}) {
    const id = SystemState.nodes.length > 0 ? Math.max(...SystemState.nodes.map(n => n.id)) + 1 : 0;
    const newNode = {
        id,
        x,
        y,
        symbolType, // 'none', 'festlager', 'loslager', etc.
        rotation,
        fixData: fixData || { fix_x: false, fix_y: false, fix_m: false }
    };
    SystemState.nodes.push(newNode);
    return newNode;
}

export function updateNodeSymbol(nodeId, symbolType, rotation, fixData) {
    const node = SystemState.nodes.find(n => n.id === nodeId);
    if (node) {
        node.symbolType = symbolType;
        node.rotation = rotation;
        node.fixData = fixData;
    }
}

export function deleteNode(nodeId) {
    // 1. Remove the node
    SystemState.nodes = SystemState.nodes.filter(n => n.id !== nodeId);

    // 2. Remove any members connected to this node
    SystemState.members = SystemState.members.filter(m => m.startNodeId !== nodeId && m.endNodeId !== nodeId);
}

// --- Member Management ---

export function addMember(startNodeId, endNodeId) {
    // Prevent self-loops
    if (startNodeId === endNodeId) return;

    // Check for duplicates
    const exists = SystemState.members.some(m =>
        (m.startNodeId === startNodeId && m.endNodeId === endNodeId) ||
        (m.startNodeId === endNodeId && m.endNodeId === startNodeId)
    );

    if (!exists) {
        SystemState.members.push({
            id: SystemState.members.length, // Simple ID generation
            startNodeId,
            endNodeId
        });
    }
}

export function deleteMember(memberId) {
    SystemState.members = SystemState.members.filter(m => m.id !== memberId);
}

export function clearSystem() {
    SystemState.nodes = [];
    SystemState.members = [];
}

// --- Export Utility ---

export function getExportData() {
    return {
        nodes: SystemState.nodes.map(n => ({
            id: n.id,
            x: n.x,
            y: n.y,
            fix_x: n.fixData.fix_x,
            fix_y: n.fixData.fix_y,
            fix_m: n.fixData.fix_m,
            _visual_type: n.symbolType,
            _visual_rotation: n.rotation
        })),
        members: SystemState.members,
        gridSize: SystemState.gridSize
    };
}


export function loadSystem(data) {
    if (!data) return;

    clearSystem();

    if (data.gridSize) {
        SystemState.gridSize = parseFloat(data.gridSize) || 1.0;
        const gridInput = document.getElementById('grid-size-input');
        if (gridInput) gridInput.value = SystemState.gridSize;
    }

    if (Array.isArray(data.nodes)) {
        SystemState.nodes = data.nodes.map(n => ({
            id: n.id,
            x: n.x,
            y: n.y,
            // Restore visual properties from saved data or default to 'none'
            symbolType: n._visual_type || 'none',
            rotation: n._visual_rotation || 0,
            // Reconstruct fixData object from flat properties
            fixData: {
                fix_x: !!n.fix_x,
                fix_y: !!n.fix_y,
                fix_m: !!n.fix_m,
                // We might need to persist 'category' if it was part of the original logic, 
                // but usually fix_x/y/m determines the physics.
                category: n.category || undefined
            }
        }));
    }

    if (Array.isArray(data.members)) {
        // We can just copy them directly if the ID structure matches
        SystemState.members = data.members.map(m => ({
            id: m.id,
            startNodeId: m.startNodeId,
            endNodeId: m.endNodeId
        }));
    }

    console.log("System Loaded:", SystemState);
}
