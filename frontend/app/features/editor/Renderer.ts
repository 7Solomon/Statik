import type { Member, Node, Vec2 } from '~/types/model';
import * as Coords from '../../lib/coordinates';
import type { InteractionState, ViewportState } from '~/types/app';

// Visual Constants
const COLORS = {
    background: '#ffffff',
    grid: '#e2e8f0', // Slate-200
    axis: '#94a3b8', // Slate-400
    member: '#334155', // Slate-700
    node: '#3b82f6', // Blue-500
    nodeFixed: '#ef4444', // Red-500 for supports
    highlight: '#f59e0b', // Amber-500
    text: '#64748b'
};

const SIZES = {
    nodeRadius: 4,
    memberWidth: 3,
    supportSize: 15, // Size of the triangle symbol in pixels
    hingeRadius: 3
};

export class Renderer {

    /**
     * Main Render Loop
     */
    static render(
        ctx: CanvasRenderingContext2D,
        canvas: HTMLCanvasElement,
        nodes: Node[],
        members: Member[],
        viewport: ViewportState,
        interaction: InteractionState
    ) {
        // 1. Clear Screen
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = COLORS.background;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // 2. Draw Grid & Axes
        this.drawGrid(ctx, canvas, viewport);

        // 3. Draw Members
        members.forEach(member => {
            const startNode = nodes.find(n => n.id === member.startNodeId);
            const endNode = nodes.find(n => n.id === member.endNodeId);
            if (startNode && endNode) {
                this.drawMember(ctx, startNode, endNode, member, viewport);
            }
        });

        // 4. Draw Interaction (Ghost Member)
        if (interaction.dragStartNodeId && interaction.activeTool === 'member') {
            const startNode = nodes.find(n => n.id === interaction.dragStartNodeId);
            if (startNode) {
                this.drawGhostMember(ctx, startNode.position, interaction.mousePos, viewport);
            }
        }

        // 5. Draw Nodes & Supports
        nodes.forEach(node => {
            const isHovered = interaction.hoveredNodeId === node.id;
            this.drawNode(ctx, node, viewport, isHovered);
        });
    }

    /**
     * Draw Infinite Grid
     */
    private static drawGrid(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, viewport: ViewportState) {
        ctx.lineWidth = 1;
        ctx.strokeStyle = COLORS.grid;

        // Calculate visible range in World Coordinates
        const topLeft = Coords.screenToWorld(0, 0, viewport, canvas.height);
        const bottomRight = Coords.screenToWorld(canvas.width, canvas.height, viewport, canvas.height);

        const gridSize = viewport.gridSize;

        // Vertical Lines (X)
        const startX = Math.floor(topLeft.x / gridSize) * gridSize;
        const endX = Math.ceil(bottomRight.x / gridSize) * gridSize;

        ctx.beginPath();
        for (let x = startX; x <= endX; x += gridSize) {
            const p = Coords.worldToScreen(x, 0, viewport); // Y doesn't matter for vertical line x-coord
            ctx.moveTo(p.x, 0);
            ctx.lineTo(p.x, canvas.height);
        }
        ctx.stroke();

        // Horizontal Lines (Y)
        const startY = Math.floor(bottomRight.y / gridSize) * gridSize; // Y is smaller at bottom in engineering? No, usually Y up.
        // Let's just use min/max safely
        const minY = Math.min(topLeft.y, bottomRight.y);
        const maxY = Math.max(topLeft.y, bottomRight.y);
        const sY = Math.floor(minY / gridSize) * gridSize;
        const eY = Math.ceil(maxY / gridSize) * gridSize;

        ctx.beginPath();
        for (let y = sY; y <= eY; y += gridSize) {
            const p = Coords.worldToScreen(0, y, viewport);
            ctx.moveTo(0, p.y);
            ctx.lineTo(canvas.width, p.y);
        }
        ctx.stroke();

        // Draw Axes (X=0 and Y=0)
        ctx.strokeStyle = COLORS.axis;
        ctx.lineWidth = 2;
        const origin = Coords.worldToScreen(0, 0, viewport);

        ctx.beginPath();
        ctx.moveTo(origin.x, 0);
        ctx.lineTo(origin.x, canvas.height); // Y Axis
        ctx.moveTo(0, origin.y);
        ctx.lineTo(canvas.width, origin.y); // X Axis
        ctx.stroke();
    }

