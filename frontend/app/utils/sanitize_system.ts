import type { ViewportState } from '~/types/app';
import type { Node, Member, Load, Scheibe, Release, ScheibeConnection, SupportValue, Vec2, Constraint } from '~/types/model';

export const DEFAULT_VIEWPORT: ViewportState = {
    zoom: 50,
    pan: { x: 400, y: 400 },
    gridSize: 1.0,
    width: 0,
    height: 0,
};

export const DEFAULT_INTERACTION = {
    activeTool: 'select' as const,
    activeSubTypeTool: null,
    isDragging: false,
    hoveredNodeId: null,
    hoveredMemberId: null,
    hoveredConstraintId: null,
    mousePos: { x: 0, y: 0 },
    selectedId: null,
    selectedType: null,
    creationState: {
        mode: 'idle' as const,
        startPos: null,
        activeId: null
    }
};

export const DEFAULT_MEMBER_PROPS = {
    E: 210e9,
    A: 0.005,
    I: 0.0001,
    m: 1,
};

export const DEFAULT_SCHEIBE_PROPS = {
    E: 210e9,
    nu: 0.3,
    thickness: 0.2,
    rho: 2500,
};

export const DEFAULT_RELEASES: Release = {
    fx: false,
    fy: false,
    mz: false
};

export const DEFAULT_NODE_SUPPORTS = {
    fixN: false,
    fixV: false,
    fixM: false,
};

export const DEFAULT_SPRING_PROPS = {
    k: 1000, // kN/m
    preload: 0
};

export const DEFAULT_DAMPER_PROPS = {
    c: 100, // kN·s/m
    k: undefined
};

export const DEFAULT_CABLE_PROPS = {
    EA: 210000, // kN
    prestress: 0,
    weightPerLength: 0
};


export const sanitizeVec2 = (vec: any): Vec2 | null => {
    if (typeof vec?.x !== 'number' || typeof vec?.y !== 'number') return null;
    return { x: vec.x, y: vec.y };
};

export const sanitizeRelease = (release: any): Release => {
    return {
        fx: release?.fx === true,
        fy: release?.fy === true,
        mz: release?.mz === true
    };
};

export const sanitizeSupportValue = (value: any): SupportValue => {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'number') return value;
    return false; // Default to free
};

export const sanitizeNode = (node: any): Node | null => {
    // Must have id and position at minimum
    if (!node?.id || typeof node.id !== 'string') return null;

    const position = sanitizeVec2(node.position);
    if (!position) return null;

    return {
        id: node.id,
        position,
        rotation: typeof node.rotation === 'number' ? node.rotation : 0,
        supports: {
            fixN: sanitizeSupportValue(node.supports?.fixN),
            fixV: sanitizeSupportValue(node.supports?.fixV),
            fixM: sanitizeSupportValue(node.supports?.fixM),
        }
    };
};

export const sanitizeMember = (member: any): Member | null => {
    // Must have id, startNodeId, and endNodeId
    if (!member?.id || typeof member.id !== 'string') return null;
    if (!member?.startNodeId || typeof member.startNodeId !== 'string') return null;
    if (!member?.endNodeId || typeof member.endNodeId !== 'string') return null;

    return {
        id: member.id,
        startNodeId: member.startNodeId,
        endNodeId: member.endNodeId,
        properties: {
            E: typeof member.properties?.E === 'number' ? member.properties.E : DEFAULT_MEMBER_PROPS.E,
            A: typeof member.properties?.A === 'number' ? member.properties.A : DEFAULT_MEMBER_PROPS.A,
            I: typeof member.properties?.I === 'number' ? member.properties.I : DEFAULT_MEMBER_PROPS.I,
            m: typeof member.properties?.m === 'number' ? member.properties.m : DEFAULT_MEMBER_PROPS.m,
        },
        releases: {
            start: sanitizeRelease(member.releases?.start),
            end: sanitizeRelease(member.releases?.end)
        }
    };
};
const sanitizeScheibeConnection = (conn: any): ScheibeConnection | null => {
    if (!conn?.nodeId || typeof conn.nodeId !== 'string') return null;

    return {
        nodeId: conn.nodeId,
        releases: conn.releases ? sanitizeRelease(conn.releases) : undefined
    };
};

