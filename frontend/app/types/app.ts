import type { Vec2 } from "./model";

export type ToolType =
    | 'select'
    | 'node'
    | 'member'
    | 'hinge'

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


export interface ViewportState {
    zoom: number;      // Scale factor (pixels per meter)
    pan: Vec2;        // Offset in pixels
    gridSize: number; // In meters (e.g., 1.0m)
}

export interface InteractionState {
    activeTool: ToolType;
    activeSubTypeTool: HingeType | SupportType | null
    isDragging: boolean;

    // Hover state for snapping
    hoveredNodeId: string | null;
    hoveredMemberId: string | null;

    // For creating members (drag from A to B)
    dragStartNodeId: string | null;

    // Current mouse position (snapped) in World Coords
    mousePos: Vec2;

    selectedId: string | null;
    selectedType: 'node' | 'member' | null;
}
