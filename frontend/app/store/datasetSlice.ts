import type { StateCreator } from "zustand";
import type { AppStore } from "./types";

export interface Dataset {
    path: string;
    yaml: string;
    created: number;
}

export interface DatasetState {
    datasets: Dataset[];
    isLoading: boolean;
    currentPreviewConfig: any | null;
}

export interface DatasetActions {
    fetchDatasets: () => Promise<void>;
    generateDataset: (numSamples: number, forceRecreate?: boolean) => Promise<void>;
    previewSymbols: () => Promise<void>;
}

export const createDatasetSlice: StateCreator<
    AppStore,
    [],
    [],
    { dataset: DatasetState & { actions: DatasetActions } }
> = (set, get) => ({
    dataset: {
        datasets: [],
        isLoading: false,
        currentPreviewConfig: null,

        actions: {
            fetchDatasets: async () => {
                console.log("FETCHING")
                set((s) => ({ dataset: { ...s.dataset, isLoading: true } }));
                try {
                    const res = await fetch('/api/generation/list_datasets');
                    const data = await res.json();
                    console.log(data)

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
                const res = await fetch(`/generation/${encodeURIComponent(datasetPath)}/info`);
                return res.json();
            },

            getSplitImages: async (datasetPath: string, split: 'train' | 'val' | 'test') => {
                const res = await fetch(`/generation/${encodeURIComponent(datasetPath)}/${split}/images`);
                return res.json();
            },

            getImageLabels: async (datasetPath: string, split: string, stem: string) => {
                const res = await fetch(`/generation/${encodeURIComponent(datasetPath)}/${split}/labels/${stem}`);
                return res.json();
            },
        },
    },
});
