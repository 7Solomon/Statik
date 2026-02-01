import { BaseInteractionHandler, type MouseEventData } from './BaseInteractionHandler';
import { v4 as uuidv4 } from 'uuid';
import * as Geo from '../../../lib/geometry';

// Configuration for default values when placing a load
const LOAD_CONFIGS: Record<string, { type: string, value: number, angle?: number }> = {
    // STATIC
    'point': { type: 'POINT', value: 10, angle: -90 },
    'moment': { type: 'MOMENT', value: 10 },
    'distributed': { type: 'DISTRIBUTED', value: 5 },

    // DYNAMIC 
    'dynamic_force': { type: 'DYNAMIC_FORCE', value: 10, angle: 0 },
    'dynamic_moment': { type: 'DYNAMIC_MOMENT', value: 10 }
};

export class LoadInteractionHandler extends BaseInteractionHandler {

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

    handleMouseDown(e: React.MouseEvent, data: MouseEventData): void {
        const { actions, state } = this.context;
        const { snapped, raw, snappedNodeId } = data;
        const subType = state.interaction.activeSubTypeTool;
        if (!subType || !LOAD_CONFIGS[subType]) return;
        const base = LOAD_CONFIGS[subType];


        // -------------------------------------------------------------
        // 1. DYNAMIC LOADS 
        // -------------------------------------------------------------
        if (base.type === 'DYNAMIC_FORCE' || base.type === 'DYNAMIC_MOMENT') {
            if (snappedNodeId) {
                const newId = uuidv4();

                // Construct the Dynamic Load Object
                actions.addLoad({
                    id: newId,
                    scope: 'NODE',
                    type: base.type as any,
                    nodeId: snappedNodeId,
                    ...(base.type === 'DYNAMIC_FORCE' ? { angle: base.angle ?? 0 } : {}),
                    signal: {
                        type: 'HARMONIC',
                        amplitude: base.value,
                        frequency: 1.0,
                        phase: 0,
                        startTime: 0
                    }
                } as any);
            }
            return;
        }

        // -------------------------------------------------------------
        // 2. STATIC LOADS
        // -------------------------------------------------------------
        if (base.type === 'POINT' || base.type === 'MOMENT') {
            const newId = uuidv4();

            if (snappedNodeId) {
                actions.addLoad({
                    id: newId,
                    scope: 'NODE',
                    type: base.type as any,
                    nodeId: snappedNodeId,
                    value: base.value,
                    angle: base.angle
                });
            } else if (base.type === 'POINT') {
                const hit = this.getMemberAtPosition(raw);
                if (hit) {
                    actions.addLoad({
                        id: newId,
                        scope: 'MEMBER',
                        type: 'POINT',
                        memberId: hit.member.id,
                        ratio: hit.ratio,
                        value: base.value,
                        angle: base.angle
                    });
                }
            }
        } else if (base.type === 'DISTRIBUTED') {
            const hit = this.getMemberAtPosition(raw);
            if (hit) {
                const newId = uuidv4();
                actions.addLoad({
                    id: newId,
                    scope: 'MEMBER',
                    type: 'DISTRIBUTED',
                    memberId: hit.member.id,
                    startRatio: hit.ratio,
                    endRatio: hit.ratio,
                    value: base.value
                });
                actions.setInteraction({
                    creationState: {
                        mode: 'sizing_load',
                        startPos: snapped,
                        activeId: newId
                    }
                });
            }
        }

    }

    handleMouseMove(e: React.MouseEvent, data: MouseEventData): void {
        const { actions, state } = this.context;
        const { snapped } = data;
        const creationState = state.interaction.creationState;

        if (creationState.mode === 'sizing_load' && creationState.activeId) {
            const currentLoad = state.loads.find(l => l.id === creationState.activeId);

            if (currentLoad && currentLoad.scope === 'MEMBER' && currentLoad.type === 'DISTRIBUTED') {
                const member = state.members.find(m => m.id === currentLoad.memberId);

                if (member) {
                    const start = state.nodes.find(n => n.id === member.startNodeId);
                    const end = state.nodes.find(n => n.id === member.endNodeId);

                    if (start && end) {
                        const proj = Geo.projectPointToSegment(snapped, start.position, end.position);
                        actions.updateLoad(currentLoad.id, { endRatio: proj.t });
                    }
                }
            }
        }
    }

    handleMouseUp(e: React.MouseEvent, data: MouseEventData): void {
        // Load creation finalizes automatically
    }
}
