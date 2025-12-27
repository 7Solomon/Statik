import { v4 as uuidv4 } from 'uuid';
import type { InteractionState, ViewportState } from '~/types/app';
import type { Node } from '~/types/model';
import type { AppStore, EditorState, EditorActions } from './types';
import type { StateCreator } from 'zustand';
import type { Member } from '~/types/model';

// Constants
const DEFAULT_VIEWPORT: ViewportState = {
    zoom: 50, // 50 pixels = 1 meter
    pan: { x: 400, y: 400 }, // Initial center offset
    gridSize: 1.0,
};

const DEFAULT_INTERACTION: InteractionState = {
    activeTool: 'select',
    activeSubTypeTool: null,
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

export const createEditorSlice: StateCreator<
    AppStore,
    [],
    [],
    EditorState & { actions: EditorActions }
> = (set, get) => ({
    nodes: [],
    members: [],
    loads: [],
    viewport: { zoom: 50, pan: { x: 400, y: 400 }, gridSize: 1.0 },
    interaction: DEFAULT_INTERACTION,

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
        addHingeAtNode: (nodeId, releaseConfig) => {
            set((state) => ({
                members: state.members.map((member) => {
                    const newReleases = {
                        start: { ...member.releases.start },
                        end: { ...member.releases.end }
                    };
                    let modified = false;

                    // If member starts at this node, merge the release config
                    if (member.startNodeId === nodeId) {
                        newReleases.start = { ...newReleases.start, ...releaseConfig };
                        modified = true;
                    }

                    // If member ends at this node, merge the release config
                    if (member.endNodeId === nodeId) {
                        newReleases.end = { ...newReleases.end, ...releaseConfig };
                        modified = true;
                    }

                    return modified ? { ...member, releases: newReleases } : member;
                })
            }));
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
    }
});
