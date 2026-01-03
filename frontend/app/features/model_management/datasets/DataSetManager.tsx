import React, { useState, useEffect } from 'react';
import {
    FolderOpen, Plus, RefreshCw, Trash2,
    Loader2, AlertCircle, FileText, Layers
} from 'lucide-react';
import DatasetViewer from './DataSetViewer';
import { useStore } from '~/store/useStore';


export default function DataSetManager() {
    // --- Store Integration ---
    const {
        datasets,
        isLoading,
        actions: { fetchDatasets, generateDataset }
    } = useStore(state => state.model_management);

    // --- Local UI State ---
    const [generating, setGenerating] = useState(false);
    const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
    const [numSamples, setNumSamples] = useState(100);

    // --- Initialization ---
    useEffect(() => {
        fetchDatasets();
    }, [fetchDatasets]);

    // --- Handlers ---
    const handleGenerate = async () => {
        setGenerating(true);
        // The store action handles the API call AND the refetching of datasets
        await generateDataset(numSamples);
        setGenerating(false);
    };

    const handleDelete = async (path: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm("Are you sure you want to delete this dataset?")) return;

        try {
            await fetch('/api/generation/dataset/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dataset_path: path })
            });
            // Update the global store after deletion
            fetchDatasets();
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="max-w-5xl mx-auto space-y-8">

            {/* 1. Generator Card */}
            <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                            <Plus className="text-indigo-500" size={20} />
                            Generate New Dataset
                        </h2>
                        <p className="text-slate-500 text-sm mt-1">
                            Create synthetic training data using the current procedural generation pipeline.
                        </p>
                    </div>
                    <div className="bg-slate-50 px-3 py-1 rounded text-xs font-mono text-slate-400 border border-slate-100">
                        Pipeline: v1.0-standard
                    </div>
                </div>

                <div className="flex items-end gap-4">
                    <div className="flex-1 max-w-xs">
                        <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">
                            Sample Count
                        </label>
                        <input
                            type="number"
                            value={numSamples}
                            onChange={(e) => setNumSamples(parseInt(e.target.value) || 0)}
                            className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                            min={10} max={5000}
                        />
                    </div>

                    <button
                        onClick={handleGenerate}
                        disabled={generating || isLoading}
                        className={`px-6 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-all ${generating || isLoading
                            ? 'bg-slate-100 text-slate-400 cursor-wait'
                            : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md hover:shadow-lg'
                            }`}
                    >
                        {generating || isLoading ? (
                            <><Loader2 className="animate-spin" size={18} /> Processing...</>
                        ) : (
                            <><Layers size={18} /> Start Generation</>
                        )}
                    </button>
                </div>
            </section>

            {/* 2. Dataset List */}
            <section>
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wide">
                        Available Datasets ({datasets.length})
                    </h3>
                    <button
                        onClick={fetchDatasets}
                        className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-full transition-colors"
                        title="Refresh List"
                    >
                        <RefreshCw size={16} />
                    </button>
                </div>

                {/* Using store 'isLoading' and 'datasets' */}
                {isLoading && datasets.length === 0 ? (
                    <div className="py-12 text-center text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                        <Loader2 className="animate-spin mx-auto mb-2" />
                        Loading datasets...
                    </div>
                ) : datasets.length === 0 ? (
                    <div className="py-12 text-center text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                        <AlertCircle className="mx-auto mb-2 opacity-50" />
                        No datasets found. Generate one above.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-3">
                        {datasets.map((ds: any) => (
                            <div
                                key={ds.path}
                                onClick={() => setSelectedDataset(ds.path)}
                                className="group bg-white p-4 rounded-xl border border-slate-200 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all cursor-pointer flex justify-between items-center"
                            >
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                                        <FolderOpen size={24} />
                                    </div>
                                    <div>
                                        <h4 className="font-semibold text-slate-700 group-hover:text-indigo-700 transition-colors">
                                            {ds.name}
                                        </h4>
                                        <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                                            <span className="flex items-center gap-1">
                                                <FileText size={12} /> {new Date(ds.created * 1000).toLocaleDateString()}
                                            </span>
                                            <span>•</span>
                                            <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-500">
                                                {ds.yaml.split('/').pop()}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3">
                                    <span className="text-xs font-medium text-indigo-600 opacity-0 group-hover:opacity-100 transition-opacity mr-2">
                                        Click to View
                                    </span>
                                    <button
                                        onClick={(e) => handleDelete(ds.path, e)}
                                        className="p-2 text-slate-300 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                        title="Delete Dataset"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* 3. Modal Viewer */}
            {selectedDataset && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="w-full max-w-6xl h-[85vh] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col">
                        <DatasetViewer
                            datasetPath={selectedDataset}
                            onClose={() => setSelectedDataset(null)}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
