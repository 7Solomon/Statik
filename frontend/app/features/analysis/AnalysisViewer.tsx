import { useEffect, useRef, useState } from 'react';
import { useStore } from '~/store/useStore';
import { ChevronLeft, Play, Pause, AlertTriangle, CheckCircle, Layers } from 'lucide-react';

export default function AnalysisViewer() {
    // Global State
    const result = useStore(s => s.analysisResult);
    const setMode = useStore(s => s.actions.setMode);

    // Local State for Viewport & Animation
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [activeModeIndex, setActiveModeIndex] = useState(0);
    const [amplitude, setAmplitude] = useState(0.5);
    const [isPlaying, setIsPlaying] = useState(true);

    // Viewport State (Separate from Editor viewport)
    const view = useRef({ x: 0, y: 0, zoom: 1.0 });
    const isDragging = useRef(false);
    const lastPos = useRef({ x: 0, y: 0 });

    // --- 1. Animation Loop ---
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !result) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationId: number;
        const startTime = Date.now();

        const render = () => {
            if (!result) return;

            // 1. Setup Canvas
            const width = canvas.parentElement?.clientWidth || 800;
            const height = canvas.parentElement?.clientHeight || 600;
            canvas.width = width;
            canvas.height = height;

            ctx.clearRect(0, 0, width, height);
            ctx.save();

            // 2. Apply Transform (Pan/Zoom)
            // Center 0,0 typically implies center of screen in structural apps
            const cx = width / 2 + view.current.x;
            const cy = height / 2 + view.current.y;

            ctx.translate(cx, cy);
            ctx.scale(view.current.zoom, -view.current.zoom); // Invert Y for engineering coordinates

            // 3. Draw Grid (Optional)
            drawGrid(ctx, view.current.zoom);

            // 4. Calculate Animation Factor
            // Sine wave for oscillation: -1 to 1
            const time = (Date.now() - startTime) / 1000;
            const animFactor = isPlaying ? Math.sin(time * 2) * amplitude : 0;

            // 5. Draw System
            drawSystem(ctx, result, activeModeIndex, animFactor);

            ctx.restore();
            animationId = requestAnimationFrame(render);
        };

        render();
        return () => cancelAnimationFrame(animationId);
    }, [result, activeModeIndex, amplitude, isPlaying]);


    // --- 2. Drawing Logic (Simplified Port of your old JS) ---
    function drawSystem(ctx: CanvasRenderingContext2D, data: any, modeIdx: number, factor: number) {
        if (!data.system) return;
        const mode = data.modes[modeIdx];

        // Draw Members
        data.system.members.forEach((m: any) => {
            const startNode = data.system.nodes.find((n: any) => n.id === m.startNodeId);
            const endNode = data.system.nodes.find((n: any) => n.id === m.endNodeId);
            if (!startNode || !endNode) return;

            // Get Displacements if kinematic
            const dStart = getDisplacement(startNode.id, mode, factor);
            const dEnd = getDisplacement(endNode.id, mode, factor);

            // Draw Deformed State
            ctx.beginPath();
            ctx.moveTo(startNode.position.x + dStart.x, startNode.position.y + dStart.y);
            ctx.lineTo(endNode.position.x + dEnd.x, endNode.position.y + dEnd.y);

            // Style based on stability
            ctx.strokeStyle = data.is_kinematic ? '#ef4444' : '#22c55e'; // Red if mechanism, Green if stable
            ctx.lineWidth = 0.05; // 5cm width in world coords
            ctx.stroke();

            // Draw Original (Ghost) State
            ctx.beginPath();
            ctx.moveTo(startNode.position.x, startNode.position.y);
            ctx.lineTo(endNode.position.x, endNode.position.y);
            ctx.strokeStyle = '#e2e8f0'; // Light slate
            ctx.lineWidth = 0.02;
            ctx.stroke();
        });

        // Draw Nodes
        data.system.nodes.forEach((n: any) => {
            const disp = getDisplacement(n.id, mode, factor);
            ctx.beginPath();
            ctx.arc(n.position.x + disp.x, n.position.y + disp.y, 0.08, 0, 2 * Math.PI);
            ctx.fillStyle = '#1e293b';
            ctx.fill();
        });
    }

    function getDisplacement(nodeId: string, mode: any, factor: number) {
        if (!mode || !mode.node_velocities[nodeId]) return { x: 0, y: 0 };
        const vel = mode.node_velocities[nodeId]; // [vx, vy, w]
        return {
            x: vel[0] * factor,
            y: vel[1] * factor
        };
    }

    function drawGrid(ctx: CanvasRenderingContext2D, zoom: number) {
        // ... simple grid logic
    }

    // --- 3. Input Handlers ---
    const handleWheel = (e: React.WheelEvent) => {
        const scale = e.deltaY > 0 ? 0.9 : 1.1;
        view.current.zoom *= scale;
    };

    const handleMouseDown = (e: React.MouseEvent) => {
        isDragging.current = true;
        lastPos.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!isDragging.current) return;
        const dx = e.clientX - lastPos.current.x;
        const dy = e.clientY - lastPos.current.y;
        view.current.x += dx;
        view.current.y += dy;
        lastPos.current = { x: e.clientX, y: e.clientY };
    };

    if (!result) return <div>No Result</div>;

    return (
        <div className="relative w-full h-full bg-slate-50 overflow-hidden">
            {/* CANVAS */}
            <canvas
                ref={canvasRef}
                className="block w-full h-full cursor-move touch-none"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={() => isDragging.current = false}
                onMouseLeave={() => isDragging.current = false}
                onWheel={handleWheel}
            />

            {/* OVERLAYS */}

            {/* Top Left: Back Button & Status */}
            <div className="absolute top-4 left-4 flex gap-4">
                <button
                    onClick={() => setMode('EDITOR')}
                    className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow-sm border border-slate-200 text-slate-600 hover:text-slate-900 font-medium transition-colors"
                >
                    <ChevronLeft size={16} />
                    Back to Editor
                </button>

                <div className={`flex items-center gap-3 px-4 py-2 rounded-lg shadow-sm border ${result.is_kinematic ? 'bg-amber-50 border-amber-200 text-amber-800' : 'bg-green-50 border-green-200 text-green-800'}`}>
                    {result.is_kinematic ? <AlertTriangle size={18} /> : <CheckCircle size={18} />}
                    <span className="font-bold">f = {result.dof}</span>
                </div>
            </div>

            {/* Bottom Center: Animation Controls (Only if Kinematic) */}
            {result.is_kinematic && (
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-white p-4 rounded-2xl shadow-xl border border-slate-100 flex flex-col gap-4 w-96">

                    {/* Playback Controls */}
                    <div className="flex items-center justify-between">
                        <button
                            onClick={() => setIsPlaying(!isPlaying)}
                            className="w-10 h-10 flex items-center justify-center rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                        >
                            {isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" className="ml-0.5" />}
                        </button>

                        <div className="flex flex-col flex-1 mx-4">
                            <label className="text-[10px] uppercase font-bold text-slate-400 mb-1">Amplitude</label>
                            <input
                                type="range"
                                min="0" max="200"
                                value={amplitude * 100}
                                onChange={(e) => setAmplitude(Number(e.target.value) / 100)}
                                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                            />
                        </div>
                    </div>

                    {/* Mode Selector */}
                    {result.modes.length > 1 && (
                        <div className="pt-3 border-t border-slate-100">
                            <div className="flex items-center gap-2 mb-2 text-slate-500">
                                <Layers size={14} />
                                <span className="text-xs font-semibold uppercase">Select Mechanism Mode</span>
                            </div>
                            <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                                {result.modes.map((_, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => setActiveModeIndex(idx)}
                                        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all whitespace-nowrap
                                            ${activeModeIndex === idx
                                                ? 'bg-blue-600 text-white shadow-md'
                                                : 'bg-slate-50 text-slate-600 hover:bg-slate-100'}`}
                                    >
                                        Mode {idx + 1}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
