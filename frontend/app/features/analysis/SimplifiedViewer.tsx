import { useCallback } from 'react';
import { useStore } from '~/store/useStore';
import { ChevronLeft, Share2 } from 'lucide-react';
import type { StructuralSystem } from '~/types/model';
import AnalysisCanvas from './AnalysisCanvas';
import { Renderer } from '../drawing/Renderer';

export default function SimplifiedViewer() {
    const simplifyResult = useStore(s => s.analysis.simplifyResult) as StructuralSystem | null;
    const interaction = useStore(s => s.analysis.interaction);
    const setMode = useStore(s => s.shared.actions.setMode);

    const handleRender = useCallback((ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, view: any) => {
        if (!simplifyResult) return;

        Renderer.renderAnalysis(
            ctx,
            canvas,
            simplifyResult.nodes,
            simplifyResult.members,
            simplifyResult.loads,
            view,
            interaction
        );
    }, [simplifyResult, interaction]);

    if (!simplifyResult) return <div>No Simplified Data</div>;

    return (
        <AnalysisCanvas onRender={handleRender}>
            <div className="absolute top-4 left-4 flex gap-4">
                <button
                    onClick={() => setMode('EDITOR')}
                    className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow-sm border border-slate-200 text-slate-600 hover:text-slate-900 font-medium transition-colors hover:bg-slate-50"
                >
                    <ChevronLeft size={16} />
                    <span>Editor</span>
                </button>

                <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow-sm border border-slate-200">
                    <Share2 size={16} className="text-blue-500" />
                    <span className="font-semibold text-sm text-slate-700">Simplified Topology</span>
                </div>
            </div>
        </AnalysisCanvas>
    );
}
