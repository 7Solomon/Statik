import type { AnalysisInteractionState, EditorInteractionState, ViewportState } from '~/types/app';
import type { Load, Member, Node, Vec2 } from '~/types/model';
import { RenderUtils } from './RenderUtils';
import { NodeRenderer } from './NodeRenderer';
import { ForceRenderer } from './ForceRenderer';

export class Renderer {
    static renderEditor(
        ctx: CanvasRenderingContext2D,
        canvas: HTMLCanvasElement,
        nodes: Node[],
        members: Member[],
        loads: Load[],
        viewport: ViewportState,
        interaction: EditorInteractionState
    ) {
        // Clear Screen
        RenderUtils.clearScreen(ctx, canvas);

        //Draw Grid
        RenderUtils.drawGrid(ctx, canvas, viewport);

        const nodeStates = NodeRenderer.analyzeNodeStates(nodes, members);
        NodeRenderer.drawRigidConnections(ctx, nodes, members, viewport, nodeStates);

        //  Draw Members
        members.forEach(member => {
            const startNode = nodes.find(n => n.id === member.startNodeId);
            const endNode = nodes.find(n => n.id === member.endNodeId);

            if (startNode && endNode) {
                // We pass the node states so the member knows whether to draw an offset or not
                RenderUtils.drawMember(
                    ctx,
                    startNode,
                    endNode,
                    member,
                    viewport,
                    nodeStates.get(startNode.id),
                    nodeStates.get(endNode.id)
                );
            }
        });

        loads.forEach(load => {
            ForceRenderer.draw(ctx, load, viewport, nodes, members);
        });

        // 6. Ghost Member
        if (interaction.dragStartNodeId && interaction.activeTool === 'member') {
            const startNode = nodes.find(n => n.id === interaction.dragStartNodeId);
            if (startNode) {
                RenderUtils.drawGhostMember(ctx, startNode.position, interaction.mousePos, viewport);
            }
        }

        // Draw Nodes & Supports
        nodes.forEach(node => {
            const isHovered = interaction.hoveredNodeId === node.id;
            const state = nodeStates.get(node.id);
            const isConnected = members.some(m => m.startNodeId === node.id || m.endNodeId === node.id);

            NodeRenderer.drawNodeSymbol(ctx, node, viewport, isHovered, state, isConnected);
        });
    }
    static renderAnalysis(
        ctx: CanvasRenderingContext2D,
        canvas: HTMLCanvasElement,
        nodes: Node[],
        members: Member[],
        loads: Load[],
        viewport: ViewportState,
        interaction: AnalysisInteractionState
    ) {
        // Clear Screen
        RenderUtils.clearScreen(ctx, canvas);

        //Draw Grid
        RenderUtils.drawGrid(ctx, canvas, viewport);

        const nodeStates = NodeRenderer.analyzeNodeStates(nodes, members);
        NodeRenderer.drawRigidConnections(ctx, nodes, members, viewport, nodeStates);

        //  Draw Members
        members.forEach(member => {
            const startNode = nodes.find(n => n.id === member.startNodeId);
            const endNode = nodes.find(n => n.id === member.endNodeId);

            if (startNode && endNode) {
                // We pass the node states so the member knows whether to draw an offset or not
                RenderUtils.drawMember(
                    ctx,
                    startNode,
                    endNode,
                    member,
                    viewport,
                    nodeStates.get(startNode.id),
                    nodeStates.get(endNode.id)
                );
            }
        });

        loads.forEach(load => {
            ForceRenderer.draw(ctx, load, viewport, nodes, members);
        });

        // Draw Nodes & Supports
        nodes.forEach(node => {
            const isHovered = interaction.hoveredNodeId === node.id;
            const state = nodeStates.get(node.id);
            const isConnected = members.some(m => m.startNodeId === node.id || m.endNodeId === node.id);

            NodeRenderer.drawNodeSymbol(ctx, node, viewport, isHovered, state, isConnected);
        });
    }
}
