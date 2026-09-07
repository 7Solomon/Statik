import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export type LabelStatus = 'unlabeled' | 'labeled' | 'skipped';

/** A corner, normalised to the image: [x, y] in [0, 1]. */
export type Corner = [number, number];

/**
 * One YOLO OBB. Four corners rather than centre/size, matching what the
 * generator writes - an axis-aligned box on a 45-degree member fills about a
 * fifth of itself and swallows whatever else is nearby.
 */
export interface LabelBox {
    class_id: number;
    corners: Corner[];
}

export function rectCorners(x0: number, y0: number, x1: number, y1: number): Corner[] {
    const [ax, bx] = x0 <= x1 ? [x0, x1] : [x1, x0];
    const [ay, by] = y0 <= y1 ? [y0, y1] : [y1, y0];
    return [[ax, ay], [bx, ay], [bx, by], [ax, by]];
}

export function centroid(corners: Corner[]): Corner {
    const n = corners.length || 1;
    return [
        corners.reduce((a, c) => a + c[0], 0) / n,
        corners.reduce((a, c) => a + c[1], 0) / n,
    ];
}

/**
 * Rotate corners about their centroid by `rad`.
 *
 * `aspect` is the image's width/height. Rotating in normalised space directly
 * would shear the box on any non-square image, because one normalised unit of x
 * is not one normalised unit of y - so x is scaled into display units, rotated,
 * and scaled back.
 */
export function rotateCorners(corners: Corner[], rad: number, aspect: number): Corner[] {
    const [cx, cy] = centroid(corners);
    const cos = Math.cos(rad);
    const sin = Math.sin(rad);
    return corners.map(([x, y]) => {
        const dx = (x - cx) * aspect;
        const dy = y - cy;
        return [
            cx + (dx * cos - dy * sin) / aspect,
            cy + (dx * sin + dy * cos),
        ] as Corner;
    });
}

/**
 * Shift corners by (dx, dy), clamped so the whole box stays on the image.
 *
 * Clamping the translation rather than each corner keeps the box rigid:
 * clamping corner by corner would squash a box dragged off the edge instead of
 * stopping it there.
 */
export function translateCorners(corners: Corner[], dx: number, dy: number): Corner[] {
    const b = boundsOf(corners);
    const cdx = Math.min(Math.max(dx, -b.x0), 1 - b.x1);
    const cdy = Math.min(Math.max(dy, -b.y0), 1 - b.y1);
    return corners.map(([x, y]) => [x + cdx, y + cdy] as Corner);
}

/** Smallest extent a box may be resized to, as a share of the image height. */
const MIN_EXTENT = 0.006;

/**
 * Drag one corner; the opposite corner stays put and the box stays a rectangle.
 *
 * Resizing has to happen in the box's OWN frame, not the image's, or a turned
 * box would shear instead of stretch. The two edges leaving the anchor give
 * that frame, the pointer is projected onto them, and the rectangle is rebuilt
 * from those two extents - so the result is square-cornered at any rotation.
 *
 * Corner order is preserved (the dragged corner stays the dragged corner),
 * which is what lets a drag continue smoothly across frames.
 */
