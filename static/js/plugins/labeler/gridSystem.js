export const GridSystem = {
    // Configuration
    canvasScaleFactor: 20.0,
    originOffsetGrids: 2.0, // Number of grid squares from bottom-left to origin

    /**
     * Converts Pixel Coordinates to Real Coordinates (Meters)
     */
    toReal: (pixelX, pixelY, canvas, gridSizeReal) => {
        const totalRealWidth = GridSystem.canvasScaleFactor * gridSizeReal;
        const aspectRatio = canvas.height / canvas.width;
        const totalRealHeight = totalRealWidth * aspectRatio;

        // Apply offset so (0,0) is not at corner
        const offsetReal = GridSystem.originOffsetGrids * gridSizeReal;

        return {
            x: (pixelX / canvas.width) * totalRealWidth - offsetReal,
            y: (1.0 - (pixelY / canvas.height)) * totalRealHeight - offsetReal
        };
    },

    /**
     * Converts Real Coordinates (Meters) to Pixel Coordinates
     */
    toPixel: (realX, realY, canvas, gridSizeReal) => {
        const totalRealWidth = GridSystem.canvasScaleFactor * gridSizeReal;
        const aspectRatio = canvas.height / canvas.width;
        const totalRealHeight = totalRealWidth * aspectRatio;

        const offsetReal = GridSystem.originOffsetGrids * gridSizeReal;

        return {
            x: ((realX + offsetReal) / totalRealWidth) * canvas.width,
            y: (1.0 - ((realY + offsetReal) / totalRealHeight)) * canvas.height
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
        const offsetReal = GridSystem.originOffsetGrids * gridSizeReal;

        // Vertical Lines
        const startX = -offsetReal;
        const endX = totalRealWidth - offsetReal;
        for (let x = Math.floor(startX / gridSizeReal) * gridSizeReal; x <= endX; x += gridSizeReal) {
            const p = GridSystem.toPixel(x, 0, canvas, gridSizeReal);
            ctx.beginPath();
            ctx.moveTo(p.x, 0);
            ctx.lineTo(p.x, canvas.height);
            ctx.stroke();
        }

        // Horizontal Lines
        const startY = -offsetReal;
        const endY = totalRealHeight - offsetReal;
        for (let y = Math.floor(startY / gridSizeReal) * gridSizeReal; y <= endY; y += gridSizeReal) {
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
        ctx.font = '12px monospace';
        ctx.fillText("(0,0)", pOrigin.x + 5, pOrigin.y - 5);
    }
};
