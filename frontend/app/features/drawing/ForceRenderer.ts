import { COLORS, SIZES, RenderUtils } from './RenderUtils';
import type { Load, Member, Node, Vec2 } from '~/types/model';
import * as Coords from '../../lib/coordinates';
import type { ViewportState } from '~/types/app';

// Configuration for visuals
const FORCE_CONFIG = {
    color: '#ef4444',     // Red
    lineWidth: 2,
    arrowSize: 8,
    pointLength: 40,
    pointOffset: 8,
    distSpacing: 20,
    distMaxHeight: 40,
};

export class ForceRenderer {

    /**
     * Main Router: Decides what to draw based on load SCOPE and TYPE
     */
    static draw(
        ctx: CanvasRenderingContext2D,
        load: Load,
        viewport: ViewportState,
        nodes: Node[],
        members: Member[]
    ) {
        ctx.save();
        ctx.strokeStyle = FORCE_CONFIG.color;
        ctx.fillStyle = FORCE_CONFIG.color;
        ctx.lineWidth = FORCE_CONFIG.lineWidth;

        // ------------------------------------------------------
        // 1. LOADS ON NODES
        // ------------------------------------------------------
        if (load.scope === 'NODE') {
            const node = nodes.find(n => n.id === load.nodeId);
            if (node) {
                const screenPos = Coords.worldToScreen(node.position.x, node.position.y, viewport);

                if (load.type === 'MOMENT') {
                    this.drawMoment(ctx, screenPos, load.value);
                } else {
                    // Point load on node
                    this.drawPointLoad(ctx, screenPos, load.angle ?? -90, load.value);
                }
            }
        }

        // ------------------------------------------------------
        // 2. LOADS ON MEMBERS
        // ------------------------------------------------------
        else if (load.scope === 'MEMBER') {
            const member = members.find(m => m.id === load.memberId);
            if (member) {
                const startNode = nodes.find(n => n.id === member.startNodeId);
                const endNode = nodes.find(n => n.id === member.endNodeId);

                if (startNode && endNode) {

                    // A. POINT LOAD ON MEMBER
                    if (load.type === 'POINT') {
                        // Calculate position based on RATIO (0 to 1)
                        const t = load.ratio;
                        const wx = startNode.position.x + (endNode.position.x - startNode.position.x) * t;
                        const wy = startNode.position.y + (endNode.position.y - startNode.position.y) * t;

                        const screenPos = Coords.worldToScreen(wx, wy, viewport);
                        this.drawPointLoad(ctx, screenPos, load.angle ?? -90, load.value);
                    }

                    // B. DISTRIBUTED LOAD
                    else if (load.type === 'DISTRIBUTED') {
                        const p1 = Coords.worldToScreen(startNode.position.x, startNode.position.y, viewport);
                        const p2 = Coords.worldToScreen(endNode.position.x, endNode.position.y, viewport);

                        this.drawDistributedLoad(ctx, p1, p2, load);
                    }
                }
            }
        }

        ctx.restore();
    }

    // ==========================================================
    // PRIMITIVES
    // ==========================================================

    private static drawPointLoad(ctx: CanvasRenderingContext2D, pos: Vec2, angleDeg: number, value: number) {
        ctx.save();
        ctx.translate(pos.x, pos.y);

        // Rotate canvas so +X is the direction of the force
        const angleRad = -(angleDeg) * (Math.PI / 180);
        ctx.rotate(angleRad);

        const L = FORCE_CONFIG.pointLength;
        const gap = FORCE_CONFIG.pointOffset;

        // Draw Arrow pointing towards (0,0) from negative X
        const tailX = -(L + gap);
        const headX = -gap;

        // Line
        ctx.beginPath();
        ctx.moveTo(tailX, 0);
        ctx.lineTo(headX, 0);
        ctx.stroke();

        // Arrowhead
        this.drawArrowHead(ctx, headX, 0, 0);

        // Label
        this.drawLabel(ctx, `${value}kN`, tailX - 10, 0, -angleRad);

        ctx.restore();
    }

