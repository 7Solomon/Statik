import { useCallback, useRef, useState } from 'react';
import {
    boundsOf, centroid, rectCorners, resizeCorners, rotateCorners, translateCorners,
    type Corner, type LabelBox,
} from './useLabeling';

/** Distinct hues per class id, so a mislabelled box is visible at a glance. */
export const CLASS_COLORS = [
    '#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6',
    '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16', '#0ea5e9',
];

export const classColor = (id: number) => CLASS_COLORS[id % CLASS_COLORS.length];

/** Below this (as a fraction of the image) a drag is a mis-click, not a box. */
const MIN_SIZE = 0.004;

interface Props {
    url: string;
    boxes: LabelBox[];
    classes: string[];
    selected: number | null;
    activeClass: number;
    onSelect: (index: number | null) => void;
    onAdd: (corners: Corner[]) => void;
    onReplace: (index: number, corners: Corner[]) => void;
    /** Reports the displayed aspect ratio so rotation stays rigid. */
    onAspect: (aspect: number) => void;
}

type Drag =
    | { mode: 'create'; x0: number; y0: number; x1: number; y1: number }
    | { mode: 'move'; index: number; start: Corner[]; from: Corner }
    | { mode: 'resize'; index: number; handle: number; start: Corner[] }
    | { mode: 'rotate'; index: number; start: Corner[]; from: number };

/** Rough cursor per corner. Exact at 0 degrees, and rotation is small in practice. */
const CORNER_CURSOR = ['nwse-resize', 'nesw-resize', 'nwse-resize', 'nesw-resize'];

