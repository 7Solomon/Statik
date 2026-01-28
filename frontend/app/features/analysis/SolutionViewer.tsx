import { useState, useCallback } from "react";
import { useStore } from "~/store/useStore";
import { RotateCw, ArrowRight, ArrowUp, Zap, Info, RefreshCw, AlertTriangle } from "lucide-react";
import AnalysisCanvas from "./AnalysisCanvas";
import { SolutionRenderer, type DiagramType } from "../drawing/SolutionRenderer";
import type { FEMResult } from "~/types/model";


export default function SolutionViewer() {
    const session = useStore(s => s.analysis.analysisSession);
    const solutionResult = session?.solutionResult;
    const system = session?.system;

    // Actions
    const setSolutionResult = useStore(s => s.analysis.actions.setSolutionResult);

    // Local State
    const [diagramType, setDiagramType] = useState<DiagramType>('M');
    const [isLoading, setIsLoading] = useState(false);

    // --- API CALL ---
    const handleRunFEM = async () => {
        if (!system) return;
        setIsLoading(true);
        try {
            const payload = {
                nodes: system.nodes,
                members: system.members,
                loads: system.loads,
                meta: { zoom: 1, pan: { x: 0, y: 0 } }
            };

            const res = await fetch('api/analyze/solution', {
                method: 'POST',
                body: JSON.stringify(payload),
                headers: { 'Content-Type': 'application/json' }
            });

            if (!res.ok) {
                // Network or server error (4xx/5xx)
                const errorText = await res.text();
                setSolutionResult({
                    success: false,
                    error: `Server error (${res.status}): ${errorText}`
                });
                return;
            }

            const data: FEMResult = await res.json();

            // Always set result (even if success=false)
            setSolutionResult(data);

        } catch (e) {
            console.error("FEM analysis failed:", e);
            setSolutionResult({
                success: false,
                error: `Network error: ${e instanceof Error ? e.message : 'Unknown error'}`
            });
        } finally {
            setIsLoading(false);
        }
    };


    const handleRender = useCallback((ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, view: any) => {
        if (!system || system.nodes.length === 0) return;

        if (!solutionResult || !solutionResult.success) {
            return;
        }

        SolutionRenderer.render(
            ctx,
            canvas,
            system,
            solutionResult,
            diagramType,
            view
        );
    }, [solutionResult, system, diagramType]);

    if (!system || system.nodes.length === 0) {
        return <div className="flex h-full items-center justify-center text-slate-400">No System Loaded</div>;
    }

    // Case 2: No Result -> Show "Run" Card
    if (!solutionResult) {
        return (
            <AnalysisCanvas onRender={handleRender}>
                <div className="absolute inset-0 flex items-center justify-center bg-white/40 backdrop-blur-[2px] z-20 pointer-events-none">
                    <div className="bg-white p-6 rounded-xl shadow-xl border border-slate-100 text-center max-w-sm w-full mx-4 animate-in zoom-in-95 duration-200 pointer-events-auto">
                        <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Zap size={24} fill="currentColor" />
                        </div>
                        <h3 className="text-lg font-bold text-slate-800 mb-2">Internal Forces (FEM)</h3>
                        <p className="text-slate-500 mb-6 text-sm">
                            Calculate N, V, M diagrams and reactions using the Matrix Displacement Method.
                        </p>
                        <button
                            onClick={handleRunFEM}
                            disabled={isLoading}
                            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg shadow-sm disabled:opacity-70 flex items-center justify-center gap-2 transition-all"
                        >
                            {isLoading ? <RotateCw className="animate-spin" size={18} /> : <Zap size={18} fill="currentColor" />}
                            <span>{isLoading ? 'Calculating...' : 'Calculate Forces'}</span>
                        </button>
                    </div>
                </div>
            </AnalysisCanvas>
        );
    }

    // Case 3A: Result with Error -> Show Error Card
    if (!solutionResult.success) {
        return (
            <AnalysisCanvas onRender={handleRender}>
                <div className="absolute inset-0 flex items-center justify-center bg-white/40 backdrop-blur-[2px] z-20 pointer-events-none">
                    <div className="bg-white p-6 rounded-xl shadow-xl border border-red-200 text-center max-w-md w-full mx-4 animate-in zoom-in-95 duration-200 pointer-events-auto">
                        <div className="w-12 h-12 bg-red-50 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
                            <AlertTriangle size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-800 mb-2">Analysis Failed</h3>

                        {/* Error Message Box */}
                        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                            <p className="text-sm text-red-700 font-mono break-words">
                                {solutionResult.error || "Unknown error occurred"}
                            </p>
                        </div>

                        {/* Helpful Tips */}
                        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 mb-6 text-left">
                            <p className="text-xs text-slate-600 mb-2 font-semibold">Common solutions:</p>
                            <ul className="text-xs text-slate-600 space-y-1.5">
                                {solutionResult.error?.includes("Singular") && (
                                    <>
                                        <li className="flex items-start gap-2">
                                            <span className="text-red-500 mt-0.5">•</span>
                                            <span>Add supports to constrain the structure</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <span className="text-red-500 mt-0.5">•</span>
                                            <span>Remove double hinges at the same node</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <span className="text-red-500 mt-0.5">•</span>
                                            <span>Check for disconnected members</span>
                                        </li>
                                    </>
                                )}
                                {!solutionResult.error?.includes("Singular") && (
                                    <>
                                        <li className="flex items-start gap-2">
                                            <span className="text-slate-400 mt-0.5">•</span>
                                            <span>Check member properties (E, A, I)</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <span className="text-slate-400 mt-0.5">•</span>
                                            <span>Verify node connectivity</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <span className="text-slate-400 mt-0.5">•</span>
                                            <span>Check load definitions</span>
                                        </li>
                                    </>
                                )}
                            </ul>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex gap-2">
                            <button
                                onClick={handleRunFEM}
                                disabled={isLoading}
                                className="flex-1 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg shadow-sm disabled:opacity-70 flex items-center justify-center gap-2 transition-all"
                            >
                                {isLoading ? (
                                    <>
                                        <RotateCw className="animate-spin" size={18} />
                                        <span>Retrying...</span>
                                    </>
                                ) : (
                                    <>
                                        <RefreshCw size={18} />
                                        <span>Retry</span>
                                    </>
                                )}
                            </button>
                            <button
                                onClick={() => setSolutionResult(null)}
                                className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-lg transition-all"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            </AnalysisCanvas>
        );
    }

    // Case 3B: Result Loaded Successfully
    return (
        <AnalysisCanvas onRender={handleRender}>
            {/* Re-Run Button (Top Left) */}
            <div className="absolute top-4 left-4 z-20">
                <button
                    onClick={handleRunFEM}
                    disabled={isLoading}
                    className="p-2 bg-white border border-slate-200 text-slate-500 hover:text-indigo-600 rounded-lg shadow-sm hover:bg-slate-50"
                    title="Recalculate Forces"
                >
                    <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
                </button>
            </div>

            {/* Bottom Center Diagram Controls */}
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-white/90 backdrop-blur-sm p-2 rounded-xl shadow-lg border border-slate-200 flex gap-2 animate-in slide-in-from-bottom-8 duration-500 z-20">
                <DiagramButton
                    active={diagramType === 'N'}
                    onClick={() => setDiagramType('N')}
                    label="N"
                    desc="Axial Force"
                    icon={<ArrowRight size={18} />}
                />
                <DiagramButton
                    active={diagramType === 'V'}
                    onClick={() => setDiagramType('V')}
                    label="V"
                    desc="Shear Force"
                    icon={<ArrowUp size={18} />}
                />
                <DiagramButton
                    active={diagramType === 'M'}
                    onClick={() => setDiagramType('M')}
                    label="M"
                    desc="Bending Moment"
                    icon={<RotateCw size={18} />}
                />

                <div className="w-px bg-slate-200 mx-1"></div>

                <DiagramButton
                    active={diagramType === 'NONE'}
                    onClick={() => setDiagramType('NONE')}
                    label="Off"
                    desc="Hide Diagrams"
                    icon={<Zap size={18} className="opacity-50" />}
                />
            </div>

            {/* Info Badge */}
            <div className="absolute top-20 left-4 bg-emerald-50 backdrop-blur px-3 py-1.5 rounded-md border border-emerald-200 text-xs text-emerald-700 font-mono flex items-center gap-2 z-20">
                <Info size={12} />
                Analysis Converged
            </div>
        </AnalysisCanvas>
    );
}

// Helper Component for the buttons
function DiagramButton({ active, onClick, label, desc, icon }: any) {
    return (
        <button
            onClick={onClick}
            title={desc}
            className={`
                relative flex items-center justify-center w-10 h-10 rounded-lg transition-all
                ${active
                    ? 'bg-blue-600 text-white shadow-md scale-105'
                    : 'bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-900'
                }
            `}
        >
            {icon}
            <span className={`absolute -bottom-1 -right-1 text-[9px] font-bold px-1 rounded ${active ? 'bg-white text-blue-600' : 'bg-slate-100 text-slate-500'
                }`}>
                {label}
            </span>
        </button>
    );
}
