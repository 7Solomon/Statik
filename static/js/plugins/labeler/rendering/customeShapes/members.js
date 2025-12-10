import { getSymbolImage } from '../assets.js'; // Adjust path if necessary

/**
 * Draws a structural member in the style of Stanli.
 * 
 * @param {CanvasRenderingContext2D} ctx
 * @param {Object} p1 - Start point {x, y}
 * @param {Object} p2 - End point {x, y}
 * @param {string} type - 'normal', 'fiber', 'truss', 'hidden'
 * @param {Object} releases - { start: { category: string }, end: { category: string } }
 */
export function drawStanliMember(ctx, p1, p2, type = 'normal', releases = { start: {}, end: {} }) {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const length = Math.sqrt(dx * dx + dy * dy);
    const memberAngle = Math.atan2(dy, dx);

    // Style Configuration
    let lineWidth = 4;
    let strokeStyle = '#334155';
    let lineDash = [];

    switch (type) {
        case 'fiber': lineWidth = 6; break;
        case 'normal': lineWidth = 4; break;
        case 'truss': lineWidth = 2; break;
        case 'hidden':
            lineWidth = 1;
            lineDash = [5, 5];
            strokeStyle = '#94a3b8';
            break;
    }

    // Determine offsets to prevent line from overlapping symbols
    // 'vollgelenk' typically needs a gap (previous logic used 6px)
    // You can adjust this based on specific categories if needed, or apply generically
    const startHasSymbol = releases.start && releases.start.category;
    const endHasSymbol = releases.end && releases.end.category;

    const startOffset = startHasSymbol ? 6 : 0;
    const endOffset = endHasSymbol ? 6 : 0;

    // Calculate actual start/end points for the line
    const cos = Math.cos(memberAngle);
    const sin = Math.sin(memberAngle);

    const drawStart = {
        x: p1.x + startOffset * cos,
        y: p1.y + startOffset * sin
    };

    const drawEnd = {
        x: p2.x - endOffset * cos,
        y: p2.y - endOffset * sin
    };

    ctx.save();
    ctx.beginPath();
    ctx.lineWidth = lineWidth;
    ctx.strokeStyle = strokeStyle;
    ctx.setLineDash(lineDash);
    ctx.lineCap = 'round';

    // 1. Draw Main Line
    ctx.moveTo(drawStart.x, drawStart.y);
    ctx.lineTo(drawEnd.x, drawEnd.y);
    ctx.stroke();

    // 2. Draw Fiber Line (if needed)
    if (type === 'fiber') {
        drawFiberLine(ctx, p1, p2, dx, dy, length);
    }

    // 3. Draw Release Symbols based on Category
    if (startHasSymbol) {
        drawReleaseSymbol(ctx, p1, releases.start.category, memberAngle);
    }

    if (endHasSymbol) {
        // For the end point, we rotate 180 degrees (Math.PI) so the symbol faces 'inwards' 
        // or aligns correctly with the member direction ending here.
        drawReleaseSymbol(ctx, p2, releases.end.category, memberAngle + Math.PI);
    }

    ctx.restore();
}

/**
 * Helper to draw a symbol image from the API based on category.
 * Uses canvas rotation to align the symbol with the member.
 */
function drawReleaseSymbol(ctx, pos, category, rotationRad) {
    // 0 passes 0 rotation to the API/cache key, we handle rotation in canvas
    console.log(category)
    const img = getSymbolImage(category, 0);

    if (!img || !img.complete || img.naturalWidth === 0) return;

    ctx.save();
    ctx.translate(pos.x, pos.y);
    ctx.rotate(rotationRad);

    // Scale configuration
    // The images are 100x100. Supports are usually drawn at scale 0.5 (50px).
    // Hinges on members should typically be smaller. 
    // Scale 0.15 gives a 15px symbol (approx radius 7.5), close to the original radius 5 circle.
    const scale = 0.15;
    const anchorX = 50; // Center of 100x100 image
    const anchorY = 50;

    ctx.drawImage(
        img,
        -anchorX * scale,
        -anchorY * scale,
        img.width * scale,
        img.height * scale
    );

    ctx.restore();
}

/**
 * Helper to draw the dashed "Fiber" line
 */
function drawFiberLine(ctx, p1, p2, dx, dy, length) {
    const fiberGap = 8;
    const nx = -dy / length;
    const ny = dx / length;

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
