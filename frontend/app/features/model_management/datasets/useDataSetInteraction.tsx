import { useState, useEffect, useCallback, useMemo } from 'react';

// --- Types ---
export interface Label {
    class_id: number;
    class_name: string;
    cx: number;
    cy: number;
    w: number;
    h: number;
}

export interface DatasetFile {
    index: number;
    filename: string;
    stem: string;
}

interface UseDatasetProps {
    datasetPath: string;
    initialSplit?: 'train' | 'val' | 'test';
}

export const useDatasetInteraction = ({ datasetPath, initialSplit = 'train' }: UseDatasetProps) => {
    const [split, setSplit] = useState<'train' | 'val' | 'test'>(initialSplit);
    const [fileList, setFileList] = useState<DatasetFile[]>([]);
    const [labelsCache, setLabelsCache] = useState<Record<string, Label[]>>({});
    const [currentIndex, setCurrentIndex] = useState(0);
    const [loading, setLoading] = useState(true);
    const [imageLoading, setImageLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [currentImageUrl, setCurrentImageUrl] = useState<string | null>(null);
    const [scale, setScale] = useState(1);

    // Helper for API calls
    const apiCall = async (endpoint: string, body: any) => {
        const res = await fetch(`api/generation/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_path: datasetPath, ...body }),
        });
        if (!res.ok) throw new Error(`API Error ${res.status}`);
        return res.json();
    };

    // 1. Fetch File List & Batch Labels
    const loadDatasetSplit = useCallback(async () => {
        setLoading(true);
        setError(null);
        setFileList([]);
        setLabelsCache({});
        setCurrentIndex(0);

        try {
            // A. Get List of Images
            const images = await apiCall('dataset/images', { split });

            // Limit to first 100 for performance/demo (remove slice for full dataset)
            const subset = images.slice(0, 100);
            setFileList(subset);

            if (subset.length > 0) {
                // B. Get Labels in BATCH (Fixes the spam)
                const stems = subset.map((f: any) => f.stem);
                const batchLabels = await apiCall('dataset/labels_batch', { split, stems });
                setLabelsCache(batchLabels);
            }

        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [datasetPath, split]);


    useEffect(() => {
        if (!fileList[currentIndex]) return;

        let active = true;
        const filename = fileList[currentIndex].filename;

        // Don't re-fetch if we already have a URL for this specific file
        // (You could expand this to cache multiple images in memory if you have RAM)
        if (currentImageUrl && currentImageUrl.includes(filename)) return;

        setImageLoading(true);

        const fetchImage = async () => {
            try {
                // Requesting just ONE image via the batch endpoint
                const batchResult = await apiCall('dataset/images_batch', {
                    split,
                    filenames: [filename]
                });

                // The batch endpoint returns { "filename.jpg": "data:image/jpeg;base64,..." }
                const base64Str = batchResult[filename];

                if (active && base64Str) {
                    setCurrentImageUrl(base64Str);
                }
            } catch (err) {
                console.error(err);
            } finally {
                if (active) setImageLoading(false);
            }
        };

        fetchImage();

        return () => { active = false; };
    }, [currentIndex, fileList, split, datasetPath]);



    // Initial Load
    useEffect(() => { loadDatasetSplit(); }, [loadDatasetSplit]);

    // Navigation & Zoom Controls
    const navigate = (dir: 'next' | 'prev') => {
        setCurrentIndex(curr => {
            if (dir === 'next') return curr < fileList.length - 1 ? curr + 1 : 0;
            return curr > 0 ? curr - 1 : fileList.length - 1;
        });
    };

    const zoomHandlers = {
        in: () => setScale(s => Math.min(s + 0.25, 4)),
        out: () => setScale(s => Math.max(s - 0.25, 0.5)),
        reset: () => setScale(1)
    };

    const currentData = useMemo(() => {
        const file = fileList[currentIndex];
        if (!file) return null;
        return {
            ...file,
            labels: labelsCache[file.stem] || [],
            url: currentImageUrl
        };
    }, [fileList, currentIndex, labelsCache, currentImageUrl]);

    return {
        split, setSplit,
        loading, imageLoading, error,
        currentData,
        totalImages: fileList.length,
        currentIndex,
        scale,
        navigate,
        zoomHandlers,
        retry: loadDatasetSplit
    };
};
