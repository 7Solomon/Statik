import type { Load, Member, Node, KinematicResult, Release, Vec2 } from '~/types/model';
import type { InteractionState, ToolType, ViewportState } from '~/types/app';

export type AppMode = 'EDITOR' | 'ANALYSIS';

// --- EDITOR DOMAIN ---
export interface EditorState {
    nodes: Node[];
    members: Member[];
    loads: Load[];
    viewport: ViewportState;
    interaction: InteractionState;
}

export interface EditorActions {
    addNode: (pos: Vec2, supports?: Partial<Node['supports']>) => string;
    addMember: (startNodeId: string, endNodeId: string) => void;
    addHingeAtNode: (nodeId: string, releases: Partial<Release>) => void;
    addLoad: (data: Load) => void;
    removeNode: (id: string) => void;
    selectObject: (id: string | null, type: 'node' | 'member' | 'load' | null) => void;
    updateNode: (id: string, data: Partial<Node>) => void;
    updateMember: (id: string, data: Partial<Member>) => void;
    updateLoad: (id: string, data: Partial<Load>) => void;
    setTool: (tool: ToolType) => void;
    setViewport: (view: Partial<ViewportState>) => void;
    setInteraction: (inter: Partial<InteractionState>) => void;
    setHoveredNode: (id: string | null) => void;
}

// --- ANALYSIS DOMAIN ---
export interface AnalysisState {
    kinematicResult: KinematicResult | null;
}

export interface AnalysisActions {
    analyzeSystem: (name: string) => Promise<void>;
    setKinematicResult: (result: KinematicResult | null) => void;
}

// --- SHARED DOMAIN ---
export interface SharedState {
    mode: AppMode;
}

export interface SharedActions {
    setMode: (mode: AppMode) => void;
}

// --- THE ROOT STORE ---
export interface AppStore {
    editor: EditorState & { actions: EditorActions };
    analysis: AnalysisState & { actions: AnalysisActions };
    shared: SharedState & { actions: SharedActions };
}
