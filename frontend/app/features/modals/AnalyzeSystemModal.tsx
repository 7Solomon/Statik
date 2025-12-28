import { useState } from "react";
import { X, Play, Loader2, CheckCircle, AlertTriangle, Activity, Wand2, ArrowRight, Zap } from "lucide-react";
import { useStore } from "~/store/useStore";
import type { KinematicResult, StructuralSystem, FEMResult } from "~/types/model";
import type { AnalysisViewMode } from "~/store/types";

interface AnalyzeSystemModalProps {
    onClose: () => void;
    onAnalysisComplete: (result: KinematicResult | StructuralSystem | FEMResult, type: AnalysisViewMode) => void;
}

export function AnalyzeSystemModal({ onClose, onAnalysisComplete }: AnalyzeSystemModalProps) {
    const nodes = useStore(s => s.editor.nodes);
    const members = useStore(s => s.editor.members);
    const loads = useStore(s => s.editor.loads);

    const [isLoading, setIsLoading] = useState(false);
    const [statusMessage, setStatusMessage] = useState<string>("");
    const [error, setError] = useState<string | null>(null);

    const [result, setResult] = useState<any | null>(null);
    const [resultType, setResultType] = useState<AnalysisViewMode | null>(null);

    const getPayload = () => ({
        nodes,
        members,
        loads,
        meta: { zoom: 1, pan: { x: 0, y: 0 } }
    });

    // --- A. KINEMATIC ANALYSIS ---
    const handleRunKinematics = async () => {
        runAnalysis('api/analyze/kinematics', 'Solving Kinematics...', 'KINEMATIC');
    };

    // --- B. SYSTEM SIMPLIFICATION ---
    const handleSimplify = async () => {
        runAnalysis('api/analyze/simplify', 'Pruning Cantilevers...', 'SIMPLIFIED');
    };

    // --- C. FEM ANALYSIS ---
    const handleRunFEMSolution = async () => {
        runAnalysis('api/analyze/solution', 'Calculating Internal Forces...', 'SOLUTION');
    };

    // Generic Runner to reduce duplication
    const runAnalysis = async (endpoint: string, message: string, type: AnalysisViewMode) => {
        setIsLoading(true);
        setStatusMessage(message);
        setError(null);
        setResult(null);
        setResultType(null);

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getPayload())
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.details || "Analysis failed");
            }

            const data = await response.json();
            console.log(data)
            setResult(data);
            setResultType(type);

        } catch (err: any) {
            console.error(err);
            setError(err.message || "Failed to connect to analysis server.");
        } finally {
            setIsLoading(false);
            setStatusMessage("");
        }
    }

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

                    {/* SUCCESS STATE - KINEMATIC */}
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

                    {/* SUCCESS STATE - SIMPLIFIED */}
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

                    {/* SUCCESS STATE - SOLUTION (FEM) */}
                    {result && resultType === 'SOLUTION' && (
                        <div className="p-4 rounded-lg border bg-blue-50 border-blue-200">
                            <div className="flex items-center gap-3">
                                <Zap className="text-blue-600" size={24} />
                                <div>
                                    <h4 className="font-bold text-blue-800">Forces Calculated</h4>
                                    <div className="text-sm text-blue-700">
                                        Max Moment: {(Math.max(0, ...Object.values(result.memberResults).map((m: any) => Math.max(Math.abs(m.maxM), Math.abs(m.minM)))) / 1000).toFixed(3)} kNm
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer Buttons */}
                <div className="flex gap-3 justify-end pt-4 border-t border-slate-100 flex-wrap">
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
                        <>
                            <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-lg">
                                Cancel
                            </button>

                            {/* Simplify */}
                            <button
                                onClick={handleSimplify}
                                disabled={isLoading}
                                className="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-sm transition-all disabled:opacity-50"
                            >
                                <Wand2 size={16} className="text-purple-500" />
                                Simplify
                            </button>

                            {/* Kinematics */}
                            <button
                                onClick={handleRunKinematics}
                                disabled={isLoading}
                                className="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-sm transition-all disabled:opacity-50"
                            >
                                <Play size={16} className="text-amber-500" />
                                Kinematics
                            </button>

                            {/* Forces (Main Action) */}
                            <button
                                onClick={handleRunFEMSolution}
                                disabled={isLoading}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 rounded-lg shadow-sm transition-all disabled:opacity-50"
                            >
                                <Zap size={16} fill="currentColor" />
                                Calculate Forces
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
