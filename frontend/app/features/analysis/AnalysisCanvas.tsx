// src/components/AnalysisCanvas.tsx

import { useEffect, useRef, type ReactNode } from 'react';
import { ZoomIn, ZoomOut, Maximize } from 'lucide-react';
import type { ViewportState } from '~/types/app';
import { useAnalysisInteractions } from './useAnalysisInteractions';

interface AnalysisCanvasProps {
    children?: ReactNode;
    onRender: (ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, view: ViewportState) => void;
}

export default function AnalysisCanvas({ children, onRender }: AnalysisCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const { view, resetView, resizeCanvas, handlers } = useAnalysisInteractions();

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        let animationId: number;

        const render = () => {
            const { width, height } = resizeCanvas(canvas, ctx);
            const dpr = window.devicePixelRatio || 1;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

            onRender(ctx, canvas, view.current);
            animationId = requestAnimationFrame(render);
        };

        render();
        return () => cancelAnimationFrame(animationId);
    }, [onRender, resizeCanvas, view]);

    return (
        <div className="relative w-full h-full bg-slate-50 overflow-hidden select-none">
            {/* The Actual Canvas */}
            <canvas
                ref={canvasRef}
                className="block w-full h-full cursor-move touch-none"
                {...handlers}
            />

            {/* View Controls */}
            <div className="absolute top-4 right-4 flex flex-col gap-2 bg-white p-1 rounded-lg shadow-sm border border-slate-200">
                <button onClick={() => { view.current.zoom *= 1.2; }} className="p-2 hover:bg-slate-100 rounded text-slate-600">
                    <ZoomIn size={18} />
                </button>
                <button onClick={() => { view.current.zoom *= 0.8; }} className="p-2 hover:bg-slate-100 rounded text-slate-600">
                    <ZoomOut size={18} />
                </button>
                <button onClick={resetView} className="p-2 hover:bg-slate-100 rounded text-slate-600" title="Reset View">
                    <Maximize size={18} />
                </button>
            </div>

            {/* Overlays */}
            {children}
        </div>
    );
}
