import type { ViewportState } from "~/types/app";
import type { Vec2 } from "~/types/model";

/**
 * Converts Screen Pixels (Mouse Event) -> World Meters (Physics)
 */
export function screenToWorld(
    screenX: number,
    screenY: number,
    viewport: ViewportState,
    canvasHeight: number // Needed because Y is inverted in Engineering
): Vec2 {
    // 1. Remove Pan
    const x = screenX - viewport.pan.x;
    const y = screenY - viewport.pan.y;

    // 2. Scale down (Pixels -> Meters)
    const worldX = x / viewport.zoom;

    // 3. Invert Y (Screen Y goes down, Engineering Y goes up)
    // We assume the pan acts as the origin point visually
    const worldY = -(y / viewport.zoom);

    return { x: worldX, y: worldY };
}

/**
 * Converts World Meters -> Screen Pixels (For Rendering)
 */
export function worldToScreen(
    worldX: number,
    worldY: number,
    viewport: ViewportState
): Vec2 {
    // 1. Scale up (Meters -> Pixels)
    const x = worldX * viewport.zoom;
    const y = -worldY * viewport.zoom; // Invert Y back

    // 2. Add Pan
    return {
        x: x + viewport.pan.x,
        y: y + viewport.pan.y
    };
}
