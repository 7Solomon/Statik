import type { Vec2 } from "./model";

export type ToolType =
    | 'select'
    | 'node'
    | 'member'
    | 'hinge'
    | 'load'
    | 'scheibe'
    | 'constraint'

export type HingeType =
    | 'vollgelenk'
    | 'schubgelenk'
    | 'normalkraftgelenk'
    | 'biegesteife_ecke';

export type SupportType =
    | 'festlager'
    | 'loslager'
    | 'feste_einspannung'
    | 'gleitlager'
    | 'feder'
    | 'torsionsfeder';

export type LoadType =
    | 'point'
    | 'moment'
    | 'distributed'
    | 'dynamic_force'
    | 'dynamic_moment'

export type ScheibeShape =
    | 'rectangle'
    | 'triangle'
    | 'circle'
    | 'polygon'

export type ConstraintType =
    | 'spring'
    | 'damper'
    | 'cable';

export interface ViewportState {
    width: number;
    height: number;
    //x: number;
    //y: number;
    zoom: number;      // Scale factor (pixels per meter)
    pan: Vec2;        // Offset in pixels
    gridSize: number; // In meters (e.g., 1.0m)
}

export interface EditorInteractionState {
    activeTool: ToolType;
    activeSubTypeTool: HingeType | SupportType | LoadType | ScheibeShape | ConstraintType | null;

    isDragging: boolean;
    mousePos: Vec2; // World coordinates

    // Snapping & Hovering
    hoveredNodeId: string | null;
    hoveredMemberId: string | null;
    hoveredConstraintId: string | null;

    creationState: {
        mode: 'idle' | 'drawing_member' | 'sizing_load' | 'sizing_scheibe' | 'drawing_constraint';
        startPos: Vec2 | null;
        activeId: string | null;
    };

    // Selection
    selectedId: string | null;
    selectedType: 'node' | 'member' | 'load' | 'scheibe' | 'constraint' | null;
}


export interface AnalysisInteractionState {
    isDragging: boolean;
    mousePos: Vec2;

    hoveredNodeId: string | null;
    hoveredMemberId: string | null;
}