export function resizeCorners(
    corners: Corner[], handle: number, pointer: Corner, aspect: number,
): Corner[] {
    // Work in display units, where one unit of x is one unit of y.
    const toD = ([x, y]: Corner): Corner => [x * aspect, y];
    const d = corners.map(toD);

    const anchor = (handle + 2) % 4;
    const A = d[anchor];
    const e1: Corner = [d[(anchor + 1) % 4][0] - A[0], d[(anchor + 1) % 4][1] - A[1]];
    const e2: Corner = [d[(anchor + 3) % 4][0] - A[0], d[(anchor + 3) % 4][1] - A[1]];
    const l1 = Math.hypot(e1[0], e1[1]);
    const l2 = Math.hypot(e2[0], e2[1]);
    if (l1 < 1e-9 || l2 < 1e-9) return corners;

    const u1: Corner = [e1[0] / l1, e1[1] / l1];
    const u2: Corner = [e2[0] / l2, e2[1] / l2];
    const p = toD(pointer);
    const rx = p[0] - A[0];
    const ry = p[1] - A[1];

    // Floored rather than allowed to go negative: a box dragged through its own
    // anchor would flip inside out, which is never what a label wants.
    const s1 = Math.max(MIN_EXTENT, rx * u1[0] + ry * u1[1]);
    const s2 = Math.max(MIN_EXTENT, rx * u2[0] + ry * u2[1]);

    const out: Corner[] = [[0, 0], [0, 0], [0, 0], [0, 0]];
    out[anchor] = A;
    out[(anchor + 1) % 4] = [A[0] + s1 * u1[0], A[1] + s1 * u1[1]];
    out[(anchor + 2) % 4] = [A[0] + s1 * u1[0] + s2 * u2[0],
                             A[1] + s1 * u1[1] + s2 * u2[1]];
    out[(anchor + 3) % 4] = [A[0] + s2 * u2[0], A[1] + s2 * u2[1]];

    const result = out.map(([x, y]) => [x / aspect, y] as Corner);
    // Clamping a corner would break the right angles, so an out-of-frame result
    // is refused outright: the box simply stops growing at the edge.
    const b = boundsOf(result);
    if (b.x0 < -1e-9 || b.y0 < -1e-9 || b.x1 > 1 + 1e-9 || b.y1 > 1 + 1e-9) {
        return corners;
    }
    return result;
}

export function boundsOf(corners: Corner[]) {
    const xs = corners.map(c => c[0]);
    const ys = corners.map(c => c[1]);
    return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) };
}

export interface ImageMeta {
    lecture?: string;
    page?: string;
    score?: number;
    source_pdf?: string;
}

export interface ImageEntry {
    filename: string;
    status: LabelStatus;
    n_boxes: number;
    meta?: ImageMeta;
}

export interface LabelSource {
    images_dir: string;
    label: string;
    count: number;
    has_manifest: boolean;
}

export type StatusFilter = 'all' | 'unlabeled' | 'labeled' | 'skipped';
export type SortMode = 'order' | 'score';

/** How many images ahead of the cursor to fetch. Crops are ~20 KB, so a small
 *  window keeps paging instant without holding the whole 1800-image set. */
const PREFETCH = 6;

async function postJSON(url: string, body: unknown) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.error || `${res.status} ${res.statusText}`);
    return data;
}

