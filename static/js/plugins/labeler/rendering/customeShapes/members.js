/**
 * Draws a structural member in the style of Stanli.
 * 
 * @param {CanvasRenderingContext2D} ctx 
 * @param {Object} p1 - Start point {x, y}
 * @param {Object} p2 - End point {x, y}
 * @param {string} type - 'normal', 'fiber', 'truss', 'hidden'
 */
export function drawStanliMember(ctx, p1, p2, type = 'normal') {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const length = Math.sqrt(dx * dx + dy * dy);

    // Style Configuration
    let lineWidth = 4;        // Default (Normal Beam)
    let strokeStyle = '#334155';
    let lineDash = [];

    switch (type) {
        case 'fiber': // Biegung mit Faser (Thickest + Fiber line)
            lineWidth = 6;
            break;

        case 'normal': // Standard Beam (Thick)
            lineWidth = 4;
            break;

        case 'truss': // Fachwerk (Thinner / Standard Line)
            lineWidth = 2;
            break;

        case 'hidden': // Versteckt (Thinnest + Dashed)
            lineWidth = 1;
            lineDash = [5, 5];
            strokeStyle = '#94a3b8'; // Lighter color
            break;

        default:
            lineWidth = 4;
            break;
    }

    ctx.save();
    ctx.beginPath();
    ctx.lineWidth = lineWidth;
    ctx.strokeStyle = strokeStyle;
    ctx.setLineDash(lineDash);
    ctx.lineCap = 'round';

    // Draw Main Line
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();

    // Draw Fiber Line (only for fiber type)
    if (type === 'fiber') {
        drawFiberLine(ctx, p1, p2, dx, dy, length);
    }

    ctx.restore();
}

/**
 * Helper to draw the dashed "Fiber" line offset from the main beam.
 */
function drawFiberLine(ctx, p1, p2, dx, dy, length) {
    const fiberGap = 8; // Offset from center

    // Normal Vector
    const nx = -dy / length;
    const ny = dx / length;

    // Offset coordinates
    const f1x = p1.x + nx * fiberGap;
    const f1y = p1.y + ny * fiberGap;
    const f2x = p2.x + nx * fiberGap;
    const f2y = p2.y + ny * fiberGap;

    ctx.beginPath();
    ctx.lineWidth = 1;
    ctx.strokeStyle = '#334155';
    ctx.setLineDash([4, 4]);
    ctx.moveTo(f1x, f1y);
    ctx.lineTo(f2x, f2y);
    ctx.stroke();
}
