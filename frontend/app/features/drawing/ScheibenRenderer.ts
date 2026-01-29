import type { Scheibe, Vec2 } from '~/types/model';
import type { ViewportState } from '~/types/app';
import * as Coords from '../../lib/coordinates';

export class ScheibenRenderer {
    /**
     * Draw a Scheibe (rigid plate element)
     */
    static draw(
        ctx: CanvasRenderingContext2D,
        scheibe: Scheibe,
        viewport: ViewportState,
        isActive: boolean,
        isSelected: boolean
    ) {
        const { corner1, corner2, shape, rotation } = scheibe;

        // Convert corners to screen coordinates
        const p1 = Coords.worldToScreen(corner1.x, corner1.y, viewport);
        const p2 = Coords.worldToScreen(corner2.x, corner2.y, viewport);

        // Calculate dimensions
        const width = Math.abs(p2.x - p1.x);
        const height = Math.abs(p2.y - p1.y);
        const centerX = (p1.x + p2.x) / 2;
        const centerY = (p1.y + p2.y) / 2;

        // Don't render if too small 
        if (width < 2 && height < 2) return;

        // Style based on state
        ctx.save();

        if (isActive) {
            // Being created - semi-transparent
            ctx.fillStyle = 'rgba(59, 130, 246, 0.15)';
            ctx.strokeStyle = '#3b82f6';
            ctx.lineWidth = 2;
            ctx.setLineDash([8, 4]);
        } else if (isSelected) {
            // Selected - highlighted
            ctx.fillStyle = 'rgba(96, 165, 250, 0.25)';
            ctx.strokeStyle = '#2563eb';
            ctx.lineWidth = 2.5;
            ctx.setLineDash([]);
        } else {
            // Normal state
            ctx.fillStyle = 'rgba(148, 163, 184, 0.15)';
            ctx.strokeStyle = '#64748b';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([]);
        }

        // Apply rotation around center ← THIS IS CORRECT!
        ctx.translate(centerX, centerY);
        ctx.rotate((rotation * Math.PI) / 180);
        ctx.translate(-centerX, -centerY);

        // Draw based on shape
        switch (shape) {
            case 'rectangle':
                this.drawRectangle(ctx, p1, p2);
                break;
            case 'circle':
                this.drawCircle(ctx, centerX, centerY, Math.max(width, height) / 2);
                break;
            case 'triangle':
                this.drawTriangle(ctx, p1, p2);
                break;
            case 'polygon':
                this.drawPolygon(ctx, scheibe, viewport);
                break;
            default:
                this.drawRectangle(ctx, p1, p2);
        }

        ctx.restore();

        // Draw corner handles if selected (WITHOUT rotation)
        if (isSelected) {
            // Handles should be drawn after restore so they're not rotated
            ctx.save();
            this.drawResizeHandles(ctx, p1, p2, centerX, centerY, rotation);
            ctx.restore();
        }

        // Draw label (WITHOUT rotation)
        //if (!isActive) {
        //    this.drawLabel(ctx, scheibe, centerX, centerY, isSelected);
        //}
    }

    private static drawRectangle(
        ctx: CanvasRenderingContext2D,
        p1: Vec2,
        p2: Vec2
    ) {
        const x = Math.min(p1.x, p2.x);
        const y = Math.min(p1.y, p2.y);
        const width = Math.abs(p2.x - p1.x);
        const height = Math.abs(p2.y - p1.y);

        ctx.fillRect(x, y, width, height);
        ctx.strokeRect(x, y, width, height);
    }

    private static drawCircle(
        ctx: CanvasRenderingContext2D,
        centerX: number,
        centerY: number,
        radius: number
    ) {
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
    }

    private static drawTriangle(
        ctx: CanvasRenderingContext2D,
        p1: Vec2,
        p2: Vec2
    ) {
        const x1 = Math.min(p1.x, p2.x);
        const x2 = Math.max(p1.x, p2.x);
        const y1 = Math.min(p1.y, p2.y);
        const y2 = Math.max(p1.y, p2.y);
        const centerX = (x1 + x2) / 2;

        ctx.beginPath();
        ctx.moveTo(centerX, y1); // Top point
        ctx.lineTo(x1, y2);       // Bottom left
        ctx.lineTo(x2, y2);       // Bottom right
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
    }