export default function LabelingCanvas({
    url, boxes, classes, selected, activeClass, onSelect, onAdd, onReplace, onAspect,
}: Props) {
    const surfaceRef = useRef<HTMLDivElement>(null);
    const [drag, setDrag] = useState<Drag | null>(null);

    const rect = () => surfaceRef.current?.getBoundingClientRect() ?? null;
    const aspect = () => {
        const r = rect();
        return r && r.height > 0 ? r.width / r.height : 1;
    };

    /** Pointer position as a fraction of the image, clamped to its edges. */
    const toLocal = useCallback((e: React.PointerEvent): Corner | null => {
        const r = rect();
        if (!r || !r.width || !r.height) return null;
        return [
            Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)),
            Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)),
        ];
    }, []);

    /** Angle of the pointer about a box centre, in display units. */
    const angleAbout = useCallback((p: Corner, centre: Corner) => {
        return Math.atan2(p[1] - centre[1], (p[0] - centre[0]) * aspect());
    }, []);

    // --- gestures --------------------------------------------------------

    const onPointerDown = useCallback((e: React.PointerEvent) => {
        if (e.button !== 0) return;
        const p = toLocal(e);
        if (!p) return;
        // Starting a drag on empty space also clears the selection, so the
        // class palette stops retargeting a box the user has moved on from.
        onSelect(null);
        e.currentTarget.setPointerCapture(e.pointerId);
        setDrag({ mode: 'create', x0: p[0], y0: p[1], x1: p[0], y1: p[1] });
    }, [toLocal, onSelect]);

    /** Press on a box: select it, and arm a move in the same gesture.
     *  A press with no movement translates by zero, so it reads as a plain click. */
    const startMove = useCallback((e: React.PointerEvent, index: number) => {
        if (e.button !== 0) return;
        e.stopPropagation();
        const p = toLocal(e);
        if (!p) return;
        onSelect(index);
        (e.currentTarget as Element).setPointerCapture(e.pointerId);
        setDrag({ mode: 'move', index, start: boxes[index].corners, from: p });
    }, [boxes, toLocal, onSelect]);

    const startResize = useCallback((e: React.PointerEvent, index: number, handle: number) => {
        if (e.button !== 0) return;
        e.stopPropagation();
        (e.currentTarget as Element).setPointerCapture(e.pointerId);
        setDrag({ mode: 'resize', index, handle, start: boxes[index].corners });
    }, [boxes]);

    const startRotate = useCallback((e: React.PointerEvent, index: number) => {
        if (e.button !== 0) return;
        e.stopPropagation();
        const p = toLocal(e);
        if (!p) return;
        (e.currentTarget as Element).setPointerCapture(e.pointerId);
        const start = boxes[index].corners;
        setDrag({ mode: 'rotate', index, start, from: angleAbout(p, centroid(start)) });
    }, [boxes, toLocal, angleAbout]);

    const onPointerMove = useCallback((e: React.PointerEvent) => {
        if (!drag) return;
        const p = toLocal(e);
        if (!p) return;
        if (drag.mode === 'create') {
            setDrag({ ...drag, x1: p[0], y1: p[1] });
        } else if (drag.mode === 'move') {
            // Always measured from the gesture's own start, never accumulated
            // frame to frame, so a fast drag cannot drift off the pointer.
            onReplace(drag.index,
                translateCorners(drag.start, p[0] - drag.from[0], p[1] - drag.from[1]));
        } else if (drag.mode === 'resize') {
            onReplace(drag.index, resizeCorners(drag.start, drag.handle, p, aspect()));
        } else {
            const delta = angleAbout(p, centroid(drag.start)) - drag.from;
            onReplace(drag.index, rotateCorners(drag.start, delta, aspect()));
        }
    }, [drag, toLocal, angleAbout, onReplace]);

    const onPointerUp = useCallback(() => {
        if (drag?.mode === 'create') {
            const w = Math.abs(drag.x1 - drag.x0);
            const h = Math.abs(drag.y1 - drag.y0);
            if (w >= MIN_SIZE && h >= MIN_SIZE) {
                onAdd(rectCorners(drag.x0, drag.y0, drag.x1, drag.y1));
            }
        }
        setDrag(null);
    }, [drag, onAdd]);

    /** Where the rotate grip goes: off the first edge, along the outward normal. */
    const rotateHandle = useCallback((cs: Corner[]): Corner => {
        const a = aspect();
        const mid: Corner = [(cs[0][0] + cs[1][0]) / 2, (cs[0][1] + cs[1][1]) / 2];
        const opp: Corner = [(cs[3][0] + cs[2][0]) / 2, (cs[3][1] + cs[2][1]) / 2];
        const dx = (mid[0] - opp[0]) * a;
        const dy = mid[1] - opp[1];
        const len = Math.hypot(dx, dy) || 1;
        const off = 0.05;  // of the image height
        return [mid[0] + (dx / len) * off / a, mid[1] + (dy / len) * off];
    }, []);

    const pct = (v: number) => `${v * 100}%`;
    const points = (cs: Corner[]) => cs.map(c => `${c[0] * 100},${c[1] * 100}`).join(' ');

    return (
        <div className="relative inline-block shadow-lg bg-white border border-slate-200 max-w-full">
            <img
                src={url}
                alt="Harvested figure"
                className="block max-h-[58vh] max-w-full object-contain select-none"
                draggable={false}
                onLoad={() => onAspect(aspect())}
            />

            <div
                ref={surfaceRef}
                className="absolute inset-0 cursor-crosshair touch-none"
                onPointerDown={onPointerDown}
                onPointerMove={onPointerMove}
                onPointerUp={onPointerUp}
                onPointerCancel={() => setDrag(null)}
            >
                {/* preserveAspectRatio="none" lets the 0-100 viewBox map straight
                    onto the image box, so polygon points are just percentages.
                    The polygons themselves are the hit targets: an enclosing
                    rectangle would swallow clicks in the empty corners around a
                    turned box, and a long diagonal one would block most of the
                    image from ever receiving a new box. */}
                <svg
                    className="absolute inset-0 w-full h-full pointer-events-none"
                    viewBox="0 0 100 100"
                    preserveAspectRatio="none"
                >
                    {boxes.map((b, i) => (
                        <polygon
                            key={i}
                            points={points(b.corners)}
                            fill={classColor(b.class_id)}
                            fillOpacity={selected === i ? 0.3 : 0.14}
                            stroke={classColor(b.class_id)}
                            strokeWidth={selected === i ? 0.6 : 0.35}
                            vectorEffect="non-scaling-stroke"
                            style={{ pointerEvents: 'auto', cursor: 'move' }}
                            onPointerDown={(e) => startMove(e, i)}
                            onPointerMove={onPointerMove}
                            onPointerUp={onPointerUp}
                        />
                    ))}
                    {drag?.mode === 'create' && (
                        <polygon
                            points={points(rectCorners(drag.x0, drag.y0, drag.x1, drag.y1))}
                            fill={classColor(activeClass)}
                            fillOpacity={0.18}
                            stroke={classColor(activeClass)}
                            strokeWidth={0.4}
                            strokeDasharray="1 1"
                            vectorEffect="non-scaling-stroke"
                        />
                    )}
                </svg>

                {/* Class names and the rotate handle sit above the polygons. */}
                {boxes.map((b, i) => {
                    const bounds = boundsOf(b.corners);
                    return (
                        <div key={i}>
                            <span
                                className="absolute text-[10px] font-bold px-1 rounded text-white
                                           whitespace-nowrap pointer-events-none -translate-y-full"
                                style={{
                                    left: pct(bounds.x0), top: pct(bounds.y0),
                                    background: classColor(b.class_id),
                                }}
                            >
                                {classes[b.class_id] ?? b.class_id}
                            </span>
                            {selected === i && (
                                <>
                                    {/* Corner handles. They ride the corners, so
                                        they stay in the right place once the box
                                        is turned. */}
                                    {b.corners.map((c, k) => (
                                        <div
                                            key={k}
                                            onPointerDown={(e) => startResize(e, i, k)}
                                            onPointerMove={onPointerMove}
                                            onPointerUp={onPointerUp}
                                            title="Drag to resize"
                                            className="absolute w-2.5 h-2.5 -ml-[5px] -mt-[5px]
                                                       bg-white border-2 rounded-[2px]"
                                            style={{
                                                left: pct(c[0]), top: pct(c[1]),
                                                borderColor: classColor(b.class_id),
                                                cursor: CORNER_CURSOR[k],
                                            }}
                                        />
                                    ))}
                                    <div
                                        onPointerDown={(e) => startRotate(e, i)}
                                        onPointerMove={onPointerMove}
                                        onPointerUp={onPointerUp}
                                        title="Drag to rotate (or use [ and ])"
                                        className="absolute w-3.5 h-3.5 -ml-[7px] -mt-[7px] rounded-full
                                                   bg-white border-2 cursor-grab active:cursor-grabbing"
                                        style={{
                                            // Just clear of the box's first edge, so it
                                            // never sits under a corner handle, and it
                                            // turns with the box.
                                            left: pct(rotateHandle(b.corners)[0]),
                                            top: pct(rotateHandle(b.corners)[1]),
                                            borderColor: classColor(b.class_id),
                                        }}
                                    />
                                </>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
