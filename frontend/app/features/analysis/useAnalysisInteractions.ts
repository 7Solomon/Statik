import { useRef, useCallback, useEffect } from 'react';
import { useStore } from '~/store/useStore';
import type { ViewportState } from '~/types/app';

const DEFAULT_VIEWPORT: ViewportState = {
    zoom: 50,
    pan: { x: 0, y: 0 },
    gridSize: 1.0,
    width: 0,
    height: 0,
};

export function useAnalysisInteractions() {
    const setViewport = useStore((state) => state.analysis.actions.setViewport);

    const initialSession = useStore.getState().analysis.analysisSession;
    const initialViewport = initialSession?.viewport || DEFAULT_VIEWPORT;

    const view = useRef<ViewportState>({ ...initialViewport });
    const isDragging = useRef(false);
    const lastPos = useRef({ x: 0, y: 0 });

    // Handle mouse move and up at document level
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isDragging.current) return;

            const dx = e.clientX - lastPos.current.x;
            const dy = e.clientY - lastPos.current.y;

            view.current.pan.x += dx;
            view.current.pan.y += dy;

            lastPos.current = { x: e.clientX, y: e.clientY };
        };

        const handleMouseUp = () => {
            if (isDragging.current) {
                isDragging.current = false;
                setViewport({ pan: { x: view.current.pan.x, y: view.current.pan.y } });
            }
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [setViewport]);

    const handleWheel = useCallback((e: React.WheelEvent) => {
        const scale = e.deltaY > 0 ? 0.9 : 1.1;
        view.current.zoom = Math.max(5, Math.min(200, view.current.zoom * scale));
        setViewport({ zoom: view.current.zoom });
    }, [setViewport]);

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        isDragging.current = true;
        lastPos.current = { x: e.clientX, y: e.clientY };
    }, []);

    const resetView = useCallback(() => {
        view.current.zoom = 50;
        view.current.pan = { x: 0, y: 0 };

        setViewport({ zoom: 50, pan: { x: 0, y: 0 } });
    }, [setViewport]);

    const resizeCanvas = useCallback((canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D) => {
        const width = canvas.parentElement?.clientWidth || 800;
        const height = canvas.parentElement?.clientHeight || 600;
        const dpr = window.devicePixelRatio || 1;

        if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
            canvas.width = width * dpr;
            canvas.height = height * dpr;
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;

            view.current.width = width;
            view.current.height = height;
        }

        return { width, height };
    }, []);

    useEffect(() => {
        const currentSession = useStore.getState().analysis.analysisSession;
        if (currentSession?.viewport) {
            view.current = { ...currentSession.viewport };
        }

        return () => {
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
            // Remove onMouseMove, onMouseUp, onMouseLeave from here
        }
    };
}
