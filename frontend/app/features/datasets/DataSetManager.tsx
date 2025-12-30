import { useEffect, useState } from 'react';
import { useStore } from '~/store/useStore';
import {
    Database, Plus, RotateCw, Clock, Eye, Cpu,
    ChevronRight, ChevronLeft, Trash2, Box, Layers
} from 'lucide-react';
import { format } from 'date-fns';
import DatasetViewer from './DataSetViewer';

export default function DatasetManager() {
    const { datasets, isLoading } = useStore((s) => s.dataset);
    const { fetchDatasets, generateDataset, previewSymbols } = useStore((s) => s.dataset.actions);

    const [numSamples, setNumSamples] = useState(100);
    const [selectedDataset, setSelectedDataset] = useState<any>(null);
    const [showViewer, setShowViewer] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);

    const estimatedSeconds = (numSamples * 0.05).toFixed(1);

    useEffect(() => {
        fetchDatasets();
    }, []);

    const handleDatasetSelect = (dataset: any) => {
        setSelectedDataset(dataset);
        setShowViewer(true);
    };

    const handleGenerate = async () => {
        setIsGenerating(true);
        await generateDataset(numSamples);
        setIsGenerating(false);
        fetchDatasets(); // Refresh list immediately after
    };

    const handleDeleteDataset = async (path: string) => {
        try {
            const res = await fetch('/api/generation/dataset/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dataset_path: path })
            });

            if (res.ok) {
                fetchDatasets();
            } else {
                const err = await res.json();
                alert(`Error deleting: ${err.error}`);
            }
        } catch (e) {
            console.error(e);
            alert("Failed to delete dataset");
        }
    };

    return (
        <div className="flex flex-col h-full w-full bg-slate-50/50">
            {/* Top Action Bar */}
            <header className="bg-white border-b border-slate-200 px-8 py-5 flex items-center justify-between sticky top-0 z-10 shadow-sm">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Dataset Management</h1>
                    <p className="text-sm text-slate-500 mt-1">Manage and generate synthetic training data</p>
                </div>

                <div className="flex items-center gap-4">
                    {/* Controls Group */}
                    <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-lg border border-slate-200">
                        <div className="px-3 flex items-center gap-2 border-r border-slate-200 pr-4">
                            <span className="text-xs font-semibold text-slate-500 uppercase">Samples</span>
                            <input
                                type="number"
                                value={numSamples}
                                onChange={(e) => setNumSamples(Math.max(10, Number(e.target.value)))}
                                className="w-16 bg-white border border-slate-300 rounded px-2 py-1 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                                min={10} max={10000}
                                disabled={isLoading || isGenerating}
                            />
                            <span className="text-[10px] text-slate-400 whitespace-nowrap hidden xl:inline-block">
                                ~{estimatedSeconds}s
                            </span>
                        </div>

                        <button
                            onClick={() => previewSymbols()}
                            className="p-2 hover:bg-white hover:shadow-sm rounded-md text-slate-600 transition-all"
                            title="Preview Symbols"
                            disabled={isLoading || isGenerating}
                        >
                            <Eye size={18} />
                        </button>
                    </div>

                    {/* Primary Action */}
                    <button
                        onClick={handleGenerate}
                        disabled={isLoading || isGenerating}
                        className={`
                            px-5 py-2.5 rounded-lg font-medium text-sm flex items-center gap-2 shadow-sm transition-all
                            ${(isLoading || isGenerating)
                                ? 'bg-indigo-100 text-indigo-400 cursor-wait'
                                : 'bg-indigo-600 hover:bg-indigo-700 text-white hover:shadow-md hover:-translate-y-0.5'
                            }
                        `}
                    >
                        {(isLoading || isGenerating) ? (
                            <RotateCw className="animate-spin w-4 h-4" />
                        ) : (
                            <Plus size={18} />
                        )}
                        <span>{isGenerating ? 'Generating...' : 'New Dataset'}</span>
                    </button>
                </div>
            </header>

            {/* Main Content Area */}
            <main className="flex-1 overflow-y-auto p-8">
                <div className="max-w-7xl mx-auto">

                    {/* Loading State Banner */}
                    {isGenerating && (
                        <div className="mb-8 p-4 bg-indigo-50 border border-indigo-100 rounded-xl flex items-center gap-4 animate-in fade-in slide-in-from-top-4">
                            <div className="p-2 bg-white rounded-lg shadow-sm">
                                <Cpu className="text-indigo-600 animate-pulse" size={20} />
                            </div>
                            <div>
                                <h3 className="text-sm font-semibold text-indigo-900">Generating Dataset...</h3>
                                <p className="text-xs text-indigo-700 mt-0.5">Creating {numSamples} samples. This may take a moment.</p>
                            </div>
                        </div>
                    )}

                    {/* Grid Header */}
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                            Available Datasets
                            <span className="bg-slate-200 text-slate-600 text-xs py-0.5 px-2 rounded-full">
                                {datasets.length}
                            </span>
                        </h2>
                        <button
                            onClick={() => fetchDatasets()}
                            className="text-sm text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1"
                        >
                            <RotateCw size={14} /> Refresh List
                        </button>
                    </div>

                    {/* Cards Grid */}
                    {datasets.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-24 border-2 border-dashed border-slate-200 rounded-2xl bg-slate-50">
                            <div className="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center mb-4">
                                <Database className="w-8 h-8 text-slate-300" />
                            </div>
                            <h3 className="text-lg font-semibold text-slate-900">No datasets found</h3>
                            <p className="text-slate-500 max-w-sm text-center mt-2">
                                Generated datasets will appear here. Start by creating a new dataset using the controls above.
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
                            {datasets.map((ds: any) => (
                                <DatasetCard
                                    key={ds.path}
                                    dataset={ds}
                                    onSelect={handleDatasetSelect}
                                    onDelete={handleDeleteDataset}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </main>

            {/* Viewer Modal */}
            {showViewer && selectedDataset && (
                <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center animate-in fade-in duration-200">
                    <DatasetViewer
                        datasetPath={selectedDataset.path}
                        onClose={() => setShowViewer(false)}
                    />
                </div>
            )}
        </div>
    );
}

// --- Subcomponent: Dataset Card ---

interface DatasetCardProps {
    dataset: any;
    onSelect: (dataset: any) => void;
    onDelete: (path: string) => void;
}

function DatasetCard({ dataset, onSelect, onDelete }: DatasetCardProps) {
    const handleDelete = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (confirm(`Are you sure you want to delete this dataset?\n\n${dataset.name}`)) {
            onDelete(dataset.path);
        }
    };

    const folderName = dataset.path.split(/[\\/]/).pop();

    return (
        <div
            onClick={() => onSelect(dataset)}
            className="group relative bg-white border border-slate-200 hover:border-indigo-400 hover:ring-4 hover:ring-indigo-50/50 rounded-xl p-5 cursor-pointer transition-all duration-200 hover:-translate-y-1 shadow-sm hover:shadow-xl"
        >
            {/* Header / Icon */}
            <div className="flex items-start justify-between mb-6">
                <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                    <Box size={24} strokeWidth={1.5} />
                </div>

                <button
                    onClick={handleDelete}
                    className="p-2 -mr-2 -mt-2 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                    title="Delete Dataset"
                >
                    <Trash2 size={18} />
                </button>
            </div>

            {/* Content */}
            <div className="space-y-1 mb-4">
                <h4 className="font-semibold text-slate-900 truncate pr-4 text-base" title={folderName}>
                    {folderName}
                </h4>
                <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
                    <Layers size={12} />
                    <span className="truncate max-w-[180px]" title={dataset.path}>
                        .../{folderName?.slice(0, 20)}
                    </span>
                </div>
            </div>

            {/* Footer Info */}
            <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <div className="flex items-center gap-1.5 bg-slate-50 px-2 py-1 rounded">
                    <Clock size={12} />
                    <span>{format(new Date(dataset.created * 1000), 'MMM d, HH:mm')}</span>
                </div>

                <div className="flex items-center gap-1 text-indigo-600 font-medium opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 duration-200">
                    View <ChevronRight size={14} />
                </div>
            </div>
        </div>
    );
}
