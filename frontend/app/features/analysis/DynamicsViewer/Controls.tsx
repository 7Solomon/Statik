import { Play, Pause, SkipBack, SkipForward } from "lucide-react";
import { useRef, useEffect } from "react";
import type { DynamicAnalysisResult } from "~/types/model";

interface Props {
    result: DynamicAnalysisResult;
    timeIndex: number;
    setTimeIndex: (i: number) => void;
    isPlaying: boolean;
    setIsPlaying: (v: boolean) => void;
    totalSteps: number;
}

export default function DynamicControls({
    result, timeIndex, setTimeIndex, isPlaying, setIsPlaying, totalSteps
}: Props) {

    const canvasRef = useRef<HTMLCanvasElement>(null);

    // Draw Graph
    useEffect(() => {
        const cvs = canvasRef.current;
        if (!cvs || !result.timeHistory.length) return;
        const ctx = cvs.getContext('2d');
        if (!ctx) return;

        // 1. Find Max Amplitude for Auto-Scaling
        let targetNodeId = Object.keys(result.timeHistory[0].displacements)[0];
        let maxAmp = 0;

        // Scan ALL steps (or at least first 100) to find the true peak
        // Scanning only 20 might miss the resonance peak later in the sim
        const scanLimit = Math.min(result.timeHistory.length, 200);
        for (let i = 0; i < scanLimit; i++) {
            const disps = result.timeHistory[i].displacements;
            for (const [id, vals] of Object.entries(disps)) {
                const amp = Math.abs(vals[1]); // Check Y-displacement
                if (amp > maxAmp) {
                    maxAmp = amp;
                    targetNodeId = id;
                }
            }
        }

        // Prevent division by zero if system is static
        if (maxAmp < 1e-9) maxAmp = 1.0;

        // 2. Setup Canvas
        const w = cvs.width;
        const h = cvs.height;
        ctx.clearRect(0, 0, w, h);

        // Draw Center Line (Zero Axis)
        ctx.strokeStyle = '#e2e8f0'; // slate-200
        ctx.beginPath();
        ctx.moveTo(0, h / 2);
        ctx.lineTo(w, h / 2);
        ctx.stroke();

        // 3. Draw The Curve
        ctx.strokeStyle = '#6366f1'; // indigo-500
        ctx.lineWidth = 2;
        ctx.beginPath();

        const stepX = w / (totalSteps - 1); // Exact fit width

        // Scale to 80% of height (leaving 10% padding top/bottom)
        const availHeight = h * 0.8;
        const scaleY = (availHeight / 2);

        result.timeHistory.forEach((step, i) => {
            const yVal = step.displacements[targetNodeId]?.[1] || 0;

            // Normalize (-1 to 1)
            const yNorm = yVal / maxAmp;

            const x = i * stepX;
            // Invert Y because Canvas Y=0 is Top
            const y = (h / 2) - (yNorm * scaleY);

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // 4. Draw Cursor
        const cursorX = timeIndex * stepX;
        ctx.strokeStyle = '#ef4444'; // red-500
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(cursorX, 0);
        ctx.lineTo(cursorX, h);
        ctx.stroke();

    }, [result, timeIndex, totalSteps]);

    // Handle Click
    const handleGraphClick = (e: React.MouseEvent) => {
        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect) return;
        const x = e.clientX - rect.left;
        const pct = Math.max(0, Math.min(1, x / rect.width));
        const newIndex = Math.floor(pct * (totalSteps - 1));
        setTimeIndex(newIndex);
        setIsPlaying(false);
    };

    return (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[600px] z-20">
            <div className="bg-white/90 backdrop-blur-sm p-4 rounded-2xl shadow-xl border border-slate-200 flex flex-col gap-4 animate-in slide-in-from-bottom-4">

                {/* Info Header */}
                <div className="flex justify-between items-center text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <span>Current: {result.timeHistory[timeIndex]?.time.toFixed(2)}s</span>
                    <span>Total: {result.timeHistory[totalSteps - 1]?.time.toFixed(1)}s</span>
                </div>

                {/* Graph Scrubber */}
                <div
                    className="relative h-20 bg-slate-50 rounded-lg border border-slate-100 overflow-hidden cursor-crosshair shadow-inner"
                    onClick={handleGraphClick}
                >
                    <canvas
                        ref={canvasRef}
                        width={600}
                        height={80} // Increased height for better visibility
                        className="w-full h-full"
                    />
                </div>

                {/* Controls */}
                <div className="flex items-center justify-center gap-6">
                    <button onClick={() => setTimeIndex(0)} className="p-2 text-slate-400 hover:text-indigo-600 transition-colors">
                        <SkipBack size={20} />
                    </button>

                    <button
                        onClick={() => setIsPlaying(!isPlaying)}
                        className="w-14 h-14 flex items-center justify-center rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg shadow-indigo-200 transition-all active:scale-95"
                    >
                        {isPlaying ? <Pause size={24} fill="currentColor" /> : <Play size={24} fill="currentColor" className="ml-1" />}
                    </button>

                    <button onClick={() => setTimeIndex(totalSteps - 1)} className="p-2 text-slate-400 hover:text-indigo-600 transition-colors">
                        <SkipForward size={20} />
                    </button>
                </div>
            </div>
        </div>
    );
}
