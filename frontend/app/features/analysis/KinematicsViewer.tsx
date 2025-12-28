import { useState, useMemo, useCallback } from 'react';
import { useStore } from '~/store/useStore';
import { ChevronLeft, Play, Pause, AlertTriangle, CheckCircle, Layers } from 'lucide-react';
import type { KinematicResult } from '~/types/model';
import AnalysisCanvas from './AnalysisCanvas';
import { drawStructuralSystem } from '../drawing/drawKinematicSystem';

export default function KinematicViewer() {
    const kinematicResult = useStore(s => s.analysis.kinematicResult) as KinematicResult | null;
    const setMode = useStore(s => s.shared.actions.setMode);

    const [activeModeIndex, setActiveModeIndex] = useState(0);
    const [amplitude, setAmplitude] = useState(0.5);
    const [isPlaying, setIsPlaying] = useState(true);

    // We use a ref for start time to keep it consistent across renders without triggering effects
    const startTime = useMemo(() => Date.now(), []);

    const handleRender = useCallback((ctx: CanvasRenderingContext2D, view: any) => {
        if (!kinematicResult || !kinematicResult.system) return;

        // 1. Draw Ghost (Original System)
        ctx.save();
        ctx.globalAlpha = 0.15;
        drawStructuralSystem(ctx, kinematicResult.system, view, kinematicResult.system.nodes);
        ctx.restore();

        // 2. Calculate Animation Factor
        const time = (Date.now() - startTime) / 1000;
        const animFactor = (isPlaying && kinematicResult.is_kinematic)
            ? Math.sin(time * 3) * amplitude
            : (kinematicResult.is_kinematic ? amplitude : 0);

        // 3. Calculate Deformed Nodes
        const mode = kinematicResult.modes[activeModeIndex];
        const deformedNodes = kinematicResult.system.nodes.map(node => {
            if (!mode?.velocities?.[node.id]) return node;
            const vel = mode.velocities[node.id];
            return {
                ...node,
                position: {
                    x: node.position.x + (vel[0] * animFactor),
                    y: node.position.y + (vel[1] * animFactor)
                }
            };
        });

        // 4. Draw Deformed System
        drawStructuralSystem(ctx, kinematicResult.system, view, deformedNodes);

    }, [kinematicResult, activeModeIndex, amplitude, isPlaying, startTime]);

    if (!kinematicResult) return <div>No Kinematic Data</div>;

    return (
        <AnalysisCanvas onRender={handleRender}>
            {/* Top Left: Back & Status */}
            <div className="absolute top-4 left-4 flex gap-4 animate-in fade-in slide-in-from-top-4 duration-500">
                <button
                    onClick={() => setMode('EDITOR')}
                    className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow-sm border border-slate-200 text-slate-600 hover:text-slate-900 font-medium transition-colors hover:bg-slate-50"
                >
                    <ChevronLeft size={16} /> <span>Editor</span>
                </button>
                <div className={`flex items-center gap-3 px-4 py-2 rounded-lg shadow-sm border ${kinematicResult.is_kinematic ? 'bg-amber-50 border-amber-200 text-amber-800' : 'bg-green-50 border-green-200 text-green-800'}`}>
                    {kinematicResult.is_kinematic ? <AlertTriangle size={18} /> : <CheckCircle size={18} />}
                    <div className="flex flex-col leading-none">
                        <span className="text-[10px] uppercase font-bold opacity-70">Status</span>
                        <span className="font-bold text-sm">
                            {kinematicResult.is_kinematic ? `Kinematic (DoF: ${kinematicResult.dof})` : 'Stable Structure'}
                        </span>
                    </div>
                </div>
            </div>

            {/* Animation Controls */}
            {kinematicResult.is_kinematic && (
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-white/90 backdrop-blur-sm p-4 rounded-2xl shadow-2xl border border-slate-200 flex flex-col gap-4 w-[420px] animate-in slide-in-from-bottom-8 duration-500">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => setIsPlaying(!isPlaying)}
                            className="w-12 h-12 flex-shrink-0 flex items-center justify-center rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-md transition-all active:scale-95"
                        >
                            {isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" className="ml-1" />}
                        </button>
                        <div className="flex flex-col flex-1 gap-1">
                            <div className="flex justify-between text-xs font-semibold text-slate-500 uppercase">
                                <span>Amplitude</span>
                                <span>{(amplitude * 100).toFixed(0)}%</span>
                            </div>
                            <input
                                type="range"
                                min="0" max="200"
                                value={amplitude * 100}
                                onChange={(e) => setAmplitude(Number(e.target.value) / 100)}
                                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                            />
                        </div>
                    </div>
                    {/* Mode Selector */}
                    {kinematicResult.modes.length > 0 && (
                        <div className="pt-3 border-t border-slate-100">
                            <div className="flex items-center gap-2 mb-2 text-slate-500">
                                <Layers size={14} />
                                <span className="text-[10px] font-bold uppercase tracking-wider">Mechanisms / Modes</span>
                            </div>
                            <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                                {kinematicResult.modes.map((_, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => setActiveModeIndex(idx)}
                                        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all whitespace-nowrap border ${activeModeIndex === idx ? 'bg-blue-50 border-blue-200 text-blue-700' : 'bg-white border-slate-200'}`}
                                    >
                                        Mode {idx + 1}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </AnalysisCanvas>
    );
}
