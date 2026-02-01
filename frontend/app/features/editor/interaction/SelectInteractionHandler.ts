import type { Scheibe } from '~/types/model';
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

    private getConstraintAtPosition(rawPos: { x: number, y: number }) {
        const { state, viewport } = this.context;
        // Constraints might be thinner visually, so maybe a tighter threshold?
        const clickThreshold = 10 / viewport.zoom;

        // Assuming state.constraints exists now
        for (const c of state.constraints) {
            const start = state.nodes.find(n => n.id === c.startNodeId);
            const end = state.nodes.find(n => n.id === c.endNodeId);

            if (start && end) {
                const proj = Geo.projectPointToSegment(rawPos, start.position, end.position);
                if (proj.dist < clickThreshold) {
                    return c;
                }
            }
        }
        return null;
    }

    private getScheibeAtPosition(rawPos: { x: number, y: number }) {
        const { state } = this.context;
        for (const s of state.scheiben) {
            if (this.isPointInScheibe(rawPos, s)) {
                return s;
            }
        }
        return null;
    }

    // Helper: Math for Rotated Rectangle Hit Test
    private isPointInScheibe(point: { x: number, y: number }, scheibe: Scheibe): boolean {
        // 1. Calculate Center and Dimensions (Local Axis Aligned)
        const c1 = scheibe.corner1;
        const c2 = scheibe.corner2;

        const centerX = (c1.x + c2.x) / 2;
        const centerY = (c1.y + c2.y) / 2;

        const width = Math.abs(c2.x - c1.x);
        const height = Math.abs(c2.y - c1.y);

        // 2. Translate point so Scheibe center is at (0,0)
        const dx = point.x - centerX;
        const dy = point.y - centerY;

        // 3. Rotate point INVERSE to the Scheibe's rotation to align it with axes
        // Assuming scheibe.rotation is in degrees
        const rad = -scheibe.rotation * (Math.PI / 180);
        const localX = dx * Math.cos(rad) - dy * Math.sin(rad);
        const localY = dx * Math.sin(rad) + dy * Math.cos(rad);

        // 4. AABB Check (Axis-Aligned Bounding Box)
        const halfW = width / 2;
        const halfH = height / 2;

        return (
            localX >= -halfW && localX <= halfW &&
            localY >= -halfH && localY <= halfH
        );
    }

    private getLoadAtPosition = (rawPos: { x: number, y: number }) => {
        const { state, viewport } = this.context;
        const mouseScreen = Coords.worldToScreen(rawPos.x, rawPos.y, viewport);

        for (const load of state.loads) {

            const isPointLike = ['POINT', 'MOMENT', 'DYNAMIC_POINT', 'DYNAMIC_FORCE', 'DYNAMIC_MOMENT'].includes(load.type);

            if (isPointLike) {
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

                    // MOMENT HIT TEST (Circle)
                    if (load.type.includes('MOMENT')) {
                        const dist = Math.hypot(mouseScreen.x - anchorScreen.x, mouseScreen.y - anchorScreen.y);
                        if (dist < 25) return load; // Radius matches renderer
                    }
                    // FORCE HIT TEST (Arrow)
                    else {
                        const angleVal = (load as any).angle ?? (load.type.includes('DYNAMIC') ? 0 : -90);
                        const angleRad = angleVal * Math.PI / 180;

                        const tip = anchorScreen;

                        const tail = {
                            x: tip.x - Math.cos(angleRad) * 40,
                            y: tip.y + Math.sin(angleRad) * 40  // PLUS sine because Screen Y is inverted
                        };

                        const proj = Geo.projectPointToSegment(mouseScreen, tail, tip);

                        // Increase buffer slightly to make selection easier
                        if (proj.dist < 12) return load;
                    }
                }
            }

            // DISTRIBUTED LOADS (Unchanged)
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

                        if (absDist > 12 && absDist < 50) {
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

        // 1. Nodes (Highest Priority)
        if (snappedNodeId) {
            actions.selectObject(snappedNodeId, 'node');
            return;
        }

        // 2. Loads
        const clickedLoad = this.getLoadAtPosition(raw);
        if (clickedLoad) {
            actions.selectObject(clickedLoad.id, 'load');
            return;
        }

        // 3. Members OR Constraints (Lines)
        const hitMember = this.getMemberAtPosition(raw);
        if (hitMember) {
            actions.selectObject(hitMember.member.id, 'member');
            return;
        }

        const hitConstraint = this.getConstraintAtPosition(raw);
        if (hitConstraint) {
            actions.selectObject(hitConstraint.id, 'constraint');
            return;
        }

        // 4. Scheiben
        const hitScheibe = this.getScheibeAtPosition(raw);
        if (hitScheibe) {
            actions.selectObject(hitScheibe.id, 'scheibe');
            return;
        }

        // 5. Deselect
        actions.selectObject(null, null);
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
