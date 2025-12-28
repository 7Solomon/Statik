import { useState, useCallback } from 'react';
import { useStore } from '~/store/useStore';
import { ChevronLeft, RotateCw, ArrowRight, ArrowUp, Zap, Info } from 'lucide-react';
import type { FEMResult } from '~/types/model';
import AnalysisCanvas from './AnalysisCanvas';
import { SolutionRenderer, type DiagramType } from '../drawing/SolutionRenderer';

export default function SolutionViewer() {
    const solutionResult = useStore(s => s.analysis.solutionResult) as FEMResult | null;
    const setMode = useStore(s => s.shared.actions.setMode);
    const [diagramType, setDiagramType] = useState<DiagramType>('M');

    const handleRender = useCallback((ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, view: any) => {
        if (!solutionResult) return;

        SolutionRenderer.render(
            ctx,
            canvas,
            solutionResult.system,
            solutionResult,
            diagramType,
            view
        );
    }, [solutionResult, diagramType]);

    if (!solutionResult) return <div className="p-4 text-slate-400">No Solution Data Available</div>;

    return (
        <AnalysisCanvas onRender={handleRender}>
            {/* Top Left: Navigation */}
            <div className="absolute top-4 left-4 flex gap-4">
                <button
                    onClick={() => setMode('EDITOR')}
                    className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow-sm border border-slate-200 text-slate-600 hover:text-slate-900 font-medium transition-colors hover:bg-slate-50"
                >
                    <ChevronLeft size={16} />
                    <span>Editor</span>
                </button>
            </div>

            {/* Bottom Center: Diagram Controls */}
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-white/90 backdrop-blur-sm p-2 rounded-xl shadow-lg border border-slate-200 flex gap-2 animate-in slide-in-from-bottom-8 duration-500">
                <DiagramButton
                    active={diagramType === 'N'}
                    onClick={() => setDiagramType('N')}
                    label="N"
                    desc="Axial Force"
                    icon={<ArrowRight size={18} />} // Horizontal Arrow
                />
                <DiagramButton
                    active={diagramType === 'V'}
                    onClick={() => setDiagramType('V')}
                    label="V"
                    desc="Shear Force"
                    icon={<ArrowUp size={18} />} // Vertical Arrow
                />
                <DiagramButton
                    active={diagramType === 'M'}
                    onClick={() => setDiagramType('M')}
                    label="M"
                    desc="Bending Moment"
                    icon={<RotateCw size={18} />} // Circular Arrow
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
            <div className="absolute top-20 left-4 bg-white/80 backdrop-blur px-3 py-1.5 rounded-md border border-slate-200 text-xs text-slate-500 font-mono flex items-center gap-2">
                <Info size={12} />
                {solutionResult.success ? "Analysis Converged" : "Analysis Failed"}
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
                    : 'bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-900'}
            `}
        >
            {icon}
            {/* Small Label Indicator */}
            <span className={`absolute -bottom-1 -right-1 text-[9px] font-bold px-1 rounded 
                ${active ? 'bg-white text-blue-600' : 'bg-slate-100 text-slate-500'}`}>
                {label}
            </span>
        </button>
    );
}
