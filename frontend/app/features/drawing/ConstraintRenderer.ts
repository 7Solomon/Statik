import type { ViewportState } from '~/types/app';
import type { Constraint, Node, Vec2 } from '~/types/model';
import * as Coords from '../../lib/coordinates';
import { COLORS } from './RenderUtils';

export class ConstraintRenderer {
    static draw(
        ctx: CanvasRenderingContext2D,
        constraint: Constraint,
        nodes: Node[],
        viewport: ViewportState,
        isHovered: boolean = false,
        isSelected: boolean = false
    ) {
        const startNode = nodes.find(n => n.id === constraint.startNodeId);
        const endNode = nodes.find(n => n.id === constraint.endNodeId);

        if (!startNode || !endNode) return;

        const p1 = Coords.worldToScreen(startNode.position.x, startNode.position.y, viewport);
        const p2 = Coords.worldToScreen(endNode.position.x, endNode.position.y, viewport);

        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const length = Math.sqrt(dx * dx + dy * dy);
        const angle = Math.atan2(dy, dx);

        if (length < 1) return;

        const color = isSelected ? '#2563eb' : isHovered ? COLORS.highlight : '#64748b';

        ctx.save();

        // 1. Transform entire context to element local system
        // Origin is at p1, X-axis points to p2
        ctx.translate(p1.x, p1.y);
        ctx.rotate(angle);

        // 2. Draw based on type
        switch (constraint.type) {
            case 'SPRING':
                this.drawSpring(ctx, length, color);
                break;
            case 'DAMPER':
                this.drawDamper(ctx, length, color);
                break;
            case 'CABLE':
                this.drawCable(ctx, length, color);
                break;
        }

        ctx.restore();

        //if (constraint.preload || constraint.c || constraint.prestress) {
        //    let label = '';
        //    if (constraint.type === 'SPRING' && constraint.preload) label = `F₀=${constraint.preload}`;
        //    if (constraint.type === 'DAMPER' && constraint.c) label = `c=${constraint.c}`;
        //    if (constraint.type === 'CABLE' && constraint.prestress) label = `T=${constraint.prestress}`;
        //
        //    //if (label) this.drawLabel(ctx, p1, p2, label, color);
        //}
    }

    private static drawSpring(ctx: CanvasRenderingContext2D, length: number, color: string) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';

        const coilCount = 8;
        const springWidth = 12;
        const leadLength = Math.min(20, length * 0.15); // Leads take up 15% or max 20px
        const activeLength = length - (leadLength * 2);
        const step = activeLength / (coilCount * 2);

        ctx.beginPath();
        // Start Lead
        ctx.moveTo(0, 0);
        ctx.lineTo(leadLength, 0);

        // Coils
        let x = leadLength;
        for (let i = 0; i < coilCount * 2; i++) {
            x += step;
            const y = (i % 2 === 0) ? -springWidth / 2 : springWidth / 2;
            ctx.lineTo(x, y);
        }

        // End Lead
        ctx.lineTo(length, 0);
        ctx.stroke();
    }

    private static drawDamper(ctx: CanvasRenderingContext2D, length: number, color: string) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.fillStyle = color;

        // Symbol Dimensions
        const potWidth = 16;
        const potLength = 24;
        const pistonWidth = 12; // Width of the T-head

        // Center the symbol
        const mid = length / 2;
        const potStart = mid - (potLength / 2);
        const potEnd = mid + (potLength / 2);

        // 1. Draw Leads (Wires to the symbol)
        ctx.beginPath();
        ctx.moveTo(0, 0);           // Start Node
        ctx.lineTo(potStart, 0);    // To Pot bottom
        ctx.moveTo(mid, 0);         // From Piston Head
        ctx.lineTo(length, 0);      // To End Node
        ctx.stroke();

        // 2. Draw Pot
        // Attached to the LEFT lead
        ctx.beginPath();
        ctx.moveTo(potEnd, -potWidth / 2); // Top right
        ctx.lineTo(potStart, -potWidth / 2); // Top left
        ctx.lineTo(potStart, potWidth / 2);  // Bottom left
        ctx.lineTo(potEnd, potWidth / 2);    // Bottom right
        ctx.stroke();

        // 3. Draw Piston
        // Attached to the RIGHT lead
        // The head is located exactly in the middle of the pot
        ctx.beginPath();
        ctx.moveTo(mid, -pistonWidth / 2);
        ctx.lineTo(mid, pistonWidth / 2);
        ctx.stroke();

    }

    private static drawCable(ctx: CanvasRenderingContext2D, length: number, color: string) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;

        // Simple line for cable
        // If you want "slack" visualization for compression, you'd check force,
        // but for pure geometry, a straight line is standard.

        // Dashed look or specific cable symbol? 
        // Often drawn as a solid line with dot endpoints.

        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(length, 0);
        ctx.stroke();

        // End dots
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(0, 0, 2.5, 0, Math.PI * 2);
        ctx.arc(length, 0, 2.5, 0, Math.PI * 2);
        ctx.fill();

        // Cross tick in middle to signify "tension member" (optional standard)
        // ctx.beginPath();
        // ctx.moveTo(length/2 - 4, -4);
        // ctx.lineTo(length/2 + 4, 4);
        // ctx.moveTo(length/2 - 4, 4);
        // ctx.lineTo(length/2 + 4, -4);
        // ctx.stroke();
    }

    private static drawLabel(
        ctx: CanvasRenderingContext2D,
        p1: Vec2,
        p2: Vec2,
        text: string,
        color: string
    ) {
        const midX = (p1.x + p2.x) / 2;
        const midY = (p1.y + p2.y) / 2;

        ctx.save();
        ctx.font = '11px monospace'; // Technical font
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const metrics = ctx.measureText(text);
        const padding = 4;
        const bgWidth = metrics.width + padding * 2;
        const bgHeight = 16;

        // Draw background pill to read text over lines
        ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
        ctx.fillRect(midX - bgWidth / 2, midY - bgHeight / 2 - 12, bgWidth, bgHeight);

        ctx.fillStyle = color;
        ctx.fillText(text, midX, midY - 12); // Offset slightly above the element
        ctx.restore();
    }



    /**
     * Draw a ghost constraint during creation
     */
    static drawGhost(
        ctx: CanvasRenderingContext2D,
        startWorld: Vec2,
        mouseWorld: Vec2,
        viewport: ViewportState,
        constraintType: 'SPRING' | 'DAMPER' | 'CABLE'
    ) {
        const p1 = Coords.worldToScreen(startWorld.x, startWorld.y, viewport);
        const p2 = Coords.worldToScreen(mouseWorld.x, mouseWorld.y, viewport);

        ctx.save();
        ctx.strokeStyle = COLORS.highlight;
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);

        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        ctx.setLineDash([]);
        ctx.restore();
    }
}
