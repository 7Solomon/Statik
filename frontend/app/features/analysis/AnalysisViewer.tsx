import { useEffect, useRef, useState } from 'react';
import { useStore } from '~/store/useStore';
import { ChevronLeft, Play, Pause, AlertTriangle, CheckCircle, Layers, ZoomIn, ZoomOut, Maximize } from 'lucide-react';
import type { KinematicResult, Member, Node, KinematicMode } from '~/types/model';



export default function AnalysisViewer() {
    // Global State
    // We cast the result to our defined type for safety
    const result = useStore(s => s.kinematicResult) as KinematicResult | null;
    const setMode = useStore(s => s.actions.setMode);

    // Local State
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [activeModeIndex, setActiveModeIndex] = useState(0);
    const [amplitude, setAmplitude] = useState(0.5); // Animation scale factor
    const [isPlaying, setIsPlaying] = useState(true);

    // Viewport State
    const view = useRef({ x: 0, y: 0, zoom: 40.0 }); // 40 pixels per meter default
    const isDragging = useRef(false);
    const lastPos = useRef({ x: 0, y: 0 });

    // --- 1. Animation Loop ---
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !result || !result.system) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationId: number;
        const startTime = Date.now();

        const render = () => {
            // 1. Resize & Clear
            const width = canvas.parentElement?.clientWidth || 800;
            const height = canvas.parentElement?.clientHeight || 600;

            // Handle DPI scaling for sharp text/lines
            const dpr = window.devicePixelRatio || 1;
            canvas.width = width * dpr;
            canvas.height = height * dpr;
            ctx.scale(dpr, dpr);
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;

            ctx.clearRect(0, 0, width, height);
            ctx.save();

            // 2. Apply Viewport Transform
            // Center (cx, cy) is the screen center + pan offset
            const cx = width / 2 + view.current.x;
            const cy = height / 2 + view.current.y;

            ctx.translate(cx, cy);
            ctx.scale(view.current.zoom, -view.current.zoom); // Invert Y for engineering coords

            // 3. Draw Grid (Optional background reference)
            drawGrid(ctx, view.current.zoom, width, height, view.current);

            // 4. Calculate Animation Factor
            const time = (Date.now() - startTime) / 1000;
            // If kinematic, oscillate. If static, stay still (or 0).
            const animFactor = (isPlaying && result.is_kinematic)
                ? Math.sin(time * 3) * amplitude
                : (result.is_kinematic ? amplitude : 0);

            // 5. Draw Structure
            drawSystem(ctx, result, activeModeIndex, animFactor);

            ctx.restore();
            animationId = requestAnimationFrame(render);
        };

        render();
        return () => cancelAnimationFrame(animationId);
    }, [result, activeModeIndex, amplitude, isPlaying]);


    // --- 2. Drawing Logic ---

    function drawSystem(
        ctx: CanvasRenderingContext2D,
        data: KinematicResult,
        modeIdx: number,
        factor: number
    ) {
        const { system, modes, is_kinematic } = data;
        // Safety check: if no modes exist but system is kinematic, don't crash
        const mode = modes[modeIdx];

        // A. Draw Members
        system.members.forEach(member => {
            const startNode = system.nodes.find(n => n.id === member.startNodeId);
            const endNode = system.nodes.find(n => n.id === member.endNodeId);
            if (!startNode || !endNode) return;

            // Calculate Deformed Positions
            const dStart = getDisplacement(startNode.id, mode, factor);
            const dEnd = getDisplacement(endNode.id, mode, factor);

            const x1 = startNode.position.x + dStart.x;
            const y1 = startNode.position.y + dStart.y;
            const x2 = endNode.position.x + dEnd.x;
            const y2 = endNode.position.y + dEnd.y;

            // 1. Draw Original (Ghost) State - Light Grey
            ctx.beginPath();
            ctx.moveTo(startNode.position.x, startNode.position.y);
            ctx.lineTo(endNode.position.x, endNode.position.y);
            ctx.strokeStyle = '#e2e8f0';
            ctx.lineWidth = 0.05; // 5cm visual width
            ctx.lineCap = 'round';
            ctx.stroke();

            // 2. Draw Deformed State - Color Coded
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.strokeStyle = is_kinematic ? '#ef4444' : '#22c55e'; // Red = Mechanism, Green = Stable
            ctx.lineWidth = 0.08;
            ctx.stroke();

            // 3. Draw Releases (Hinges)
            drawRelease(ctx, x1, y1, x2, y2, member.releases.start.mz);
            drawRelease(ctx, x2, y2, x1, y1, member.releases.end.mz);
        });

        // B. Draw Nodes & Supports
        system.nodes.forEach(node => {
            const disp = getDisplacement(node.id, mode, factor);
            const x = node.position.x + disp.x;
            const y = node.position.y + disp.y;

            ctx.save();
            ctx.translate(x, y);

            // Draw Support Symbol if fixed
            if (node.supports.fixX || node.supports.fixY) {
                drawSupport(ctx, node);
            }

            // Draw Node Dot
            ctx.beginPath();
            ctx.arc(0, 0, 0.1, 0, 2 * Math.PI); // 10cm radius
            ctx.fillStyle = '#1e293b';
            ctx.fill();
            ctx.restore();
        });
    }

    function getDisplacement(nodeId: string, mode: KinematicMode | undefined, factor: number) {
        if (!mode || !mode.velocities || !mode.velocities[nodeId]) {
            return { x: 0, y: 0 };
        }
        // Access the velocities array [vx, vy]
        const vel = mode.velocities[nodeId];
        return {
            x: vel[0] * factor,
            y: vel[1] * factor
        };
    }

    function drawRelease(ctx: CanvasRenderingContext2D, x: number, y: number, lookX: number, lookY: number, isReleased: boolean) {
        if (!isReleased) return;
        // Calculate position slightly offset from node towards member center
        const dx = lookX - x;
        const dy = lookY - y;
        const len = Math.sqrt(dx * dx + dy * dy);
        if (len < 0.001) return;

        const off = 0.25; // Offset distance
        const cx = x + (dx / len) * off;
        const cy = y + (dy / len) * off;

        ctx.beginPath();
        ctx.arc(cx, cy, 0.06, 0, 2 * Math.PI);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 0.02;
        ctx.stroke();
    }

    function drawSupport(ctx: CanvasRenderingContext2D, node: Node) {
        ctx.save();
        // Rotate context if support is angled (converted to radians)
        ctx.rotate(node.rotation * (Math.PI / 180));

        ctx.strokeStyle = '#64748b';
        ctx.lineWidth = 0.04;
        ctx.fillStyle = '#cbd5e1';

        if (node.supports.fixX && node.supports.fixY && node.supports.fixM) {
            // Fixed (Clamp)
            ctx.beginPath();
            ctx.moveTo(0, -0.3);
            ctx.lineTo(0, 0.3);
            ctx.stroke();
            // Hatches
            for (let i = -0.3; i <= 0.3; i += 0.1) {
                ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(-0.15, i - 0.05); ctx.stroke();
            }
        } else if (node.supports.fixX && node.supports.fixY) {
            // Pinned (Triangle)
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(-0.2, -0.3);
            ctx.lineTo(0.2, -0.3);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
        } else if (node.supports.fixY) {
            // Roller (Circle or Triangle with line)
            ctx.beginPath();
            ctx.arc(0, -0.15, 0.15, 0, 2 * Math.PI);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(-0.25, -0.3);
            ctx.lineTo(0.25, -0.3);
            ctx.stroke();
        }

        ctx.restore();
    }

    function drawGrid(ctx: CanvasRenderingContext2D, zoom: number, w: number, h: number, viewState: any) {
        // Simple faint grid
        const gridSize = 1.0; // 1 meter grid
        const opacity = Math.min(1, Math.max(0, (zoom - 10) / 30)); // Fade in grid
        if (opacity <= 0) return;

        ctx.strokeStyle = `rgba(0,0,0, ${0.05 * opacity})`;
        ctx.lineWidth = 1 / zoom;

        // Calculate visible bounds to optimize
        // (Simplified: just drawing a large area around center for now)
        const range = 50;
        ctx.beginPath();
        for (let i = -range; i <= range; i++) {
            ctx.moveTo(i * gridSize, -range);
            ctx.lineTo(i * gridSize, range);
            ctx.moveTo(-range, i * gridSize);
            ctx.lineTo(range, i * gridSize);
        }
        ctx.stroke();
    }


    // --- 3. Input Handlers ---
    const handleWheel = (e: React.WheelEvent) => {
        const scale = e.deltaY > 0 ? 0.9 : 1.1;
        view.current.zoom = Math.max(5, Math.min(200, view.current.zoom * scale));
    };

    const handleMouseDown = (e: React.MouseEvent) => {
        isDragging.current = true;
        lastPos.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!isDragging.current) return;
        const dx = e.clientX - lastPos.current.x;
        const dy = e.clientY - lastPos.current.y;

        // Invert dy for canvas pan
        view.current.x += dx;
        view.current.y += dy;
        lastPos.current = { x: e.clientX, y: e.clientY };
    };

    const resetView = () => {
        view.current = { x: 0, y: 0, zoom: 40.0 };
    };


    if (!result) return <div className="p-8 text-center text-slate-400">No analysis results available.</div>;

    return (
        <div className="relative w-full h-full bg-slate-50 overflow-hidden select-none">

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

            {/* --- UI OVERLAYS --- */}

            {/* Top Left: Back & Status */}
            <div className="absolute top-4 left-4 flex gap-4 animate-in fade-in slide-in-from-top-4 duration-500">
                <button
                    onClick={() => setMode('EDITOR')}
                    className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg shadow-sm border border-slate-200 text-slate-600 hover:text-slate-900 font-medium transition-colors hover:bg-slate-50"
                >
                    <ChevronLeft size={16} />
                    <span>Editor</span>
                </button>

                <div className={`flex items-center gap-3 px-4 py-2 rounded-lg shadow-sm border ${result.is_kinematic ? 'bg-amber-50 border-amber-200 text-amber-800' : 'bg-green-50 border-green-200 text-green-800'}`}>
                    {result.is_kinematic ? <AlertTriangle size={18} /> : <CheckCircle size={18} />}
                    <div className="flex flex-col leading-none">
                        <span className="text-[10px] uppercase font-bold opacity-70">Status</span>
                        <span className="font-bold text-sm">
                            {result.is_kinematic ? `Kinematic (DoF: ${result.dof})` : 'Stable Structure'}
                        </span>
                    </div>
                </div>
            </div>

            {/* Top Right: View Controls */}
            <div className="absolute top-4 right-4 flex flex-col gap-2 bg-white p-1 rounded-lg shadow-sm border border-slate-200">
                <button onClick={() => view.current.zoom *= 1.2} className="p-2 hover:bg-slate-100 rounded text-slate-600"><ZoomIn size={18} /></button>
                <button onClick={() => view.current.zoom *= 0.8} className="p-2 hover:bg-slate-100 rounded text-slate-600"><ZoomOut size={18} /></button>
                <button onClick={resetView} className="p-2 hover:bg-slate-100 rounded text-slate-600" title="Reset View"><Maximize size={18} /></button>
            </div>

            {/* Bottom Center: Animation Controls (Only if Kinematic) */}
            {result.is_kinematic && (
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
                    {result.modes.length > 0 && (
                        <div className="pt-3 border-t border-slate-100">
                            <div className="flex items-center gap-2 mb-2 text-slate-500">
                                <Layers size={14} />
                                <span className="text-[10px] font-bold uppercase tracking-wider">Mechanisms / Modes</span>
                            </div>
                            <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                                {result.modes.map((_, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => setActiveModeIndex(idx)}
                                        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all whitespace-nowrap border
                      ${activeModeIndex === idx
                                                ? 'bg-blue-50 border-blue-200 text-blue-700 shadow-sm'
                                                : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}
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
