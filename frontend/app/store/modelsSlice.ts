import type { StateCreator } from "zustand";
import type { AppStore } from "./types";

export const createModelManagementSlice: StateCreator<
    AppStore,
    [],
    [],
    Pick<AppStore, 'model_management'>
> = (set, get) => ({
    model_management: {
        // --- State Defaults ---
        viewMode: 'TRAINING',
        datasets: [],
        models: [],
        isLoading: false,
        currentPreviewConfig: null,

        actions: {
            // 1. View Switching
            setViewMode: (mode) => {
                set((s) => ({
                    model_management: { ...s.model_management, viewMode: mode }
                }));
            },

            // 2. Fetch Datasets
            fetchDatasets: async () => {
                set((s) => ({ model_management: { ...s.model_management, isLoading: true } }));
                try {
                    const res = await fetch('/api/generation/list_datasets');
                    const data = await res.json();
                    set((s) => ({
                        model_management: {
                            ...s.model_management,
                            datasets: data.datasets || [],
                            isLoading: false
                        },
                    }));
                } catch (e) {
                    console.error("Failed to fetch datasets", e);
                    set((s) => ({ model_management: { ...s.model_management, isLoading: false } }));
                }
            },

            // 3. Fetch Models
            fetchModels: async () => {
                // We typically don't set global isLoading for this background fetch, 
                // but you can if you want the whole UI to lock.
                try {
                    const res = await fetch('/api/models/list');
                    if (res.ok) {
                        const models = await res.json();
                        set((s) => ({
                            model_management: { ...s.model_management, models: models }
                        }));
                    }
                } catch (e) {
                    console.error("Failed to fetch models", e);
                }
            },

            // 4. Generate Dataset
            generateDataset: async (numSamples, forceRecreate = false) => {
                set((s) => ({ model_management: { ...s.model_management, isLoading: true } }));
                try {
                    const res = await fetch('/api/generation/yolo_dataset', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            num_samples: numSamples,
                            datasets_dir: './content/datasets',
                        }),
                    });

                    if (!res.ok) {
                        const err = await res.json();
                        throw new Error(err.error || 'Generation failed');
                    }

                    // Refresh list after generation
                    await get().model_management.actions.fetchDatasets();
                } catch (e) {
                    console.error("Failed to generate dataset", e);
                    alert("Generation failed. Check console.");
                } finally {
                    set((s) => ({ model_management: { ...s.model_management, isLoading: false } }));
                }
            },

            // 5. Preview Symbols (Debug)
            previewSymbols: async () => {
                try {
                    await fetch('/api/generation/preview_symbols', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ datasets_dir: './content/datasets' }),
                    });
                } catch (e) {
                    console.error("Failed to launch preview", e);
                }
            },

            // 6. API Helpers (Getters)
            getDatasetInfo: async (datasetPath: string) => {
                const res = await fetch('/api/generation/dataset/info', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dataset_path: datasetPath })
                });
                return res.json();
            },

            getSplitImages: async (datasetPath: string, split: 'train' | 'val' | 'test') => {
                const res = await fetch('/api/generation/dataset/images', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dataset_path: datasetPath, split })
                });
                return res.json();
            },

            getImageLabels: async (datasetPath: string, split: string, stem: string) => {
                const res = await fetch('/api/generation/dataset/labels_batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        dataset_path: datasetPath,
                        split,
                        stems: [stem]
                    })
                });
                const data = await res.json();
                return data[stem] || [];
            },
        },
    },
});
