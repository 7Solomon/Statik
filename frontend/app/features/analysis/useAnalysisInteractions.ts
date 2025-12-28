import { useRef, useCallback, useEffect } from 'react';
import { useStore } from '~/store/useStore'; // Adjust path to your store hook
import type { ViewportState } from '~/types/app';

export function useAnalysisInteractions() {
    // 1. Access Store Actions (without subscribing to state changes to avoid re-renders)
    const setViewport = useStore((state) => state.analysis.actions.setViewport);

    const initialViewport = useStore.getState().analysis.viewport;

    const view = useRef<ViewportState>({ ...initialViewport });
    const isDragging = useRef(false);
    const lastPos = useRef({ x: 0, y: 0 });

    // 3. Handlers
    const handleWheel = useCallback((e: React.WheelEvent) => {
        const scale = e.deltaY > 0 ? 0.9 : 1.1;
        view.current.zoom = Math.max(5, Math.min(200, view.current.zoom * scale));

        // Sync to store immediately for wheel (or debounce if you prefer)
        setViewport({ zoom: view.current.zoom });
    }, [setViewport]);

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        isDragging.current = true;
        lastPos.current = { x: e.clientX, y: e.clientY };
    }, []);

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (!isDragging.current) return;

        const dx = e.clientX - lastPos.current.x;
        const dy = e.clientY - lastPos.current.y;

        // Update Ref strictly for the Animation Loop (Fast)
        view.current.x += dx;
        view.current.y += dy;

        lastPos.current = { x: e.clientX, y: e.clientY };
    }, []);

    const handleMouseUp = useCallback(() => {
        if (isDragging.current) {
            isDragging.current = false;

            // Sync final position to Store (Persistence)
            setViewport({ x: view.current.x, y: view.current.y });
        }
    }, [setViewport]);

    // 4. Utilities
    const resetView = useCallback(() => {
        // Reset Ref
        view.current.zoom = 50;
        view.current.x = 0;
        view.current.y = 0;

        // Reset Store
        setViewport({ zoom: 50, x: 0, y: 0 });
    }, [setViewport]);

    const resizeCanvas = useCallback((canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D) => {
        const width = canvas.parentElement?.clientWidth || 800;
        const height = canvas.parentElement?.clientHeight || 600;
        const dpr = window.devicePixelRatio || 1;

        // Only resize if dimensions actually changed to avoid thrashing
        if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
            canvas.width = width * dpr;
            canvas.height = height * dpr;
            ctx.scale(dpr, dpr);
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;

            view.current.width = width;
            view.current.height = height;

            // Optional: Update store with new dimensions
            // setViewport({ width, height }); 
        }

        return { width, height };
    }, []);

    // 5. Sync on Mount/Unmount (Optional safety)
    useEffect(() => {
        // Ensure ref matches store when component mounts (in case store changed elsewhere)
        const currentStoreState = useStore.getState().analysis.viewport;
        view.current = { ...currentStoreState };

        return () => {
            // Save state on unmount
            setViewport(view.current);
        };
    }, [setViewport]);

    return {
        view,
        resetView,
        resizeCanvas,
        handlers: {
            onWheel: handleWheel,
            onMouseDown: handleMouseDown,
            onMouseMove: handleMouseMove,
            onMouseUp: handleMouseUp,
            onMouseLeave: handleMouseUp,
        }
    };
}
