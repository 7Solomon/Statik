import { v4 as uuidv4 } from 'uuid';
import type { AppStore, EditorActions, EditorState } from './types';
import type { StateCreator } from 'zustand';
import type { Node, Member, Load } from '~/types/model';

// Constants
const DEFAULT_VIEWPORT = {
    zoom: 50,
    pan: { x: 400, y: 400 },
    gridSize: 1.0,
    width: 0,
    height: 0,
    x: 0,
    y: 0
};

const DEFAULT_INTERACTION = {
    activeTool: 'select' as const,
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
    Pick<AppStore, 'editor'>
> = (set, get) => ({
    editor: {
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

                set((state) => ({
                    editor: {
                        ...state.editor,
                        nodes: [...state.editor.nodes, newNode]
                    }
                }));
                return newNode.id;
            },

            addMember: (startNodeId, endNodeId) => {
                // Access state via nested path
                const { members } = get().editor;

                if (startNodeId === endNodeId) return;

                const exists = members.some(m =>
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

                set((state) => ({
                    editor: {
                        ...state.editor,
                        members: [...state.editor.members, newMember]
                    }
                }));
            },

            addHingeAtNode: (nodeId, releaseConfig) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        members: state.editor.members.map((member) => {
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
                    }
                }));
            },

            addLoad: (load) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        loads: [...state.editor.loads, load]
                    }
                }));
            },

            removeNode: (id) => {
                set((state) => {
                    // Extract from nested state
                    const { members, nodes, loads } = state.editor;

                    const connectedMembers = members.filter(m => m.startNodeId === id || m.endNodeId === id);
                    const connectedMemberIds = connectedMembers.map(m => m.id);

                    return {
                        editor: {
                            ...state.editor, // Preserve actions & viewport
                            nodes: nodes.filter(n => n.id !== id),
                            members: members.filter(m => !connectedMemberIds.includes(m.id)),
                            loads: loads.filter(l => {
                                if (l.scope === 'NODE' && l.nodeId === id) return false;
                                if (l.scope === 'MEMBER' && connectedMemberIds.includes(l.memberId)) return false;
                                return true;
                            })
                        }
                    };
                });
            },

            setTool: (tool) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        interaction: { ...state.editor.interaction, activeTool: tool }
                    }
                }));
            },

            setViewport: (view) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        viewport: { ...state.editor.viewport, ...view }
                    }
                }));
            },

            setInteraction: (inter) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        interaction: { ...state.editor.interaction, ...inter }
                    }
                }));
            },

            setHoveredNode: (id) => {
                if (get().editor.interaction.hoveredNodeId !== id) {
                    set((state) => ({
                        editor: {
                            ...state.editor,
                            interaction: { ...state.editor.interaction, hoveredNodeId: id }
                        }
                    }));
                }
            },

            selectObject: (id, type) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        interaction: { ...state.editor.interaction, selectedId: id, selectedType: type }
                    }
                }));
            },

            updateNode: (id, data) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        nodes: state.editor.nodes.map(n => n.id === id ? { ...n, ...data } : n)
                    }
                }));
            },

            updateMember: (id, data) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        members: state.editor.members.map(m => m.id === id ? { ...m, ...data } : m)
                    }
                }));
            },

            updateLoad: (id, data) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        loads: state.editor.loads.map(l => {
                            if (l.id !== id) return l;
                            return { ...l, ...data } as Load;
                        })
                    }
                }));
            },
            loadStructuralSystem: (system) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        nodes: system.nodes,
                        members: system.members,
                        loads: system.loads,
                        interaction: {
                            ...state.editor.interaction,
                            selectedId: null,
                            selectedType: null,
                            hoveredNodeId: null,
                            hoveredMemberId: null
                        }
                    }
                }));
            },
            exportStructuralSystem: () => {
                const { nodes, members, loads } = get().editor;
                return {
                    nodes,
                    members,
                    loads
                };
            }
        }
    }
});
