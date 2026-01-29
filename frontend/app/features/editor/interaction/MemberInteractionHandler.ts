import { BaseInteractionHandler, type MouseEventData } from './BaseInteractionHandler';
import * as Geo from '../../../lib/geometry';
import type { ScheibeConnection } from '~/types/model';

export class MemberInteractionHandler extends BaseInteractionHandler {
    handleMouseDown(e: React.MouseEvent, data: MouseEventData): void {
        const { actions } = this.context;
        const { snapped, snappedNodeId } = data;

        if (snappedNodeId) {
            actions.setInteraction({
                creationState: {
                    mode: 'drawing_member',
                    startPos: snapped,
                    activeId: snappedNodeId
                }
            });
        }
    }

    handleMouseMove(e: React.MouseEvent, data: MouseEventData): void {
        // Ghost line is rendered automatically via creationState
    }

    handleMouseUp(e: React.MouseEvent, data: MouseEventData): void {
        const { actions, state } = this.context;
        const { snappedNodeId } = data;
        const creationState = state.interaction.creationState;

        if (creationState.mode === 'drawing_member' && creationState.activeId) {
            if (snappedNodeId && snappedNodeId !== creationState.activeId) {
                actions.addMember(creationState.activeId, snappedNodeId);

                // NEW: Auto-connect both nodes to any containing Scheiben
                const startNode = state.nodes.find(n => n.id === creationState.activeId);
                const endNode = state.nodes.find(n => n.id === snappedNodeId);

                if (startNode) {
                    this.connectNodeToContainingScheiben(startNode.id, startNode.position);
                }
                if (endNode) {
                    this.connectNodeToContainingScheiben(endNode.id, endNode.position);
                }
            }
        }
    }

    /**
     * Connect a node to all Scheiben that contain its position
     */
    private connectNodeToContainingScheiben(nodeId: string, position: { x: number, y: number }): void {
        const { actions, state } = this.context;

        const containingScheiben = Geo.getScheibenContainingPoint(position, state.scheiben);

        for (const scheibe of containingScheiben) {
            const isAlreadyConnected = scheibe.connections.some(conn => conn.nodeId === nodeId);

            if (!isAlreadyConnected) {
                const newConnection: ScheibeConnection = {
                    nodeId: nodeId,
                    releases: undefined
                };

                const updatedConnections = [...scheibe.connections, newConnection];

                actions.updateScheibe(scheibe.id, {
                    connections: updatedConnections
                });

                //console.log(`Node ${nodeId} auto-connected to Scheibe ${scheibe.id}`);
            }
        }
    }
}
