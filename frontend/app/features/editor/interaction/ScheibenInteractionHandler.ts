import { BaseInteractionHandler, type MouseEventData } from './BaseInteractionHandler';
import { v4 as uuidv4 } from 'uuid';
import type { Scheibe, ScheibeConnection } from '~/types/model';
import type { ScheibeShape } from '~/types/app';
import * as Geo from '../../../lib/geometry';

export class ScheibeInteractionHandler extends BaseInteractionHandler {
    handleMouseDown(e: React.MouseEvent, data: MouseEventData): void {
        const { actions, state } = this.context;
        const { snapped } = data;
        const subType = state.interaction.activeSubTypeTool as ScheibeShape;

        if (!subType) return;

        const newId = uuidv4();
        const newScheibe: Scheibe = {
            id: newId,
            shape: subType,
            corner1: snapped,
            corner2: snapped,
            rotation: 0,
            type: 'RIGID',
            properties: {
                E: 30e9,
                nu: 0.2,
                thickness: 0.2,
                rho: 2400
            },
            connections: [],
            meshLevel: 3
        };

        actions.addScheibe(newScheibe);

        actions.setInteraction({
            creationState: {
                mode: 'sizing_scheibe',
                startPos: snapped,
                activeId: newId
            }
        });
    }

    handleMouseMove(e: React.MouseEvent, data: MouseEventData): void {
        const { actions, state } = this.context;
        const { snapped } = data;
        const creationState = state.interaction.creationState;

        if (creationState.mode === 'sizing_scheibe' && creationState.activeId) {
            const currentScheibe = state.scheiben.find(s => s.id === creationState.activeId);

            if (currentScheibe) {
                actions.updateScheibe(currentScheibe.id, {
                    corner2: snapped
                });
            }
        }
    }

    handleMouseUp(e: React.MouseEvent, data: MouseEventData): void {
        const { actions, state } = this.context;
        const creationState = state.interaction.creationState;

        if (creationState.mode === 'sizing_scheibe' && creationState.activeId) {
            const scheibe = state.scheiben.find(s => s.id === creationState.activeId);

            if (scheibe) {
                const width = Math.abs(scheibe.corner2.x - scheibe.corner1.x);
                const height = Math.abs(scheibe.corner2.y - scheibe.corner1.y);

                if (width < 0.1 && height < 0.1) {
                    // Too small - delete
                    actions.removeScheibe(scheibe.id);
                } else {
                    // Auto-connect to all nodes inside this Scheibe
                    this.connectScheibeToContainedNodes(scheibe.id);
                }
            }
        }
    }

    /**
     * Connect a Scheibe to all nodes within its bounds
     */
    private connectScheibeToContainedNodes(scheibeId: string): void {
        const { actions, state } = this.context;
        const scheibe = state.scheiben.find(s => s.id === scheibeId);

        if (!scheibe) return;

        // Find all nodes inside this Scheibe
        const nodesInside = Geo.getNodesInsideScheibe(scheibe, state.nodes);

        // Create connections for all contained nodes
        const connections: ScheibeConnection[] = nodesInside.map(node => ({
            nodeId: node.id,
            releases: undefined  // Rigid by default
        }));

        actions.updateScheibe(scheibeId, { connections });

        //console.log(`Scheibe ${scheibeId} auto-connected to ${connections.length} nodes`);
    }
}
