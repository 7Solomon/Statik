// structureData.js

export const SystemState = {
    nodes: [],
    members: [],
    loads: [],
    gridSize: 1.0
};

// --- Load Management ---
export function addLoad(target, type, values, angle = 0) {
    // 1. Get a Primary Value for basic component calc
    // If values is [10], val = 10. If [10, 20], val = 10 (start).
    const primaryValue = Array.isArray(values) ? values[0] : values;

    let fx = 0, fy = 0, m = 0;

    if (type === 'force') {
        const rad = (angle * Math.PI) / 180;
        fx = primaryValue * Math.cos(rad);
        fy = primaryValue * Math.sin(rad);

    } else if (type === 'moment') {
        m = primaryValue;
    }

    const newLoad = {
        id: SystemState.loads.length > 0 ? Math.max(...SystemState.loads.map(l => l.id)) + 1 : 0,

        type: type,
        values: Array.isArray(values) ? values : [values], // Always store as array
        angle: angle,

        // PHYSICS (Cached for Point Loads)
        fx: parseFloat(fx.toFixed(4)),
        fy: parseFloat(fy.toFixed(4)),
        m: parseFloat(m.toFixed(4)),

        // LOCATION
        locationType: target.type, // 'node' or 'member'
        locationId: target.id,

        // POSITON (Polymorphic: float or array)
        t: target.t
    };

    SystemState.loads.push(newLoad);
    return newLoad;
}

export function deleteLoadsOnNode(nodeId) {
    SystemState.loads = SystemState.loads.filter(l => l.nodeId !== nodeId);
}
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
    SystemState.loads = [];
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
        loads: SystemState.loads,
        gridSize: SystemState.gridSize
    };
}

export function loadSystem(data) {
    if (!data) return;

    clearSystem();

    // 1. Grid
    if (data.gridSize) {
        SystemState.gridSize = parseFloat(data.gridSize) || 1.0;
        const gridInput = document.getElementById('grid-size-input');
        if (gridInput) gridInput.value = SystemState.gridSize;
    }

    // 2. Nodes
    if (Array.isArray(data.nodes)) {
        SystemState.nodes = data.nodes.map(n => ({
            id: n.id,
            x: n.x,
            y: n.y,
            symbolType: n._visual_type || 'none',
            rotation: n._visual_rotation || 0,
            fixData: {
                fix_x: !!n.fix_x,
                fix_y: !!n.fix_y,
                fix_m: !!n.fix_m,
                category: n.category || undefined
            }
        }));
    }

    // 3. Members
    if (Array.isArray(data.members)) {
        SystemState.members = data.members.map(m => ({
            id: m.id,
            startNodeId: m.startNodeId,
            endNodeId: m.endNodeId
        }));
    }

    // 4. Loads (UPDATED)
    if (Array.isArray(data.loads)) {
        SystemState.loads = data.loads.map(l => ({
            id: l.id,

            // Core Identity
            type: l.type || 'force',

            // Values (Handle legacy single value vs new array)
            values: Array.isArray(l.values) ? l.values : [l.value || 10],
            angle: l.angle || 0,

            // Physics Components
            fx: l.fx || 0,
            fy: l.fy || 0,
            m: l.m || 0,

            // Location Strategy (Handle migration from old nodeId schema)
            locationType: l.locationType || (l.nodeId !== undefined ? 'node' : 'member'),
            locationId: l.locationId !== undefined ? l.locationId : (l.nodeId !== undefined ? l.nodeId : l.memberId),

            // Position
            t: l.t // Can be null, float, or array
        }));
    }

    console.log("System Loaded:", SystemState);
}