    private static drawMoment(ctx: CanvasRenderingContext2D, pos: Vec2, value: number) {
        ctx.save();
        ctx.translate(pos.x, pos.y);

        const r = 20;
        const isClockwise = value < 0; // Convention check

        ctx.beginPath();
        const startAngle = 0;
        const endAngle = 1.5 * Math.PI;
        ctx.arc(0, 0, r, startAngle, endAngle);
        ctx.stroke();

        const tipX = r * Math.cos(endAngle);
        const tipY = r * Math.sin(endAngle);

        ctx.save();
        ctx.translate(tipX, tipY);
        ctx.rotate(endAngle + (isClockwise ? Math.PI / 2 : -Math.PI / 2));
        this.drawArrowHead(ctx, 0, 0, 0);
        ctx.restore();

        this.drawLabel(ctx, `${Math.abs(value)}kNm`, 0, -r - 10, 0);
        ctx.restore();
    }

    private static drawDistributedLoad(
        ctx: CanvasRenderingContext2D,
        p1: Vec2,
        p2: Vec2,
        load: any // Typed as any here just to access specific member-dist props safely
    ) {
        // We know it is MemberDistLoad here
        const rStart = load.startRatio;
        const rEnd = load.endRatio;
        const valStart = load.startValue ?? load.value;
        const valEnd = load.endValue ?? load.value;

        // Geometry
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const lengthPx = Math.sqrt(dx * dx + dy * dy);
        const angleRad = Math.atan2(dy, dx);

        ctx.save();
        ctx.translate(p1.x, p1.y);
        ctx.rotate(angleRad); // X-axis along beam

        // Heights (Visual Scaling)
        const maxVal = Math.max(Math.abs(valStart), Math.abs(valEnd));
        const scale = maxVal === 0 ? 0 : FORCE_CONFIG.distMaxHeight / maxVal;

        // Y-direction: Positive loads usually point DOWN (positive Y in canvas)
        // Adjust sign based on your structural convention (usually loads oppose Global Y)
        const hStart = -valStart * scale;
        const hEnd = -valEnd * scale;

        const xStart = lengthPx * rStart;
        const xEnd = lengthPx * rEnd;
        const width = xEnd - xStart;

        // 1. Draw "Container" Polygon
        if (Math.abs(width) > 1) { // Only draw if length > 1px
            ctx.beginPath();
            ctx.moveTo(xStart, 0);
            ctx.lineTo(xStart, hStart);
            ctx.lineTo(xEnd, hEnd);
            ctx.lineTo(xEnd, 0);
            ctx.fillStyle = `${FORCE_CONFIG.color}33`; // Transparent fill
            ctx.fill();

            // Top line
            ctx.beginPath();
            ctx.moveTo(xStart, hStart);
            ctx.lineTo(xEnd, hEnd);
            ctx.stroke();

            // 2. Internal Arrows
            // Ensure strictly positive spacing loop
            const spacing = FORCE_CONFIG.distSpacing;
            const numArrows = Math.floor(Math.abs(width) / spacing);

            for (let i = 0; i <= numArrows; i++) {
                // lerp ratio (0 to 1)
                const t = numArrows === 0 ? 0.5 : i / numArrows;
                const curX = xStart + (xEnd - xStart) * t;
                const curH = hStart + (hEnd - hStart) * t;

                this.drawArrowLine(ctx, curX, curH, curX, 0);
            }
        }

        // Labels
        this.drawLabel(ctx, `${valStart}`, xStart, hStart - 10, -angleRad);
        if (valStart !== valEnd) {
            this.drawLabel(ctx, `${valEnd}`, xEnd, hEnd - 10, -angleRad);
        }

        ctx.restore();
    }

    // --- HELPERS ---

    private static drawArrowLine(ctx: CanvasRenderingContext2D, x1: number, y1: number, x2: number, y2: number) {
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();

        const dx = x2 - x1;
        const dy = y2 - y1;
        const angle = Math.atan2(dy, dx);

        this.drawArrowHead(ctx, x2, y2, angle);
    }

    private static drawArrowHead(ctx: CanvasRenderingContext2D, x: number, y: number, rotation: number) {
        const s = FORCE_CONFIG.arrowSize;
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(rotation);
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(-s, -s * 0.4);
        ctx.lineTo(-s, s * 0.4);
        ctx.closePath();
        ctx.fillStyle = FORCE_CONFIG.color;
        ctx.fill();
        ctx.restore();
    }

    private static drawLabel(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, counterRotateRad: number) {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(counterRotateRad);
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        ctx.fillStyle = FORCE_CONFIG.color;
        ctx.fillText(text, 0, 0);
        ctx.restore();
    }
}
