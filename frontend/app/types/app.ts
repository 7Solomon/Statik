import type { Vec2 } from "./model";

export type ToolType =
    | 'select'
    | 'node'
    | 'member'
    | 'hinge'
    | 'load'
    | 'scheibe'

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
    | 'distributed';

export type ScheibeShape =
    | 'rectangle'
    | 'triangle'
    | 'circle'
    | 'polygon'

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
    activeSubTypeTool: HingeType | SupportType | LoadType | ScheibeShape | null;

    isDragging: boolean;
    mousePos: Vec2; // World coordinates

    // Snapping & Hovering
    hoveredNodeId: string | null;
    hoveredMemberId: string | null;

    // NEW: Unified creation state
    creationState: {
        mode: 'idle' | 'drawing_member' | 'sizing_load' | 'sizing_scheibe';
        startPos: Vec2 | null;
        activeId: string | null;
    };

    // Selection
    selectedId: string | null;
    selectedType: 'node' | 'member' | 'load' | 'scheibe' | null;
}


export interface AnalysisInteractionState {
    isDragging: boolean;
    mousePos: Vec2;

    hoveredNodeId: string | null;
    hoveredMemberId: string | null;
}
