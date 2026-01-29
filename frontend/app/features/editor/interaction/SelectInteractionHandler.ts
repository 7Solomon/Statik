import * as Coords from '../../../lib/coordinates';
import * as Geo from '../../../lib/geometry';
import { BaseInteractionHandler, type MouseEventData } from './BaseInteractionHandler';

export class SelectInteractionHandler extends BaseInteractionHandler {
    private getMemberAtPosition(rawPos: { x: number, y: number }) {
        const { state, viewport } = this.context;
        const clickThreshold = 10 / viewport.zoom;

        for (const m of state.members) {
            const start = state.nodes.find(n => n.id === m.startNodeId);
            const end = state.nodes.find(n => n.id === m.endNodeId);

            if (start && end) {
                const proj = Geo.projectPointToSegment(rawPos, start.position, end.position);
                if (proj.dist < clickThreshold) {
                    return { member: m, ratio: proj.t };
                }
            }
        }
        return null;
    }

    private getLoadAtPosition = (rawPos: { x: number, y: number }) => {
        const { state, viewport } = this.context;
        const mouseScreen = Coords.worldToScreen(rawPos.x, rawPos.y, viewport);

        for (const load of state.loads) {
            // 1. POINT LOADS (Node or Member)
            if (load.type === 'POINT' || load.type === 'MOMENT') {
                let anchorWorld: { x: number, y: number } | null = null;

                if (load.scope === 'NODE') {
                    const n = state.nodes.find(node => node.id === load.nodeId);
                    if (n) anchorWorld = n.position;
                } else if (load.scope === 'MEMBER' && load.type === 'POINT') {
                    const m = state.members.find(mem => mem.id === load.memberId);
                    if (m) {
                        const s = state.nodes.find(n => n.id === m.startNodeId);
                        const e = state.nodes.find(n => n.id === m.endNodeId);
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
                        const dist = Math.hypot(mouseScreen.x - anchorScreen.x, mouseScreen.y - anchorScreen.y);
                        if (dist < 25) return load;
                    } else {
                        const angleRad = (load.angle ?? 90) * Math.PI / 180;
                        const tip = anchorScreen;
                        const tail = {
                            x: tip.x - Math.cos(angleRad) * 40,
                            y: tip.y - Math.sin(angleRad) * 40
                        };
                        const proj = Geo.projectPointToSegment(mouseScreen, tail, tip);
                        if (proj.dist < 10) return load;
                    }
                }
            }

            // 2. DISTRIBUTED LOADS
            else if (load.scope === 'MEMBER' && load.type === 'DISTRIBUTED') {
                const m = state.members.find(mem => mem.id === load.memberId);
                if (!m) continue;

                const s = state.nodes.find(n => n.id === m.startNodeId);
                const e = state.nodes.find(n => n.id === m.endNodeId);

                if (s && e) {
                    const proj = Geo.projectPointToSegment(rawPos, s.position, e.position);
                    const start = Math.min(load.startRatio, load.endRatio);
                    const end = Math.max(load.startRatio, load.endRatio);

                    if (proj.t >= start && proj.t <= end) {
                        const p1 = Coords.worldToScreen(s.position.x, s.position.y, viewport);
                        const p2 = Coords.worldToScreen(e.position.x, e.position.y, viewport);
                        const mouseS = Coords.worldToScreen(rawPos.x, rawPos.y, viewport);

                        const dx = p2.x - p1.x;
                        const dy = p2.y - p1.y;
                        const len = Math.hypot(dx, dy);

                        if (len === 0) continue;

                        const crossProduct = dx * (mouseS.y - p1.y) - dy * (mouseS.x - p1.x);
                        const signedDist = crossProduct / len;
                        const absDist = Math.abs(signedDist);

                        const MEMBER_THICKNESS_BUFFER = 12;
                        const LOAD_HEIGHT_LIMIT = 50;

                        if (absDist > MEMBER_THICKNESS_BUFFER && absDist < LOAD_HEIGHT_LIMIT) {
                            return load;
                        }
                    }
                }
            }
        }
        return null;
    };


    handleMouseDown(e: React.MouseEvent, data: MouseEventData): void {
        const { actions } = this.context;
        const { raw, snappedNodeId } = data;

        // Priority: Node > Load > Member
        if (snappedNodeId) {
            actions.selectObject(snappedNodeId, 'node');
            return;
        }

        const clickedLoad = this.getLoadAtPosition(raw);
        if (clickedLoad) {
            actions.selectObject(clickedLoad.id, 'load');
            return;
        }

        const hit = this.getMemberAtPosition(raw);
        if (hit) {
            actions.selectObject(hit.member.id, 'member');
        } else {
            actions.selectObject(null, null);
        }
    }

    handleMouseMove(e: React.MouseEvent, data: MouseEventData): void {
        const { actions, viewport, state } = this.context;

        // Pan when dragging in select mode
        if (state.interaction.creationState.mode === 'idle' && e.buttons === 1) {
            const dx = e.movementX;
            const dy = e.movementY;

            actions.setViewport({
                pan: {
                    x: viewport.pan.x + dx,
                    y: viewport.pan.y + dy
                }
            });
        }
    }

    handleMouseUp(e: React.MouseEvent, data: MouseEventData): void {
        // No specific behavior
    }
}
