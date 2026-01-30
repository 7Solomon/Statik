import type { ViewportState } from '~/types/app';
import type { Member, Node, SupportValue, Vec2 } from '~/types/model';
import * as Coords from '../../lib/coordinates';
import { SymbolRenderer } from './SymbolRenderer';
import { COLORS, SIZES, RenderUtils, type NodeState } from './RenderUtils';

export class NodeRenderer {

    static analyzeNodeStates(nodes: Node[], members: Member[]): Map<string, NodeState> {
        const map = new Map<string, NodeState>();

        nodes.forEach(node => {
            const connected = members.filter(m => m.startNodeId === node.id || m.endNodeId === node.id);

            if (connected.length === 0) {
                map.set(node.id, 'ISOLATED');
                return;
            }

            let allSameFx = true;
            let allSameFy = true;
            let allSameMz = true;

            const firstRel = connected[0].startNodeId === node.id ? connected[0].releases.start : connected[0].releases.end;
            let commonFx = firstRel.fx;
            let commonFy = firstRel.fy;
            let commonMz = firstRel.mz;

            for (let i = 1; i < connected.length; i++) {
                const m = connected[i];
                const rel = m.startNodeId === node.id ? m.releases.start : m.releases.end;
                if (rel.fx !== commonFx) allSameFx = false;
                if (rel.fy !== commonFy) allSameFy = false;
                if (rel.mz !== commonMz) allSameMz = false;
            }

            if (!commonFx && !commonFy && !commonMz && allSameFx && allSameFy && allSameMz) {
                map.set(node.id, 'RIGID');
                return;
            }

            // Global Hinge Checks
            if (allSameMz && commonMz && !commonFx && !commonFy) {
                map.set(node.id, 'GLOBAL_HINGE_MOMENT');
                return;
            }
            if (allSameFy && commonFy) {
                map.set(node.id, 'GLOBAL_HINGE_SHEAR');
                return;
            }
            if (allSameFx && commonFx) {
                map.set(node.id, 'GLOBAL_HINGE_AXIAL');
                return;
            }

            map.set(node.id, 'MIXED');
        });

        return map;
    }

    static drawRigidConnections(
        ctx: CanvasRenderingContext2D,
        nodes: Node[],
        members: Member[],
        viewport: ViewportState,
        nodeStates: Map<string, NodeState>
    ) {
        nodes.forEach(node => {
            const state = nodeStates.get(node.id);
            if (state !== 'RIGID' && state !== 'MIXED') return;

            const rigidMembers = members.filter(m => {
                const isStart = m.startNodeId === node.id;
                const isEnd = m.endNodeId === node.id;
                if (!isStart && !isEnd) return false;
                const rel = isStart ? m.releases.start : m.releases.end;
                return !RenderUtils.hasRelease(rel);
            });

            if (rigidMembers.length < 2) return;

            const center = Coords.worldToScreen(node.position.x, node.position.y, viewport);

            const memberData = rigidMembers.map(m => {
                const otherId = m.startNodeId === node.id ? m.endNodeId : m.startNodeId;
                const otherNode = nodes.find(n => n.id === otherId);
                if (!otherNode) return null;

                const otherPos = Coords.worldToScreen(otherNode.position.x, otherNode.position.y, viewport);
                const dx = otherPos.x - center.x;
                const dy = otherPos.y - center.y;
                const angle = Math.atan2(dy, dx);
                return { angle, dx, dy, length: Math.sqrt(dx * dx + dy * dy) };
            }).filter(Boolean) as { angle: number, dx: number, dy: number, length: number }[];

            memberData.sort((a, b) => a.angle - b.angle);

            ctx.fillStyle = COLORS.member;
            ctx.beginPath();
            ctx.moveTo(center.x, center.y);

            const cornerDist = SIZES.rigidCornerSize;

            for (let i = 0; i < memberData.length; i++) {
                const curr = memberData[i];
                const next = memberData[(i + 1) % memberData.length];

                const p1X = center.x + (curr.dx / curr.length) * cornerDist;
                const p1Y = center.y + (curr.dy / curr.length) * cornerDist;

                const p2X = center.x + (next.dx / next.length) * cornerDist;
                const p2Y = center.y + (next.dy / next.length) * cornerDist;

                ctx.lineTo(p1X, p1Y);
                ctx.lineTo(p2X, p2Y);
            }

            ctx.closePath();
            ctx.fill();
        });
    }

