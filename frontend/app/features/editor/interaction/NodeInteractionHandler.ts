import { BaseInteractionHandler, type MouseEventData } from "./BaseInteractionHandler";
import type { ScheibeConnection } from "~/types/model";
import * as Geo from '../../../lib/geometry';

const SUPPORT_CONFIGS: Record<string, any> = {
    'festlager': { fixX: true, fixY: true, fixM: false },
    'loslager': { fixX: false, fixY: true, fixM: false },
    'feste_einspannung': { fixX: true, fixY: true, fixM: true },
    'gleitlager': { fixX: true, fixY: false, fixM: true },
};

export class NodeInteractionHandler extends BaseInteractionHandler {
    handleMouseDown(e: React.MouseEvent, data: MouseEventData): void {
        const { actions, state } = this.context;
        const { snapped, snappedNodeId } = data;
        const subType = state.interaction.activeSubTypeTool;

        if (subType && SUPPORT_CONFIGS[subType]) {
            // Adding/updating support
            if (snappedNodeId) {
                actions.updateNode(snappedNodeId, { supports: SUPPORT_CONFIGS[subType] });
            } else {
                const newNodeId = actions.addNode(snapped, SUPPORT_CONFIGS[subType]);

                // Auto-connect to any Scheiben containing this node
                this.connectNodeToContainingScheiben(newNodeId, snapped);
            }
        } else {
            // Adding regular node
            if (!snappedNodeId) {
                const newNodeId = actions.addNode(snapped);

                // Auto-connect to any Scheiben containing this node
                this.connectNodeToContainingScheiben(newNodeId, snapped);
            }
        }
    }

    /**
     * Connect a node to all Scheiben that contain its position
     */
    private connectNodeToContainingScheiben(nodeId: string, position: { x: number, y: number }): void {
        const { actions, state } = this.context;

        // Find all Scheiben that contain this point
        const containingScheiben = Geo.getScheibenContainingPoint(position, state.scheiben);

        for (const scheibe of containingScheiben) {
            // Check if node is already connected
            const isAlreadyConnected = scheibe.connections.some(conn => conn.nodeId === nodeId);

            if (!isAlreadyConnected) {
                const newConnection: ScheibeConnection = {
                    nodeId: nodeId,
                    releases: undefined  // Rigid connection by default
                };

                const updatedConnections = [...scheibe.connections, newConnection];

                actions.updateScheibe(scheibe.id, {
                    connections: updatedConnections
                });

                //console.log(`Node ${nodeId} auto-connected to Scheibe ${scheibe.id}`);
            }
        }
    }

    handleMouseMove(e: React.MouseEvent, data: MouseEventData): void {
        // No move behavior
    }

    handleMouseUp(e: React.MouseEvent, data: MouseEventData): void {
        // No up behavior
    }
}
