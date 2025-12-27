import { v4 as uuidv4 } from 'uuid';
import type { InteractionState, ViewportState } from '~/types/app';
import type { Node, Member, Load } from '~/types/model';
import type { AppStore, EditorState, EditorActions } from './types';
import type { StateCreator } from 'zustand';

// Constants
const DEFAULT_VIEWPORT: ViewportState = {
    zoom: 50,
    pan: { x: 400, y: 400 },
    gridSize: 1.0,
    width: 0,
    height: 0,
    x: 0,
    y: 0
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
    E: 210e9,
    A: 0.005,
    I: 0.0001,
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
    viewport: DEFAULT_VIEWPORT,
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
                    ...supports
                },
            };
            set((state) => ({ nodes: [...state.nodes, newNode] }));
            return newNode.id;
        },

        addMember: (startNodeId, endNodeId) => {
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

                    if (member.startNodeId === nodeId) {
                        newReleases.start = { ...newReleases.start, ...releaseConfig };
                        modified = true;
                    }
                    if (member.endNodeId === nodeId) {
                        newReleases.end = { ...newReleases.end, ...releaseConfig };
                        modified = true;
                    }

                    return modified ? { ...member, releases: newReleases } : member;
                })
            }));
        },

        addLoad: (load) => {
            set((state) => ({ loads: [...state.loads, load] }));
        },

        // --- UPDATED REMOVE NODE ---
        removeNode: (id) => {
            set((state) => {
                const connectedMembers = state.members.filter(m => m.startNodeId === id || m.endNodeId === id);
                const connectedMemberIds = connectedMembers.map(m => m.id);

                return {
                    nodes: state.nodes.filter(n => n.id !== id),
                    members: state.members.filter(m => !connectedMemberIds.includes(m.id)),
                    loads: state.loads.filter(l => {
                        // 1. Check if it's on this Node
                        if (l.scope === 'NODE' && l.nodeId === id) return false;

                        // 2. Check if it's on a Deleted Member
                        if (l.scope === 'MEMBER' && connectedMemberIds.includes(l.memberId)) return false;

                        return true;
                    })
                };
            });
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
            if (get().interaction.hoveredNodeId !== id) {
                set((state) => ({
                    interaction: { ...state.interaction, hoveredNodeId: id }
                }));
            }
        },
        selectObject: (id, type) => set(s => ({ interaction: { ...s.interaction, selectedId: id, selectedType: type } })),

        updateNode: (id, data) => set(s => ({
            nodes: s.nodes.map(n => n.id === id ? { ...n, ...data } : n)
        })),

        updateMember: (id, data) => set(s => ({
            members: s.members.map(m => m.id === id ? { ...m, ...data } : m)
        })),

        updateLoad: (id, data) => set(s => ({
            loads: s.loads.map(l => {
                if (l.id !== id) return l;
                return { ...l, ...data } as Load;
            })
        })),
    }
});
