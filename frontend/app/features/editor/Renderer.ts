import type { Member, Node, Vec2, SupportValue } from '~/types/model';
import * as Coords from '../../lib/coordinates';
import type { InteractionState, ViewportState } from '~/types/app';
import { SymbolRenderer } from './SymbolRenderer';

// --- Visual Constants ---
const COLORS = {
    background: '#ffffff',
    grid: '#f1f5f9',
    axis: '#cbd5e1',
    member: '#334155',
    node: '#3b82f6',
    highlight: '#f59e0b',
    support: '#0f172a',
    text: '#64748b'
};

const SIZES = {
    nodeRadius: 4,
    memberWidth: 3,
    hingeOffset: 16, // <--- NEW: Distance from node center to hinge symbol
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

        // 4. Ghost Member
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

    private static drawGrid(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, viewport: ViewportState) {
        // ... (Keep existing grid logic) ... 
        // For brevity, assuming this is unchanged from previous message
        ctx.lineWidth = 1;
        ctx.strokeStyle = COLORS.grid;
        const topLeft = Coords.screenToWorld(0, 0, viewport, canvas.height);
        const bottomRight = Coords.screenToWorld(canvas.width, canvas.height, viewport, canvas.height);
        const gridSize = viewport.gridSize;

        const startX = Math.floor(topLeft.x / gridSize) * gridSize;
        const endX = Math.ceil(bottomRight.x / gridSize) * gridSize;
        ctx.beginPath();
        for (let x = startX; x <= endX; x += gridSize) {
            const p = Coords.worldToScreen(x, 0, viewport);
            ctx.moveTo(p.x, 0);
            ctx.lineTo(p.x, canvas.height);
        }
        ctx.stroke();

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

        ctx.strokeStyle = COLORS.axis;
        ctx.lineWidth = 2;
        const origin = Coords.worldToScreen(0, 0, viewport);
        ctx.beginPath();
        ctx.moveTo(origin.x, 0);
        ctx.lineTo(origin.x, canvas.height);
        ctx.moveTo(0, origin.y);
        ctx.lineTo(canvas.width, origin.y);
        ctx.stroke();
    }

    /**
     * Draw Single Member + Hinges with Offset
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

        // 1. Calculate Geometry
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const length = Math.sqrt(dx * dx + dy * dy);

        // Normalize vector
        const ux = dx / length;
        const uy = dy / length;

        // Angle in degrees
        const angleDeg = Math.atan2(dy, dx) * (180 / Math.PI);

        // 2. Draw the Line (From node center to node center)
        ctx.lineWidth = SIZES.memberWidth;
        ctx.strokeStyle = COLORS.member;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();

        // 3. Draw Hinges with Offset
        // We move the draw position 'down' the line by SIZES.hingeOffset

        // Start Hinge Position: Move FROM p1 TOWARDS p2
        const startHingePos = {
            x: p1.x + ux * SIZES.hingeOffset,
            y: p1.y + uy * SIZES.hingeOffset
        };

        // End Hinge Position: Move FROM p2 TOWARDS p1
        const endHingePos = {
            x: p2.x - ux * SIZES.hingeOffset,
            y: p2.y - uy * SIZES.hingeOffset
        };

        this.drawReleaseSymbol(ctx, member.releases.start, startHingePos, angleDeg, viewport);

        // Note: For the end node, we still rotate by 'angleDeg'.
        // Why? Because symbols like 'Box' or 'Vertical Line' are symmetric.
        // If you had a directional symbol (arrow), you'd need angleDeg + 180.
        this.drawReleaseSymbol(ctx, member.releases.end, endHingePos, angleDeg, viewport);
    }

    private static drawReleaseSymbol(
        ctx: CanvasRenderingContext2D,
        release: { fx: boolean, fy: boolean, mz: boolean },
        pos: { x: number, y: number },
        rotationDeg: number,
        viewport: ViewportState
    ) {
        let symbolKey: string | null = null;

        // Priority Logic:
        // 1. Axial (N) - Box Sleeve
        if (release.fx) {
            symbolKey = 'HINGE_NORMALKRAFTGELENK';
        }
        // 2. Shear (V) - Vertical Lines
        else if (release.fy) {
            symbolKey = 'HINGE_SCHUBGELENK';
        }
        // 3. Moment (M) - Circle
        else if (release.mz) {
            symbolKey = 'HINGE_VOLLGELENK';
        }

        if (symbolKey) {
            // Draw white background for the symbol to cover the line beneath it
            // (Optional, but looks cleaner for boxes/circles)
            SymbolRenderer.draw(ctx, symbolKey, pos, rotationDeg, COLORS.member);
        }
    }

    private static drawGhostMember(ctx: CanvasRenderingContext2D, startWorld: Vec2, mouseWorld: Vec2, viewport: ViewportState) {
        const p1 = Coords.worldToScreen(startWorld.x, startWorld.y, viewport);
        const p2 = Coords.worldToScreen(mouseWorld.x, mouseWorld.y, viewport);

        ctx.lineWidth = 2;
        ctx.strokeStyle = COLORS.highlight;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    private static drawNode(ctx: CanvasRenderingContext2D, node: Node, viewport: ViewportState, isHovered: boolean) {
        const p = Coords.worldToScreen(node.position.x, node.position.y, viewport);
        const { fixX, fixY, fixM } = node.supports;
        const rotation = node.rotation;

        const isRigid = (val: SupportValue) => val === true;
        const isFree = (val: SupportValue) => val === false;
        const isSpring = (val: SupportValue) => typeof val === 'number';

        let symbolKey: string | null = null;
        let activeColor = isHovered ? COLORS.highlight : COLORS.support;

        if (isRigid(fixX) && isRigid(fixY) && isRigid(fixM)) {
            symbolKey = 'SUPPORT_FESTE_EINSPANNUNG';
        }
        else if (isRigid(fixX) && isRigid(fixY)) {
            if (isSpring(fixM)) {
                symbolKey = 'SUPPORT_TORSIONSFEDER';
            } else {
                symbolKey = 'SUPPORT_FESTLAGER';
            }
        }
        else if (isRigid(fixY) && isFree(fixX) && isFree(fixM)) {
            symbolKey = 'SUPPORT_LOSLAGER';
        }
        else if (isRigid(fixX) && isFree(fixY)) {
            symbolKey = 'SUPPORT_GLEITLAGER';
        }
        else if (isSpring(fixY) && isFree(fixX)) {
            symbolKey = 'SUPPORT_FEDER';
        }

        if (symbolKey) {
            SymbolRenderer.draw(ctx, symbolKey, p, rotation, activeColor);
        }

        ctx.fillStyle = isHovered ? COLORS.highlight : COLORS.node;
        ctx.beginPath();
        ctx.arc(p.x, p.y, SIZES.nodeRadius, 0, Math.PI * 2);
        ctx.fill();
    }
}
