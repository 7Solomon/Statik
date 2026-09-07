import { useCallback, useEffect, useRef, useState } from 'react';
import {
    ChevronLeft, ChevronRight, SkipForward, Save, Trash2, RotateCcw,
    Loader2, AlertCircle, ImageOff, Download, Tag, FolderOpen,
} from 'lucide-react';
import LabelingCanvas, { classColor } from './LabelingCanvas';
import { useLabeling, type StatusFilter } from './useLabeling';

const STATUS_TABS: { key: StatusFilter; label: string }[] = [
    { key: 'unlabeled', label: 'To do' },
    { key: 'labeled', label: 'Labelled' },
    { key: 'skipped', label: 'Not a system' },
    { key: 'all', label: 'All' },
];

export default function LabelingManager() {
    const L = useLabeling();
    const [exportName, setExportName] = useState('real-systems');
    const [exportResult, setExportResult] = useState<string | null>(null);

    const {
        current, boxes, classes, deleteSelected, chooseClass, go, save, skip, setSelected,
        rotateSelected, moveSelected,
    } = L;

    // Displayed width/height of the image, so rotation stays rigid on a crop of
    // any shape - the harvest runs to 13:1.
    const selected = L.selected;
    const aspect = useRef(1);
    const ROTATE_STEP = Math.PI / 90;  // 2 degrees per keypress
    const NUDGE = 0.004;               // of the image height, per keypress

    // Keyboard: digits pick a class, arrows page, S saves, X skips.
    const onKey = useCallback((e: KeyboardEvent) => {
        const el = e.target as HTMLElement | null;
        if (el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) return;
        if (e.metaKey || e.ctrlKey || e.altKey) return;

        if (e.key >= '1' && e.key <= '9') {
            const idx = Number(e.key) - 1;
            if (idx < classes.length) { chooseClass(idx); e.preventDefault(); }
            return;
        }
        if (e.key === '0' && classes.length >= 10) { chooseClass(9); e.preventDefault(); return; }

        // With a box selected the arrows nudge it; with nothing selected they
        // page through images. Escape drops the selection and hands them back.
        if (e.key.startsWith('Arrow')) {
            const step = (e.shiftKey ? 4 : 1) * NUDGE;
            if (selected !== null) {
                // The x step is divided by the aspect so a nudge covers the same
                // number of pixels sideways as it does vertically.
                const dx = step / (aspect.current || 1);
                if (e.key === 'ArrowLeft') moveSelected(-dx, 0);
                else if (e.key === 'ArrowRight') moveSelected(dx, 0);
                else if (e.key === 'ArrowUp') moveSelected(0, -step);
                else moveSelected(0, step);
                e.preventDefault();
            } else if (e.key === 'ArrowRight') go(1);
            else if (e.key === 'ArrowLeft') go(-1);
            return;
        }

        switch (e.key) {
            case '[': rotateSelected(-ROTATE_STEP, aspect.current); break;
            case ']': rotateSelected(ROTATE_STEP, aspect.current); break;
            case 'Delete': case 'Backspace': deleteSelected(); e.preventDefault(); break;
            case 'Escape': setSelected(null); break;
            case 's': case 'S': save(); break;
            case 'x': case 'X': skip(); break;
            default: return;
        }
    }, [classes.length, chooseClass, go, deleteSelected, save, skip, setSelected,
        rotateSelected, moveSelected, selected, ROTATE_STEP, NUDGE]);

    useEffect(() => {
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [onKey]);

    const runExport = async () => {
        const r = await L.exportDataset({ dataset_name: exportName, include_negatives: true });
        if (r?.success) {
            setExportResult(
                `${r.total} images -> ${r.dataset_path} ` +
                `(train ${r.counts.train}, val ${r.counts.val}, ${r.negatives} negatives)`
            );
        }
    };

    const done = L.counts.labeled + L.counts.skipped;
    const total = done + L.counts.unlabeled;

    return (
        <div className="space-y-4">
            {/* --- Source + progress -------------------------------------- */}
            <div className="bg-white rounded-xl border border-slate-200 p-4">
                <div className="flex flex-wrap items-center gap-4">
                    <div className="flex items-center gap-2">
                        <FolderOpen size={16} className="text-slate-400" />
                        <select
                            value={L.imagesDir ?? ''}
                            onChange={(e) => L.setImagesDir(e.target.value)}
                            className="text-sm border border-slate-200 rounded-lg px-2 py-1.5 bg-white"
                        >
                            {L.sources.length === 0 && <option value="">No image folder found</option>}
                            {L.sources.map(s => (
                                <option key={s.images_dir} value={s.images_dir}>
                                    {s.label} ({s.count})
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="flex-1 min-w-[200px]">
                        <div className="flex justify-between text-xs text-slate-500 mb-1">
                            <span>{done} of {total} decided</span>
                            <span className="font-mono">
                                {L.counts.labeled} labelled · {L.counts.skipped} negative
                            </span>
                        </div>
                        <div className="h-2 bg-slate-100 rounded-full overflow-hidden flex">
                            <div className="bg-emerald-500 h-full"
                                style={{ width: `${total ? (L.counts.labeled / total) * 100 : 0}%` }} />
                            <div className="bg-slate-400 h-full"
                                style={{ width: `${total ? (L.counts.skipped / total) * 100 : 0}%` }} />
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        <input
                            value={exportName}
                            onChange={(e) => setExportName(e.target.value)}
                            className="text-sm border border-slate-200 rounded-lg px-2 py-1.5 w-40"
                            placeholder="dataset name"
                        />
                        <button
                            onClick={runExport}
                            disabled={L.busy || L.counts.labeled === 0}
                            className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 text-white text-xs
                                       font-semibold rounded-lg hover:bg-slate-800 disabled:opacity-40"
                        >
                            <Download size={14} /> Export YOLO
                        </button>
                    </div>
                </div>

                {exportResult && (
                    <p className="mt-3 text-xs font-mono text-emerald-700 bg-emerald-50
                                  border border-emerald-200 rounded-lg px-3 py-2">
                        {exportResult}
                    </p>
                )}
            </div>

            {/* --- Filters ------------------------------------------------ */}
            <div className="flex flex-wrap items-center gap-3">
                <div className="flex gap-1 p-1 bg-slate-100 rounded-lg border border-slate-200">
                    {STATUS_TABS.map(t => (
                        <button
                            key={t.key}
                            onClick={() => { L.setStatusFilter(t.key); L.setCursor(0); }}
                            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                                L.statusFilter === t.key
                                    ? 'bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200'
                                    : 'text-slate-500 hover:text-slate-700'
                            }`}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>

                {L.lectures.length > 0 && (
                    <select
                        value={L.lectureFilter}
                        onChange={(e) => { L.setLectureFilter(e.target.value); L.setCursor(0); }}
                        className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white"
                        title="Source PDF collection - the strongest predictor of whether a crop is a real system"
                    >
                        <option value="all">All sources</option>
                        {L.lectures.map(l => <option key={l} value={l}>{l}</option>)}
                    </select>
                )}

                <select
                    value={L.sortMode}
                    onChange={(e) => { L.setSortMode(e.target.value as any); L.setCursor(0); }}
                    className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white"
                >
                    <option value="order">Harvest order</option>
                    <option value="score">Best score first</option>
                </select>

                <span className="text-xs text-slate-400 ml-auto font-mono">
                    {L.visible.length ? L.cursor + 1 : 0} / {L.visible.length}
                </span>
            </div>

            {/* --- Error -------------------------------------------------- */}
            {L.error && (
                <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3">
                    <AlertCircle size={16} className="text-red-500 mt-0.5 flex-none" />
                    <p className="text-sm text-red-700 flex-1">{L.error}</p>
                    <button onClick={() => L.setError(null)} className="text-red-400 text-xs">dismiss</button>
                </div>
            )}

            {/* --- Stage + class rail ------------------------------------- */}
            <div className="flex items-start gap-4">
            <div className="flex-1 min-w-0 bg-white rounded-xl border border-slate-200 p-4">
                {L.loading ? (
                    <div className="h-64 flex flex-col items-center justify-center text-slate-400">
                        <Loader2 className="w-8 h-8 animate-spin mb-3" />
                        <p className="text-sm">Loading image index…</p>
                    </div>
                ) : !current ? (
                    <div className="h-64 flex flex-col items-center justify-center text-slate-400">
                        <ImageOff className="w-10 h-10 mb-3 opacity-30" />
                        <p className="text-sm font-medium">
                            {L.sources.length === 0
                                ? 'No image folder mounted at content/harvest'
                                : 'Nothing left in this filter'}
                        </p>
                        <p className="text-xs mt-1">
                            {L.sources.length === 0
                                ? 'Add ./tmp/out:/app/content/harvest to the backend volumes and restart.'
                                : 'Switch to “All” to review images you already decided.'}
                        </p>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-3">
                        <div className="w-full flex items-center justify-between text-xs">
                            <span className="font-mono text-slate-500 truncate max-w-[45%]"
                                title={current.filename}>
                                {current.filename}
                            </span>
                            <div className="flex items-center gap-3 text-slate-400">
                                {current.meta?.lecture && (
                                    <span className="truncate max-w-[220px]">{current.meta.lecture}</span>
                                )}
                                {current.meta?.page && <span>p.{current.meta.page}</span>}
                                <StatusPill status={current.status} />
                            </div>
                        </div>

                        {L.currentUrl ? (
                            <LabelingCanvas
                                url={L.currentUrl}
                                boxes={boxes}
                                classes={classes}
                                selected={L.selected}
                                activeClass={L.activeClass}
                                onSelect={L.setSelected}
                                onAdd={L.addBox}
                                onReplace={L.replaceBox}
                                onAspect={(a) => { aspect.current = a; }}
                            />
                        ) : (
                            <div className="h-64 w-full flex items-center justify-center">
                                <Loader2 className="w-7 h-7 text-indigo-400 animate-spin" />
                            </div>
                        )}

                        <p className="text-[11px] text-slate-400">
                            Drag on empty space to draw — a new box stays unselected, so
                            <kbd className="mx-1 px-1 bg-slate-100 rounded border">1-9</kbd>
                            arms the next one. Drag a box to move it; once selected, the
                            square corner grips resize it and the round grip or
                            <kbd className="mx-1 px-1 bg-slate-100 rounded border">[ ]</kbd>
                            turns it. With a box selected
                            <kbd className="mx-1 px-1 bg-slate-100 rounded border">↑↓←→</kbd>
                            nudge it (<kbd className="mx-1 px-1 bg-slate-100 rounded border">⇧</kbd>
                            faster), otherwise they page ·
                            <kbd className="mx-1 px-1 bg-slate-100 rounded border">Esc</kbd>deselect ·
                            <kbd className="mx-1 px-1 bg-slate-100 rounded border">Del</kbd>remove ·
                            <kbd className="mx-1 px-1 bg-slate-100 rounded border">S</kbd>save ·
                            <kbd className="mx-1 px-1 bg-slate-100 rounded border">X</kbd>not a system
                        </p>
                    </div>
                )}
            </div>

            {/* Class rail. Beside the image rather than under it: picking a
                class is the one thing done on every single box, and from down
                the page it meant looking away from the drawing each time. */}
            <aside className="w-64 flex-none bg-white rounded-xl border border-slate-200 p-3
                              sticky top-4 max-h-[calc(100vh-8rem)] overflow-y-auto">
                <div className="flex items-center gap-2 mb-2 px-1">
                    <Tag size={13} className="text-slate-400" />
                    <h3 className="text-[11px] font-bold uppercase tracking-wide text-slate-500">
                        Class
                    </h3>
                </div>

                <p className="text-[10px] leading-snug text-slate-400 px-1 mb-2">
                    {L.selected !== null
                        ? 'A box is selected — picking a class changes that box.'
                        : 'Picking a class arms the next box you draw.'}
                </p>

                <div className="flex flex-col gap-0.5">
                    {classes.map((name, i) => {
                        const active = L.activeClass === i;
                        return (
                            <button
                                key={name}
                                onClick={() => chooseClass(i)}
                                title={name}
                                // The active row stays light on purpose: the icons
                                // are dark line art on transparent, and a dark
                                // highlight swallowed them.
                                className={`flex items-center gap-2 pr-2 py-1 rounded-lg text-[11px]
                                            font-semibold text-left transition-all border-l-[3px] ${
                                    active
                                        ? 'bg-indigo-50 text-indigo-900 ring-1 ring-indigo-200'
                                        : 'text-slate-600 hover:bg-slate-50'
                                }`}
                                style={{ borderLeftColor: classColor(i) }}
                            >
                                <span className="w-[52px] h-6 flex-none flex items-center justify-center">
                                    {L.icons[name] ? (
                                        <img
                                            src={L.icons[name]}
                                            alt=""
                                            className="max-w-full max-h-full object-contain"
                                            draggable={false}
                                        />
                                    ) : (
                                        <span className="w-2.5 h-2.5 rounded-sm"
                                            style={{ background: classColor(i) }} />
                                    )}
                                </span>
                                <span className="flex-1 truncate">{name}</span>
                                {i < 10 && (
                                    <kbd className={`text-[9px] font-mono px-1 rounded border ${
                                        active
                                            ? 'border-indigo-300 text-indigo-500'
                                            : 'border-slate-200 text-slate-400'
                                    }`}>
                                        {(i + 1) % 10}
                                    </kbd>
                                )}
                            </button>
                        );
                    })}
                </div>

                {boxes.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-100">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-1 mb-1.5">
                            On this image
                        </p>
                        <div className="flex flex-col gap-0.5">
                            {boxes.map((b, i) => (
                                <button
                                    key={i}
                                    onClick={() => L.setSelected(L.selected === i ? null : i)}
                                    className={`flex items-center gap-2 px-2 py-1 rounded text-[11px]
                                                text-left transition-colors ${
                                        L.selected === i
                                            ? 'bg-slate-100 text-slate-900 font-semibold'
                                            : 'text-slate-500 hover:bg-slate-50'
                                    }`}
                                >
                                    <span className="w-2 h-2 rounded-sm flex-none"
                                        style={{ background: classColor(b.class_id) }} />
                                    {L.icons[classes[b.class_id]] && (
                                        <img src={L.icons[classes[b.class_id]]} alt=""
                                            className="h-4 w-7 object-contain flex-none opacity-70"
                                            draggable={false} />
                                    )}
                                    <span className="flex-1 truncate">
                                        {classes[b.class_id] ?? b.class_id}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </aside>
            </div>

            {/* --- Actions ------------------------------------------------ */}
            <div className="flex items-center gap-2 sticky bottom-0 bg-slate-50/90 backdrop-blur py-3">
                <button onClick={() => go(-1)} disabled={L.cursor === 0}
                    className="w-10 h-10 flex items-center justify-center rounded-xl bg-white
                               border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40">
                    <ChevronLeft size={18} />
                </button>
                <button onClick={() => go(1)} disabled={L.cursor >= L.visible.length - 1}
                    className="w-10 h-10 flex items-center justify-center rounded-xl bg-white
                               border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40">
                    <ChevronRight size={18} />
                </button>

                <button onClick={L.deleteSelected} disabled={L.selected === null}
                    className="flex items-center gap-2 px-3 h-10 rounded-xl bg-white border border-slate-200
                               text-slate-600 text-xs font-semibold hover:bg-slate-50 disabled:opacity-40">
                    <Trash2 size={14} /> Delete box
                </button>

                <button onClick={L.reset} disabled={!current || current.status === 'unlabeled' || L.busy}
                    className="flex items-center gap-2 px-3 h-10 rounded-xl bg-white border border-slate-200
                               text-slate-600 text-xs font-semibold hover:bg-slate-50 disabled:opacity-40">
                    <RotateCcw size={14} /> Reset
                </button>

                <div className="flex-1" />

                <button onClick={skip} disabled={!current || L.busy}
                    className="flex items-center gap-2 px-4 h-10 rounded-xl bg-white border border-slate-300
                               text-slate-700 text-sm font-semibold hover:bg-slate-100 disabled:opacity-40">
                    <SkipForward size={16} /> Not a system
                </button>

                <button onClick={save} disabled={!current || L.busy || boxes.length === 0}
                    className="flex items-center gap-2 px-5 h-10 rounded-xl bg-indigo-600 text-white
                               text-sm font-bold hover:bg-indigo-700 shadow-sm disabled:opacity-40">
                    {L.busy ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                    Save {boxes.length > 0 && `(${boxes.length})`}
                </button>
            </div>
        </div>
    );
}

function StatusPill({ status }: { status: string }) {
    const style = status === 'labeled'
        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
        : status === 'skipped'
            ? 'bg-slate-100 text-slate-500 border-slate-200'
            : 'bg-amber-50 text-amber-700 border-amber-200';
    const text = status === 'labeled' ? 'labelled'
        : status === 'skipped' ? 'negative' : 'to do';
    return <span className={`px-2 py-0.5 rounded-full border text-[10px] font-semibold ${style}`}>{text}</span>;
}
