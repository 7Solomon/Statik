// structureData.js

export const SystemState = {
    nodes: [],
    members: [],
    loads: [],
    gridSize: 1.0
};

// --- Load Management ---
export function addLoad(target, type, values, angle = 0, extraParams = {}) {
    const primaryValue = Array.isArray(values) ? values[0] : values;

    let fx = 0, fy = 0, m = 0;

    // Physics for Point Loads / Moments
    if (type === 'force' || type === 'point') { // Handle both names if you use them
        const rad = (angle * Math.PI) / 180;
        fx = primaryValue * Math.cos(rad);
        fy = primaryValue * Math.sin(rad);
    } else if (type === 'moment') {
        m = primaryValue;
    }
    // Note: Distributed loads usually don't set global fx/fy here 
    // because it depends on member length.

    const newLoad = {
        id: SystemState.loads.length > 0 ? Math.max(...SystemState.loads.map(l => l.id)) + 1 : 0,

        type: type,
        values: Array.isArray(values) ? values : [values],
        angle: angle,

        // PHYSICS
        fx: parseFloat(fx.toFixed(4)),
        fy: parseFloat(fy.toFixed(4)),
        m: parseFloat(m.toFixed(4)),

        // LOCATION
        locationType: target.type, // 'node' or 'member'
        locationId: target.id,

        // POSITION: Default to target.t, but allow override from extraParams
        // This is crucial for Distributed Loads which pass { tStart, tEnd }
        t: target.t,

        // Spread extra params (tStart, tEnd) directly into the object
        ...extraParams
    };

    SystemState.loads.push(newLoad);
    return newLoad;
}


export function deleteLoadsOnNode(nodeId) {
    SystemState.loads = SystemState.loads.filter(l => l.nodeId !== nodeId);
}
// --- Node Management ---


export function addNode(x, y, symbolType, rotation, fixData) {
    const id = SystemState.nodes.length > 0 ? Math.max(...SystemState.nodes.map(n => n.id)) + 1 : 0;
    console.log(fixData)
    const newNode = {
        id,
        x,
        y,
        symbolType,
        rotation,
        fixData: fixData
    };
    SystemState.nodes.push(newNode);
    return newNode;
}

export function updateNode(nodeId, symbolType, rotation, fixData) {
    const node = SystemState.nodes.find(n => n.id === nodeId);
    if (node) {
        node.symbolType = symbolType;
        node.rotation = rotation;
        node.fixData = {
            fix_x_local: fixData.fix_x_local,
            fix_y_local: fixData.fix_y_local,
            fix_m: fixData.fix_m,
            category: fixData.category
        };
    }
}

export function updateMember(memberId, releases) {
    console.log(releases)
    const member = SystemState.members.find(m => m.id === memberId);
    if (!member) return;
    member.releases = releases;

}


export function deleteNode(nodeId) {
    // 1. Remove the node
    SystemState.nodes = SystemState.nodes.filter(n => n.id !== nodeId);

    // 2. Remove any members connected to this node
    SystemState.members = SystemState.members.filter(m => m.startNodeId !== nodeId && m.endNodeId !== nodeId);
}

// --- Member Management ---
export function addMember(startNodeId, endNodeId, type, releases) {
    if (startNodeId === endNodeId) return;
    console.log(releases)


    const exists = SystemState.members.some(m =>
        (m.startNodeId === startNodeId && m.endNodeId === endNodeId) ||
        (m.startNodeId === endNodeId && m.endNodeId === startNodeId)
    );
    //releases = {
    //            start: { m: false, n: false, q: true, category: '' },
    //            end: { m: false, n: false, q: true, category: '' }
    //        }

    if (!exists) {
        SystemState.members.push({
            id: SystemState.members.length,
            startNodeId,
            endNodeId,
            type: type,
            releases: releases
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
    console.log(SystemState.members)
    return {
        nodes: SystemState.nodes.map(n => ({
            id: n.id,
            x: n.x,
            y: n.y,
            fix_x_local: n.fixData.fix_x_local,
            fix_y_local: n.fixData.fix_y_local,
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
                fix_x_local: !!n.fix_x_local,
                fix_y_local: !!n.fix_y_local,
                fix_m: !!n.fix_m,
                category: n.category
            }
        }));
    }

    // 3. Members
    if (Array.isArray(data.members)) {
        SystemState.members = data.members.map(m => ({
            id: m.id,
            startNodeId: m.startNodeId,
            endNodeId: m.endNodeId,
            releases: m.releases,
            type: m.type || 'normal'  // normal CAN BE LATER DELETED BUT NOW COMPATIABILITY
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
