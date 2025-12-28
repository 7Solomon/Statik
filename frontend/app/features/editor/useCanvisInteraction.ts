import { useRef, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import * as Geo from '../../lib/geometry';
import * as Coords from '../../lib/coordinates';
import { v4 as uuidv4 } from 'uuid';
import type { Release, LoadType } from '~/types/model';

// --- CONFIGS ---
const SUPPORT_CONFIGS: Record<string, any> = {
    'festlager': { fixX: true, fixY: true, fixM: false },
    'loslager': { fixX: false, fixY: true, fixM: false },
    'feste_einspannung': { fixX: true, fixY: true, fixM: true },
    'gleitlager': { fixX: true, fixY: false, fixM: true },
};

const HINGE_CONFIGS: Record<string, Partial<Release>> = {
    'vollgelenk': { fx: false, fy: false, mz: true },
    'schubgelenk': { fx: false, fy: true, mz: false },
    'normalkraftgelenk': { fx: true, fy: false, mz: false },
    'biegesteife_ecke': { fx: false, fy: false, mz: false },
};

// Use simple config objects. We will build the full Load object in logic below.
const LOAD_CONFIGS: Record<string, { type: LoadType, value: number, angle?: number }> = {
    'point': { type: 'POINT', value: 10, angle: 90 },
    'moment': { type: 'MOMENT', value: 10 },
    'distributed': { type: 'DISTRIBUTED', value: 5 },
};

export const useCanvasInteraction = (canvasRef: React.RefObject<HTMLCanvasElement>) => {
    const { actions, viewport, interaction, nodes, members, loads } = useStore((state) => state.editor);
    const tool = interaction.activeTool;
    const subType = interaction.activeSubTypeTool;

    // --- REFS ---
    const isDragging = useRef(false);
    const lastMouse = useRef<{ x: number, y: number } | null>(null);
    const dragStartNodeIdRef = useRef<string | null>(null);
    const activeLoadIdRef = useRef<string | null>(null); // For dragging distributed loads

    // --- HELPERS ---

    // Find Member and specific position (ratio) on it
    const getMemberAtPosition = (rawPos: { x: number, y: number }) => {
        const clickThreshold = 10 / viewport.zoom;
        for (const m of members) {
            const start = nodes.find(n => n.id === m.startNodeId);
            const end = nodes.find(n => n.id === m.endNodeId);
            if (start && end) {
                const proj = Geo.projectPointToSegment(rawPos, start.position, end.position);
                if (proj.dist < clickThreshold) {
                    return { member: m, ratio: proj.t, startPos: start.position, endPos: end.position };
                }
            }
        }
        return null;
    };

    // Find existing Load to select it
    const getLoadAtPosition = (rawPos: { x: number, y: number }) => {
        const threshold = 15 / viewport.zoom;

        // Visual Constants (Must match your Renderer!)
        const ARROW_LEN = 40 / viewport.zoom; // Scaled by zoom to match screen pixels if needed, 


        // We need Screen Coordinates of the mouse for "Screen Space" collision
        const mouseScreen = Coords.worldToScreen(rawPos.x, rawPos.y, viewport);

        for (const load of loads) {

            // ----------------------------------------------------
            // 1. POINT LOADS (Node or Member)
            // ----------------------------------------------------
            if (load.type === 'POINT' || load.type === 'MOMENT') {
                let anchorWorld: { x: number, y: number } | null = null;

                // Find Anchor Point in World Space
                if (load.scope === 'NODE') {
                    const n = nodes.find(node => node.id === load.nodeId);
                    if (n) anchorWorld = n.position;
                } else if (load.scope === 'MEMBER' && load.type === 'POINT') {
                    const m = members.find(mem => mem.id === load.memberId);
                    if (m) {
                        const s = nodes.find(n => n.id === m.startNodeId);
                        const e = nodes.find(n => n.id === m.endNodeId);
                        if (s && e) {
                            anchorWorld = {
                                x: s.position.x + (e.position.x - s.position.x) * load.ratio,
                                y: s.position.y + (e.position.y - s.position.y) * load.ratio
                            };
                        }
                    }
                }

                if (anchorWorld) {
                    const anchorScreen = Coords.worldToScreen(anchorWorld.x, anchorWorld.y, viewport);

                    if (load.type === 'MOMENT') {
                        // Circle check around the node
                        const dist = Math.hypot(mouseScreen.x - anchorScreen.x, mouseScreen.y - anchorScreen.y);
                        if (dist < 25) return load; // 25px radius
                    } else {
                        // Arrow Check: The arrow is drawn at an angle. 
                        // It starts at (anchor) and goes backwards/outwards.
                        // Or usually, tip is at anchor, tail is away.
                        const angleRad = (load.angle ?? 90) * Math.PI / 180;

                        // Tip (at node)
                        const tip = anchorScreen;
                        // Tail (40px away, opposite to force direction)
                        // Force points in `angle`, so tail is at `angle + 180` (or minus)
                        const tail = {
                            x: tip.x - Math.cos(angleRad) * 40,
                            y: tip.y - Math.sin(angleRad) * 40
                        };

                        // Check distance to the Line Segment (Tail -> Tip)
                        const proj = Geo.projectPointToSegment(mouseScreen, tail, tip);
                        if (proj.dist < 10) return load; // 10px tolerance around the arrow shaft
                    }
                }
            }

            // ----------------------------------------------------
            // 2. DISTRIBUTED LOADS
            // ----------------------------------------------------
            else if (load.scope === 'MEMBER' && load.type === 'DISTRIBUTED') {
                const m = members.find(mem => mem.id === load.memberId);
                if (!m) continue;
                const s = nodes.find(n => n.id === m.startNodeId);
                const e = nodes.find(n => n.id === m.endNodeId);

                if (s && e) {
                    // Check if mouse is "near" the beam segment covered by the load
                    // This is the simplest robust way. Checking the "polygon" of the arrows is complex.
                    // Usually, clicking the beam under the load is enough.

                    const proj = Geo.projectPointToSegment(rawPos, s.position, e.position);
                    const start = Math.min(load.startRatio, load.endRatio);
                    const end = Math.max(load.startRatio, load.endRatio);

                    // 1. Must be within the start/end ratio
                    if (proj.t >= start && proj.t <= end) {
                        // 2. Must be close to the beam line (World Units)
                        // OR close to the "Load Height" (Screen Units)

                        // Simple Check: Distance to beam < Threshold
                        if (proj.dist < threshold) return load;

                        // Advanced Check: Check if mouse is "above" the beam in the load area
                        // This requires knowing the load direction and height. 
                        // If you want to click the "arrows" floating above the beam:

                        // Convert everything to Screen
                        const p1 = Coords.worldToScreen(s.position.x, s.position.y, viewport);
                        const p2 = Coords.worldToScreen(e.position.x, e.position.y, viewport);
                        const mouseS = Coords.worldToScreen(rawPos.x, rawPos.y, viewport);

                        // Project mouse onto screen line
                        const projS = Geo.projectPointToSegment(mouseS, p1, p2);

                        // If we are "above" the beam (distance > 0), check if we are within max load height (e.g. 40px)
                        // We check the "perpendicular distance"
                        if (projS.dist < 45) return load; // 45px covers the beam + the arrows
                    }
                }
            }
        }
        return null;
    };


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

    // ==========================================
    // MOUSE DOWN
    // ==========================================
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        isDragging.current = true;
        lastMouse.current = { x: e.clientX, y: e.clientY };

        const { snapped, raw, snappedNodeId } = getWorldPos(e);

        if (e.button === 0) {
            // --- NODE & SUPPORT ---
            if (tool === 'node') {
                if (subType && SUPPORT_CONFIGS[subType]) {
                    if (snappedNodeId) actions.updateNode(snappedNodeId, { supports: SUPPORT_CONFIGS[subType] });
                    else actions.addNode(snapped, SUPPORT_CONFIGS[subType]);
                } else {
                    if (!snappedNodeId) actions.addNode(snapped);
                }
            }
            // --- HINGE ---
            else if (tool === 'hinge' && snappedNodeId && subType && HINGE_CONFIGS[subType]) {
                actions.addHingeAtNode(snappedNodeId, HINGE_CONFIGS[subType]);
            }
            // --- MEMBER ---
            else if (tool === 'member' && snappedNodeId) {
                dragStartNodeIdRef.current = snappedNodeId;
                actions.setInteraction({ dragStartNodeId: snappedNodeId });
            }

            // --- LOAD---
            else if (tool === 'load') {
                if (!subType || !LOAD_CONFIGS[subType]) return;
                const base = LOAD_CONFIGS[subType];

                // 1. Point/Moment
                if (base.type === 'POINT' || base.type === 'MOMENT') {
                    const newId = uuidv4(); // Generate ID here

                    // A. Node Load
                    if (snappedNodeId) {
                        actions.addLoad({
                            id: newId,          // <--- Pass ID
                            scope: 'NODE',
                            type: base.type,
                            nodeId: snappedNodeId,
                            value: base.value,
                            angle: base.angle
                        });
                    }
                    // B. Member Point Load
                    else if (base.type === 'POINT') {
                        const hit = getMemberAtPosition(raw);
                        if (hit) {
                            actions.addLoad({
                                id: newId,      // <--- Pass ID
                                scope: 'MEMBER',
                                type: 'POINT',
                                memberId: hit.member.id,
                                ratio: hit.ratio,
                                value: base.value,
                                angle: base.angle
                            });
                        }
                    }
                }

                // 2. Distributed Load
                else if (base.type === 'DISTRIBUTED') {
                    const hit = getMemberAtPosition(raw);
                    if (hit) {
                        const newId = uuidv4();
                        activeLoadIdRef.current = newId; // Track ID for dragging

                        actions.addLoad({
                            id: newId,          // <--- Pass ID
                            scope: 'MEMBER',
                            type: 'DISTRIBUTED',
                            memberId: hit.member.id,
                            startRatio: hit.ratio,
                            endRatio: hit.ratio,
                            value: base.value
                        });
                    }
                }
            }

            // --- SELECT ---
            else if (tool === 'select') {
                // 1. Check Node (Highest Priority)
                if (snappedNodeId) {
                    actions.selectObject(snappedNodeId, 'node');
                    return;
                }

                // 2. Check Load (Medium Priority - blocks Member)
                const clickedLoad = getLoadAtPosition(raw);
                if (clickedLoad) {
                    actions.selectObject(clickedLoad.id, 'load');
                    return;
                }

                // 3. Check Member (Lowest Priority)
                const hit = getMemberAtPosition(raw);
                if (hit) {
                    actions.selectObject(hit.member.id, 'member');
                } else {
                    actions.selectObject(null, null); // Deselect
                }
            }

        }
    }, [tool, subType, viewport, nodes, members, loads]);

    // ==========================================
    // MOUSE MOVE
    // ==========================================
    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        const { snapped, raw } = getWorldPos(e);
        actions.setInteraction({ mousePos: snapped });

        // Pan
        if (isDragging.current && tool === 'select') {
            const dx = e.clientX - (lastMouse.current?.x || 0);
            const dy = e.clientY - (lastMouse.current?.y || 0);
            actions.setViewport({ pan: { x: viewport.pan.x + dx, y: viewport.pan.y + dy } });
            lastMouse.current = { x: e.clientX, y: e.clientY };
        }

        // Drag Distributed Load
        if (isDragging.current && tool === 'load' && activeLoadIdRef.current) {
            const currentLoad = loads.find(l => l.id === activeLoadIdRef.current);
            if (currentLoad && currentLoad.scope === 'MEMBER' && currentLoad.type === 'DISTRIBUTED') {
                const member = members.find(m => m.id === currentLoad.memberId);
                if (member) {
                    const start = nodes.find(n => n.id === member.startNodeId);
                    const end = nodes.find(n => n.id === member.endNodeId);
                    if (start && end) {
                        const proj = Geo.projectPointToSegment(snapped, start.position, end.position);
                        actions.updateLoad(currentLoad.id, { endRatio: proj.t });
                    }
                }
            }
        }
    }, [tool, viewport, nodes, members, loads]);

    // ==========================================
    // MOUSE UP
    // ==========================================
    const handleMouseUp = useCallback((e: React.MouseEvent) => {
        isDragging.current = false;
        const { snappedNodeId } = getWorldPos(e);

        if (tool === 'member' && dragStartNodeIdRef.current) {
            if (snappedNodeId && snappedNodeId !== dragStartNodeIdRef.current) {
                actions.addMember(dragStartNodeIdRef.current, snappedNodeId);
            }
            dragStartNodeIdRef.current = null;
            actions.setInteraction({ dragStartNodeId: null });
        }

        // Stop drawing load
        if (tool === 'load') {
            activeLoadIdRef.current = null;
        }
    }, [tool, nodes, viewport]);

    return { handleMouseDown, handleMouseMove, handleMouseUp };
};
