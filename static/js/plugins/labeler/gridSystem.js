export const GridSystem = {
    // Configuration
    canvasScaleFactor: 10.0, // Canvas is always 10 * L wide

    /**
     * Converts Pixel Coordinates to Real Coordinates (Meters)
     */
    toReal: (pixelX, pixelY, canvas, gridSizeReal) => {
        const totalRealWidth = GridSystem.canvasScaleFactor * gridSizeReal;
        const aspectRatio = canvas.height / canvas.width;
        const totalRealHeight = totalRealWidth * aspectRatio;

        return {
            x: (pixelX / canvas.width) * totalRealWidth,
            y: (1.0 - (pixelY / canvas.height)) * totalRealHeight // Invert Y
        };
    },

    /**
     * Converts Real Coordinates (Meters) to Pixel Coordinates
     */
    toPixel: (realX, realY, canvas, gridSizeReal) => {
        const totalRealWidth = GridSystem.canvasScaleFactor * gridSizeReal;
        const aspectRatio = canvas.height / canvas.width;
        const totalRealHeight = totalRealWidth * aspectRatio;

        return {
            x: (realX / totalRealWidth) * canvas.width,
            y: (1.0 - (realY / totalRealHeight)) * canvas.height // Invert Y back
        };
    },

    /**
     * Draws the grid lines and axes
     */
    draw: (ctx, canvas, gridSizeReal, colors) => {
        if (!ctx) return;

        ctx.lineWidth = 1;
        ctx.strokeStyle = colors.grid;

        const totalRealWidth = GridSystem.canvasScaleFactor * gridSizeReal;
        const aspectRatio = canvas.height / canvas.width;
        const totalRealHeight = totalRealWidth * aspectRatio;

        // Vertical Lines
        for (let x = 0; x <= totalRealWidth + 0.1; x += gridSizeReal) {
            const p = GridSystem.toPixel(x, 0, canvas, gridSizeReal);
            ctx.beginPath();
            ctx.moveTo(p.x, 0);
            ctx.lineTo(p.x, canvas.height);
            ctx.stroke();
        }

        // Horizontal Lines
        for (let y = 0; y <= totalRealHeight + 0.1; y += gridSizeReal) {
            const p = GridSystem.toPixel(0, y, canvas, gridSizeReal);
            ctx.beginPath();
            ctx.moveTo(0, p.y);
            ctx.lineTo(canvas.width, p.y);
            ctx.stroke();
        }

        // Axes
        ctx.strokeStyle = colors.axis;
        ctx.lineWidth = 2;
        const pOrigin = GridSystem.toPixel(0, 0, canvas, gridSizeReal);

        // Y Axis
        ctx.beginPath();
        ctx.moveTo(pOrigin.x, 0);
        ctx.lineTo(pOrigin.x, canvas.height);
        ctx.stroke();

        // X Axis
        ctx.beginPath();
        ctx.moveTo(0, pOrigin.y);
        ctx.lineTo(canvas.width, pOrigin.y);
        ctx.stroke();

        ctx.fillStyle = colors.axis;
        ctx.font = '10px monospace';
        ctx.fillText("(0,0)", pOrigin.x + 5, pOrigin.y - 5);
    }
};
