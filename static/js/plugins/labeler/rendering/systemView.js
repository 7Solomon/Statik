import { getSymbolImage } from './assets.js';
import { COLORS } from './shapes.js';

const BODY_COLORS = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899'];
let SYMBOL_DEFINITIONS = {};

export function setSystemViewDefinitions(defs) {
    SYMBOL_DEFINITIONS = defs;
}

export function renderSystemView(ctx, canvas, state) {
    const { width, height } = canvas;
    const { systemData, view, animationTime, isMechanism } = state;

    // 1. Clear & Setup
    ctx.clearRect(0, 0, width, height);

    if (!systemData) return;

    ctx.save(); // Save untransformed state

    // 2. Apply View Transform (Pan & Zoom)
    // We move origin to the pan location
    ctx.translate(view.panX, view.panY);
    // We Scale Zoom. 
    // CRITICAL: Scale Y by -1 to flip coordinate system so +Y is UP.
    ctx.scale(view.zoom, -view.zoom);

    // 3. Calculate Animation Factor
    const animFactor = isMechanism ? Math.sin(animationTime * 3) : 0;
    const amp = (state.amplitude !== undefined) ? state.amplitude : 0.5;

    // Helper: Transform grid coord (x,y) to pixel coord (in Transformed Space)
    // Since we flipped Y with scale(1, -1), we can just use normal (x,y).
    // Inside renderSystemView function...

    const getDeformedPos = (node) => {
        const scale = 100;
        const px = node.x * scale;
        const py = node.y * scale;

        // 0. Default: Return original position (STATIC)
        // This ensures stationary parts are always drawn
        const defaultPos = { x: px, y: py, ox: px, oy: py, rotation: 0 };

        // Check if we have velocity data at all for this node
        let v = state.nodeVelocities[node.id];

        // If no velocity or effectively zero velocity, return static position
        if (!v || (Math.abs(v[0]) < 1e-6 && Math.abs(v[1]) < 1e-6)) {
            return defaultPos;
        }

        // 1. Find Rigid Body for ROTATION Logic
        const rb = state.rigidBodies.find(b => {
            return b.member_ids.some(mid => {
                const m = state.systemData.members.find(mem => mem.id === mid);
                return m && (m.startNodeId === node.id || m.endNodeId === node.id);
            });
        });

        // 2. Linear Fallback (Translation or unknown body)
        if (!rb || rb.movement_type === 'translation' || !rb.center_or_vector) {
            const dx = v[0] * scale * amp * animFactor;
            const dy = v[1] * scale * amp * animFactor;
            return { x: px + dx, y: py + dy, ox: px, oy: py, rotation: 0 };
        }

        // 3. Rotational Physics (The Arc)
        const center = rb.center_or_vector;
        const cx = center[0] * scale;
        const cy = center[1] * scale;

        const rx = px - cx;
        const ry = py - cy;
        const radius = Math.sqrt(rx * rx + ry * ry);

        // Safety check: if radius is tiny (node is ON the rotation center), it doesn't move
        if (radius < 0.1) return defaultPos;

        const currentAngle = Math.atan2(ry, rx);

        // Calculate omega
        const vMag = Math.sqrt(v[0] * v[0] + v[1] * v[1]);
        const cross = rx * v[1] - ry * v[0];
        const direction = cross > 0 ? 1 : -1;

        // Calculate angle delta
        const angleDelta = (vMag / (radius / scale)) * amp * animFactor * direction;

        return {
            x: cx + radius * Math.cos(currentAngle + angleDelta),
            y: cy + radius * Math.sin(currentAngle + angleDelta),
            ox: px,
            oy: py,
            rotation: angleDelta
        };
    };


    // --- DRAW ORIGIN (Coordinate System) ---
    // Note: Since Y is flipped, drawing "down" means negative Y in local coords
    ctx.save();
    ctx.lineWidth = 2 / view.zoom;
    ctx.strokeStyle = '#94a3b8';

    // X-Axis
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(50, 0);
    ctx.stroke();

    // Y-Axis (draws "up" in world space)
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(0, 50);
    ctx.stroke();

    // Origin Dot
    ctx.beginPath();
    ctx.arc(0, 0, 3 / view.zoom, 0, Math.PI * 2);
    ctx.fillStyle = '#64748b';
    ctx.fill();
    ctx.restore();

    // --- DRAW MEMBERS (unchanged logic but using systemData and getDeformedPos) ---
    const bodyColorMap = {};
    if (state.rigidBodies) {
        state.rigidBodies.forEach((rb, i) => {
            const color = BODY_COLORS[i % BODY_COLORS.length];
            rb.member_ids.forEach(mid => bodyColorMap[mid] = color);
        });
    }

    systemData.members.forEach(m => {
        const n1 = systemData.nodes.find(n => n.id == m.startNodeId);
        const n2 = systemData.nodes.find(n => n.id == m.endNodeId);
        if (!n1 || !n2) return;

        const p1 = getDeformedPos(n1);
        const p2 = getDeformedPos(n2);

        // Draw Deformed State
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.strokeStyle = bodyColorMap[m.id] || '#334155';
        ctx.lineWidth = 4; // visual width (in world-space units)
        ctx.lineCap = 'round';
        ctx.stroke();

        // Draw Ghost (Original) State for mechanisms
        if (isMechanism) {
            ctx.beginPath();
            ctx.moveTo(p1.ox, p1.oy);
            ctx.lineTo(p2.ox, p2.oy);
            ctx.strokeStyle = '#cbd5e1';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            ctx.stroke();
            ctx.setLineDash([]);
        }
    });

    // --- DRAW NODES & SYMBOLS (images must be un-flipped locally) ---
    systemData.nodes.forEach(n => {
        const p = getDeformedPos(n);

        const symbolType = n.symbolType || n._visual_type || 'none';
        const rotation = (n.rotation !== undefined) ? n.rotation : (n._visual_rotation || 0);

        // Draw Symbol
        if (symbolType && symbolType !== 'none' && SYMBOL_DEFINITIONS[symbolType]) {
            const def = SYMBOL_DEFINITIONS[symbolType];
            const img = getSymbolImage(symbolType, rotation, () => { /* optional re-render callback */ });

            if (img.complete && img.naturalWidth > 0) {
                const baseScale = 0.8;
                const finalScale = baseScale / view.zoom;

                const anchorX = def.anchor ? def.anchor[0] : 50;
                const anchorY = def.anchor ? def.anchor[1] : 50;

                // Un-flip image locally: translate to position, flip Y, draw centered
                ctx.save();
                ctx.translate(p.x, p.y);
                ctx.scale(1, -1); // UN-FLIP Image so it appears upright after world flip
                ctx.drawImage(
                    img,
                    -anchorX * finalScale,
                    -anchorY * finalScale,
                    img.width * finalScale,
                    img.height * finalScale
                );
                ctx.restore();
            }
        }

        // Draw Node Dot (circle is symmetric so flip doesn't affect appearance)
        ctx.beginPath();
        ctx.arc(p.x, p.y, 6 / view.zoom, 0, Math.PI * 2);
        ctx.fillStyle = COLORS.node;
        ctx.fill();
    });

    ctx.restore();
}
