import supportLibraryRaw from '~/assets/support_symbols.json';
import hingeLibraryRaw from '~/assets/hinge_symbols.json';
import type { Vec2 } from '~/types/model';

// 1. Define Types
type SymbolOp = {
    d: string;
    type: 'stroke' | 'fill';
    width?: number;
    color?: string;
};

type CachedSymbol = {
    path: Path2D;
    type: 'stroke' | 'fill';
    width: number;
    color: string | null;
}[];

// 2. Merge libraries into one lookup object
// We cast them to 'any' or a specific Record type because JSON imports 
// are treated as specific shapes by TS, which can be annoying to iterate over.
const RAW_LIBRARIES = {
    ...supportLibraryRaw,
    ...hingeLibraryRaw
} as Record<string, SymbolOp[]>;

// 3. Initialize Cache
const SYMBOL_CACHE: Record<string, CachedSymbol> = {};

if (typeof window !== 'undefined' && typeof Path2D !== 'undefined') {
    Object.entries(RAW_LIBRARIES).forEach(([key, ops]) => {
        SYMBOL_CACHE[key] = ops.map((op) => ({
            path: new Path2D(op.d),
            type: op.type,
            width: op.width || 1,
            color: op.color || null,
        }));
    });
}

export class SymbolRenderer {
    /**
     * Draws a symbol from the library at the specified position and rotation.
     * @param ctx Canvas Context
     * @param symbolName Key from stanli_paths.json (e.g., 'SUPPORT_FESTLAGER')
     * @param pos Screen position {x, y}
     * @param rotationDeg Rotation in degrees
     * @param overrideColor Optional: Force a specific color (e.g. for selection highlight)
     */
    static draw(
        ctx: CanvasRenderingContext2D,
        symbolName: string,
        pos: Vec2,
        rotationDeg: number = 0,
        overrideColor: string | null = null
    ) {
        const operations = SYMBOL_CACHE[symbolName];
        if (!operations) {
            // Fail silently or warn once to avoid console spam loop
            return;
        }

        ctx.save();

        // 1. Transform coordinates to the node position
        ctx.translate(pos.x, pos.y);
        ctx.rotate((rotationDeg * Math.PI) / 180);

        // 2. Execute drawing operations
        operations.forEach((op) => {
            // Determine color: Override -> Op defined (e.g. white fill) -> Default Black
            const color = overrideColor || op.color || '#334155'; // Slate-700 default

            if (op.type === 'fill') {
                ctx.fillStyle = color;
                ctx.fill(op.path);
            } else {
                ctx.strokeStyle = color;
                ctx.lineWidth = op.width;
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';
                ctx.stroke(op.path);
            }
        });

        ctx.restore();
    }
}
