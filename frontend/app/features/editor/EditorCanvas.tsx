import React, { useEffect, useRef } from 'react';
import { useStore } from '../../store/useStore'; // Adjust path if needed
import { Renderer } from './Renderer';
import { useCanvasInteraction } from './useCanvisInteraction';

const EditorCanvas: React.FC = () => {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // Connect Interaction Logic (Controller)
    const { handleMouseDown, handleMouseMove, handleMouseUp } = useCanvasInteraction(canvasRef as React.RefObject<HTMLCanvasElement>);

    // Connect Data (Store)
    const nodes = useStore((state) => state.nodes);
    const members = useStore((state) => state.members);
    const interaction = useStore((state) => state.interaction);
    const viewport = useStore((state) => state.viewport);
    const actions = useStore((state) => state.actions);

    // --- Resize Handler ---

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const onWheel = (e: WheelEvent) => {
            e.preventDefault(); // Now allowed because passive: false
            const zoomIntensity = 0.1;
            const direction = e.deltaY > 0 ? -1 : 1;
            const factor = 1 + (direction * zoomIntensity);

            // Access store directly or via a ref to avoid stale closures in event listener
            const currentZoom = useStore.getState().viewport.zoom;

            useStore.getState().actions.setViewport({
                zoom: Math.max(10, Math.min(200, currentZoom * factor))
            });
        };

        canvas.addEventListener('wheel', onWheel, { passive: false });

        return () => {
            canvas.removeEventListener('wheel', onWheel);
        };
    }, []);

    // --- Main Render Loop (Reactive) ---
    // Whenever the store changes, we repaint the canvas.
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Use RequestAnimationFrame for smooth updates if dragging
        // But for now, direct call is fine for this scale.
        requestAnimationFrame(() => {
            Renderer.render(ctx, canvas, nodes, members, viewport, interaction);
        });

    }, [nodes, members, viewport, interaction]); // Dependency array ensures we only paint when needed

    // --- Wheel Zoom Handler ---
    // (Optional: You can move this to useCanvasInteraction if you prefer)
    const handleWheel = (e: React.WheelEvent) => {
        e.preventDefault();
        const zoomIntensity = 0.1;
        const direction = e.deltaY > 0 ? -1 : 1;
        const factor = 1 + (direction * zoomIntensity);

        // Simple center zoom for now
        actions.setViewport({
            zoom: Math.max(10, Math.min(200, viewport.zoom * factor))
        });
    };

    return (
        <div ref={containerRef} className="w-full h-full bg-slate-50 overflow-hidden relative">
            <canvas
                ref={canvasRef}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onWheel={handleWheel}
                className="block touch-none cursor-crosshair"
                // Prevent default browser context menu on right click
                onContextMenu={(e) => e.preventDefault()}
            />

            {/* Overlay Debug Info (Optional) */}
            <div className="absolute bottom-4 left-4 bg-white/90 p-2 rounded shadow text-xs font-mono text-slate-600 pointer-events-none select-none">
                <div>Pos: {interaction.mousePos.x.toFixed(2)}, {interaction.mousePos.y.toFixed(2)} m</div>
                <div>Zoom: {viewport.zoom.toFixed(1)} px/m</div>
                <div>Nodes: {nodes.length} | Members: {members.length}</div>
            </div>
        </div>
    );
};

export default EditorCanvas;
