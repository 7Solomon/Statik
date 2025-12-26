import { useRef, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import * as Geo from '../../lib/geometry';
import * as Coords from '../../lib/coordinates';

const SUPPORT_CONFIGS: Record<string, { fixX: boolean | number, fixY: boolean | number, fixM: boolean | number }> = {
    'support_festlager': { fixX: true, fixY: true, fixM: false },
    'support_loslager': { fixX: false, fixY: true, fixM: false },
    'support_feste_einspannung': { fixX: true, fixY: true, fixM: true },
    'support_gleitlager': { fixX: true, fixY: false, fixM: true },
    'support_feder': { fixX: false, fixY: 10000, fixM: false },
    'support_torsionsfeder': { fixX: true, fixY: true, fixM: 10000 },
};

export const useCanvasInteraction = (canvasRef: React.RefObject<HTMLCanvasElement>) => {
    const { actions, viewport, interaction, nodes, members } = useStore();
    const tool = interaction.activeTool;

    // --- REFS ---
    const isDragging = useRef(false);
    const lastMouse = useRef<{ x: number, y: number } | null>(null);
    const dragStartNodeIdRef = useRef<string | null>(null); // <--- THE FIX

    const getWorldPos = (e: React.MouseEvent) => {
        if (!canvasRef.current) return { raw: { x: 0, y: 0 }, snapped: { x: 0, y: 0 }, snappedNodeId: null };

        const rect = canvasRef.current.getBoundingClientRect();
        const raw = Coords.screenToWorld(e.clientX - rect.left, e.clientY - rect.top, viewport, canvasRef.current.height);

        const snappedNodeId = Geo.getNearestNode(raw, nodes, viewport.zoom);
        let snapped = raw;

        if (snappedNodeId) {
            const node = nodes.find(n => n.id === snappedNodeId);
            if (node) snapped = node.position;
            if (interaction.hoveredNodeId !== snappedNodeId) actions.setHoveredNode(snappedNodeId);
        } else {
            snapped = Geo.snapToGrid(raw, viewport.gridSize);
            if (interaction.hoveredNodeId !== null) actions.setHoveredNode(null);
        }

        return { raw, snapped, snappedNodeId };
    };

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        isDragging.current = true;
        lastMouse.current = { x: e.clientX, y: e.clientY };

        const { snapped, raw, snappedNodeId } = getWorldPos(e);

        if (e.button === 0) {
            // 1. Placing Nodes
            if (tool === 'node') {
                if (!snappedNodeId) {
                    actions.addNode(snapped);
                }
            }

            // 2. Placing Supports
            else if (tool.startsWith('support_')) {
                const config = SUPPORT_CONFIGS[tool];
                if (config) {
                    if (snappedNodeId) {
                        actions.updateNode(snappedNodeId, { supports: config });
                    }
                    else {
                        actions.addNode(snapped, config);
                    }
                }
            }

            // 3. Member Tool
            else if (tool === 'member') {
                let startId = snappedNodeId;
                if (startId) {
                    // FIX: Set BOTH the Ref (logic) and Store (visuals)
                    dragStartNodeIdRef.current = startId;
                    actions.setInteraction({ dragStartNodeId: startId });
                }
            }

            // 4. Select Tool
            else if (tool === 'select') {
                if (snappedNodeId) {
                    actions.selectObject(snappedNodeId, 'node');
                    return;
                }

                // Member Selection Logic
                let clickedMemberId = null;
                const clickThreshold = 10 / viewport.zoom;

                for (const m of members) {
                    const start = nodes.find(n => n.id === m.startNodeId);
                    const end = nodes.find(n => n.id === m.endNodeId);
                    if (start && end) {
                        const dist = Geo.pDistance(raw.x, raw.y, start.position.x, start.position.y, end.position.x, end.position.y);
                        if (dist < clickThreshold) {
                            clickedMemberId = m.id;
                            break;
                        }
                    }
                }

                if (clickedMemberId) {
                    actions.selectObject(clickedMemberId, 'member');
                } else {
                    actions.selectObject(null, null);
                }
            }
        }
    }, [tool, viewport, nodes, members, interaction.hoveredNodeId]);


    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        const { snapped } = getWorldPos(e);

        // This causes frequent re-renders, which is why we need Refs for logic
        actions.setInteraction({ mousePos: snapped });

        if (isDragging.current && tool === 'select') {
            const dx = e.clientX - (lastMouse.current?.x || 0);
            const dy = e.clientY - (lastMouse.current?.y || 0);
            actions.setViewport({
                pan: { x: viewport.pan.x + dx, y: viewport.pan.y + dy }
            });
            lastMouse.current = { x: e.clientX, y: e.clientY };
        }
    }, [tool, viewport, nodes]);


    const handleMouseUp = useCallback((e: React.MouseEvent) => {
        isDragging.current = false;

        const { snappedNodeId } = getWorldPos(e);

        // FIX: Check the Ref, not the Store
        if (tool === 'member' && dragStartNodeIdRef.current) {

            const startId = dragStartNodeIdRef.current;
            const endNodeId = snappedNodeId;

            if (endNodeId && endNodeId !== startId) {
                actions.addMember(startId, endNodeId);
            }

            // Reset both
            dragStartNodeIdRef.current = null;
            actions.setInteraction({ dragStartNodeId: null });
        }

    }, [tool, nodes, viewport]);

    return {
        handleMouseDown,
        handleMouseMove,
        handleMouseUp
    };
};
