import React, { useEffect, useRef } from 'react';
import { useStore } from '../../store/useStore';
import { Renderer } from '../drawing/Renderer';
import { useCanvasInteraction } from './useCanvisInteraction';

const EditorCanvas: React.FC = () => {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // Connect Interaction Logic (Controller)
    const { handleMouseDown, handleMouseMove, handleMouseUp } = useCanvasInteraction(canvasRef as React.RefObject<HTMLCanvasElement>);

    // Connect Data (Store)
    const nodes = useStore((state) => state.editor.nodes);
    const members = useStore((state) => state.editor.members);
    const loads = useStore((state) => state.editor.loads)
    const interaction = useStore((state) => state.editor.interaction);
    const viewport = useStore((state) => state.editor.viewport);
    // const actions = useStore((state) => state.editor.actions); // Not strictly needed here if handled in logic

    // --- RESIZE HANDLER ---
    useEffect(() => {
        const canvas = canvasRef.current;
        const container = containerRef.current;
        if (!canvas || !container) return;

        const resizeObserver = new ResizeObserver(() => {
            const { clientWidth, clientHeight } = container;
            const dpr = window.devicePixelRatio || 1;

            // Update internal resolution (Sharpness)
            canvas.width = clientWidth * dpr;
            canvas.height = clientHeight * dpr;

            // Update CSS display size (Layout)
            canvas.style.width = `${clientWidth}px`;
            canvas.style.height = `${clientHeight}px`;

            // Scale drawing context
            const ctx = canvas.getContext('2d');
            if (ctx) {
                ctx.scale(dpr, dpr);
                // CRITICAL: Re-render immediately because changing width clears the canvas
                Renderer.renderEditor(
                    ctx,
                    canvas,
                    useStore.getState().editor.nodes,
                    useStore.getState().editor.members,
                    useStore.getState().editor.loads,
                    useStore.getState().editor.viewport,
                    useStore.getState().editor.interaction
                );
            }
        });

        resizeObserver.observe(container);

        return () => resizeObserver.disconnect();
    }, []);

    // --- 2. WHEEL / ZOOM HANDLER (Native for performance) ---
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const onWheel = (e: WheelEvent) => {
            e.preventDefault(); // Prevents browser page scrolling

            const zoomIntensity = 0.1;
            const direction = e.deltaY > 0 ? -1 : 1;
            const factor = 1 + (direction * zoomIntensity);

            const currentZoom = useStore.getState().editor.viewport.zoom;

            useStore.getState().editor.actions.setViewport({
                zoom: Math.max(10, Math.min(200, currentZoom * factor))
            });
        };

        // passive: false is required to use e.preventDefault()
        canvas.addEventListener('wheel', onWheel, { passive: false });

        return () => {
            canvas.removeEventListener('wheel', onWheel);
        };
    }, []);

    // --- 3. MAIN RENDER LOOP (Reactive) ---
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        requestAnimationFrame(() => {
            Renderer.renderEditor(ctx, canvas, nodes, members, loads, viewport, interaction);
        });

    }, [nodes, members, viewport, interaction]);

    return (
        // Added touch-none to container to prevent mobile scroll gestures on the background
        <div ref={containerRef} className="w-full h-full bg-slate-50 overflow-hidden relative touch-none">
            <canvas
                ref={canvasRef}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                // onWheel removed here (handled by useEffect above)
                className="block cursor-crosshair"
                onContextMenu={(e) => e.preventDefault()}
            />

            {/* Overlay Debug Info */}
            <div className="absolute bottom-4 left-4 bg-white/90 p-2 rounded shadow text-xs font-mono text-slate-600 pointer-events-none select-none z-10">
                <div>Pos: {interaction.mousePos.x.toFixed(2)}, {interaction.mousePos.y.toFixed(2)} m</div>
                <div>Zoom: {viewport.zoom.toFixed(1)} px/m</div>
                <div>Nodes: {nodes.length} | Members: {members.length} | Loads {loads.length}</div>
            </div>
        </div>
    );
};

export default EditorCanvas;
