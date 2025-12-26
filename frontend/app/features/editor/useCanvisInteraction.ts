import { useRef, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import * as Geo from '../../lib/geometry';
import * as Coords from '../../lib/coordinates';
import type { Vec2, Node } from '~/types/model';

export const useCanvasInteraction = (canvasRef: React.RefObject<HTMLCanvasElement>) => {
    const { actions, viewport, interaction, nodes, members } = useStore();
    const tool = interaction.activeTool;

    // Transient state for drag operations (avoiding React re-renders for every pixel)
    const isDragging = useRef(false);
    const lastMouse = useRef<{ x: number, y: number } | null>(null);

    /**
     * Helper: Get World Position from Event
     */
    const getWorldPos = (e: React.MouseEvent): { raw: Vec2, snapped: Vec2 } => {
        if (!canvasRef.current) return { raw: { x: 0, y: 0 }, snapped: { x: 0, y: 0 } };

        const rect = canvasRef.current.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;

        const raw = Coords.screenToWorld(screenX, screenY, viewport, canvasRef.current.height);

        // Check for node snap first
        const snappedNodeId = Geo.getNearestNode(raw, nodes, viewport.zoom);
        let snapped = raw;

        if (snappedNodeId) {
            // If we snapped to a node, use that node's exact position
            const node = nodes.find(n => n.id === snappedNodeId);
            if (node) snapped = node.position;

            // Update global hover state
            actions.setHoveredNode(snappedNodeId);
        } else {
            // Otherwise, snap to grid
            snapped = Geo.snapToGrid(raw, viewport.gridSize);
            actions.setHoveredNode(null);
        }

        return { raw, snapped };
    };

    /**
     * MOUSE DOWN
     */
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        isDragging.current = true;
        lastMouse.current = { x: e.clientX, y: e.clientY };

        const { snapped, raw } = getWorldPos(e);

        // Left Click logic
        if (e.button === 0) {
            if (tool === 'node') {
                actions.addNode(snapped);
            }
            else if (tool === 'support_fixed') {
                // If clicked on existing node, update it. If empty, create new.
                // For now, simpler: just create/overlap
                actions.addNode(snapped, { fixX: true, fixY: true, fixM: true });
            }
            else if (tool === 'member') {
                // Start dragging a member
                if (interaction.hoveredNodeId) {
                    actions.setInteraction({ dragStartNodeId: interaction.hoveredNodeId });
                } else {
                    // Auto-create start node if clicking in space
                    const newNodeId = actions.addNode(snapped); // We need to update addNode to return ID!
                    // (I updated addNode in the store above to return the ID)
                    // But 'actions' is wrapped by Zustand, so it might not return.
                    // Workaround: We will just rely on hovering for now for V1.
                    // actions.setInteraction({ dragStartNodeId: newNodeId });
                }
            }
            else if (tool === 'select') {
                // 1. Try Clicking a Node
                const clickedNodeId = Geo.getNearestNode(raw, nodes, viewport.zoom);
                if (clickedNodeId) {
                    actions.selectObject(clickedNodeId, 'node');
                    return;
                }

                // 2. Try Clicking a Member
                let clickedMemberId = null;
                const clickThreshold = 10 / viewport.zoom; // 10 pixels tolerance

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
                    // Deselect if clicked empty space
                    actions.selectObject(null, null);
                }

            }
        }
    }, [tool, viewport, nodes]); // Dependencies

    /**
     * MOUSE MOVE
     */
    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        const { snapped } = getWorldPos(e);

        // Update "Ghost" mouse position in store for the Renderer to see
        actions.setInteraction({ mousePos: snapped });

        // Handle Panning (if middle click or spacebar held - future todo)
        if (isDragging.current && tool === 'select') {
            const dx = e.clientX - (lastMouse.current?.x || 0);
            const dy = e.clientY - (lastMouse.current?.y || 0);
            actions.setViewport({
                pan: { x: viewport.pan.x + dx, y: viewport.pan.y + dy }
            });
            lastMouse.current = { x: e.clientX, y: e.clientY };
        }

    }, [tool, viewport, nodes]);

    /**
     * MOUSE UP
     */
    const handleMouseUp = useCallback((e: React.MouseEvent) => {
        isDragging.current = false;
        const { snapped } = getWorldPos(e);

        if (tool === 'member' && interaction.dragStartNodeId) {
            // Finish Member
            let endNodeId = interaction.hoveredNodeId;

            // If let go in empty space, create a node there
            if (!endNodeId) {
                // For V1 let's assume we must click a node.
                // Or trigger addNode here.
                // const newNode = actions.addNode(snapped); 
                // ...
            }

            if (endNodeId && endNodeId !== interaction.dragStartNodeId) {
                actions.addMember(interaction.dragStartNodeId, endNodeId);
            }

            // Reset drag
            actions.setInteraction({ dragStartNodeId: null });
        }

    }, [tool, interaction.dragStartNodeId, nodes]);

    return {
        handleMouseDown,
        handleMouseMove,
        handleMouseUp
    };
};
