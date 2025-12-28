import type { ViewportState } from '~/types/app';
import type { Member, Node, Vec2 } from '~/types/model';
import * as Coords from '../../lib/coordinates';
import { SymbolRenderer } from './SymbolRenderer';

export const COLORS = {
    background: '#ffffff',
    grid: '#f1f5f9',
    axis: '#cbd5e1',
    member: '#334155',
    node: '#3b82f6',
    highlight: '#f59e0b',
    support: '#0f172a',
    globalHingeFill: '#ffffff',
    globalHingeStroke: '#334155'
};

export const SIZES = {
    nodeRadius: 4,
    globalHingeRadius: 6,
    memberWidth: 3,
    hingeOffset: 16,
    hingeSymbolRadius: 6,
    rigidCornerSize: 14
};

export type NodeState =
    | 'ISOLATED'
    | 'RIGID'
    | 'MIXED'
    | 'GLOBAL_HINGE_MOMENT'
    | 'GLOBAL_HINGE_SHEAR'
    | 'GLOBAL_HINGE_AXIAL';

export class RenderUtils {

    static clearScreen(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = COLORS.background;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    static drawGrid(ctx: CanvasRenderingContext2D, canvas: HTMLCanvasElement, viewport: ViewportState) {
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

    static drawMember(
        ctx: CanvasRenderingContext2D,
        start: Node,
        end: Node,
        member: Member,
        viewport: ViewportState,
        startNodeState: NodeState = 'ISOLATED',
        endNodeState: NodeState = 'ISOLATED'
    ) {
        const p1 = Coords.worldToScreen(start.position.x, start.position.y, viewport);
        const p2 = Coords.worldToScreen(end.position.x, end.position.y, viewport);

        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const length = Math.sqrt(dx * dx + dy * dy);
        const ux = dx / length;
        const uy = dy / length;
        const angleDeg = Math.atan2(dy, dx) * (180 / Math.PI);

        const startReleased = this.hasRelease(member.releases.start);
        const endReleased = this.hasRelease(member.releases.end);

        const lineStart = { x: p1.x, y: p1.y };
        const lineEnd = { x: p2.x, y: p2.y };

        // Helper to check if a state is ANY global hinge
        const isGlobal = (s: NodeState) => s.startsWith('GLOBAL_HINGE');

        // --- START NODE LOGIC ---
        if (isGlobal(startNodeState)) {
            // Stop at the global symbol radius. 
            // We use the same radius for all types to keep it consistent.
            lineStart.x = p1.x + ux * SIZES.globalHingeRadius;
            lineStart.y = p1.y + uy * SIZES.globalHingeRadius;
        }
        else if (startReleased) {
            // Mixed/Single: Use Offset
            const trim = SIZES.hingeOffset - SIZES.hingeSymbolRadius;
            lineStart.x = p1.x + ux * trim;
            lineStart.y = p1.y + uy * trim;
        }

        // --- END NODE LOGIC ---
        if (isGlobal(endNodeState)) {
            lineEnd.x = p2.x - ux * SIZES.globalHingeRadius;
            lineEnd.y = p2.y - uy * SIZES.globalHingeRadius;
        }
        else if (endReleased) {
            const trim = SIZES.hingeOffset - SIZES.hingeSymbolRadius;
            lineEnd.x = p2.x - ux * trim;
            lineEnd.y = p2.y - uy * trim;
        }

        // --- Draw Line ---
        ctx.lineWidth = SIZES.memberWidth;
        ctx.strokeStyle = COLORS.member;
        ctx.beginPath();
        ctx.moveTo(lineStart.x, lineStart.y);
        ctx.lineTo(lineEnd.x, lineEnd.y);
        ctx.stroke();

        // --- Draw Symbols ---
        // ONLY draw individual symbols if it is NOT a global hinge.
        if (startReleased && !isGlobal(startNodeState)) {
            const pos = { x: p1.x + ux * SIZES.hingeOffset, y: p1.y + uy * SIZES.hingeOffset };
            this.drawReleaseSymbol(ctx, member.releases.start, pos, angleDeg);
        }

        if (endReleased && !isGlobal(endNodeState)) {
            const pos = { x: p2.x - ux * SIZES.hingeOffset, y: p2.y - uy * SIZES.hingeOffset };
            this.drawReleaseSymbol(ctx, member.releases.end, pos, angleDeg);
        }
    }

    static drawReleaseSymbol(
        ctx: CanvasRenderingContext2D,
        release: { fx: boolean, fy: boolean, mz: boolean },
        pos: { x: number, y: number },
        rotationDeg: number
    ) {
        let symbolKey: string | null = null;
        if (release.fx) symbolKey = 'NORMALKRAFTGELENK';
        else if (release.fy) symbolKey = 'SCHUBGELENK';
        else if (release.mz) symbolKey = 'VOLLGELENK';

        if (symbolKey) {
            SymbolRenderer.draw(ctx, symbolKey, pos, rotationDeg, COLORS.member);
        }
    }

    static drawGhostMember(ctx: CanvasRenderingContext2D, startWorld: Vec2, mouseWorld: Vec2, viewport: ViewportState) {
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

    static hasRelease(r: { fx: boolean, fy: boolean, mz: boolean }): boolean {
        return !!(r.fx || r.fy || r.mz);
    }

    // FOR SIMLIEFIED SOKUTION REDNERER MAYBE USE ALSO IN THE REST
    static project(pos: Vec2, viewport: ViewportState): Vec2 {
        return Coords.worldToScreen(pos.x, pos.y, viewport);
    }
}
