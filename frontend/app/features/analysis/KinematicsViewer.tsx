import { useState, useMemo, useCallback } from "react";
import { useStore } from "~/store/useStore";
import { Play, Pause, AlertTriangle, CheckCircle, Layers, RotateCw, RefreshCw } from "lucide-react";
import AnalysisCanvas from "./AnalysisCanvas";
import { drawStructuralSystem } from "../drawing/drawKinematicSystem";
import { RenderUtils } from "../drawing/RenderUtils";

export default function KinematicViewer() {
    const session = useStore(s => s.analysis.analysisSession);
    const kinematicResult = session?.kinematicResult;
    const system = session?.system;

    // Actions
    const setKinematicResult = useStore(s => s.analysis.actions.setKinematicResult);

    // Local State
    const [isLoading, setIsLoading] = useState(false);
    const [activeModeIndex, setActiveModeIndex] = useState(0);
    const [amplitude, setAmplitude] = useState(0.5);
    const [isPlaying, setIsPlaying] = useState(true);

    // Animation Timer
    const startTime = useMemo(() => Date.now(), []);

    // --- API CALL ---
    const handleRunAnalysis = async () => {
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

            const res = await fetch('api/analyze/kinematics', {
                method: 'POST',
                body: JSON.stringify(payload),
                headers: { 'Content-Type': 'application/json' }
            });

            if (!res.ok) throw new Error("Failed");
            const data = await res.json();
            setKinematicResult(data);
        } catch (e) {
            console.error("Kinematic analysis failed:", e);
            // Ideally invoke a toast here
        } finally {
            setIsLoading(false);
        }
    };

    // --- RENDER LOOP ---
    // In KinematicViewer.tsx

    const handleRender = useCallback((ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, view: any) => {
        if (!system) return;

        RenderUtils.clearScreen(ctx, canvas);
        RenderUtils.drawGrid(ctx, canvas, view);

        if (!kinematicResult) {
            drawStructuralSystem(ctx, system, view, system.nodes);
            return;
        }

        // Draw Ghost
        ctx.save();
        ctx.globalAlpha = 0.15;
        drawStructuralSystem(ctx, system, view, system.nodes);
        ctx.restore();

        // Animation Factor
        const time = (Date.now() - startTime) / 1000;
        const animFactor = (isPlaying && kinematicResult.is_kinematic)
            ? Math.sin(time * 3) * amplitude
            : (kinematicResult.is_kinematic ? amplitude : 0);

        const mode = kinematicResult.modes[activeModeIndex];

        // Deform Nodes
        const deformedNodes = (mode && mode.node_velocities)
            ? system.nodes.map(node => {
                if (!mode.node_velocities[node.id]) return node;
                const vel = mode.node_velocities[node.id];
                return {
                    ...node,
                    position: {
                        x: node.position.x + vel[0] * animFactor,
                        y: node.position.y + vel[1] * animFactor
                    }
                };
            })
            : system.nodes;

        // Deform Scheiben
        // Deform Scheiben - USE TRANSFORM APPROACH
        const deformedScheiben = (mode?.scheibe_velocities && system.scheiben)
            ? system.scheiben.map(scheibe => {
                const vel = mode.scheibe_velocities?.[scheibe.id];
                if (!vel) return scheibe;

                const [center_vx, center_vy, omega] = vel;

                // Current center
                const old_cx = (scheibe.corner1.x + scheibe.corner2.x) / 2;
                const old_cy = (scheibe.corner1.y + scheibe.corner2.y) / 2;

                // New center (translation only)
                const new_cx = old_cx + center_vx * animFactor;
                const new_cy = old_cy + center_vy * animFactor;

                // Keep corners at same relative positions (don't rotate them)
                const dx1 = scheibe.corner1.x - old_cx;
                const dy1 = scheibe.corner1.y - old_cy;
                const dx2 = scheibe.corner2.x - old_cx;
                const dy2 = scheibe.corner2.y - old_cy;

                // Rotation angle (accumulate)
                const angle = omega * animFactor;

                return {
                    ...scheibe,
                    corner1: {
                        x: new_cx + dx1,  // Translate only
                        y: new_cy + dy1
                    },
                    corner2: {
                        x: new_cx + dx2,  // Translate only
                        y: new_cy + dy2
                    },
                    rotation: scheibe.rotation + angle * (180 / Math.PI)  // Store total rotation
                };
            })
            : system.scheiben;


        // Create deformed system
        const deformedSystem = {
            ...system,
            scheiben: deformedScheiben
        };

        // Extract rigid bodies
        const rigidBodyScheibeIds = new Set<string>();
        if (mode?.rigid_bodies && system.scheiben) {
            mode.rigid_bodies.forEach(rb => {
                const scheibe = system.scheiben[rb.id];
                if (scheibe) rigidBodyScheibeIds.add(scheibe.id);
            });
        }

        // Draw
        drawStructuralSystem(
            ctx,
            deformedSystem,
            view,
            deformedNodes,
            kinematicResult.is_kinematic,
            rigidBodyScheibeIds
        );

    }, [kinematicResult, system, activeModeIndex, amplitude, isPlaying, startTime]);

    // --- RENDER UI ---
    // Case 1: No System (Shouldn't happen if initialized correctly)
    if (!system || system.nodes.length === 0) return <div className="flex h-full items-center justify-center text-slate-400">No System Loaded</div>;

    // Case 2: System Loaded, No Result -> Show "Run" Card
    if (!kinematicResult) {
        return (
            <AnalysisCanvas onRender={handleRender}>
                <div className="absolute inset-0 flex items-center justify-center bg-white/40 backdrop-blur-[2px] z-20 pointer-events-none">
                    <div className="bg-white p-6 rounded-xl shadow-xl border border-slate-100 text-center max-w-sm w-full mx-4 animate-in zoom-in-95 duration-200 pointer-events-auto">
                        <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Layers size={24} />
                        </div>
                        <h3 className="text-lg font-bold text-slate-800 mb-2">Kinematic Analysis</h3>
                        <p className="text-slate-500 mb-6 text-sm">
                            Analyze degrees of freedom to check for mechanisms and stability issues.
                        </p>
                        <button
                            onClick={handleRunAnalysis}
                            disabled={isLoading}
                            className="w-full py-2.5 px-4 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded-lg shadow-sm disabled:opacity-70 flex items-center justify-center gap-2 transition-all"
                        >
                            {isLoading ? <RotateCw className="animate-spin" size={18} /> : <Play size={18} />}
                            <span>{isLoading ? 'Solving...' : 'Run Kinematics'}</span>
                        </button>
                    </div>
                </div>
            </AnalysisCanvas>
        );
    }

    // Case 3: Result Loaded -> Show Full UI
    return (
        <AnalysisCanvas onRender={handleRender}>
            {/* Top Left: Status Badge */}
            <div className="absolute top-4 left-4 flex gap-4 animate-in fade-in slide-in-from-top-4 duration-500 z-20">
                <div className={`flex items-center gap-3 px-4 py-2 rounded-lg shadow-sm border ${kinematicResult.is_kinematic
                    ? 'bg-amber-50 border-amber-200 text-amber-800'
                    : 'bg-green-50 border-green-200 text-green-800'
                    }`}>
                    {kinematicResult.is_kinematic ? <AlertTriangle size={18} /> : <CheckCircle size={18} />}
                    <div className="flex flex-col leading-none">
                        <span className="text-[10px] uppercase font-bold opacity-70">Status</span>
                        <span className="font-bold text-sm">
                            {kinematicResult.is_kinematic
                                ? `Kinematic (DoF: ${kinematicResult.dof})`
                                : "Stable Structure"}
                        </span>
                    </div>
                </div>

                {/* Re-Run Button */}
                <button
                    onClick={handleRunAnalysis}
                    disabled={isLoading}
                    className="p-2 bg-white border border-slate-200 text-slate-500 hover:text-blue-600 rounded-lg shadow-sm hover:bg-slate-50"
                    title="Re-run Analysis"
                >
                    <RefreshCw size={18} className={isLoading ? "animate-spin" : ""} />
                </button>
            </div>

            {/* Bottom Center: Animation Controls (Only if Kinematic) */}
            {kinematicResult.is_kinematic && (
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-white/90 backdrop-blur-sm p-4 rounded-2xl shadow-2xl border border-slate-200 flex flex-col gap-4 w-[420px] animate-in slide-in-from-bottom-8 duration-500 z-20">
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
                                        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all whitespace-nowrap border ${activeModeIndex === idx
                                            ? 'bg-blue-50 border-blue-200 text-blue-700'
                                            : 'bg-white border-slate-200 hover:bg-slate-50 text-slate-600'
                                            }`}
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
