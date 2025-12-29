import { useState, useEffect, useCallback, useRef } from 'react';
import {
    ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCw,
    Loader2, Database, AlertCircle
} from 'lucide-react';

interface DatasetViewerProps {
    datasetPath: string;
    onClose: () => void;
}

interface Label {
    class_id: number;
    class_name: string;
    cx: number;
    cy: number;
    w: number;
    h: number;
}

interface ImageData {
    index: number;
    filename: string;
    stem: string;
    labels: Label[];
}

export default function DatasetViewer({ datasetPath, onClose }: DatasetViewerProps) {
    const [split, setSplit] = useState<'train' | 'val' | 'test'>('train');
    const [images, setImages] = useState<ImageData[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [scale, setScale] = useState(1);
    const [classes, setClasses] = useState<{ [key: number]: string }>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [imageBlobUrl, setImageBlobUrl] = useState<string>('');
    const imageRef = useRef<HTMLImageElement>(null);

    // Keyboard shortcuts
    useEffect(() => {
        const handleKey = (e: KeyboardEvent) => {
            switch (e.key) {
                case 'Escape': onClose(); break;
                case 'ArrowLeft': navigate('prev'); break;
                case 'ArrowRight': navigate('next'); break;
                case '0': resetZoom(); break;
                case '+': case '=': zoomIn(); break;
                case '-': zoomOut(); break;
            }
        };
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, []);

    const apiRequest = async (endpoint: string, body: any) => {
        const res = await fetch(`api/generation/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_path: datasetPath, ...body })
        });
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return res.json();
    };

    const fetchDatasetInfo = useCallback(async () => {
        setLoading(true); setError(null);
        try {
            // 1. Classes
            const info = await apiRequest('dataset/info', {});
            setClasses(Object.fromEntries(
                info.classes.map((name: string, i: number) => [i, name])
            ));

            // 2. Images
            const imageList = await apiRequest('dataset/images', { split });
            if (imageList.length === 0) {
                setImages([]);
                return;
            }

            // 3. Labels (parallel)
            const imagesWithLabels = await Promise.all(
                imageList.slice(0, 100).map(async (img: any, idx: number) => ({
                    index: idx,
                    filename: img.filename,
                    stem: img.stem,
                    labels: await apiRequest('dataset/labels', { split, stem: img.stem })
                }))
            );

            setImages(imagesWithLabels);
            setCurrentIndex(0);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [datasetPath, split]);

    useEffect(() => {
        fetchDatasetInfo();
    }, [fetchDatasetInfo]);

    // Load image
    useEffect(() => {
        if (!images[currentIndex]) return;

        let url = '';
        apiRequest('dataset/image', { split, filename: images[currentIndex].filename })
            .then(res => res.blob())
            .then(blob => {
                url = URL.createObjectURL(blob);
                setImageBlobUrl(url);
            })
            .catch(() => setImageBlobUrl(''));

        return () => { if (url) URL.revokeObjectURL(url); };
    }, [currentIndex, split]);

    const currentImage = images[currentIndex];
    const navigate = (dir: 'prev' | 'next') =>
        setCurrentIndex(i => dir === 'prev' ? (i > 0 ? i - 1 : images.length - 1) : (i < images.length - 1 ? i + 1 : 0));

    const resetZoom = () => setScale(1);
    const zoomIn = () => setScale(Math.min(scale + 0.25, 3));
    const zoomOut = () => setScale(Math.max(scale - 0.25, 0.25));

    if (loading) return (
        <div className="fixed inset-0 bg-slate-900 flex items-center justify-center z-50">
            <div className="bg-white/90 p-12 rounded-3xl shadow-2xl text-center animate-in">
                <Loader2 className="w-16 h-16 mx-auto mb-6 text-indigo-500 animate-spin" />
                <h3 className="text-2xl font-bold text-slate-900 mb-2">Loading Dataset</h3>
                <p className="text-slate-600">Loading {split.toUpperCase()} split...</p>
            </div>
        </div>
    );

    return (
        <div className="fixed inset-0 bg-slate-900 z-50 flex flex-col">
            {/* Header */}
            <div className="bg-slate-800/95 backdrop-blur p-6 border-b border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <button onClick={onClose} className="p-3 hover:bg-slate-700 rounded-xl text-slate-300 hover:text-white">
                        <ChevronLeft size={24} />
                    </button>
                    <div>
                        <h2 className="text-xl font-bold text-white">{datasetPath.split(/[\\/]/).pop()}</h2>
                        <p className="text-sm text-slate-400">{split.toUpperCase()} ({images.length} images)</p>
                    </div>
                </div>
                <div className="flex gap-3">
                    {(['train', 'val', 'test'] as const).map(s => (
                        <button key={s} onClick={() => setSplit(s)}
                            className={`px-4 py-2 rounded-lg text-xs font-medium transition-all ${split === s ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white bg-slate-700/50 hover:bg-slate-600'
                                }`}>
                            {s.toUpperCase()}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 flex items-center justify-center p-8 overflow-auto">
                {error ? (
                    <div className="text-center p-12">
                        <AlertCircle className="w-16 h-16 mx-auto mb-4 text-red-400" />
                        <h3 className="text-xl font-bold text-slate-300 mb-2">{error}</h3>
                        <button onClick={fetchDatasetInfo}
                            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
                            Retry
                        </button>
                    </div>
                ) : images.length === 0 ? (
                    <div className="text-center">
                        <Database className="w-16 h-16 mx-auto mb-4 text-slate-500" />
                        <p className="text-slate-400">No images in {split.toUpperCase()}</p>
                    </div>
                ) : (
                    <div className="max-w-4xl w-full flex flex-col items-center">
                        {/* Image */}
                        <div className="relative bg-slate-800 rounded-2xl p-4 shadow-2xl"
                            style={{ transform: `scale(${scale})` }}>
                            {imageBlobUrl ? (
                                <>
                                    <img ref={imageRef} src={imageBlobUrl}
                                        className="max-w-full max-h-[70vh] rounded-xl object-contain block shadow-xl" />

                                    {/* Labels */}
                                    {currentImage?.labels?.map((label, i) => {
                                        const rect = imageRef.current?.getBoundingClientRect();
                                        if (!rect) return null;

                                        const left = (label.cx - label.w / 2) * rect.width;
                                        const top = (label.cy - label.h / 2) * rect.height;
                                        const width = label.w * rect.width;
                                        const height = label.h * rect.height;

                                        return (
                                            <div key={i} className="absolute border-4 border-indigo-400 bg-indigo-500/20 rounded-lg p-1"
                                                style={{ left: `${left}px`, top: `${top}px`, width: `${width}px`, height: `${height}px` }}>
                                                <span className="text-xs font-bold text-white">{label.class_name}</span>
                                            </div>
                                        );
                                    })}
                                </>
                            ) : (
                                <div className="w-96 h-96 flex items-center justify-center bg-slate-700 rounded-xl">
                                    <Loader2 className="w-12 h-12 animate-spin text-indigo-400" />
                                </div>
                            )}
                        </div>

                        {/* Controls */}
                        <div className="flex gap-4 mt-8 items-center">
                            <button onClick={() => navigate('prev')} className="p-3 bg-slate-700 hover:bg-slate-600 rounded-xl">
                                <ChevronLeft size={24} />
                            </button>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-white">{currentIndex + 1}/{images.length}</div>
                                <div className="text-sm text-slate-400">{currentImage?.labels?.length || 0} labels</div>
                            </div>
                            <button onClick={() => navigate('next')} className="p-3 bg-slate-700 hover:bg-slate-600 rounded-xl">
                                <ChevronRight size={24} />
                            </button>
                            <div className="flex gap-2 ml-8">
                                <button onClick={zoomOut} className="p-2 hover:bg-slate-600 rounded-lg"><ZoomOut size={18} /></button>
                                <span className="text-white px-4 py-2 bg-slate-700 rounded-lg min-w-[70px] text-center">{Math.round(scale * 100)}%</span>
                                <button onClick={zoomIn} className="p-2 hover:bg-slate-600 rounded-lg"><ZoomIn size={18} /></button>
                                <button onClick={resetZoom} className="p-2 hover:bg-slate-600 rounded-lg ml-2">1:1</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