    // --- UPDATED NODE DRAWING ---
    static drawNodeSymbol(
        ctx: CanvasRenderingContext2D,
        node: Node,
        viewport: ViewportState,
        isHovered: boolean,
        state: NodeState | undefined,
        isConnected: boolean
    ) {
        const p = Coords.worldToScreen(node.position.x, node.position.y, viewport);
        const { fixN, fixV, fixM } = node.supports;
        const rotation = node.rotation;

        const isRigid = (val: SupportValue) => val === true;
        const isFree = (val: SupportValue) => val === false;
        const isSpring = (val: SupportValue) => typeof val === 'number';

        let symbolKey: string | null = null;
        let drawRotation = node.rotation;
        let activeColor = isHovered ? COLORS.highlight : COLORS.support;


        // 1. FULLY FIXED (Clamped)
        if (isRigid(fixN) && isRigid(fixV) && isRigid(fixM)) {
            symbolKey = 'FESTE_EINSPANNUNG';
        }
        // 2. PINNED (Hinged Support) - Fixed X/Y, Free Moment
        else if (isRigid(fixN) && isRigid(fixV) && isFree(fixM)) {
            symbolKey = 'FESTLAGER';
        }
        // 3. TORSION SPRING (Pinned XY + Spring M)
        else if (isRigid(fixN) && isRigid(fixV) && isSpring(fixM)) {
            symbolKey = 'TORSIONSFEDER';
        }
        // 4. ROLLER (Loslager) - One direction fixed, one free, moment free
        //    We need to handle X-only or Y-only by rotating the symbol.
        else if (isFree(fixM)) {
            // Case A: Standard Roller (Fix Y, Free X) -> Rotation 0
            if (isRigid(fixV) && isFree(fixN)) {
                symbolKey = 'LOSLAGER';
                // drawRotation stays as node.rotation (usually 0)
            }
            // Case B: Vertically Rolling (Fix X, Free Y) -> Rotation 90
            else if (isRigid(fixN) && isFree(fixV)) {
                symbolKey = 'LOSLAGER';
                drawRotation += 90; // Rotate the roller symbol 90 degrees
            }
            // Case C: Spring Support (Spring Y, Free X)
            else if (isSpring(fixV) && isFree(fixN)) {
                symbolKey = 'FEDER';
            }
            else if (isSpring(fixN) && isFree(fixV)) {
                symbolKey = 'FEDER';
                drawRotation += 90;
            }
        }
        // 5. SLIDER (Gleitlager) - Fixed Rotation + Fixed Transverse, Free Axial
        else if (isRigid(fixM)) {
            // Case A: Horizontal Slider (Fix Y, Fix M, Free X)
            if (isRigid(fixV) && isFree(fixN)) {
                symbolKey = 'GLEITLAGER';
            }
            // Case B: Vertical Slider (Fix X, Fix M, Free Y)
            else if (isRigid(fixN) && isFree(fixV)) {
                symbolKey = 'GLEITLAGER';
                drawRotation += 90;
            }
        }

        if (symbolKey) {
            SymbolRenderer.draw(ctx, symbolKey, p, drawRotation, activeColor);
        }

        // 2. Draw Node Appearance based on State
        if (isConnected && !isHovered) {

            // A. Global Moment Hinge (Hollow Circle)
            if (state === 'GLOBAL_HINGE_MOMENT') {
                SymbolRenderer.draw(ctx, 'VOLLGELENK', p, rotation, COLORS.member);
                //ctx.beginPath();
                //ctx.fillStyle = COLORS.globalHingeFill;
                //ctx.strokeStyle = COLORS.globalHingeStroke;
                //ctx.lineWidth = 2;
                //ctx.arc(p.x, p.y, SIZES.globalHingeRadius, 0, Math.PI * 2);
                //ctx.fill();
                //ctx.stroke();
                return;
            }

            // B. Global Shear Hinge (Single Symbol)
            if (state === 'GLOBAL_HINGE_SHEAR') {
                // Draw the SCHUBGELENK symbol centered at the node
                // Use the node's rotation, or 0 if unrotated
                SymbolRenderer.draw(ctx, 'SCHUBGELENK', p, rotation, COLORS.member);
                return;
            }

            // C. Global Axial Hinge (Single Symbol)
            if (state === 'GLOBAL_HINGE_AXIAL') {
                // Draw NORMALKRAFTGELENK centered
                SymbolRenderer.draw(ctx, 'NORMALKRAFTGELENK', p, rotation, COLORS.member);
                return;
            }

            // Rigid / Mixed -> Hide dot (showing clean corner connection)
            return;
        }

        // 3. Isolated or Hovered -> Draw Blue Dot
        ctx.beginPath();
        ctx.fillStyle = isHovered ? COLORS.highlight : COLORS.node;
        ctx.arc(p.x, p.y, SIZES.nodeRadius, 0, Math.PI * 2);
        ctx.fill();
    }
}