    private static drawPolygon(
        ctx: CanvasRenderingContext2D,
        scheibe: Scheibe,
        viewport: ViewportState
    ) {
        if (!scheibe.additionalPoints || scheibe.additionalPoints.length < 3) {
            // Fallback to rectangle if not enough points
            const p1 = Coords.worldToScreen(scheibe.corner1.x, scheibe.corner1.y, viewport);
            const p2 = Coords.worldToScreen(scheibe.corner2.x, scheibe.corner2.y, viewport);
            this.drawRectangle(ctx, p1, p2);
            return;
        }

        ctx.beginPath();
        const firstPoint = Coords.worldToScreen(scheibe.additionalPoints[0].x, scheibe.additionalPoints[0].y, viewport);
        ctx.moveTo(firstPoint.x, firstPoint.y);

        for (let i = 1; i < scheibe.additionalPoints.length; i++) {
            const point = Coords.worldToScreen(scheibe.additionalPoints[i].x, scheibe.additionalPoints[i].y, viewport);
            ctx.lineTo(point.x, point.y);
        }

        ctx.closePath();
        ctx.fill();
        ctx.stroke();
    }

    private static drawResizeHandles(
        ctx: CanvasRenderingContext2D,
        p1: Vec2,
        p2: Vec2,
        centerX: number,
        centerY: number,
        rotation: number  // ← Add rotation parameter
    ) {
        const handleSize = 6;

        // Calculate handle positions in local space (before rotation)
        const localHandles = [
            { x: Math.min(p1.x, p2.x), y: Math.min(p1.y, p2.y) },           // Top-left
            { x: Math.max(p1.x, p2.x), y: Math.min(p1.y, p2.y) },           // Top-right
            { x: Math.max(p1.x, p2.x), y: Math.max(p1.y, p2.y) },           // Bottom-right
            { x: Math.min(p1.x, p2.x), y: Math.max(p1.y, p2.y) },           // Bottom-left
        ];

        // Rotate handles
        const angleRad = (rotation * Math.PI) / 180;
        const cos_a = Math.cos(angleRad);
        const sin_a = Math.sin(angleRad);

        const rotatedHandles = localHandles.map(handle => {
            const dx = handle.x - centerX;
            const dy = handle.y - centerY;
            return {
                x: centerX + (dx * cos_a - dy * sin_a),
                y: centerY + (dx * sin_a + dy * cos_a)
            };
        });

        ctx.fillStyle = '#ffffff';
        ctx.strokeStyle = '#2563eb';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([]);

        rotatedHandles.forEach(handle => {
            ctx.fillRect(
                handle.x - handleSize / 2,
                handle.y - handleSize / 2,
                handleSize,
                handleSize
            );
            ctx.strokeRect(
                handle.x - handleSize / 2,
                handle.y - handleSize / 2,
                handleSize,
                handleSize
            );
        });
    }

    private static drawLabel(
        ctx: CanvasRenderingContext2D,
        scheibe: Scheibe,
        centerX: number,
        centerY: number,
        isSelected: boolean
    ) {
        // Calculate dimensions in world units
        const width = Math.abs(scheibe.corner2.x - scheibe.corner1.x);
        const height = Math.abs(scheibe.corner2.y - scheibe.corner1.y);

        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0); // Reset all transforms for text

        ctx.font = '11px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const label = `${width.toFixed(2)} × ${height.toFixed(2)} m`;

        // Background
        const textMetrics = ctx.measureText(label);
        const padding = 6;
        const bgWidth = textMetrics.width + padding * 2;
        const bgHeight = 18;

        ctx.fillStyle = isSelected ? 'rgba(37, 99, 235, 0.9)' : 'rgba(71, 85, 105, 0.9)';
        ctx.fillRect(
            centerX - bgWidth / 2,
            centerY - bgHeight / 2,
            bgWidth,
            bgHeight
        );

        // Text
        ctx.fillStyle = '#ffffff';
        ctx.fillText(label, centerX, centerY);

        ctx.restore();
    }
}
