import React from 'react';
import { useStore } from "~/store/useStore";
import { Database, BrainCircuit, Layout } from "lucide-react";
import DataSetManager from "./datasets/DataSetManager"; // Make sure this path points to your INNER component
import TrainingManager from "./models/TrainingManager";

export default function ModelManagement() {
    const viewMode = useStore((s) => s.model_management.viewMode);
    const setViewMode = useStore((s) => s.model_management.actions.setViewMode);
    const datasets = useStore((s) => s.model_management.datasets);

    return (
        // ABSOLUTE INSET-0 IS CRITICAL HERE
        <div className="absolute inset-0 flex flex-col w-full h-full bg-slate-50">

            {/* 1. Header with Tab Switcher */}
            <header className="flex-none px-6 py-3 flex items-center justify-between bg-white border-b border-slate-200 z-10">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                        <Layout size={20} />
                    </div>
                    <div>
                        <h1 className="font-bold text-slate-800 text-sm uppercase tracking-wide">Model Management</h1>
                        <p className="text-xs text-slate-500">
                            {viewMode === 'DATASETS' ? 'Synthetic Data Generation' : 'Model Training & Evaluation'}
                        </p>
                    </div>
                </div>

                {/* The Pill Switcher */}
                <div className="flex gap-1 p-1 bg-slate-100 rounded-lg border border-slate-200">
                    <TabButton
                        active={viewMode === 'DATASETS'}
                        onClick={() => setViewMode('DATASETS')}
                        icon={<Database size={14} />}
                        label="Datasets"
                    />
                    <TabButton
                        active={viewMode === 'TRAINING'}
                        onClick={() => setViewMode('TRAINING')}
                        icon={<BrainCircuit size={14} />}
                        label="Training"
                    />
                </div>

                <div className="w-32"></div> {/* Spacer for balance */}
            </header>

            {/* 2. Content Area */}
            <div className="flex-1 relative overflow-hidden">
                <div className="w-full h-full overflow-y-auto custom-scrollbar p-6">
                    <div className="max-w-7xl mx-auto">
                        {viewMode === 'DATASETS' && <DataSetManager />}
                        {viewMode === 'TRAINING' && <TrainingManager />}
                    </div>
                </div>
            </div>
        </div>
    );
}

function TabButton({ active, onClick, icon, label }: any) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${active
                ? 'bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200'
                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'
                }`}
        >
            {icon}
            <span>{label}</span>
        </button>
    );
}
