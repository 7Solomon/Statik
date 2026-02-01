import type { StateCreator } from "zustand";
import type { AppStore } from "./types";
import type { ViewportState, AnalysisInteractionState } from "~/types/app";
import type { StructuralSystem } from "~/types/model";

const DEFAULT_VIEWPORT_ANALYSIS: ViewportState = {
    zoom: 50,
    pan: { x: 400, y: 300 }, // Legacy field often unused if x/y used directly, but keeping for type safety
    gridSize: 1.0,
    width: 0,
    height: 0,
};

const DEFAULT_INTERACTION_ANALYSIS: AnalysisInteractionState = {
    isDragging: false,
    mousePos: { x: 0, y: 0 },
    hoveredNodeId: null,
    hoveredMemberId: null
};

export const createAnalysisSlice: StateCreator<
    AppStore,
    [],
    [],
    Pick<AppStore, 'analysis'>
> = (set, get) => ({

    analysis: {
        analysisSession: null, // Start with no active analysis session

        actions: {
            // Initialize a new analysis session
            startAnalysis: (system: StructuralSystem) => {
                console.log("ANALYZE");
                console.log(system);
                set((state) => ({
                    analysis: {
                        ...state.analysis,
                        analysisSession: {
                            system, // MANDATORY SYSTEM
                            viewMode: 'KINEMATIC',
                            viewport: DEFAULT_VIEWPORT_ANALYSIS,
                            interaction: DEFAULT_INTERACTION_ANALYSIS,
                            kinematicResult: null,
                            simplifyResult: null,
                            solutionResult: null,
                            dynamicResult: null,
                        }
                    },
                    // Automatically switch app mode when analysis starts
                    shared: { ...state.shared, mode: 'ANALYSIS' }
                }));
            },

            clearAnalysisSession: () => {
                set((state) => ({
                    analysis: {
                        ...state.analysis,
                        analysisSession: null
                    },
                    shared: { ...state.shared, mode: 'EDITOR' }
                }));
            },

            setViewport: (partialViewport) => {
                set((state) => {
                    if (!state.analysis.analysisSession) return state;
                    return {
                        analysis: {
                            ...state.analysis,
                            analysisSession: {
                                ...state.analysis.analysisSession,
                                viewport: { ...state.analysis.analysisSession.viewport, ...partialViewport }
                            }
                        }
                    };
                });
            },

            setInteraction: (partialInteraction) => {
                set((state) => {
                    if (!state.analysis.analysisSession) return state;
                    return {
                        analysis: {
                            ...state.analysis,
                            analysisSession: {
                                ...state.analysis.analysisSession,
                                interaction: { ...state.analysis.analysisSession.interaction, ...partialInteraction }
                            }
                        }
                    };
                });
            },

            setKinematicResult: (result) => {
                set((state) => {
                    if (!state.analysis.analysisSession) return state;
                    return {
                        analysis: {
                            ...state.analysis,
                            analysisSession: { ...state.analysis.analysisSession, kinematicResult: result }
                        }
                    };
                });
            },

            setSimplifyResult: (result) => {
                set((state) => {
                    if (!state.analysis.analysisSession) return state;
                    return {
                        analysis: {
                            ...state.analysis,
                            analysisSession: { ...state.analysis.analysisSession, simplifyResult: result }
                        }
                    };
                });
            },

            setSolutionResult: (result) => {
                set((state) => {
                    if (!state.analysis.analysisSession) return state;
                    return {
                        analysis: {
                            ...state.analysis,
                            analysisSession: { ...state.analysis.analysisSession, solutionResult: result }
                        }
                    };
                });
            },

            setViewMode: (mode) => {
                set((state) => {
                    if (!state.analysis.analysisSession) return state;
                    return {
                        analysis: {
                            ...state.analysis,
                            analysisSession: { ...state.analysis.analysisSession, viewMode: mode }
                        }
                    };
                });
            },

            setDynamicResult: (result) => {
                set((state) => {
                    if (!state.analysis.analysisSession) return state;
                    console.log(result)
                    return {
                        analysis: {
                            ...state.analysis,
                            analysisSession: {
                                ...state.analysis.analysisSession,
                                dynamicResult: result
                            }
                        }
                    };
                });
            },
        }
    }
});
