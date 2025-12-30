import React, { useState, useEffect } from 'react';
import { Play, Activity, Package, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function ModelManager() {
    const [models, setModels] = useState([]);
    const [trainingStatus, setTrainingStatus] = useState<any>(null);
    const [config, setConfig] = useState({ datasetPath: '', epochs: 10, name: 'my_yolo_model' });
    const [activeTab, setActiveTab] = useState('overview');

    useEffect(() => {
        const fetchStatus = async () => {
            const res = await fetch('/api/models/status');
            const data = await res.json();
            setTrainingStatus(data);
        };

        const interval = setInterval(fetchStatus, 3000);
        return () => clearInterval(interval);
    }, []);

    const startTraining = async () => {
        await fetch('/api/models/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                dataset_path: config.datasetPath,
                model_name: config.name,
                epochs: config.epochs
            })
        });
    };

    return (
        <div className="p-8 bg-slate-50 min-h-screen">
            <div className="max-w-6xl mx-auto">
                <header className="mb-8">
                    <h1 className="text-3xl font-bold text-slate-900">Model Training Lab</h1>
                    <p className="text-slate-500">Train and monitor YOLO detection models</p>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left: Training Form */}
                    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <Play size={18} className="text-indigo-600" /> Start New Session
                        </h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-slate-500 uppercase mb-1">Model Name</label>
                                <input
                                    className="w-full border rounded-md p-2 text-sm"
                                    value={config.name}
                                    onChange={e => setConfig({ ...config, name: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 uppercase mb-1">Dataset Path</label>
                                <input
                                    className="w-full border rounded-md p-2 text-sm font-mono"
                                    placeholder="./content/datasets/dataset_..."
                                    value={config.datasetPath}
                                    onChange={e => setConfig({ ...config, datasetPath: e.target.value })}
                                />
                            </div>
                            <button
                                onClick={startTraining}
                                disabled={trainingStatus?.is_running}
                                className="w-full bg-indigo-600 text-white py-2 rounded-md font-medium hover:bg-indigo-700 disabled:bg-slate-300 transition-colors"
                            >
                                {trainingStatus?.is_running ? 'Training in Progress...' : 'Launch Training'}
                            </button>
                        </div>
                    </div>

                    {/* Right: Monitoring Chart */}
                    <div className="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                        <h2 className="text-lg font-semibold mb-4 flex items-center justify-between">
                            <div className="flex items-center gap-2"><Activity size={18} className="text-emerald-500" /> Live Metrics</div>
                            {trainingStatus?.is_running && (
                                <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full animate-pulse">
                                    Epoch {trainingStatus.metrics?.length || 0}
                                </span>
                            )}
                        </h2>

                        <div className="h-64 w-full">
                            {trainingStatus?.metrics?.length > 0 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={trainingStatus.metrics}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis dataKey="epoch" />
                                        <YAxis />
                                        <Tooltip />
                                        <Line type="monotone" dataKey="train/box_loss" stroke="#6366f1" strokeWidth={2} dot={false} />
                                        <Line type="monotone" dataKey="val/box_loss" stroke="#ec4899" strokeWidth={2} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-slate-400">
                                    <Package size={48} strokeWidth={1} className="mb-2" />
                                    <p className="text-sm">No active training data to display</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Model Gallery / History */}
                <div className="mt-8">
                    <h2 className="text-xl font-bold text-slate-800 mb-4">Trained Models</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Map through your model list API here */}
                        <div className="bg-white border border-slate-200 rounded-lg p-4 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-emerald-50 text-emerald-600 rounded">
                                    <CheckCircle2 size={20} />
                                </div>
                                <div>
                                    <div className="font-medium text-slate-900">yolov8_stanli_v1</div>
                                    <div className="text-xs text-slate-500">mAP50: 0.92 • 48.2MB</div>
                                </div>
                            </div>
                            <button className="text-xs font-semibold text-indigo-600 hover:underline">Test Model</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}