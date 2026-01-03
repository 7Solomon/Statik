import React, { useState, useEffect, useCallback } from 'react';
import {
    Play, Loader2, Cpu, Save
} from 'lucide-react';
import { useStore } from '~/store/useStore';

export default function TrainingManager() {
    // --- Store Integration ---
    const {
        models,
        datasets,
        actions: { fetchModels, fetchDatasets }
    } = useStore(state => state.model_management);

    // --- Local UI State ---
    // We keep status local because it requires high-frequency polling (2s) 
    // and doesn't necessarily need to be global until training finishes.
    const [status, setStatus] = useState<any>({ is_running: false });
    const [selectedDataset, setSelectedDataset] = useState<string>("");
    const [config, setConfig] = useState({ modelName: "", epochs: 50 });
    const [loading, setLoading] = useState(false);

    // --- Initialization ---
    // Load models and datasets when this component mounts
    useEffect(() => {
        fetchModels();
        fetchDatasets();
    }, [fetchModels, fetchDatasets]);

    // --- Training Status Polling ---
    const fetchStatus = useCallback(async () => {
        try {
            const res = await fetch('/api/models/status');
            if (res.ok) {
                const data = await res.json();

                // If training just finished (was running, now isn't), refresh the global models list
                if (!data.is_running && status.is_running) {
                    fetchModels();
                }
                setStatus(data);
            }
        } catch (e) { console.error("Failed to get status", e); }
    }, [status.is_running, fetchModels]);

    // Poll status every 2 seconds
    useEffect(() => {
        const interval = setInterval(fetchStatus, 2000);
        return () => clearInterval(interval);
    }, [fetchStatus]);

    // --- Actions ---
    const startTraining = async () => {
        if (!selectedDataset) return;
        setLoading(true);
        try {
            const res = await fetch('/api/models/train', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    dataset_path: selectedDataset,
                    model_name: config.modelName || `model_${Date.now()}`,
                    epochs: config.epochs
                })
            });
            if (!res.ok) throw new Error("Failed to start");
            fetchStatus(); // Immediately update status UI
        } catch (e) {
            alert("Error starting training: " + e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-500">

            {/* 1. Active Training Status Card */}
            {status.is_running ? (
                <div className="bg-white p-6 rounded-xl border border-indigo-100 shadow-sm relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-1 bg-indigo-100">
                        <div className="h-full bg-indigo-500 animate-progress"></div>
                    </div>
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h3 className="text-lg font-semibold text-indigo-900 flex items-center gap-2">
                                <Loader2 className="animate-spin text-indigo-500" size={20} />
                                Training in Progress
                            </h3>
                            <p className="text-slate-500 text-sm mt-1">Model: {status.model_name}</p>
                        </div>
                        <div className="text-right">
                            <span className="text-2xl font-mono font-bold text-slate-700">
                                {status.metrics?.length > 0 ? status.metrics[status.metrics.length - 1].epoch : 0}
                            </span>
                            <span className="text-slate-400 text-sm ml-1">epochs</span>
                        </div>
                    </div>

                    {/* Metrics Preview */}
                    <div className="bg-slate-50 rounded-lg p-3 font-mono text-xs text-slate-600 h-32 overflow-y-auto">
                        {status.metrics?.slice(-5).map((m: any, i: number) => (
                            <div key={i} className="flex justify-between border-b border-slate-100 last:border-0 py-1">
                                <span>Ep {m.epoch}:</span>
                                <span>box_loss: {m['train/box_loss']?.toFixed(4)}</span>
                                <span>mAP50: {m['metrics/mAP50(B)']?.toFixed(4)}</span>
                            </div>
                        ))}
                        {(!status.metrics || status.metrics.length === 0) && (
                            <div className="text-center py-8 text-slate-400">Initializing training environment...</div>
                        )}
                    </div>
                </div>
            ) : (
                /* 2. Start New Training Form */
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                    <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                        <Cpu size={20} className="text-slate-400" />
                        Start New Model
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-500 uppercase">Target Dataset</label>
                            <select
                                value={selectedDataset}
                                onChange={(e) => setSelectedDataset(e.target.value)}
                                className="w-full p-2.5 rounded-lg border border-slate-200 bg-slate-50 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                            >
                                <option value="">Select a dataset...</option>
                                {/* Mapped from STORE datasets instead of props */}
                                {datasets.map((ds: any) => (
                                    <option key={ds.path} value={ds.path}>{ds.name}</option>
                                ))}
                            </select>
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-500 uppercase">Model Name (Optional)</label>
                            <input
                                type="text"
                                placeholder="e.g. v1_production"
                                value={config.modelName}
                                onChange={e => setConfig({ ...config, modelName: e.target.value })}
                                className="w-full p-2.5 rounded-lg border border-slate-200 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-500 uppercase">Epochs</label>
                            <input
                                type="number"
                                value={config.epochs}
                                onChange={e => setConfig({ ...config, epochs: parseInt(e.target.value) })}
                                className="w-full p-2.5 rounded-lg border border-slate-200 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                            />
                        </div>
                    </div>

                    <div className="flex justify-end">
                        <button
                            onClick={startTraining}
                            disabled={!selectedDataset || loading}
                            className={`flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium transition-all ${!selectedDataset || loading
                                ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                                : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md hover:shadow-lg'
                                }`}
                        >
                            {loading ? <Loader2 className="animate-spin" size={18} /> : <Play size={18} />}
                            Start Training
                        </button>
                    </div>
                </div>
            )}

            {/* 3. Trained Models List */}
            <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-500 uppercase flex items-center gap-2">
                    <Save size={14} /> Available Models
                </h3>

                {models.length === 0 ? (
                    <div className="text-center p-8 bg-slate-50 rounded-lg border border-dashed border-slate-200 text-slate-400">
                        No trained models found.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {models.map((model: any) => (
                            <div key={model.name} className="bg-white p-4 rounded-lg border border-slate-200 hover:border-indigo-200 transition-colors group">
                                <div className="flex justify-between items-start mb-2">
                                    <div className="font-medium text-slate-700">{model.name}</div>
                                    <span className="text-xs text-slate-400">{new Date(model.created * 1000).toLocaleDateString()}</span>
                                </div>
                                <div className="flex gap-2 mt-4">
                                    <button className="flex-1 py-1.5 text-xs font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 rounded border border-slate-200 transition-colors">
                                        Download Weights
                                    </button>
                                    <button className="flex-1 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded border border-indigo-200 transition-colors">
                                        Run Inference
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
