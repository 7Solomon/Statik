import { NodeRenderer } from './NodeRenderer';
import { RenderUtils } from './RenderUtils';
import type { ViewportState } from '~/types/app';
import type { Node, StructuralSystem } from '~/types/model';

/**
 * Draws a complete structural system (nodes + members + supports)
 * onto the canvas context.
 * 
 * @param ctx - The Canvas 2D context
 * @param system - The structural system data (members, etc.)
 * @param view - Current viewport state (zoom, pan)
 * @param nodePositions - The specific node positions to draw (allows for deformed states)
 */
export function drawStructuralSystem(
    ctx: CanvasRenderingContext2D,
    system: StructuralSystem,
    view: ViewportState,
    nodePositions: Node[]
) {
    // 1. Analyze Node States (for correct connection corners/hinges)
    // We must pass the original members but the specific (potentially deformed) node positions
    const nodeStates = NodeRenderer.analyzeNodeStates(nodePositions, system.members);

    // 2. Draw Rigid Connections (The nice corners)
    NodeRenderer.drawRigidConnections(ctx, nodePositions, system.members, view, nodeStates);

    // 3. Draw Members
    system.members.forEach(member => {
        const startNode = nodePositions.find(n => n.id === member.startNodeId);
        const endNode = nodePositions.find(n => n.id === member.endNodeId);

        if (startNode && endNode) {
            // Use the standard drawMember utility
            RenderUtils.drawMember(
                ctx,
                startNode,
                endNode,
                member,
                view,
                nodeStates.get(startNode.id),
                nodeStates.get(endNode.id)
            );
        }
    });

    // 4. Draw Nodes & Supports
    nodePositions.forEach(node => {
        // Check if connected (to decide if we hide the dot for rigid corners)
        const isConnected = system.members.some(m => m.startNodeId === node.id || m.endNodeId === node.id);
        const state = nodeStates.get(node.id);

        NodeRenderer.drawNodeSymbol(
            ctx,
            node,
            view,
            false, // isHovered is false in analysis view
            state,
            isConnected
        );
    });
}
