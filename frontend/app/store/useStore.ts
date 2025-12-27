import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type { InteractionState, ToolType, ViewportState } from '~/types/app';
import type { Load, Member, Vec2, Node, KinematicResult } from '~/types/model';

export type AppMode = 'EDITOR' | 'ANALYSIS';

// --- Default Values FOR EDITOR---
const DEFAULT_VIEWPORT: ViewportState = {
    zoom: 50, // 50 pixels = 1 meter
    pan: { x: 400, y: 400 }, // Initial center offset
    gridSize: 1.0,
};

const DEFAULT_INTERACTION: InteractionState = {
    activeTool: 'select',
    isDragging: false,
    hoveredNodeId: null,
    hoveredMemberId: null,
    dragStartNodeId: null,
    mousePos: { x: 0, y: 0 },
    selectedId: null,
    selectedType: null,
};

const DEFAULT_MEMBER_PROPS = {
    E: 210e9, // Steel (Pa)
    A: 0.005, // Area (m2)
    I: 0.0001, // Moment of Inertia (m4)
};

const DEFAULT_RELEASES = {
    fx: false, fy: false, mz: false
};

// --- Store Interface ---
interface AppState {
    mode: AppMode;

    // Data
    nodes: Node[];
    members: Member[];
    loads: Load[];

    // UI State
    viewport: ViewportState;
    interaction: InteractionState;

    // API 
    kinematicResult: KinematicResult | null;

    // Actions
    actions: {
        setMode: (mode: AppMode) => void;

        // EDITOR
        // Model Actions
        addNode: (pos: Vec2, supports?: Partial<Node['supports']>) => void;
        addMember: (startNodeId: string, endNodeId: string) => void;
        removeNode: (id: string) => void;
        selectObject: (id: string | null, type: 'node' | 'member' | null) => void;
        updateNode: (id: string, data: Partial<Node>) => void;
        updateMember: (id: string, data: Partial<Member>) => void;

        // UI Actions
        setTool: (tool: ToolType) => void;
        setViewport: (view: Partial<ViewportState>) => void;
        setInteraction: (inter: Partial<InteractionState>) => void;
        setHoveredNode: (id: string | null) => void;

        ///// ANALYSIATON
        analyzeSystem: (name: string) => Promise<void>;
        setKinematicResult: (result: KinematicResult | null) => void;
    };
}

// --- Store Implementation ---
export const useStore = create<AppState>((set, get) => ({

    mode: 'EDITOR',

    nodes: [],
    members: [],
    loads: [],

    viewport: DEFAULT_VIEWPORT,
    interaction: DEFAULT_INTERACTION,

    kinematicResult: null,

    actions: {
        addNode: (pos, supports) => {
            const newNode: Node = {
                id: uuidv4(),
                position: pos,
                rotation: 0,
                supports: {
                    fixX: false,
                    fixY: false,
                    fixM: false,
                    ...supports // Merge custom supports (e.g., if tool is 'support_fixed')
                },
            };
            set((state) => ({ nodes: [...state.nodes, newNode] }));
            return newNode.id; // Return ID in case we need to link it immediately
        },

        addMember: (startNodeId, endNodeId) => {
            // Prevent duplicate members and self-loops
            if (startNodeId === endNodeId) return;

            const exists = get().members.some(m =>
                (m.startNodeId === startNodeId && m.endNodeId === endNodeId) ||
                (m.startNodeId === endNodeId && m.endNodeId === startNodeId)
            );
            if (exists) return;

            const newMember: Member = {
                id: uuidv4(),
                startNodeId,
                endNodeId,
                properties: { ...DEFAULT_MEMBER_PROPS },
                releases: {
                    start: { ...DEFAULT_RELEASES },
                    end: { ...DEFAULT_RELEASES }
                }
            };
            set((state) => ({ members: [...state.members, newMember] }));
        },

        removeNode: (id) => {
            set((state) => ({
                nodes: state.nodes.filter(n => n.id !== id),
                // Cascade delete: remove connected members
                members: state.members.filter(m => m.startNodeId !== id && m.endNodeId !== id),
                // Cascade delete: remove loads on this node
                loads: state.loads.filter(l => !(l.target === 'node' && l.targetId === id))
            }));
        },

        setTool: (tool) => {
            set((state) => ({
                interaction: { ...state.interaction, activeTool: tool }
            }));
        },

        setViewport: (view) => {
            set((state) => ({
                viewport: { ...state.viewport, ...view }
            }));
        },

        setInteraction: (inter) => {
            set((state) => ({
                interaction: { ...state.interaction, ...inter }
            }));
        },

        setHoveredNode: (id) => {
            // Only update if changed to prevent thrashing
            if (get().interaction.hoveredNodeId !== id) {
                set((state) => ({
                    interaction: { ...state.interaction, hoveredNodeId: id }
                }));
            }
        },
        selectObject: (id: string | null, type: 'node' | 'member' | null) => {
            set(state => ({
                interaction: { ...state.interaction, selectedId: id, selectedType: type }
            }));
        },
        updateNode: (id: string, data: Partial<Node>) => {
            set(state => ({
                nodes: state.nodes.map(n => n.id === id ? { ...n, ...data } : n)
            }));
        },
        updateMember: (id: string, data: Partial<Member>) => {
            set(state => ({
                members: state.members.map(m => m.id === id ? { ...m, ...data } : m)
            }));
        },

        analyzeSystem: async (name: string) => {
            const state = get();

            const payload = {
                name: name,
                system: {
                    nodes: state.nodes,
                    members: state.members,
                    loads: state.loads,
                    // Save viewport settings to restore view later, why not
                    meta: {
                        gridSize: state.viewport.gridSize,
                        zoom: state.viewport.zoom,
                        pan: state.viewport.pan
                    }
                }
            };

            try {
                const response = await fetch('api/analyze/kinematics', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload),
                });

                if (!response.ok) {
                    throw new Error(`Export failed: ${response.statusText}`);
                }

                const result = await response.json();
                console.log('System saved successfully:', result.slug);

            } catch (error) {
                console.error('Failed to export system:', error);
            }
        },

        setMode: (mode) => set({ mode }),
        setKinematicResult: (result) => set({ kinematicResult: result }),
    }
}));
3