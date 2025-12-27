import React from 'react';
import { useStore } from '~/store/useStore';
import { ChevronLeft, Trash2, ArrowDown, RotateCw, Waves } from 'lucide-react';
import type { Load } from '~/types/model';

// --- Shared Helper Components ---

const EditorHeader = ({ title, type, icon, onDelete, onBack }: any) => (
    <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-white sticky top-0 z-10">
        <div className="flex items-center gap-3">
            <button onClick={onBack} className="p-1.5 hover:bg-slate-100 rounded-md text-slate-500">
                <ChevronLeft size={18} />
            </button>
            <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                    {icon}
                </div>
                <div>
                    <h2 className="font-semibold text-slate-800 text-sm">{title}</h2>
                    <p className="text-[10px] text-slate-500 uppercase font-bold">{type}</p>
                </div>
            </div>
        </div>
        <button onClick={onDelete} className="p-2 text-red-400 hover:bg-red-50 hover:text-red-600 rounded-md">
            <Trash2 size={16} />
        </button>
    </div>
);

const NumberInput = ({ label, value, onChange, unit, step = 1, min, max }: any) => (
    <div className="flex items-center justify-between gap-2 text-sm">
        <label className="text-slate-500 w-24 shrink-0 truncate">{label}</label>
        <div className="flex items-center relative w-full">
            <input
                type="number"
                step={step}
                min={min}
                max={max}
                value={value ?? 0}
                onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1.5 text-right pr-8 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {unit && <span className="absolute right-2 text-slate-400 text-[10px] pointer-events-none">{unit}</span>}
        </div>
    </div>
);

const RangeInput = ({ label, value, onChange }: any) => (
    <div className="space-y-2">
        <div className="flex justify-between items-center">
            <label className="text-xs font-bold text-slate-400 uppercase">{label}</label>
            <span className="text-xs font-mono text-slate-600">{(value * 100).toFixed(0)}%</span>
        </div>
        <input
            type="range"
            min={0} max={1} step={0.01}
            value={value}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
    </div>
);

// --- MAIN COMPONENT ---

export const LoadEditor = ({ loadId }: { loadId: string }) => {
    const load = useStore(s => s.loads.find(l => l.id === loadId));
    const actions = useStore(s => s.actions);

    if (!load) return null;

    const updateLoad = (data: Partial<Load>) => {
        actions.updateLoad(loadId, data);
    };

    // Determine Icon & Title
    let icon = <ArrowDown size={18} />;
    let typeLabel = "Force";

    if (load.type === 'MOMENT') {
        icon = <RotateCw size={18} />;
        typeLabel = "Moment";
    } else if (load.type === 'DISTRIBUTED') {
        icon = <Waves size={18} />;
        typeLabel = "Line Load";
    }

    const unit = load.type === 'MOMENT' ? 'kNm' : (load.type === 'DISTRIBUTED' ? 'kN/m' : 'kN');

    return (
        <div className="flex flex-col h-full bg-white">
            <EditorHeader
                title={`Load ${load.id.slice(0, 4)}`}
                type={typeLabel}
                icon={icon}
                onBack={() => actions.setInteraction({ selectedId: null, selectedType: null })}
            //onDelete={() => {

            //}}
            />

            <div className="p-4 space-y-6 overflow-y-auto">

                {/* 1. MAGNITUDE */}
                <div className="space-y-3">
                    <label className="text-xs font-bold text-slate-400 uppercase">Magnitude</label>
                    <NumberInput
                        label="Value"
                        value={load.value}
                        onChange={(v: number) => updateLoad({ value: v })}
                        unit={unit}
                    />

                    {/* For trapezoidal loads */}
                    {load.type === 'DISTRIBUTED' && load.startValue !== undefined && (
                        <NumberInput
                            label="End Value"
                            value={load.endValue ?? load.value}
                            onChange={(v: number) => updateLoad({ endValue: v })}
                            unit={unit}
                        />
                    )}
                </div>

                <div className="h-px bg-slate-100" />

                {/* 2. GEOMETRY / POSITION */}
                <div className="space-y-4">
                    <label className="text-xs font-bold text-slate-400 uppercase">Position & Geometry</label>

                    {/* ANGLE (Point Loads Only) */}
                    {load.type === 'POINT' && (
                        <NumberInput
                            label="Angle"
                            value={load.angle ?? 90}
                            onChange={(v: number) => updateLoad({ angle: v })}
                            unit="deg"
                            step={15}
                        />
                    )}

                    {/* RATIO (Point on Member Only) */}
                    {load.scope === 'MEMBER' && load.type === 'POINT' && (
                        <RangeInput
                            label="Position along Beam"
                            value={load.ratio}
                            onChange={(v: number) => updateLoad({ ratio: v })}
                        />
                    )}

                    {/* DISTRIBUTED RANGE */}
                    {load.scope === 'MEMBER' && load.type === 'DISTRIBUTED' && (
                        <>
                            <RangeInput
                                label="Start Position"
                                value={load.startRatio}
                                onChange={(v: number) => updateLoad({ startRatio: v })}
                            />
                            <RangeInput
                                label="End Position"
                                value={load.endRatio}
                                onChange={(v: number) => updateLoad({ endRatio: v })}
                            />
                        </>
                    )}
                </div>

                {/* 3. INFO */}
                <div className="p-3 bg-slate-50 rounded text-xs text-slate-500">
                    <p>Attached to: <span className="font-mono font-bold text-slate-700">
                        {load.scope === 'NODE' ? 'Node' : 'Member'}
                    </span></p>
                    <p className="mt-1 opacity-70">
                        ID: {load.id}
                    </p>
                </div>

            </div>
        </div>
    );
};
