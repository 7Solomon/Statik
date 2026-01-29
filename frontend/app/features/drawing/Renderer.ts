import type { AnalysisInteractionState, EditorInteractionState, ViewportState } from '~/types/app';
import type { Load, Member, Node, Scheibe } from '~/types/model';
import { RenderUtils } from './RenderUtils';
import { NodeRenderer } from './NodeRenderer';
import { ForceRenderer } from './ForceRenderer';
import { ScheibenRenderer } from './ScheibenRenderer';

export class Renderer {
    static renderEditor(
        ctx: CanvasRenderingContext2D,
        canvas: HTMLCanvasElement,
        nodes: Node[],
        members: Member[],
        loads: Load[],
        scheiben: Scheibe[],
        viewport: ViewportState,
        interaction: EditorInteractionState
    ) {
        // Clear Screen
        RenderUtils.clearScreen(ctx, canvas);

        // Draw Grid
        RenderUtils.drawGrid(ctx, canvas, viewport);

        // Draw Scheiben
        scheiben.forEach(scheibe => {
            const isActive = interaction.creationState.mode === 'sizing_scheibe'
                && interaction.creationState.activeId === scheibe.id;
            const isSelected = interaction.selectedType === 'scheibe'
                && interaction.selectedId === scheibe.id;

            ScheibenRenderer.draw(ctx, scheibe, viewport, isActive, isSelected);
        });

        const nodeStates = NodeRenderer.analyzeNodeStates(nodes, members);
        NodeRenderer.drawRigidConnections(ctx, nodes, members, viewport, nodeStates);

        // Draw Members
        members.forEach(member => {
            const startNode = nodes.find(n => n.id === member.startNodeId);
            const endNode = nodes.find(n => n.id === member.endNodeId);

            if (startNode && endNode) {
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

        // Draw Loads
        loads.forEach(load => {
            ForceRenderer.draw(ctx, load, viewport, nodes, members);
        });

        // Ghost Member
        if (interaction.creationState.mode === 'drawing_member' && interaction.creationState.startPos) {
            const startNode = nodes.find(n => n.id === interaction.creationState.activeId);
            if (startNode) {
                RenderUtils.drawGhostMember(ctx, startNode.position, interaction.mousePos, viewport);
            }
        }

        // Draw Nodes & Supports (on top)
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
        scheiben: Scheibe[],
        viewport: ViewportState,
        interaction: AnalysisInteractionState
    ) {
        // Clear Screen
        RenderUtils.clearScreen(ctx, canvas);

        // Draw Grid
        RenderUtils.drawGrid(ctx, canvas, viewport);

        // Draw Scheiben (behind everything)
        scheiben.forEach(scheibe => {
            ScheibenRenderer.draw(ctx, scheibe, viewport, false, false);
        });

        const nodeStates = NodeRenderer.analyzeNodeStates(nodes, members);
        NodeRenderer.drawRigidConnections(ctx, nodes, members, viewport, nodeStates);

        // Draw Members
        members.forEach(member => {
            const startNode = nodes.find(n => n.id === member.startNodeId);
            const endNode = nodes.find(n => n.id === member.endNodeId);

            if (startNode && endNode) {
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

        // Draw Loads
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
