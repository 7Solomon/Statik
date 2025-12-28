import type { StateCreator } from "zustand";
import type { AppStore } from "./types";

export const createAnalysisSlice: StateCreator<
    AppStore,
    [],
    [],
    Pick<AppStore, 'analysis'>
> = (set, get) => ({

    analysis: {
        // 1. STATE
        kinematicResult: null,

        // 2. ACTIONS
        actions: {
            analyzeSystem: async (name: string) => {
                // Access the root state
                const state = get();

                // DATA SOURCE: Now we pull from 'state.editor'
                const { nodes, members, loads, viewport } = state.editor;

                const payload = {
                    name: name,
                    system: {
                        nodes: nodes,
                        members: members,
                        loads: loads,
                        meta: {
                            gridSize: viewport.gridSize,
                            zoom: viewport.zoom,
                            pan: viewport.pan
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

                    // Optional: You might want to auto-set the result here if the API returns analysis data immediately
                    // get().analysis.actions.setKinematicResult(result.data);

                } catch (error) {
                    console.error('Failed to export system:', error);
                }
            },

            setKinematicResult: (result) => {
                set((state) => ({
                    analysis: {
                        ...state.analysis, // Keep actions intact
                        kinematicResult: result
                    }
                }));
            },
        }
    }
});
