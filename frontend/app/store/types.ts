import type { Load, Member, Node, KinematicResult, Release, Vec2, StructuralSystem, FEMResult, Scheibe, Constraint, DynamicAnalysisResult } from '~/types/model';
import type { AnalysisInteractionState, EditorInteractionState, ToolType, ViewportState } from '~/types/app';

// --- SHARED DOMAIN ---
export type AppMode = 'EDITOR' | 'ANALYSIS' | 'MODELS';
export type AnalysisViewMode = 'KINEMATIC' | 'SIMPLIFIED' | 'SOLUTION' | 'DYNAMIC';;
export type ModelViewMode = 'TRAINING' | 'DATASETS';

// --- EDITOR DOMAIN ---
export interface EditorState {
    nodes: Node[];
    members: Member[];
    loads: Load[];
    scheiben: Scheibe[];
    constraints: Constraint[];
    viewport: ViewportState;
    interaction: EditorInteractionState;
}

// EditorActions interface
export interface EditorActions {
    addNode: (pos: Vec2, supports?: Partial<Node['supports']>) => string;
    addMember: (startNodeId: string, endNodeId: string) => void;
    addHingeAtNode: (nodeId: string, releases: Partial<Release>) => void;
    addLoad: (data: Load) => void;
    addScheibe: (data: Omit<Scheibe, 'id'>) => string;
    addConstraint: (constraint: Constraint) => void;
    removeNode: (id: string) => void;
    removeScheibe: (id: string) => void;
    removeConstraint: (id: string) => void;
    selectObject: (id: string | null, type: 'node' | 'member' | 'load' | 'scheibe' | 'constraint' | null) => void;
    updateNode: (id: string, data: Partial<Node>) => void;
    updateMember: (id: string, data: Partial<Member>) => void;
    updateLoad: (id: string, data: Partial<Load>) => void;
    updateScheibe: (id: string, data: Partial<Scheibe>) => void;
    updateConstraint: (id: string, data: Partial<Constraint>) => void;
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
    dynamicResult: DynamicAnalysisResult | null;
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
    setDynamicResult: (result: DynamicAnalysisResult | null) => void;
}

// --- DATASET & MODEL DOMAIN ---
export interface Dataset {
    path: string;
    yaml: string;
    created: number;
    name: string;
}

export interface Model {
    name: string;
    created: number;
    path: string;
}

export interface ModelManagementState {
    viewMode: ModelViewMode;
    datasets: Dataset[];
    models: Model[];
    isLoading: boolean;
    currentPreviewConfig: any | null;
}

export interface ModelManagementActions {
    setViewMode: (mode: ModelViewMode) => void;

    // Data Fetching
    fetchDatasets: () => Promise<void>;
    fetchModels: () => Promise<void>;

    // Actions
    generateDataset: (numSamples: number, forceRecreate?: boolean) => Promise<void>;
    previewSymbols: () => Promise<void>;

    // API Helpers
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
    model_management: ModelManagementState & { actions: ModelManagementActions };
    shared: SharedState & { actions: SharedActions };
}
