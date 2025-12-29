import { useEffect, useState } from 'react';
import { useStore } from '~/store/useStore';
import {
    Database, Plus, RotateCw, Image as ImageIcon, Clock, Eye, Cpu, AlertCircle,
    Folder, ChevronRight, ChevronLeft, Download
} from 'lucide-react';
import { format } from 'date-fns';
import DatasetViewer from './DataSetViewer';

export default function DatasetManager() {
    const { datasets, isLoading } = useStore((s) => s.dataset);
    const { fetchDatasets, generateDataset, previewSymbols } = useStore((s) => s.dataset.actions);

    const [numSamples, setNumSamples] = useState(100);
    const [selectedDataset, setSelectedDataset] = useState<any>(null);
    const [showViewer, setShowViewer] = useState(false);

    const estimatedSeconds = (numSamples * 0.05).toFixed(1);

    useEffect(() => {
        fetchDatasets();
    }, []);

    const handleDatasetSelect = (dataset: any) => {
        setSelectedDataset(dataset);
        setShowViewer(true);
    };

    return (
        <div className="flex flex-col h-full w-full bg-slate-50 p-6 overflow-hidden">
            <div className="max-w-7xl mx-auto w-full space-y-8 flex-1 overflow-y-auto pr-4">

                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold text-slate-800">Dataset Management</h1>
                    <p className="text-slate-500 mt-2">Synthetic structural engineering datasets for YOLO training.</p>
                </div>

                {/* Generator Card */}
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                    <div className="flex flex-col lg:flex-row gap-6 items-start lg:items-center justify-between">
                        <div className="space-y-4 w-full lg:w-auto">
                            <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                                <Cpu size={20} className="text-indigo-600" />
                                Generate New Dataset
                            </h3>

                            <div className="flex items-end gap-4">
                                <div className="space-y-1">
                                    <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Samples</label>
                                    <input
                                        type="number"
                                        value={numSamples}
                                        onChange={(e) => setNumSamples(Math.max(10, Number(e.target.value)))}
                                        className="block w-32 px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-indigo-500 outline-none transition-all disabled:bg-slate-100"
                                        min={10}
                                        max={10000}
                                        disabled={isLoading}
                                    />
                                </div>
                                <div className="pb-2 text-sm text-slate-400 flex items-center gap-1.5">
                                    <Clock size={14} />
                                    <span>Est. ~{estimatedSeconds}s</span>
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-3 self-end lg:self-center">
                            <button
                                onClick={() => previewSymbols()}
                                disabled={isLoading}
                                className="px-4 py-2.5 text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 font-medium rounded-lg flex items-center gap-2 transition-all disabled:opacity-50"
                            >
                                <Eye size={18} />
                                Preview Symbols
                            </button>
                            <button
                                onClick={() => generateDataset(numSamples)}
                                disabled={isLoading}
                                className={`px-6 py-2.5 font-medium rounded-lg flex items-center gap-2 shadow-sm transition-all ${isLoading
                                        ? 'bg-indigo-400 text-white cursor-not-allowed'
                                        : 'bg-indigo-600 hover:bg-indigo-700 text-white hover:shadow-md'
                                    }`}
                            >
                                {isLoading ? (
                                    <>
                                        <RotateCw className="animate-spin w-4 h-4" />
                                        Generating...
                                    </>
                                ) : (
                                    <>
                                        <Plus size={18} />
                                        Generate
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {isLoading && (
                        <div className="mt-6 p-4 bg-indigo-50 border border-indigo-200 rounded-xl flex items-center gap-3">
                            <RotateCw className="text-indigo-600 animate-spin" size={20} />
                            <div className="text-sm text-indigo-800">
                                <span className="font-semibold">Generation in progress</span> - Processing {numSamples} samples...
                            </div>
                        </div>
                    )}
                </div>

                {/* Datasets Grid */}
                <div className="space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                            Datasets ({datasets.length})
                        </h2>
                        <button
                            onClick={() => fetchDatasets()}
                            disabled={isLoading}
                            className="p-2 text-slate-400 hover:text-indigo-600 transition-all disabled:opacity-30"
                        >
                            <RotateCw size={18} />
                        </button>
                    </div>

                    {datasets.length === 0 ? (
                        <div className="grid place-items-center py-20 border-2 border-dashed border-slate-200 rounded-2xl bg-white/50">
                            <Database className="w-16 h-16 text-slate-300 mb-4" />
                            <h3 className="text-lg font-semibold text-slate-600 mb-1">No datasets yet</h3>
                            <p className="text-slate-500">Generate your first dataset above</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
                            {datasets.map((ds: any, i: number) => (
                                <DatasetCard
                                    key={ds.path}
                                    dataset={ds}
                                    onSelect={handleDatasetSelect}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Dataset Viewer (Slide-in Panel) */}
            {showViewer && selectedDataset && (
                <div className="fixed inset-0 bg-black/50 z-50 flex">
                    <button
                        onClick={() => setShowViewer(false)}
                        className="absolute top-6 right-6 z-10 p-2 bg-white/90 hover:bg-white rounded-full shadow-lg transition-all"
                    >
                        <ChevronLeft size={24} className="text-slate-700" />
                    </button>
                    <DatasetViewer
                        datasetPath={selectedDataset.path}
                        onClose={() => setShowViewer(false)}
                    />
                </div>
            )}
        </div>
    );
}

interface DatasetCardProps {
    dataset: any;
    onSelect: (dataset: any) => void;
}

function DatasetCard({ dataset, onSelect }: DatasetCardProps) {
    return (
        <div
            className="group bg-white border border-slate-200 hover:border-indigo-300 hover:shadow-xl rounded-xl p-5 cursor-pointer transition-all overflow-hidden hover:-translate-y-1"
            onClick={() => onSelect(dataset)}
        >
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                        <Database size={24} className="text-white drop-shadow-sm" />
                    </div>
                    <div className="min-w-0 flex-1">
                        <h4 className="font-semibold text-slate-900 truncate text-base" title={dataset.path}>
                            {dataset.path.split(/[\\/]/).pop()}
                        </h4>
                        <p className="text-xs text-slate-500 truncate" title={dataset.path}>
                            {dataset.path}
                        </p>
                    </div>
                </div>
                <div className="opacity-0 group-hover:opacity-100 transition-all ml-2">
                    <ChevronRight size={20} className="text-indigo-500" />
                </div>
            </div>

            <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between text-slate-600">
                    <span>Created</span>
                    <span>{format(new Date(dataset.created * 1000), 'MMM d, HH:mm')}</span>
                </div>
            </div>
        </div>
    );
}
