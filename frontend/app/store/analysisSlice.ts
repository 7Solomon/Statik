import type { StateCreator } from "zustand";
import type { AppStore } from "./types"; // Adjust path as needed
import type { ViewportState } from "~/types/app";

const DEFAULT_VIEWPORT_ANALYSIS: ViewportState = {
    zoom: 50,           // Pixels per meter
    pan: { x: 400, y: 300 },
    gridSize: 1.0,
    width: 0,
    height: 0,
    x: 0,
    y: 0
};

const DEFAULT_INTERACTION_ANALYSIS = {
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
        // 1. STATE
        viewMode: 'KINEMATIC',
        viewport: DEFAULT_VIEWPORT_ANALYSIS,
        interaction: DEFAULT_INTERACTION_ANALYSIS,
        kinematicResult: null,
        simplifyResult: null,

        // 2. ACTIONS
        actions: {
            // --- NEW ACTION ---
            setViewport: (partialViewport) => {
                set((state) => ({
                    analysis: {
                        ...state.analysis,
                        viewport: { ...state.analysis.viewport, ...partialViewport }
                    }
                }));
            },
            setInteraction: (partialInteraction) => {
                set((state) => ({
                    analysis: {
                        ...state.analysis,
                        viewport: { ...state.analysis.viewport, ...partialInteraction }
                    }
                }));
            },

            setKinematicResult: (result) => {
                set((state) => ({
                    analysis: { ...state.analysis, kinematicResult: result }
                }));
            },
            setSimplifyResult: (result) => {
                set((state) => ({
                    analysis: { ...state.analysis, simplifyResult: result }
                }));
            },
            setViewMode: (mode) => {
                set((state) => ({
                    analysis: { ...state.analysis, viewMode: mode }
                }));
            }
        }
    }
});
