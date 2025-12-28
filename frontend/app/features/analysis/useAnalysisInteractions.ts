import { useRef, useCallback } from 'react';
import type { ViewportState } from '~/types/app';

export function useAnalysisInteractions() {

    // 1. State Refs (Mutable, does not trigger re-renders)
    // We use refs so the animation loop can read the latest values instantly without React overhead.
    const view = useRef<ViewportState>({
        zoom: 50,              // Pixels per meter
        pan: { x: 400, y: 300 }, // Default center offset
        gridSize: 1.0,
        width: 0,
        height: 0,
        x: 0,                  // Calculated Pan X
        y: 0                   // Calculated Pan Y
    });

    const isDragging = useRef(false);
    const lastPos = useRef({ x: 0, y: 0 });

    // 2. Handlers
    const handleWheel = useCallback((e: React.WheelEvent) => {
        // Zoom towards the mouse pointer could be added here, 
        // but simple center zoom is easier for start:
        const scale = e.deltaY > 0 ? 0.9 : 1.1;
        view.current.zoom = Math.max(5, Math.min(200, view.current.zoom * scale));
    }, []);

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        isDragging.current = true;
        lastPos.current = { x: e.clientX, y: e.clientY };
    }, []);

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (!isDragging.current) return;

        const dx = e.clientX - lastPos.current.x;
        const dy = e.clientY - lastPos.current.y;

        // Update the Viewport Ref directly
        view.current.x += dx;
        view.current.y += dy;

        lastPos.current = { x: e.clientX, y: e.clientY };
    }, []);

    const handleMouseUp = useCallback(() => {
        isDragging.current = false;
    }, []);

    // 3. Utilities
    const resetView = useCallback(() => {
        view.current.zoom = 50;
        view.current.x = 0;
        view.current.y = 0;
    }, []);

    const resizeCanvas = useCallback((canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D) => {
        // Get parent dimensions
        const width = canvas.parentElement?.clientWidth || 800;
        const height = canvas.parentElement?.clientHeight || 600;

        // Handle High DPI (Retina Displays)
        const dpr = window.devicePixelRatio || 1;

        // Set actual canvas size (pixels)
        canvas.width = width * dpr;
        canvas.height = height * dpr;

        // Scale context so drawing logic uses CSS pixels
        ctx.scale(dpr, dpr);

        // Set CSS size
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;

        // Update Viewport state
        view.current.width = width;
        view.current.height = height;

        return { width, height };
    }, []);

    return {
        view,         // Pass this to your draw functions
        resetView,    // Call this from a button
        resizeCanvas, // Call this at start of render loop
        handlers: {   // Spread this onto the <canvas> tag
            onWheel: handleWheel,
            onMouseDown: handleMouseDown,
            onMouseMove: handleMouseMove,
            onMouseUp: handleMouseUp,
            onMouseLeave: handleMouseUp,
        }
    };
}
