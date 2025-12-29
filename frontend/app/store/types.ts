import type { Load, Member, Node, KinematicResult, Release, Vec2, StructuralSystem, FEMResult } from '~/types/model';
import type { AnalysisInteractionState, EditorInteractionState, ToolType, ViewportState } from '~/types/app';

// --- SHARED DOMAIN ---
export type AppMode = 'EDITOR' | 'ANALYSIS' | 'DATASET';
export type AnalysisViewMode = 'KINEMATIC' | 'SIMPLIFIED' | 'SOLUTION';

// --- EDITOR DOMAIN ---
export interface EditorState {
    nodes: Node[];
    members: Member[];
    loads: Load[];
    viewport: ViewportState;
    interaction: EditorInteractionState;
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
    setInteraction: (inter: Partial<EditorInteractionState>) => void;
    setHoveredNode: (id: string | null) => void;
    loadStructuralSystem: (system: StructuralSystem) => void;
    exportStructuralSystem: () => StructuralSystem;
}

// --- ANALYSIS DOMAIN ---
export interface AnalysisSession {
    system: StructuralSystem;
    viewMode: AnalysisViewMode;
    viewport: ViewportState;
    interaction: AnalysisInteractionState;
    kinematicResult: KinematicResult | null;
    simplifyResult: StructuralSystem | null;
    solutionResult: FEMResult | null;
}

export interface AnalysisState {
    analysisSession: AnalysisSession | null;
}

export interface AnalysisActions {
    startAnalysis: (system: StructuralSystem) => void;
    clearAnalysisSession: () => void;
    setViewMode: (mode: AnalysisViewMode) => void;
    setViewport: (view: Partial<ViewportState>) => void;
    setInteraction: (inter: Partial<AnalysisInteractionState>) => void;
    setKinematicResult: (result: KinematicResult | null) => void;
    setSimplifyResult: (result: StructuralSystem | null) => void;
    setSolutionResult: (result: FEMResult | null) => void;
}

// --- DATASET DOMAIN ---
export interface Dataset {
    path: string;
    yaml: string;
    created: number;
}

export interface DatasetState {
    datasets: Dataset[];
    isLoading: boolean;
    currentPreviewConfig: any | null;
}

export interface DatasetActions {
    fetchDatasets: () => Promise<void>;
    generateDataset: (numSamples: number, forceRecreate?: boolean) => Promise<void>;
    previewSymbols: () => Promise<void>;

    getDatasetInfo: (datasetPath: string) => Promise<any>;
    getSplitImages: (datasetPath: string, split: 'train' | 'val' | 'test') => Promise<any[]>;
    getImageLabels: (datasetPath: string, split: string, stem: string) => Promise<any[]>;
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
    dataset: DatasetState & { actions: DatasetActions };
    shared: SharedState & { actions: SharedActions };
}
