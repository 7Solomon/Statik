import { useCallback, useState } from "react";
import { useStore } from "~/store/useStore";
import { Share2, Wand2, RotateCw, RefreshCw } from "lucide-react";
import AnalysisCanvas from "./AnalysisCanvas";
import { Renderer } from "../drawing/Renderer";
import { RenderUtils } from "../drawing/RenderUtils";
import type { AnalysisInteractionState } from "~/types/app";

export default function SimplifiedViewer() {
    const session = useStore(s => s.analysis.analysisSession);
    const simplifyResult = session?.simplifyResult;
    const system = session?.system;

    // Actions
    const setSimplifyResult = useStore(s => s.analysis.actions.setSimplifyResult);

    const [isLoading, setIsLoading] = useState(false);

    // --- API CALL ---
    const handleSimplify = async () => {
        if (!system || system.nodes.length === 0) return;
        setIsLoading(true);
        try {
            const payload = {
                nodes: system.nodes,
                members: system.members,
                loads: system.loads,
                scheiben: system.scheiben,
                meta: { zoom: 1, pan: { x: 0, y: 0 } }
            };

            const res = await fetch('api/analyze/simplify', {
                method: 'POST',
                body: JSON.stringify(payload),
                headers: { 'Content-Type': 'application/json' }
            });

            //console.log('Response status:', res.status);

            if (!res.ok) throw new Error("Failed");
            const data = await res.json();
            setSimplifyResult(data); // This is a StructuralSystem
        } catch (e) {
            console.error("Simplification failed:", e);
        } finally {
            setIsLoading(false);
        }
    };


    // Determine what to render: The simplified result OR the original system (as background)
    const systemToRender = simplifyResult ?? system;
    const interaction = session?.interaction;

    const handleRender = useCallback((ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, view: any) => {
        if (!systemToRender) return;

        const interaction: AnalysisInteractionState = session?.interaction ?? {
            isDragging: false,
            mousePos: { x: 0, y: 0 },
            hoveredNodeId: null,
            hoveredMemberId: null
        };

        Renderer.renderAnalysis(
            ctx,
            canvas,
            systemToRender.nodes,
            systemToRender.members,
            systemToRender.loads,
            systemToRender.scheiben,
            view,
            interaction
        );
    }, [systemToRender, session?.interaction]);


    if (!system || system.nodes.length === 0) return <div className="flex h-full items-center justify-center text-slate-400">No System Loaded</div>;

    // Case 2: No Result -> Show "Run" Card
    if (!simplifyResult) {
        return (
            <AnalysisCanvas onRender={handleRender}>
                <div className="absolute inset-0 flex items-center justify-center bg-white/40 backdrop-blur-[2px] z-20 pointer-events-none">
                    <div className="bg-white p-6 rounded-xl shadow-xl border border-slate-100 text-center max-w-sm w-full mx-4 animate-in zoom-in-95 duration-200 pointer-events-auto">
                        <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Wand2 size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-800 mb-2">Model Simplification</h3>
                        <p className="text-slate-500 mb-6 text-sm">
                            Automatically prune cantilevers and reduce the system to its essential load-bearing topology.
                        </p>
                        <button
                            onClick={handleSimplify}
                            disabled={isLoading}
                            className="w-full py-2.5 px-4 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-lg shadow-sm disabled:opacity-70 flex items-center justify-center gap-2 transition-all"
                        >
                            {isLoading ? <RotateCw className="animate-spin" size={18} /> : <Wand2 size={18} />}
                            <span>{isLoading ? 'Processing...' : 'Simplify System'}</span>
                        </button>
                    </div>
                </div>
            </AnalysisCanvas>
        );
    }

    // Case 3: Result Loaded
    return (
        <AnalysisCanvas onRender={handleRender}>
            <div className="absolute top-4 left-4 flex gap-2 z-20">
                <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow-sm border border-slate-200">
                    <Share2 size={16} className="text-purple-500" />
                    <span className="font-semibold text-sm text-slate-700">Simplified Topology</span>
                    <span className="text-xs text-slate-400 ml-2 border-l border-slate-200 pl-2">
                        {simplifyResult.members.length} Members
                    </span>
                </div>

                {/* Re-Run Button */}
                <button
                    onClick={handleSimplify}
                    disabled={isLoading}
                    className="p-2 bg-white border border-slate-200 text-slate-500 hover:text-purple-600 rounded-lg shadow-sm hover:bg-slate-50"
                    title="Re-run Simplification"
                >
                    <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
                </button>
            </div>
        </AnalysisCanvas>
    );
}
