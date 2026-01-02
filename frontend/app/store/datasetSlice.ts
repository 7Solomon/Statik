import type { StateCreator } from "zustand";
import type { AppStore } from "./types";

export const createDatasetSlice: StateCreator<
    AppStore,
    [],
    [],
    Pick<AppStore, 'dataset'>
> = (set, get) => ({
    dataset: {
        datasets: [],
        isLoading: false,
        currentPreviewConfig: null,

        actions: {
            fetchDatasets: async () => {
                set((s) => ({ dataset: { ...s.dataset, isLoading: true } }));
                try {
                    const res = await fetch('/api/generation/list_datasets');
                    const data = await res.json();

                    set((s) => ({
                        dataset: { ...s.dataset, datasets: data.datasets, isLoading: false },
                    }));
                } catch (e) {
                    console.error("Failed to fetch datasets", e);
                    set((s) => ({ dataset: { ...s.dataset, isLoading: false } }));
                }
            },

            generateDataset: async (numSamples, forceRecreate = false) => {
                set((s) => ({ dataset: { ...s.dataset, isLoading: true } }));
                try {
                    const res = await fetch('/api/generation/yolo_dataset', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            num_samples: numSamples,
                            datasets_dir: './content/datasets',
                            force_recreate: forceRecreate,
                        }),
                    });

                    if (!res.ok) throw new Error('Generation failed');

                    // Refresh list after generation
                    await get().dataset.actions.fetchDatasets();
                } catch (e) {
                    console.error("Failed to generate dataset", e);
                } finally {
                    set((s) => ({ dataset: { ...s.dataset, isLoading: false } }));
                }
            },

            previewSymbols: async () => {
                try {
                    await fetch('/api/preview_symbols', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ datasets_dir: './content/datasets' }),
                    });
                } catch (e) {
                    console.error("Failed to launch preview", e);
                }
            },

            getDatasetInfo: async (datasetPath: string) => {
                const res = await fetch(`/api/generation/${encodeURIComponent(datasetPath)}/info`);
                return res.json();
            },

            getSplitImages: async (datasetPath: string, split: 'train' | 'val' | 'test') => {
                const res = await fetch(`/api/generation/${encodeURIComponent(datasetPath)}/${split}/images`);
                return res.json();
            },

            getImageLabels: async (datasetPath: string, split: string, stem: string) => {
                const res = await fetch(`/api/generation/${encodeURIComponent(datasetPath)}/${split}/labels/${stem}`);
                return res.json();
            },
        },
    },
});