export const sanitizeScheibe = (scheibe: any): Scheibe | null => {
    // Must have id
    if (!scheibe?.id || typeof scheibe.id !== 'string') return null;
    console.log(scheibe)
    // Validate shape

    const incomingShape = scheibe.shape?.toUpperCase();

    const validShapes = ['RECTANGLE', 'TRIANGLE', 'CUSTOM'];
    if (!validShapes.includes(incomingShape)) return null;

    // Validate required geometry
    const corner1 = sanitizeVec2(scheibe.corner1);
    const corner2 = sanitizeVec2(scheibe.corner2);
    if (!corner1 || !corner2) return null;

    // Validate type
    const type = scheibe.type === 'ELASTIC' ? 'ELASTIC' : 'RIGID';

    // Sanitize connections
    const connections = Array.isArray(scheibe.connections)
        ? scheibe.connections
            .map((c: any) => sanitizeScheibeConnection(c))
            .filter((c: any): c is ScheibeConnection => c !== null)
        : [];

    // Sanitize additional points if present
    const additionalPoints = Array.isArray(scheibe.additionalPoints)
        ? scheibe.additionalPoints
            .map((p: any) => sanitizeVec2(p))
            .filter((p: any): p is Vec2 => p !== null)
        : undefined;

    // Validate meshLevel
    const meshLevel = [1, 2, 3, 4, 5].includes(scheibe.meshLevel)
        ? scheibe.meshLevel as (1 | 2 | 3 | 4 | 5)
        : undefined;

    console.log(scheibe)

    return {
        id: scheibe.id,
        shape: scheibe.shape,
        corner1,
        corner2,
        additionalPoints,
        rotation: typeof scheibe.rotation === 'number' ? scheibe.rotation : 0,
        type,
        properties: {
            E: typeof scheibe.properties?.E === 'number' ? scheibe.properties.E : DEFAULT_SCHEIBE_PROPS.E,
            nu: typeof scheibe.properties?.nu === 'number' ? scheibe.properties.nu : DEFAULT_SCHEIBE_PROPS.nu,
            thickness: typeof scheibe.properties?.thickness === 'number' ? scheibe.properties.thickness : DEFAULT_SCHEIBE_PROPS.thickness,
            rho: typeof scheibe.properties?.rho === 'number' ? scheibe.properties.rho : DEFAULT_SCHEIBE_PROPS.rho,
        },
        connections,
        meshLevel
    };
};

export const sanitizeConstraint = (constraint: any): Constraint | null => {
    // Must have id, type, and both node IDs
    if (!constraint?.id || typeof constraint.id !== 'string') return null;
    if (!constraint?.type) return null;
    if (!constraint?.startNodeId || typeof constraint.startNodeId !== 'string') return null;
    if (!constraint?.endNodeId || typeof constraint.endNodeId !== 'string') return null;

    const baseConstraint = {
        id: constraint.id,
        startNodeId: constraint.startNodeId,
        endNodeId: constraint.endNodeId,
        rotation: typeof constraint.rotation === 'number' ? constraint.rotation : undefined
    };

    switch (constraint.type) {
        case 'SPRING':
            return {
                ...baseConstraint,
                type: 'SPRING',
                k: typeof constraint.k === 'number' ? constraint.k : DEFAULT_SPRING_PROPS.k,
                preload: typeof constraint.preload === 'number' ? constraint.preload : DEFAULT_SPRING_PROPS.preload
            };

        case 'DAMPER':
            return {
                ...baseConstraint,
                type: 'DAMPER',
                c: typeof constraint.c === 'number' ? constraint.c : DEFAULT_DAMPER_PROPS.c,
                k: typeof constraint.k === 'number' ? constraint.k : DEFAULT_DAMPER_PROPS.k
            };

        case 'CABLE':
            return {
                ...baseConstraint,
                type: 'CABLE',
                EA: typeof constraint.EA === 'number' ? constraint.EA : DEFAULT_CABLE_PROPS.EA,
                prestress: typeof constraint.prestress === 'number' ? constraint.prestress : DEFAULT_CABLE_PROPS.prestress,
                weightPerLength: typeof constraint.weightPerLength === 'number' ? constraint.weightPerLength : DEFAULT_CABLE_PROPS.weightPerLength
            };

        default:
            return null;
    }
};

export const sanitizeLoad = (load: any): Load | null => {
    // Must have id and scope at minimum
    if (!load?.id || typeof load.id !== 'string') return null;
    if (!load?.scope) return null;

    // Basic validation - you might want to add more specific checks based on Load type
    return load as Load;
};