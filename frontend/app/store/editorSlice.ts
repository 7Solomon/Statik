import { v4 as uuidv4 } from 'uuid';
import type { AppStore, EditorActions, EditorState } from './types';
import type { StateCreator } from 'zustand';
import type { Node, Member, Load, Scheibe } from '~/types/model';
import type { ViewportState } from '~/types/app';
import { DEFAULT_INTERACTION, DEFAULT_MEMBER_PROPS, DEFAULT_RELEASES, DEFAULT_VIEWPORT, sanitizeLoad, sanitizeMember, sanitizeNode, sanitizeScheibe } from '~/utils/sanitize_system';




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
        scheiben: [],
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

            addScheibe: (data) => {
                const newScheibe: Scheibe = {
                    id: uuidv4(),
                    ...data
                };

                set((state) => ({
                    editor: {
                        ...state.editor,
                        scheiben: [...state.editor.scheiben, newScheibe]
                    }
                }));
                return newScheibe.id;
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

            removeScheibe: (id) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        scheiben: state.editor.scheiben.filter(s => s.id !== id)
                    }
                }));
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

            updateScheibe: (id, data) => {
                set((state) => ({
                    editor: {
                        ...state.editor,
                        scheiben: state.editor.scheiben.map(s =>
                            s.id === id ? { ...s, ...data } : s
                        )
                    }
                }));
            },

            loadStructuralSystem: (system) => {
                // Sanitize and validate all arrays
                const sanitizedNodes = (system.nodes ?? [])
                    .map(sanitizeNode)
                    .filter((n): n is Node => n !== null);

                const sanitizedMembers = (system.members ?? [])
                    .map(sanitizeMember)
                    .filter((m): m is Member => m !== null);

                const sanitizedScheiben = (system.scheiben ?? [])
                    .map(sanitizeScheibe)
                    .filter((s): s is Scheibe => s !== null);

                const sanitizedLoads = (system.loads ?? [])
                    .map(sanitizeLoad)
                    .filter((l): l is Load => l !== null);

                set((state) => ({
                    editor: {
                        ...state.editor,
                        nodes: sanitizedNodes,
                        members: sanitizedMembers,
                        loads: sanitizedLoads,
                        scheiben: sanitizedScheiben,
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
                const { nodes, members, loads, scheiben } = get().editor;
                return {
                    nodes,
                    members,
                    loads,
                    scheiben
                };
            }
        }
    }
});
