import { useRef, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import * as Geo from '../../lib/geometry';
import * as Coords from '../../lib/coordinates';
import type { Release } from '~/types/model';

// 1. Update keys to match the 'subType' from your ToolBar
const SUPPORT_CONFIGS: Record<string, { fixX: boolean | number, fixY: boolean | number, fixM: boolean | number }> = {
    'festlager': { fixX: true, fixY: true, fixM: false },
    'loslager': { fixX: false, fixY: true, fixM: false },
    'feste_einspannung': { fixX: true, fixY: true, fixM: true },
    'gleitlager': { fixX: true, fixY: false, fixM: true },
    'feder': { fixX: false, fixY: 10000, fixM: false },
    'torsionsfeder': { fixX: true, fixY: true, fixM: 10000 },
};

const HINGE_CONFIGS: Record<string, Partial<Release>> = {
    'vollgelenk': { fx: false, fy: false, mz: true },
    'schubgelenk': { fx: false, fy: true, mz: false },
    'normalkraftgelenk': { fx: true, fy: false, mz: false },
    'biegesteife_ecke': { fx: false, fy: false, mz: false }, // Resets everything to rigid
    'halbgelenk': { fx: false, fy: false, mz: true },
};


export const useCanvasInteraction = (canvasRef: React.RefObject<HTMLCanvasElement>) => {
    const { actions, viewport, interaction, nodes, members } = useStore();
    const tool = interaction.activeTool;
    const subType = interaction.activeSubTypeTool; // <--- Grab the subTool

    // --- REFS ---
    const isDragging = useRef(false);
    const lastMouse = useRef<{ x: number, y: number } | null>(null);
    const dragStartNodeIdRef = useRef<string | null>(null);

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

            // 1. NODE TOOLS (Includes Supports)
            if (tool === 'node') {
                // Case A: It is a Support Tool
                if (subType && SUPPORT_CONFIGS[subType]) {
                    const config = SUPPORT_CONFIGS[subType];

                    if (snappedNodeId) {
                        // Update existing node
                        actions.updateNode(snappedNodeId, { supports: config });
                    } else {
                        // Create new node with support
                        actions.addNode(snapped, config);
                    }
                }
                // Case B: It is a plain Node Tool
                else {
                    if (!snappedNodeId) {
                        actions.addNode(snapped);
                    }
                }
            }

            // 2. HINGE TOOLS
            else if (tool === 'hinge') {
                // We check if we have a valid node AND a valid subType configuration
                if (snappedNodeId && subType && HINGE_CONFIGS[subType]) {

                    // LOOKUP the config object
                    const physicsPayload = HINGE_CONFIGS[subType];

                    // PASS the object to the store (Store doesn't know about 'vollgelenk')
                    actions.addHingeAtNode(snappedNodeId, physicsPayload);
                }
            }

            // 3. MEMBER CREATION
            else if (tool === 'member') {
                let startId = snappedNodeId;
                if (startId) {
                    dragStartNodeIdRef.current = startId;
                    actions.setInteraction({ dragStartNodeId: startId });
                }
            }

            // 4. SELECTION
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
    }, [tool, subType, viewport, nodes, members]);

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        const { snapped } = getWorldPos(e);

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

        if (tool === 'member' && dragStartNodeIdRef.current) {
            const startId = dragStartNodeIdRef.current;
            const endNodeId = snappedNodeId;

            if (endNodeId && endNodeId !== startId) {
                actions.addMember(startId, endNodeId);
            }

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