export function useLabeling() {
    const [sources, setSources] = useState<LabelSource[]>([]);
    const [imagesDir, setImagesDir] = useState<string | null>(null);

    const [classes, setClasses] = useState<string[]>([]);
    /** class name -> data-URI PNG, drawn server-side from the real symbols. */
    const [icons, setIcons] = useState<Record<string, string>>({});
    const [images, setImages] = useState<ImageEntry[]>([]);
    const [lectures, setLectures] = useState<string[]>([]);

    const [statusFilter, setStatusFilter] = useState<StatusFilter>('unlabeled');
    const [lectureFilter, setLectureFilter] = useState<string>('all');
    const [sortMode, setSortMode] = useState<SortMode>('order');

    const [cursor, setCursor] = useState(0);
    const [boxes, setBoxes] = useState<LabelBox[]>([]);
    const [activeClass, setActiveClass] = useState(0);
    const [selected, setSelected] = useState<number | null>(null);

    const [loading, setLoading] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // filename -> data URI. Plain ref: this is a cache, never a render input.
    const urlCache = useRef<Map<string, string>>(new Map());
    const [, forceRender] = useState(0);

    // --- sources ---------------------------------------------------------

    // Static for the life of the backend, so fetched once and never refreshed.
    useEffect(() => {
        fetch('/api/labeling/class_icons')
            .then(r => r.json())
            .then(d => setIcons(d.icons || {}))
            .catch(() => { /* the rail falls back to colour swatches */ });
    }, []);

    useEffect(() => {
        fetch('/api/labeling/sources')
            .then(r => r.json())
            .then(d => {
                setSources(d.sources || []);
                if (d.sources?.length) setImagesDir((prev) => prev ?? d.sources[0].images_dir);
            })
            .catch(e => setError(String(e)));
    }, []);

    // --- session ---------------------------------------------------------

    const loadSession = useCallback(async (dir: string) => {
        setLoading(true);
        setError(null);
        try {
            const data = await postJSON('/api/labeling/session', { images_dir: dir });
            setClasses(data.classes || []);
            setImages(data.images || []);
            setLectures(data.lectures || []);
            urlCache.current.clear();
            setCursor(0);
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
            setImages([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (imagesDir) loadSession(imagesDir);
    }, [imagesDir, loadSession]);

    // --- the working list ------------------------------------------------

    const visible = useMemo(() => {
        let list = images;
        if (statusFilter !== 'all') list = list.filter(i => i.status === statusFilter);
        if (lectureFilter !== 'all') list = list.filter(i => i.meta?.lecture === lectureFilter);
        if (sortMode === 'score') {
            list = [...list].sort((a, b) => (b.meta?.score ?? 0) - (a.meta?.score ?? 0));
        }
        return list;
    }, [images, statusFilter, lectureFilter, sortMode]);

    // Filtering can strip the list out from under the cursor.
    const safeCursor = visible.length ? Math.min(cursor, visible.length - 1) : 0;
    const current: ImageEntry | null = visible[safeCursor] ?? null;

    const counts = useMemo(() => {
        const c = { unlabeled: 0, labeled: 0, skipped: 0 };
        for (const i of images) c[i.status] += 1;
        return c;
    }, [images]);

    // --- image + box loading ---------------------------------------------

    const fetchImages = useCallback(async (filenames: string[]) => {
        const missing = filenames.filter(f => f && !urlCache.current.has(f));
        if (!missing.length || !imagesDir) return;
        try {
            const data = await postJSON('/api/labeling/images_batch',
                { images_dir: imagesDir, filenames: missing });
            for (const [name, url] of Object.entries(data)) {
                if (typeof url === 'string') urlCache.current.set(name, url);
            }
            forceRender(n => n + 1);
        } catch { /* a failed prefetch is not worth surfacing */ }
    }, [imagesDir]);

    useEffect(() => {
        if (!current) return;
        const window_ = visible.slice(safeCursor, safeCursor + PREFETCH).map(i => i.filename);
        fetchImages(window_);
    }, [current, visible, safeCursor, fetchImages]);

    // Boxes always come from the server, so what is drawn is what is on disk.
    useEffect(() => {
        let cancelled = false;
        setSelected(null);
        if (!current || !imagesDir) { setBoxes([]); return; }
        if (current.status !== 'labeled') { setBoxes([]); return; }
        postJSON('/api/labeling/boxes', { images_dir: imagesDir, filename: current.filename })
            .then(d => { if (!cancelled) setBoxes(d.boxes || []); })
            .catch(() => { if (!cancelled) setBoxes([]); });
        return () => { cancelled = true; };
    }, [current?.filename, current?.status, imagesDir]);

    const currentUrl = current ? urlCache.current.get(current.filename) ?? null : null;

    // --- navigation ------------------------------------------------------

    const go = useCallback((delta: number) => {
        setCursor(c => {
            const next = c + delta;
            if (next < 0) return 0;
            if (next >= visible.length) return Math.max(0, visible.length - 1);
            return next;
        });
    }, [visible.length]);

    /** Advance without moving, when the filter has already removed this image. */
    const advanceAfterWrite = useCallback((nextStatus: LabelStatus) => {
        const filteredOut = statusFilter !== 'all' && statusFilter !== nextStatus;
        if (!filteredOut) setCursor(c => Math.min(c + 1, Math.max(0, visible.length - 1)));
    }, [statusFilter, visible.length]);

    const applyStatus = useCallback((filename: string, status: LabelStatus, nBoxes: number) => {
        setImages(list => list.map(i =>
            i.filename === filename ? { ...i, status, n_boxes: nBoxes } : i));
    }, []);

    // --- writes ----------------------------------------------------------

    const save = useCallback(async () => {
        if (!current || !imagesDir) return;
        setBusy(true);
        try {
            const r = await postJSON('/api/labeling/save',
                { images_dir: imagesDir, filename: current.filename, boxes });
            applyStatus(current.filename, r.status, r.n_boxes);
            advanceAfterWrite(r.status);
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            setBusy(false);
        }
    }, [current, imagesDir, boxes, applyStatus, advanceAfterWrite]);

    const skip = useCallback(async () => {
        if (!current || !imagesDir) return;
        setBusy(true);
        try {
            const r = await postJSON('/api/labeling/skip',
                { images_dir: imagesDir, filename: current.filename });
            applyStatus(current.filename, r.status, 0);
            advanceAfterWrite(r.status);
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            setBusy(false);
        }
    }, [current, imagesDir, applyStatus, advanceAfterWrite]);

    const reset = useCallback(async () => {
        if (!current || !imagesDir) return;
        setBusy(true);
        try {
            const r = await postJSON('/api/labeling/reset',
                { images_dir: imagesDir, filename: current.filename });
            applyStatus(current.filename, r.status, 0);
            setBoxes([]);
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
        } finally {
            setBusy(false);
        }
    }, [current, imagesDir, applyStatus]);

    const exportDataset = useCallback(async (opts: {
        dataset_name: string; include_negatives: boolean;
    }) => {
        if (!imagesDir) return null;
        setBusy(true);
        try {
            return await postJSON('/api/labeling/export', { images_dir: imagesDir, ...opts });
        } catch (e) {
            setError(e instanceof Error ? e.message : String(e));
            return null;
        } finally {
            setBusy(false);
        }
    }, [imagesDir]);

    // --- box editing -----------------------------------------------------

    const addBox = useCallback((corners: Corner[]) => {
        // Deliberately leaves nothing selected. Selecting the box you just drew
        // means the next class keypress retargets it instead of arming the class
        // for the next box, which silently relabels the one you just finished.
        // Click a box to select it when you actually want to change or turn it.
        setBoxes(bs => [...bs, { corners, class_id: activeClass }]);
        setSelected(null);
    }, [activeClass]);

    const replaceBox = useCallback((index: number, corners: Corner[]) => {
        setBoxes(bs => bs.map((b, i) => (i === index ? { ...b, corners } : b)));
    }, []);

    /** Turn the selected box in place; used by the handle and by [ / ]. */
    const rotateSelected = useCallback((rad: number, aspect: number) => {
        if (selected === null) return;
        setBoxes(bs => bs.map((b, i) =>
            i === selected ? { ...b, corners: rotateCorners(b.corners, rad, aspect) } : b));
    }, [selected]);

    /** Nudge the selected box; used by the arrow keys. */
    const moveSelected = useCallback((dx: number, dy: number) => {
        if (selected === null) return;
        setBoxes(bs => bs.map((b, i) =>
            i === selected ? { ...b, corners: translateCorners(b.corners, dx, dy) } : b));
    }, [selected]);

    const deleteSelected = useCallback(() => {
        if (selected === null) return;
        setBoxes(bs => bs.filter((_, i) => i !== selected));
        setSelected(null);
    }, [selected]);

    const setClassOf = useCallback((index: number, classId: number) => {
        setBoxes(bs => bs.map((b, i) => (i === index ? { ...b, class_id: classId } : b)));
    }, []);

    /** Picking a class retargets the selected box, else arms the next one. */
    const chooseClass = useCallback((classId: number) => {
        setActiveClass(classId);
        if (selected !== null) setClassOf(selected, classId);
    }, [selected, setClassOf]);

    return {
        sources, imagesDir, setImagesDir,
        classes, icons, lectures, counts,
        visible, current, currentUrl, cursor: safeCursor,
        statusFilter, setStatusFilter,
        lectureFilter, setLectureFilter,
        sortMode, setSortMode,
        boxes, setBoxes, addBox, replaceBox, rotateSelected, moveSelected,
        deleteSelected, chooseClass,
        activeClass, selected, setSelected,
        loading, busy, error, setError,
        go, setCursor, save, skip, reset, exportDataset,
    };
}
