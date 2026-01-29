import { RenderUtils } from './RenderUtils';
import { ScheibenRenderer } from './ScheibenRenderer';
import type { ViewportState } from '~/types/app';
import type { Node, Member, StructuralSystem } from '~/types/model';
import type { FEMResult, MemberResult, StationResult } from '~/types/model';

export type DiagramType = 'NONE' | 'N' | 'V' | 'M';

export class SolutionRenderer {

    /**
     * Main entry point to draw analysis results.
     */
    static render(
        ctx: CanvasRenderingContext2D,
        canvas: HTMLCanvasElement,
        system: StructuralSystem,
        result: FEMResult,
        diagramType: DiagramType,
        viewport: ViewportState
    ) {
        // 1. Clear & Grid (Standard)
        RenderUtils.clearScreen(ctx, canvas);
        RenderUtils.drawGrid(ctx, canvas, viewport);

        // 2. Draw Base Structure (Undeformed)
        this.drawBaseStructure(ctx, system, viewport);

        // 3. Draw Diagrams
        if (diagramType !== 'NONE' && result.success && result.memberResults) {
            const scaleFactor = this.calculateDiagramScale(result, diagramType, viewport);

            Object.values(result.memberResults).forEach(memberResult => {
                const member = system.members.find(m => m.id === memberResult.memberId);

                if (!member) return;

                const startNode = system.nodes.find(n => n.id === member.startNodeId);
                const endNode = system.nodes.find(n => n.id === member.endNodeId);

                if (startNode && endNode) {
                    this.drawMemberDiagram(
                        ctx,
                        startNode,
                        endNode,
                        memberResult,
                        diagramType,
                        scaleFactor,
                        viewport
                    );
                }
            });
        }

        // 4. Draw Reactions (Arrows at supports)
        if (result.reactions) {
            this.drawReactions(ctx, system.nodes, result.reactions, viewport);
        }

        // 5. Draw Node Symbols (Joints) on top
        system.nodes.forEach(node => {
            const screenPos = RenderUtils.project(node.position, viewport);
            ctx.beginPath();
            ctx.arc(screenPos.x, screenPos.y, 3, 0, 2 * Math.PI);
            ctx.fillStyle = '#334155';
            ctx.fill();
        });
    }

    private static drawBaseStructure(
        ctx: CanvasRenderingContext2D,
        system: StructuralSystem,
        view: ViewportState
    ) {
        // 1. Draw Scheiben first (as background) ← NEW
        if (system.scheiben && system.scheiben.length > 0) {
            system.scheiben.forEach(scheibe => {
                ScheibenRenderer.draw(
                    ctx,
                    scheibe,
                    view,
                    false,  // Not active
                    false   // Not selected
                );
            });
        }

        // 2. Draw Members
        ctx.strokeStyle = '#cbd5e1'; // Light grey for base structure
        ctx.lineWidth = 1;

        system.members.forEach(m => {
            const n1 = system.nodes.find(n => n.id === m.startNodeId);
            const n2 = system.nodes.find(n => n.id === m.endNodeId);
            if (n1 && n2) {
                const p1 = RenderUtils.project(n1.position, view);
                const p2 = RenderUtils.project(n2.position, view);
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.stroke();
            }
        });
    }

