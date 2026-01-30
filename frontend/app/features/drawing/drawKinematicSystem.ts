import { ConstraintRenderer } from './ConstraintRenderer';
import { NodeRenderer } from './NodeRenderer';
import { RenderUtils } from './RenderUtils';
import { ScheibenRenderer } from './ScheibenRenderer';  // ← ADD THIS IMPORT
import type { ViewportState } from '~/types/app';
import type { Node, StructuralSystem } from '~/types/model';

/**
 * Draws a complete structural system (nodes + members + supports + scheiben)
 * onto the canvas context.
 * 
 * @param ctx - The Canvas 2D context
 * @param system - The structural system data (members, scheiben, etc.)
 * @param view - Current viewport state (zoom, pan)
 * @param nodePositions - The specific node positions to draw (allows for deformed states)
 * @param highlightRigidBodies - Optional: highlight rigid body Scheiben (for kinematic modes)
 * @param rigidBodyIds - Optional: IDs of Scheiben acting as rigid bodies in current mode
 */
export function drawStructuralSystem(
    ctx: CanvasRenderingContext2D,
    system: StructuralSystem,
    view: ViewportState,
    nodePositions: Node[],
    highlightRigidBodies: boolean = false,
    rigidBodyIds: Set<string> = new Set()
) {
    // 0. Draw Scheiben FIRST (as background layer)
    system.scheiben?.forEach(scheibe => {
        const isRigidBody = highlightRigidBodies && rigidBodyIds.has(scheibe.id);
        ScheibenRenderer.draw(
            ctx,
            scheibe,
            view,
            false,        // isActive = false (not being created)
            isRigidBody   // isSelected = true if it's a rigid body in mechanism
        );
    });

    // 1. Analyze Node States (for correct connection corners/hinges)
    const nodeStates = NodeRenderer.analyzeNodeStates(nodePositions, system.members);

    // 2. Draw Rigid Connections (The nice corners)
    NodeRenderer.drawRigidConnections(ctx, nodePositions, system.members, view, nodeStates);

    // 3. Draw Members
    system.members.forEach(member => {
        const startNode = nodePositions.find(n => n.id === member.startNodeId);
        const endNode = nodePositions.find(n => n.id === member.endNodeId);

        if (startNode && endNode) {
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


    // Draw Constraints
    system.constraints?.forEach(constraint => {
        //const isHovered = interaction.hoveredConstraintId === constraint.id;
        //const isSelected = interaction.selectedType === 'constraint'
        //    && interaction.selectedId === constraint.id;

        ConstraintRenderer.draw(ctx, constraint, nodePositions, view, false, false);  // HERE ADD INTERACTOIN DONT KNOw HOW 
    });

    // 4. Draw Nodes & Supports
    nodePositions.forEach(node => {
        // Check if connected to members OR scheiben
        const isConnectedToMember = system.members.some(
            m => m.startNodeId === node.id || m.endNodeId === node.id
        );

        const isConnectedToScheibe = system.scheiben?.some(
            s => s.connections.some(conn => conn.nodeId === node.id)
        ) ?? false;

        const isConnected = isConnectedToMember || isConnectedToScheibe;
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

    // 5. Optional: Draw Scheibe connection indicators (for debugging/clarity)
    if (highlightRigidBodies) {
        drawScheibeConnections(ctx, system, view, nodePositions);
    }
}

/**
 * Helper: Draw lines connecting Scheiben to their nodes (for visualization)
 */
function drawScheibeConnections(
    ctx: CanvasRenderingContext2D,
    system: StructuralSystem,
    view: ViewportState,
    nodePositions: Node[]
) {
    if (!system.scheiben) return;

    ctx.save();
    ctx.strokeStyle = 'rgba(59, 130, 246, 0.3)';  // Light blue
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    system.scheiben.forEach(scheibe => {
        if (scheibe.type !== 'RIGID') return;

        // Get scheibe center
        const centerX = (scheibe.corner1.x + scheibe.corner2.x) / 2;
        const centerY = (scheibe.corner1.y + scheibe.corner2.y) / 2;
        const centerScreen = RenderUtils.project({ x: centerX, y: centerY }, view);

        // Draw lines to all connected nodes
        scheibe.connections.forEach(conn => {
            const node = nodePositions.find(n => n.id === conn.nodeId);
            if (!node) return;

            const nodeScreen = RenderUtils.project(node.position, view);

            ctx.beginPath();
            ctx.moveTo(centerScreen.x, centerScreen.y);
            ctx.lineTo(nodeScreen.x, nodeScreen.y);
            ctx.stroke();

            // Draw a small circle at connection point
            ctx.fillStyle = conn.releases
                ? 'rgba(239, 68, 68, 0.6)'   // Red if hinged
                : 'rgba(59, 130, 246, 0.6)';  // Blue if rigid

            ctx.beginPath();
            ctx.arc(nodeScreen.x, nodeScreen.y, 4, 0, Math.PI * 2);
            ctx.fill();
        });
    });

    ctx.restore();
}
