import { useEffect, useRef } from 'react';
import {
    ChevronLeft, ChevronRight, X, ZoomIn, ZoomOut, Maximize,
    Loader2, AlertCircle, Box, Layers
} from 'lucide-react';
import { useDatasetInteraction } from './useDataSetInteraction';

interface DatasetViewerProps {
    datasetPath: string;
    onClose: () => void;
}

export default function DatasetViewer({ datasetPath, onClose }: DatasetViewerProps) {
    const {
        split, setSplit,
        loading, imageLoading, error,
        currentData,
        totalImages, currentIndex,
        scale, navigate, zoomHandlers, retry
    } = useDatasetInteraction({ datasetPath });

    const imageRef = useRef<HTMLImageElement>(null);

    // Keyboard support
    useEffect(() => {
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
            if (e.key === 'ArrowRight') navigate('next');
            if (e.key === 'ArrowLeft') navigate('prev');
        };
        window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, [navigate, onClose]);

    return (
        <div className="fixed inset-0 z-50 flex flex-col bg-gray-50 text-slate-900 animate-in fade-in duration-200">

            {/* --- Top Bar (Light Mode) --- */}
            <div className="h-16 bg-white border-b border-gray-200 px-6 flex items-center justify-between shadow-sm z-10">
                <div className="flex items-center gap-4">
                    <div className="bg-indigo-50 p-2 rounded-lg">
                        <Box className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div>
                        <h2 className="font-semibold text-slate-800 leading-tight">
                            {datasetPath.split(/[\\/]/).pop()}
                        </h2>
                        <p className="text-xs text-slate-500 font-medium tracking-wide">
                            DATASET VIEWER
                        </p>
                    </div>
                </div>

                {/* Split Switcher */}
                <div className="flex bg-gray-100 p-1 rounded-lg border border-gray-200">
                    {(['train', 'val', 'test'] as const).map((s) => (
                        <button
                            key={s}
                            onClick={() => setSplit(s)}
                            className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-all ${split === s
                                ? 'bg-white text-indigo-600 shadow-sm border border-gray-200'
                                : 'text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            {s.toUpperCase()}
                        </button>
                    ))}
                </div>

                <button
                    onClick={onClose}
                    className="p-2 text-slate-400 hover:text-slate-600 hover:bg-gray-100 rounded-full transition-colors"
                >
                    <X size={20} />
                </button>
            </div>

            {/* --- Main Content Area --- */}
            <div className="flex-1 overflow-hidden relative flex items-center justify-center bg-gray-100/50">

                {/* Background Grid Pattern */}
                <div className="absolute inset-0 opacity-[0.03]"
                    style={{ backgroundImage: 'radial-gradient(#4f46e5 1px, transparent 1px)', backgroundSize: '24px 24px' }}>
                </div>

                {loading ? (
                    <div className="text-center flex flex-col items-center animate-pulse">
                        <Loader2 className="w-10 h-10 text-indigo-600 animate-spin mb-4" />
                        <p className="text-slate-500 font-medium">Loading dataset metadata...</p>
                    </div>
                ) : error ? (
                    <div className="bg-white p-8 rounded-2xl shadow-xl border border-red-100 text-center max-w-md">
                        <div className="bg-red-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4">
                            <AlertCircle className="text-red-500" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-800 mb-2">Failed to load</h3>
                        <p className="text-slate-500 text-sm mb-6">{error}</p>
                        <button onClick={retry} className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm hover:bg-slate-800">
                            Try Again
                        </button>
                    </div>
                ) : totalImages === 0 ? (
                    <div className="text-center text-slate-400">
                        <Layers className="w-12 h-12 mx-auto mb-3 opacity-20" />
                        <p>No images found in {split} split</p>
                    </div>
                ) : (
                    // Image Canvas
                    <div
                        className="relative shadow-2xl bg-white transition-transform duration-200 ease-out border border-gray-200"
                        style={{ transform: `scale(${scale})` }}
                    >
                        {(!currentData?.url || imageLoading) && (
                            <div className="absolute inset-0 flex items-center justify-center bg-gray-50 z-10">
                                <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                            </div>
                        )}

                        {currentData?.url && (
                            <>

                                {currentData.labels.map((label, i) => {
                                    if (!imageRef.current) return null;

                                    return (
                                        <div
                                            key={i}
                                            // 1. "group": Allows child elements to react when this parent is hovered
                                            className="absolute border-2 border-indigo-500 bg-indigo-500/10 group cursor-help transition-colors hover:bg-indigo-500/20 hover:border-indigo-400 z-10"
                                            style={{
                                                left: `${(label.cx - label.w / 2) * 100}%`,
                                                top: `${(label.cy - label.h / 2) * 100}%`,
                                                width: `${label.w * 100}%`,
                                                height: `${label.h * 100}%`
                                            }}
                                        >
                                            {/* 2. The Tooltip Label */}
                                            <div className="absolute 
                                                    /* Position: centered above the box */
                                                    left-1/2 -translate-x-1/2 -top-8
                                                    /* Appearance: Dark tooltip with arrow */
                                                    bg-slate-900 text-white text-xs px-2 py-1 rounded shadow-xl
                                                    /* Behavior: Hidden by default, visible on group-hover */
                                                    opacity-0 group-hover:opacity-100 transition-opacity duration-200
                                                    pointer-events-none whitespace-nowrap z-20 flex flex-col items-center">

                                                {/* The Text */}
                                                <span className="font-semibold">{label.class_name}</span>
                                                <span className="text-[10px] text-slate-400 font-mono">
                                                    ID: {label.class_id}
                                                </span>

                                                {/* Little triangle arrow pointing down */}
                                                <div className="w-2 h-2 bg-slate-900 rotate-45 absolute -bottom-1"></div>
                                            </div>
                                        </div>
                                    );
                                })}
                                <img
                                    ref={imageRef}
                                    src={currentData.url}
                                    alt="Dataset Sample"
                                    className="max-h-[75vh] max-w-[90vw] object-contain block select-none"
                                    draggable={false}
                                />
                                {/* Bounding Boxes */}
                                {currentData.labels.map((label, i) => {
                                    if (!imageRef.current) return null;
                                    // Bounding box logic relies on CSS percentages if container matches img size,
                                    // or explicit pixel calc if necessary. 
                                    // Using percentage based styling is easiest for responsive scaling:

                                    return (
                                        <div
                                            key={i}
                                            className="absolute border-2 border-indigo-500 bg-indigo-500/10 group hover:bg-indigo-500/20 transition-colors cursor-crosshair"
                                            style={{
                                                left: `${(label.cx - label.w / 2) * 100}%`,
                                                top: `${(label.cy - label.h / 2) * 100}%`,
                                                width: `${label.w * 100}%`,
                                                height: `${label.h * 100}%`
                                            }}
                                        >
                                            <span className="absolute -top-6 left-0 bg-indigo-600 text-white text-[10px] px-1.5 py-0.5 rounded shadow-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-20">
                                                {label.class_name}
                                            </span>
                                        </div>
                                    );
                                })}
                            </>
                        )}
                    </div>
                )}
            </div>

            {/* --- Footer Controls (Light Mode) --- */}
            <div className="h-20 bg-white border-t border-gray-200 px-6 flex items-center justify-between z-10">

                {/* Navigation */}
                <div className="flex items-center gap-3">
                    <button onClick={() => navigate('prev')} className="w-10 h-10 flex items-center justify-center rounded-xl bg-gray-100 hover:bg-gray-200 text-slate-600 transition-colors">
                        <ChevronLeft size={20} />
                    </button>
                    <div className="text-center px-2">
                        <div className="text-sm font-bold text-slate-800 font-mono">
                            {(currentIndex + 1).toString().padStart(3, '0')}
                            <span className="text-slate-400 mx-1">/</span>
                            {totalImages}
                        </div>
                    </div>
                    <button onClick={() => navigate('next')} className="w-10 h-10 flex items-center justify-center rounded-xl bg-gray-100 hover:bg-gray-200 text-slate-600 transition-colors">
                        <ChevronRight size={20} />
                    </button>
                </div>

                {/* Metadata Badge */}
                {currentData && (
                    <div className="hidden md:flex items-center gap-6 text-sm text-slate-500">
                        <div className="flex flex-col">
                            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Filename</span>
                            <span className="font-mono text-slate-700 truncate max-w-[200px]">{currentData.filename}</span>
                        </div>
                        <div className="h-8 w-px bg-gray-200"></div>
                        <div className="flex flex-col">
                            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Objects</span>
                            <span className="font-mono text-slate-700">{currentData.labels.length} Detected</span>
                        </div>
                    </div>
                )}

                {/* Zoom Tools */}
                <div className="flex items-center bg-gray-100 rounded-lg p-1 border border-gray-200">
                    <button onClick={zoomHandlers.out} className="p-2 hover:bg-white hover:shadow-sm rounded text-slate-500"><ZoomOut size={16} /></button>
                    <span className="text-xs font-mono w-12 text-center text-slate-600">{Math.round(scale * 100)}%</span>
                    <button onClick={zoomHandlers.in} className="p-2 hover:bg-white hover:shadow-sm rounded text-slate-500"><ZoomIn size={16} /></button>
                    <div className="w-px h-4 bg-gray-300 mx-1"></div>
                    <button onClick={zoomHandlers.reset} className="p-2 hover:bg-white hover:shadow-sm rounded text-slate-500" title="Reset View"><Maximize size={16} /></button>
                </div>
            </div>
        </div>
    );
}
