import type { Load, Member, Node, KinematicResult, Release, Vec2 } from '~/types/model';
import type { InteractionState, ToolType, ViewportState } from '~/types/app';

export type AppMode = 'EDITOR' | 'ANALYSIS';

// --- EDITOR TYPES ---
export interface EditorState {
    nodes: Node[];
    members: Member[];
    loads: Load[];
    viewport: ViewportState;
    interaction: InteractionState;
}

export interface EditorActions {
    addNode: (pos: Vec2, supports?: Partial<Node['supports']>) => void;
    addMember: (startNodeId: string, endNodeId: string) => void;
    addHingeAtNode: (nodeId: string, releases: Partial<Release>) => void;
    removeNode: (id: string) => void;
    selectObject: (id: string | null, type: 'node' | 'member' | null) => void;
    updateNode: (id: string, data: Partial<Node>) => void;
    updateMember: (id: string, data: Partial<Member>) => void;
    setTool: (tool: ToolType) => void;
    setViewport: (view: Partial<ViewportState>) => void;
    setInteraction: (inter: Partial<InteractionState>) => void;
    setHoveredNode: (id: string | null) => void;
}

// --- ANALYSIS TYPES ---
export interface AnalysisState {
    kinematicResult: KinematicResult | null;
}

export interface AnalysisActions {
    analyzeSystem: (name: string) => Promise<void>;
    setKinematicResult: (result: KinematicResult | null) => void;
}

// --- SHARED TYPES ---
export interface SharedState {
    mode: AppMode;
}

export interface SharedActions {
    setMode: (mode: AppMode) => void;
}

// --- THE BIG MERGE ---
// This is the key part: "actions" contains the union of all action types
export interface AppStore extends EditorState, AnalysisState, SharedState {
    actions: EditorActions & AnalysisActions & SharedActions;
}