    /**
     * Draw Single Member
     */
    private static drawMember(
        ctx: CanvasRenderingContext2D,
        start: Node,
        end: Node,
        member: Member,
        viewport: ViewportState
    ) {
        const p1 = Coords.worldToScreen(start.position.x, start.position.y, viewport);
        const p2 = Coords.worldToScreen(end.position.x, end.position.y, viewport);

        ctx.lineWidth = SIZES.memberWidth;
        ctx.strokeStyle = COLORS.member;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        // Draw Hinges (Releases)
        // If start is released (moment = false/hinge), draw circle
        // Note: In your model 'true' meant RELEASED (Hinge), 'false' meant FIXED.
        // But verify your types/model.ts. I usually prefer boolean 'isFixed'.
        // Let's assume released.start.mz === true means "Hinge"

        if (member.releases.start.mz) {
            this.drawHinge(ctx, p1, p2);
        }
        if (member.releases.end.mz) {
            this.drawHinge(ctx, p2, p1);
        }
    }

    /**
     * Helper: Draw a little white circle with black border to represent a hinge
     * Offset slightly from the node towards the member center
     */
    private static drawHinge(ctx: CanvasRenderingContext2D, at: Vec2, towards: Vec2) {
        // Calculate vector direction
        const dx = towards.x - at.x;
        const dy = towards.y - at.y;
        const len = Math.sqrt(dx * dx + dy * dy);

        // Offset by e.g. 10 pixels
        const offset = 8;
        const cx = at.x + (dx / len) * offset;
        const cy = at.y + (dy / len) * offset;

        ctx.fillStyle = '#fff';
        ctx.strokeStyle = COLORS.member;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx, cy, SIZES.hingeRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
    }

    /**
     * Draw Ghost Member (Interaction)
     */
    private static drawGhostMember(ctx: CanvasRenderingContext2D, startWorld: Vec2, mouseWorld: Vec2, viewport: ViewportState) {
        const p1 = Coords.worldToScreen(startWorld.x, startWorld.y, viewport);
        const p2 = Coords.worldToScreen(mouseWorld.x, mouseWorld.y, viewport);

        ctx.lineWidth = 2;
        ctx.strokeStyle = COLORS.highlight;
        ctx.setLineDash([5, 5]); // Dashed line
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
        ctx.setLineDash([]); // Reset
    }

    /**
     * Draw Node & Symbol
     */
    private static drawNode(ctx: CanvasRenderingContext2D, node: Node, viewport: ViewportState, isHovered: boolean) {
        const p = Coords.worldToScreen(node.position.x, node.position.y, viewport);

        // 1. Draw Support Symbol (if supports exist)
        const { fixX, fixY, fixM } = node.supports;

        ctx.save();
        ctx.translate(p.x, p.y);

        // Rotation logic (if needed later)
        // ctx.rotate(node.rotation * Math.PI / 180);

        ctx.strokeStyle = COLORS.nodeFixed;
        ctx.lineWidth = 2;

        if (fixX && fixY && fixM) {
            // Fixed Support (Block/Hatch)
            ctx.beginPath();
            ctx.rect(-10, 5, 20, 10); // Draw block below
            ctx.stroke();
            // Hatching
            ctx.beginPath();
            ctx.moveTo(-10, 15); ctx.lineTo(-5, 5);
            ctx.moveTo(0, 15); ctx.lineTo(5, 5);
            ctx.moveTo(10, 15); ctx.lineTo(15, 5);
            ctx.stroke();
        }
        else if (fixX && fixY && !fixM) {
            // Pinned Support (Triangle)
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(-10, 15);
            ctx.lineTo(10, 15);
            ctx.closePath();
            ctx.stroke();
        }
        else if (!fixX && fixY && !fixM) {
            // Roller (Triangle + Wheels/Line)
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(-10, 12);
            ctx.lineTo(10, 12);
            ctx.closePath();
            ctx.stroke();

            // Wheels
            ctx.beginPath();
            ctx.moveTo(-15, 15); ctx.lineTo(15, 15); // Floor line
            ctx.stroke();
        }

        ctx.restore();

        // 2. Draw Node Point
        ctx.fillStyle = isHovered ? COLORS.highlight : COLORS.node;
        ctx.beginPath();
        ctx.arc(p.x, p.y, SIZES.nodeRadius, 0, Math.PI * 2);
        ctx.fill();
    }
}
