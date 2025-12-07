/**
 * Draws a Point Load (Einzellast).
 * Arrow points TOWARD the target (x,y).
 */
export function drawStanliPointLoad(ctx, x, y, angleDeg, lengthPx = 40, distancePx = 5) {
    const angleRad = (angleDeg * Math.PI) / 180;

    // In Stanli, the load is often detached slightly from the node (distancePx)
    // Start of arrow (Tip)
    const startX = x + Math.cos(angleRad + Math.PI) * distancePx;
    const startY = y + Math.sin(angleRad + Math.PI) * distancePx;

    // End of arrow (Tail)
    const endX = startX + Math.cos(angleRad + Math.PI) * lengthPx;
    const endY = startY + Math.sin(angleRad + Math.PI) * lengthPx;

    ctx.beginPath();
    ctx.moveTo(endX, endY);
    ctx.lineTo(startX, startY);
    ctx.stroke();

    // Arrowhead is at the start (Tip), pointing towards the node
    // The angle of the shaft is (angleRad + PI), so the arrow points that way.
    drawStanliArrowHead(ctx, startX, startY, angleRad + Math.PI);
}

/**
 * Draws a Moment (Momentenlast).
 * Circular arc with arrow.
 */
export function drawStanliMoment(ctx, x, y, radiusPx = 20, isClockwise = true) {
    const startAngle = 0;
    const endAngle = 1.5 * Math.PI; // 270 degrees

    ctx.beginPath();
    // Arc is drawn from 0 to 270
    ctx.arc(x, y, radiusPx, startAngle, endAngle, false);
    ctx.stroke();

    // Calculate Arrow Position
    // If Clockwise: Arrow at start (0) pointing down/tangent
    // If Counter-Clockwise: Arrow at end (270) pointing tangent

    let arrowX, arrowY, arrowAngle;

    if (isClockwise) {
        // Arrow at Angle 0
        arrowX = x + radiusPx * Math.cos(startAngle);
        arrowY = y + radiusPx * Math.sin(startAngle);
        // Tangent at 0 is PI/2 (90 deg) for CW motion
        arrowAngle = Math.PI / 2;
    } else {
        // For visual distinction, we might flip the arc or just put arrow at the other end.
        // Let's put arrow at the end (270 deg)
        arrowX = x + radiusPx * Math.cos(endAngle);
        arrowY = y + radiusPx * Math.sin(endAngle);
        // Tangent at 270 is 0 (0 deg) for CCW motion
        arrowAngle = 0;
    }

    drawStanliArrowHead(ctx, arrowX, arrowY, arrowAngle);

    // Optional: Draw the center dot or "torque" marker if needed
    ctx.beginPath();
    ctx.arc(x, y, 2, 0, Math.PI * 2);
    ctx.fill();
}

/**
 * Draws a distributed load with optional custom angle.
 * @param {number|null} forceAngleDeg - If set, arrows point in this global angle. If null, perpendicular.
 */
export function drawStanliDistributedLoad(ctx, pStart, pEnd, spacingPx = 15, lengthPx = 30, flip = false, forceAngleDeg = null) {
    const dx = pEnd.x - pStart.x;
    const dy = pEnd.y - pStart.y;
    const beamLength = Math.sqrt(dx * dx + dy * dy);
    if (beamLength < 1) return;

    // Unit vector along beam
    const ux = dx / beamLength;
    const uy = dy / beamLength;

    let nx, ny;

    // --- NEW LOGIC: ANGLE VS PERPENDICULAR ---
    if (forceAngleDeg !== null && forceAngleDeg !== undefined) {
        // CASE A: User specified an angle (e.g., 90 for vertical down)
        // We want the arrow to point in this direction.
        // So the "Tail" (start of arrow) must be opposite to this direction.
        const rad = (forceAngleDeg * Math.PI) / 180;

        // Direction vector of the arrow (Tip - Tail)
        const ax = Math.cos(rad);
        const ay = Math.sin(rad);

        // The Connecting Bar is at the Tail.
        // Tail = Tip - ArrowVector * Length
        // So the "offset" from beam to bar is:
        nx = -ax;
        ny = -ay;

    } else {
        // CASE B: Perpendicular (Default)
        // Standard normal (-uy, ux)
        nx = -uy;
        ny = ux;
        if (flip) {
            nx = -nx;
            ny = -ny;
        }
    }

    // Offset vector for the connecting bar
    const offX = nx * lengthPx;
    const offY = ny * lengthPx;

    // Draw Connecting Bar
    ctx.beginPath();
    ctx.moveTo(pStart.x + offX, pStart.y + offY);
    ctx.lineTo(pEnd.x + offX, pEnd.y + offY);
    ctx.stroke();

    // Draw Arrows
    const count = Math.ceil(beamLength / spacingPx);
    const actualSpacing = beamLength / count;

    for (let i = 0; i <= count; i++) {
        const t = (i * actualSpacing);

        // Tip (on beam)
        const tipX = pStart.x + ux * t;
        const tipY = pStart.y + uy * t;

        // Tail (on bar)
        // Note: For constant angle load, the bar might not be parallel to beam if we just add offset!
        // But Stanli usually keeps bar parallel. 
        // If we want the bar parallel to beam, we just use the fixed offset calculated above.
        const tailX = tipX + offX;
        const tailY = tipY + offY;

        ctx.beginPath();
        ctx.moveTo(tailX, tailY);
        ctx.lineTo(tipX, tipY);
        ctx.stroke();

        const arrowAngle = Math.atan2(tipY - tailY, tipX - tailX);
        drawStanliArrowHead(ctx, tipX, tipY, arrowAngle);
    }
}

/**
 * Helper to draw a standard Stanli-style arrow head
 */
function drawStanliArrowHead(ctx, x, y, angleRad) {
    const headLen = 8; // Size of arrow head
    const headAngle = Math.PI / 6; // 30 degrees spread

    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(
        x - headLen * Math.cos(angleRad - headAngle),
        y - headLen * Math.sin(angleRad - headAngle)
    );
    ctx.lineTo(
        x - headLen * Math.cos(angleRad + headAngle),
        y - headLen * Math.sin(angleRad + headAngle)
    );
    ctx.fillStyle = ctx.strokeStyle; // Match the line color
    ctx.fill();
}