    private static drawMemberDiagram(
        ctx: CanvasRenderingContext2D,
        startNode: Node,
        endNode: Node,
        res: MemberResult,
        type: DiagramType,
        scale: number,
        view: ViewportState
    ) {
        const p1 = RenderUtils.project(startNode.position, view);
        const p2 = RenderUtils.project(endNode.position, view);

        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const L_screen = Math.sqrt(dx * dx + dy * dy);
        const angle = Math.atan2(dy, dx);

        ctx.save();
        ctx.translate(p1.x, p1.y);
        ctx.rotate(angle);

        // Begin Path for the Filled Diagram
        ctx.beginPath();
        ctx.moveTo(0, 0); // Start at node 1

        // Find max length (to normalize x)
        const L_real = res.stations[res.stations.length - 1].x;

        res.stations.forEach(s => {
            const px = (s.x / L_real) * L_screen;

            // Get value based on type
            let val = 0;
            if (type === 'M') val = -s.M; // Invert Moment for standard "Tension Side" plot
            else if (type === 'V') val = s.V;
            else if (type === 'N') val = s.N;

            // py is perpendicular offset
            const py = val * scale;

            ctx.lineTo(px, -py); // Negative Y is "Up" in local coords
        });

        ctx.lineTo(L_screen, 0); // Close to node 2
        ctx.closePath();

        // Style based on Type
        if (type === 'M') {
            ctx.fillStyle = 'rgba(239, 68, 68, 0.15)'; // Red tint
            ctx.strokeStyle = '#ef4444';
        } else if (type === 'V') {
            ctx.fillStyle = 'rgba(59, 130, 246, 0.15)'; // Blue tint
            ctx.strokeStyle = '#3b82f6';
        } else {
            ctx.fillStyle = 'rgba(16, 185, 129, 0.15)'; // Green tint
            ctx.strokeStyle = '#10b981';
        }

        ctx.fill();
        ctx.stroke();

        ctx.restore();
    }

    private static calculateDiagramScale(result: FEMResult, type: DiagramType, view: ViewportState): number {
        let maxVal = 0;

        if (!result.memberResults) return 1;

        Object.values(result.memberResults).forEach(m => {
            if (type === 'M') maxVal = Math.max(maxVal, Math.abs(m.maxM), Math.abs(m.minM));
            else if (type === 'V') maxVal = Math.max(maxVal, Math.abs(m.maxV), Math.abs(m.minV));
            else if (type === 'N') maxVal = Math.max(maxVal, Math.abs(m.maxN || 0));
        });

        if (maxVal < 1e-6) return 1;

        const targetHeightPixels = 50;
        return targetHeightPixels / maxVal;
    }


    private static drawReactions(
        ctx: CanvasRenderingContext2D,
        nodes: Node[],
        reactions: Record<string, [number, number, number]>,
        view: ViewportState
    ) {
        ctx.font = '10px sans-serif';
        ctx.fillStyle = '#0f172a';
        ctx.strokeStyle = '#0f172a';

        nodes.forEach(node => {
            const r = reactions[node.id];
            if (!r) return;

            const [rx, ry, mz] = r;
            const screenPos = RenderUtils.project(node.position, view);

            // Draw Reaction Arrows
            if (Math.abs(rx) > 1e-3) {
                this.drawArrow(ctx, screenPos.x - 30 * Math.sign(rx), screenPos.y, screenPos.x, screenPos.y);
                ctx.fillText(`Rx:${rx.toFixed(1)}`, screenPos.x - 40, screenPos.y - 5);
            }
            if (Math.abs(ry) > 1e-3) {
                this.drawArrow(ctx, screenPos.x, screenPos.y + 30 * Math.sign(ry), screenPos.x, screenPos.y);
                ctx.fillText(`Ry:${ry.toFixed(1)}`, screenPos.x + 5, screenPos.y + 20);
            }
        });
    }

    private static drawArrow(ctx: CanvasRenderingContext2D, x1: number, y1: number, x2: number, y2: number) {
        const headlen = 10;
        const dx = x2 - x1;
        const dy = y2 - y1;
        const angle = Math.atan2(dy, dx);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.lineTo(x2 - headlen * Math.cos(angle - Math.PI / 6), y2 - headlen * Math.sin(angle - Math.PI / 6));
        ctx.moveTo(x2, y2);
        ctx.lineTo(x2 - headlen * Math.cos(angle + Math.PI / 6), y2 - headlen * Math.sin(angle + Math.PI / 6));
        ctx.stroke();
    }
}
