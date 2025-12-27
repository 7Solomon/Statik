import type { StateCreator } from "zustand";
import type { AppStore, AnalysisState, AnalysisActions } from "./types";

export const createAnalysisSlice: StateCreator<
    AppStore,
    [],
    [],
    AnalysisState & { actions: AnalysisActions }
> = (set, get) => ({

    kinematicResult: null,

    actions: {
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

        setKinematicResult: (result) => set({ kinematicResult: result }),
    }
});
