import { useEffect, useRef, useState } from 'react';
import { useStore } from '~/store/useStore';
import { ChevronLeft, Play, Pause, AlertTriangle, CheckCircle, Layers, ZoomIn, ZoomOut, Maximize } from 'lucide-react';
import type { KinematicResult, Member, Node, KinematicMode } from '~/types/model';
import { NodeRenderer } from '../drawing/NodeRenderer';
import { RenderUtils } from '../drawing/RenderUtils';
import type { ViewportState } from '~/types/app';



export default function AnalysisViewer() {
    // Global State
    // We cast the result to our defined type for safety
    const result = useStore(s => s.analysis.kinematicResult) as KinematicResult | null;
    const setMode = useStore(s => s.shared.actions.setMode);

    // Local State
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [activeModeIndex, setActiveModeIndex] = useState(0);
    const [amplitude, setAmplitude] = useState(0.5); // Animation scale factor
    const [isPlaying, setIsPlaying] = useState(true);

    // Viewport State
    const isDragging = useRef(false);
    const lastPos = useRef({ x: 0, y: 0 });
    const view = useRef<ViewportState>({
        zoom: 50, // 50 pixels = 1 meter
        pan: { x: 400, y: 400 }, // Initial center offset
        gridSize: 1.0,
        width: 0,
        height: 0,
        x: 0,
        y: 0
    });

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

            view.current.width = width;
            view.current.height = height;

            // Handle DPI scaling
            const dpr = window.devicePixelRatio || 1;
            canvas.width = width * dpr;
            canvas.height = height * dpr;

            // KEEP THIS: This scales for retina displays
            ctx.scale(dpr, dpr);
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;

            // Clear screen
            ctx.clearRect(0, 0, width, height);
            ctx.save();

            // 3. Draw Grid 
            RenderUtils.drawGrid(ctx, canvas, view.current);


            // --- GHOST  ---
            ctx.save();
            ctx.globalAlpha = 0.15;
            drawSystem(ctx, result, activeModeIndex, 0);
            ctx.restore();
            // -------------------------


            // 4. Calculate Animation Factor
            const time = (Date.now() - startTime) / 1000;
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
        const { system, modes } = data;
        const mode = modes[modeIdx];

        // 1. Create "Deformed" Nodes List
        // We map the original nodes to new positions based on the animation factor
        const deformedNodes = system.nodes.map(node => {
            const d = getDisplacement(node.id, mode, factor);
            return {
                ...node,
                position: { x: node.position.x + d.x, y: node.position.y + d.y }
            };
        });

        // 2. Analyze Node States (for correct connection corners/hinges)
        // We must pass the original members but the DEFORMED nodes
        const nodeStates = NodeRenderer.analyzeNodeStates(deformedNodes, system.members);

        // 3. Draw Rigid Connections (The nice corners)
        NodeRenderer.drawRigidConnections(ctx, deformedNodes, system.members, view.current, nodeStates);

        // 4. Draw Members
        system.members.forEach(member => {
            const startNode = deformedNodes.find(n => n.id === member.startNodeId);
            const endNode = deformedNodes.find(n => n.id === member.endNodeId);

            if (startNode && endNode) {
                // Use the fancy drawMember from RenderUtils
                // It handles releases, offsets, and global hinges automatically
                RenderUtils.drawMember(
                    ctx,
                    startNode,
                    endNode,
                    member,
                    view.current,
                    nodeStates.get(startNode.id),
                    nodeStates.get(endNode.id)
                );
            }
        });

        // 5. Draw Nodes & Supports
        deformedNodes.forEach(node => {
            // Check if connected (to decide if we hide the dot for rigid corners)
            const isConnected = system.members.some(m => m.startNodeId === node.id || m.endNodeId === node.id);
            const state = nodeStates.get(node.id);

            // Use the fancy drawNodeSymbol
            // We pass 'false' for isHovered since we aren't interacting here
            NodeRenderer.drawNodeSymbol(
                ctx,
                node,
                view.current,
                false, // isHovered
                state,
                isConnected
            );
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
        view.current = {
            zoom: 50, // 50 pixels = 1 meter
            pan: { x: 400, y: 400 }, // Initial center offset
            gridSize: 1.0,
            width: 0,
            height: 0,
            x: 0,
            y: 0
        }
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
