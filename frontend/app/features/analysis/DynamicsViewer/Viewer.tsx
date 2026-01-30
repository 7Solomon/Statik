import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { useStore } from "~/store/useStore";
import { RefreshCw, XCircle, RotateCw, Play, Activity, Waves, Clock, Zap } from "lucide-react";
import AnalysisCanvas from "../AnalysisCanvas"; // Reuse your existing canvas
import { drawStructuralSystem } from "../../drawing/drawKinematicSystem";
import { RenderUtils } from "../../drawing/RenderUtils";
import DynamicInsights from "./Insights";
import DynamicControls from "./Controls";
import { getDeformedSystem } from "./Utils";


export default function DynamicAnalysisViewer() {
    const session = useStore(s => s.analysis.analysisSession);
    const system = session?.system;
    const dynamicResult = session?.dynamicResult;
    const setDynamicResult = useStore(s => s.analysis.actions.setDynamicResult);

    // State
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'modal' | 'transient'>('modal');
    const [activeModeIndex, setActiveModeIndex] = useState(0);
    const [modeAmplitude, setModeAmplitude] = useState(0.5);
    const [timeIndex, setTimeIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    const animationRef = useRef<number | null>(null);

    // --- API Call (Same as before) ---
    const handleRunDynamics = async () => {
        if (!system) return;
        setIsLoading(true);
        setError(null);

        try {
            const payload = {
                nodes: system.nodes,
                members: system.members,
                loads: system.loads,
                scheiben: system.scheiben,
                constraints: system.constraints
            };

            const res = await fetch('api/analyze/dynamics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error(`Server returned ${res.status}`);

            const data = await res.json();

            // CHECK FOR BUSINESS LOGIC ERROR (success: false)
            if (data.success === false) {
                setError(data.message || "Unknown analysis error");
                setDynamicResult(null); // Clear invalid previous results
            } else {
                // Success
                setDynamicResult(data);

                // Auto-switch tab if time history exists
                if (data.timeHistory?.length > 0) {
                    setActiveTab('transient');
                    setIsPlaying(true);
                } else {
                    setActiveTab('modal');
                }
            }

        } catch (e) {
            console.error(e);
            setError("Failed to connect to analysis server.");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (activeTab !== 'transient' || !isPlaying || !dynamicResult?.timeHistory) {
            if (animationRef.current) cancelAnimationFrame(animationRef.current);
            return;
        }

        let lastTime = performance.now();
        const dt = (dynamicResult.timeHistory[1]?.time || 0.01) - (dynamicResult.timeHistory[0]?.time || 0);

        const loop = (now: number) => {
            const delta = (now - lastTime) / 1000;
            if (delta >= dt) {
                setTimeIndex(prev => {
                    const next = prev + 1;
                    if (next >= dynamicResult.timeHistory.length) {
                        setIsPlaying(false);
                        return 0; // Loop or Stop
                    }
                    return next;
                });
                lastTime = now;
            }
            animationRef.current = requestAnimationFrame(loop);
        };

        animationRef.current = requestAnimationFrame(loop);
        return () => cancelAnimationFrame(animationRef.current!);
    }, [isPlaying, activeTab, dynamicResult]);


    // --- Render Handler ---
    const handleRender = useCallback((ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, view: any) => {
        if (!system) return;
        RenderUtils.clearScreen(ctx, canvas);
        RenderUtils.drawGrid(ctx, canvas, view);

        if (!dynamicResult) {
            drawStructuralSystem(ctx, system, view, system.nodes);
            return;
        }

        // 1. Draw Ghost (Original System)
        ctx.save();
        ctx.globalAlpha = 0.1;
        drawStructuralSystem(ctx, system, view, system.nodes);
        ctx.restore();

        // 2. Calculate Deformation
        const t_vis = performance.now() / 1000;
        const deformResult = getDeformedSystem(
            system, dynamicResult, activeTab, activeModeIndex, timeIndex, modeAmplitude, t_vis
        );

        // 3. Draw Active System
        if (deformResult) {
            drawStructuralSystem(
                ctx,
                deformResult.system,
                view,
                deformResult.nodes,
                false, // isKinematicMode
                new Set() // rigidBodies
            );
        }

    }, [system, dynamicResult, activeTab, activeModeIndex, timeIndex, modeAmplitude]);


    // --- UI Structure ---
    if (!dynamicResult) {
        return (
            <AnalysisCanvas onRender={handleRender}>
                <div className="absolute inset-0 flex items-center justify-center bg-white/40 backdrop-blur-[2px] z-20">
                    <div className="bg-white p-6 rounded-xl shadow-xl border border-slate-100 text-center max-w-sm w-full mx-4 animate-in zoom-in-95">
                        <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Activity size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-800 mb-2">Dynamic Analysis</h3>
                        <p className="text-slate-500 mb-6 text-sm">
                            Compute natural frequencies, mode shapes, and time history response.
                        </p>
                        <button
                            onClick={handleRunDynamics}
                            disabled={isLoading}
                            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg shadow-sm disabled:opacity-70 flex items-center justify-center gap-2 transition-all"
                        >
                            {isLoading ? <RotateCw className="animate-spin" size={18} /> : <Play size={18} />}
                            <span>{isLoading ? 'Solving...' : 'Run Analysis'}</span>
                        </button>
                    </div>
                </div>
            </AnalysisCanvas>
        );
    }

    return (
        <AnalysisCanvas onRender={handleRender}>

            {/* TOP LEFT: Info & Tabs */}
            <div className="absolute top-4 left-4 flex flex-col gap-3 z-20 animate-in slide-in-from-left-4 duration-500">

                {/* 1. Status Badge */}
                <div className="flex items-center gap-3 px-4 py-2 rounded-xl shadow-sm border bg-white border-slate-200 backdrop-blur-sm bg-white/90">
                    {dynamicResult.isStable
                        ? <div className="p-1.5 bg-green-100 text-green-700 rounded-full"><Zap size={14} fill="currentColor" /></div>
                        : <div className="p-1.5 bg-red-100 text-red-700 rounded-full"><Activity size={14} /></div>
                    }

                    <div className="flex flex-col leading-none">
                        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">System State</span>
                        <span className={`font-bold text-sm ${dynamicResult.isStable ? 'text-green-700' : 'text-red-600'}`}>
                            {dynamicResult.isStable ? 'Stable' : 'Unstable'}
                        </span>
                    </div>

                    <div className="w-px h-6 bg-slate-100 mx-1" />

                    <button
                        onClick={handleRunDynamics}
                        disabled={isLoading}
                        className="p-2 hover:bg-slate-50 text-slate-400 hover:text-indigo-600 rounded-lg transition-all active:scale-95"
                        title="Re-run Analysis"
                    >
                        <RefreshCw size={16} className={isLoading ? "animate-spin" : ""} />
                    </button>
                </div>

                <div className="bg-white/90 backdrop-blur-sm p-1 rounded-xl shadow-sm border border-slate-200 flex gap-1">
                    <button
                        onClick={() => { setActiveTab('modal'); setIsPlaying(true); }}
                        className={`flex-1 px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-2 ${activeTab === 'modal'
                            ? 'bg-indigo-50 text-indigo-700 shadow-sm border border-indigo-100'
                            : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                            }`}
                    >
                        <Waves size={14} /> Modes
                    </button>
                    <button
                        onClick={() => { setActiveTab('transient'); setIsPlaying(true); }}
                        className={`flex-1 px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-2 ${activeTab === 'transient'
                            ? 'bg-indigo-50 text-indigo-700 shadow-sm border border-indigo-100'
                            : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                            }`}
                    >
                        <Clock size={14} /> Time History
                    </button>
                </div>
            </div>


            {/* RIGHT: Engineering Insights */}
            <DynamicInsights result={dynamicResult} />

            {activeTab === 'transient' && (
                <DynamicControls
                    result={dynamicResult}
                    timeIndex={timeIndex}
                    setTimeIndex={setTimeIndex}
                    isPlaying={isPlaying}
                    setIsPlaying={setIsPlaying}
                    totalSteps={dynamicResult.timeHistory.length}
                />
            )}

            {/* 2. MODAL CONTROLS */}
            {activeTab === 'modal' && (
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 w-[480px] z-20">
                    <div className="bg-white/90 backdrop-blur-sm p-4 rounded-2xl shadow-xl border border-slate-200 animate-in slide-in-from-bottom-4">

                        {/* Header Info */}
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Natural Frequencies</span>
                            <span className="text-xs font-mono bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded border border-indigo-100">
                                {dynamicResult.naturalFrequencies[activeModeIndex]?.frequency.toFixed(2)} Hz
                            </span>
                        </div>

                        {/* Mode Selector List */}
                        <div className="flex gap-2 overflow-x-auto pb-2 mb-2 scrollbar-thin scrollbar-thumb-slate-200 scrollbar-track-transparent">
                            {dynamicResult.naturalFrequencies.map((_, i) => (
                                <button
                                    key={i}
                                    onClick={() => setActiveModeIndex(i)}
                                    className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${activeModeIndex === i
                                        ? 'bg-indigo-600 border-indigo-600 text-white shadow-md'
                                        : 'bg-white border-slate-200 text-slate-600 hover:border-indigo-300 hover:bg-slate-50'
                                        }`}
                                >
                                    Mode {i + 1}
                                </button>
                            ))}
                        </div>

                        {/* Amplitude Slider */}
                        <div className="flex items-center gap-3 bg-slate-50 p-2 rounded-lg border border-slate-100">
                            <span className="text-[10px] font-bold text-slate-400 uppercase">Amplitude</span>
                            <input
                                type="range"
                                min="0.1"
                                max="2"
                                step="0.1"
                                value={modeAmplitude}
                                onChange={(e) => setModeAmplitude(parseFloat(e.target.value))}
                                className="flex-1 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                            />
                            <span className="text-[10px] font-mono text-slate-500 w-6 text-right">{modeAmplitude.toFixed(1)}x</span>
                        </div>
                    </div>
                </div>
            )}

        </AnalysisCanvas>
    );
}