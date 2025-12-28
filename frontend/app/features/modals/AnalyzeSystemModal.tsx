import { useState } from "react";
import { X, Play, Loader2, CheckCircle, AlertTriangle, Activity, Wand2, ArrowRight } from "lucide-react";
import { useStore } from "~/store/useStore";
import type { KinematicResult, StructuralSystem } from "~/types/model";
import type { AnalysisViewMode } from "~/store/types";


interface AnalyzeSystemModalProps {
    onClose: () => void;
    onAnalysisComplete: (result: StructuralSystem | KinematicResult, type: AnalysisViewMode) => void;
}

export function AnalyzeSystemModal({ onClose, onAnalysisComplete }: AnalyzeSystemModalProps) {
    // 1. Get Data from Store (Read Only)
    const nodes = useStore(s => s.editor.nodes);
    const members = useStore(s => s.editor.members);
    const loads = useStore(s => s.editor.loads);

    // 2. Local State
    const [isLoading, setIsLoading] = useState(false);
    const [statusMessage, setStatusMessage] = useState<string>("");
    const [error, setError] = useState<string | null>(null);

    const [result, setResult] = useState<any | null>(null);
    const [resultType, setResultType] = useState<AnalysisViewMode | null>(null);

    // --- SHARED PAYLOAD BUILDER ---
    const getPayload = () => ({
        nodes,
        members,
        loads,
        meta: { zoom: 1, pan: { x: 0, y: 0 } }
    });

    // --- A. KINEMATIC ANALYSIS ---
    const handleRunAnalysis = async () => {
        setIsLoading(true);
        setStatusMessage("Solving Kinematics...");
        setError(null);
        setResult(null);
        setResultType(null);

        try {
            const response = await fetch('api/analyze/kinematics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getPayload())
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.details || "Analysis failed");
            }

            const data: KinematicResult = await response.json();

            // Store locally first
            setResult(data);
            setResultType('KINEMATIC');

        } catch (err: any) {
            console.error(err);
            setError(err.message || "Failed to connect to analysis server.");
        } finally {
            setIsLoading(false);
            setStatusMessage("");
        }
    };

    // --- B. SYSTEM SIMPLIFICATION ---
    const handleSimplify = async () => {
        setIsLoading(true);
        setStatusMessage("Pruning Cantilevers...");
        setError(null);
        setResult(null);
        setResultType(null);

        try {
            const response = await fetch('api/analyze/simplify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getPayload())
            });

            if (!response.ok) {
                throw new Error("Simplification failed");
            }

            const data: StructuralSystem = await response.json();

            // Store locally first
            setResult(data);
            setResultType('SIMPLIFIED');

        } catch (err: any) {
            console.error(err);
            setError(err.message || "Failed to simplify system.");
        } finally {
            setIsLoading(false);
            setStatusMessage("");
        }
    };

    // --- FINAL HANDOFF ---
    const handleConfirm = () => {
        if (result && resultType) {
            onAnalysisComplete(result, resultType);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/20 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-md bg-white rounded-xl shadow-2xl border border-slate-100 p-6 flex flex-col scale-100 animate-in zoom-in-95 duration-200">

                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div className="flex items-center gap-2">
                        <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                            <Activity size={20} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-800">System Analysis</h3>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
                        <X size={20} />
                    </button>
                </div>

                {/* Content Area */}
                <div className="flex-1 mb-6">
                    {!result && !isLoading && !error && (
                        <div className="text-center py-6 px-4 bg-slate-50 rounded-lg border border-slate-100 border-dashed">
                            <p className="text-sm text-slate-500 mb-2">
                                Ready to analyze system with:
                            </p>
                            <div className="font-semibold text-slate-700">
                                {nodes.length} Nodes &bull; {members.length} Members
                            </div>
                        </div>
                    )}

                    {isLoading && (
                        <div className="flex flex-col items-center justify-center py-8">
                            <Loader2 size={32} className="animate-spin text-indigo-600 mb-3" />
                            <p className="text-sm font-medium text-slate-500">{statusMessage}</p>
                        </div>
                    )}

                    {error && (
                        <div className="bg-red-50 border border-red-100 text-red-600 p-4 rounded-lg text-sm flex items-start gap-3">
                            <AlertTriangle size={18} className="shrink-0 mt-0.5" />
                            <div>
                                <span className="font-semibold block mb-1">Error</span>
                                {error}
                            </div>
                        </div>
                    )}

                    {/* SUCCESS STATE - DIFFERENTIATED BY TYPE */}
                    {result && resultType === 'KINEMATIC' && (
                        <div className={`p-4 rounded-lg border ${result.is_kinematic ? 'bg-amber-50 border-amber-200' : 'bg-green-50 border-green-200'}`}>
                            <div className="flex items-center gap-3">
                                {result.is_kinematic ? <AlertTriangle className="text-amber-600" size={24} /> : <CheckCircle className="text-green-600" size={24} />}
                                <div>
                                    <h4 className={`font-bold ${result.is_kinematic ? 'text-amber-800' : 'text-green-800'}`}>
                                        {result.is_kinematic ? "System is Kinematic" : "System is Stable"}
                                    </h4>
                                    <div className={`text-sm ${result.is_kinematic ? 'text-amber-700' : 'text-green-700'}`}>
                                        Degree of Freedom: {result.dof}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {result && resultType === 'SIMPLIFIED' && (
                        <div className="p-4 rounded-lg border bg-purple-50 border-purple-200">
                            <div className="flex items-center gap-3">
                                <Wand2 className="text-purple-600" size={24} />
                                <div>
                                    <h4 className="font-bold text-purple-800">System Simplified</h4>
                                    <div className="text-sm text-purple-700">
                                        Reduced to {result.members.length} members
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer Buttons */}
                <div className="flex gap-3 justify-end pt-4 border-t border-slate-100">

                    {/* 1. Results are ready: Show "Visualize" button */}
                    {result ? (
                        <>
                            <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-500 hover:text-slate-700">
                                Back
                            </button>
                            <button
                                onClick={handleConfirm}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm"
                            >
                                <span>Visualize Result</span>
                                <ArrowRight size={16} />
                            </button>
                        </>
                    ) : (
                        /* 2. Initial State: Show Action Buttons */
                        <>
                            <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-lg">
                                Cancel
                            </button>

                            <button
                                onClick={handleSimplify}
                                disabled={isLoading}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-sm transition-all disabled:opacity-50"
                            >
                                <Wand2 size={16} className="text-purple-500" />
                                Simplify
                            </button>

                            <button
                                onClick={handleRunAnalysis}
                                disabled={isLoading}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 rounded-lg shadow-sm transition-all disabled:opacity-50"
                            >
                                <Play size={16} fill="currentColor" />
                                Run Analysis
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
