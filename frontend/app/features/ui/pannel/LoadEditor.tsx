import React from 'react';
import { useStore } from '~/store/useStore';
import { ChevronLeft, Trash2, ArrowDown, RotateCw, Waves, Activity, Radio } from 'lucide-react';
import type {
    Load,
    DynamicForceLoad,
    DynamicMomentLoad,
    NodeLoad,
    MemberPointLoad,
    MemberDistLoad,
    DynamicSignal,
    HarmonicSignal,
    PulseSignal,
    RampSignal
} from '~/types/model';

// --- HELPERS ---

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

const RatioInput = ({ label, value, onChange }: { label: string, value: number, onChange: (v: number) => void }) => {
    const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = parseFloat(e.target.value);
        if (!isNaN(val)) onChange(val);
    };

    return (
        <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
                <label className="font-bold text-slate-400 uppercase">{label}</label>
                <span className="font-mono text-slate-600">{(value * 100).toFixed(0)}%</span>
            </div>
            <div className="flex gap-2 items-center">
                <input
                    type="range"
                    min={0} max={1} step={0.01}
                    value={value || 0}
                    onChange={handleSliderChange}
                    className="flex-1 h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
            </div>
        </div>
    );
};

// --- MAIN COMPONENT ---

export const LoadEditor = ({ loadId }: { loadId: string }) => {
    // 1. Selector: Get Load
    const load = useStore(s => s.editor.loads.find(l => l.id === loadId));
    const actions = useStore(s => s.editor.actions);

    if (!load) return null;

    // 2. Type Guard
    const isDynamic = load.type === 'DYNAMIC_FORCE' || load.type === 'DYNAMIC_MOMENT';

    // 3. Update Helpers
    const updateLoad = (data: Partial<Load>) => {
        actions.updateLoad(loadId, data);
    };

    // Helper for signal updates (Type Safe)
    const updateSignal = (patch: Partial<DynamicSignal>) => {
        if (isDynamic) {
            const dLoad = load as DynamicForceLoad | DynamicMomentLoad;
            actions.updateLoad(loadId, {
                signal: { ...dLoad.signal, ...patch }
            } as any);
        }
    };

    // Determine UI Labels
    let icon = <ArrowDown size={18} />;
    let typeLabel = "Force";

    switch (load.type) {
        case 'MOMENT':
            icon = <RotateCw size={18} />;
            typeLabel = "Moment";
            break;
        case 'DISTRIBUTED':
            icon = <Waves size={18} />;
            typeLabel = "Line Load";
            break;
        case 'DYNAMIC_FORCE':
            icon = <Activity size={18} />;
            typeLabel = "Dyn. Force";
            break;
        case 'DYNAMIC_MOMENT':
            icon = <Radio size={18} />;
            typeLabel = "Dyn. Moment";
            break;
    }

    const unit = (load.type === 'MOMENT' || load.type === 'DYNAMIC_MOMENT') ? 'kNm' : 'kN';

    return (
        <div className="flex flex-col h-full bg-white">
            <EditorHeader
                title={`Load ${load.id.slice(0, 4)}`}
                type={typeLabel}
                icon={icon}
                onBack={() => actions.setInteraction({ selectedId: null, selectedType: null })}
                onDelete={() => {

                    //actions.removeLoad(loadId);
                    actions.setInteraction({ selectedId: null, selectedType: null });
                }}
            />

            <div className="p-4 space-y-6 overflow-y-auto">

                {/* --- DYNAMIC LOAD EDITOR (Signal) --- */}
                {isDynamic ? (() => {
                    const dLoad = load as DynamicForceLoad | DynamicMomentLoad;
                    const signal = dLoad.signal;

                    return (
                        <div className="space-y-3">
                            <label className="text-xs font-bold text-slate-400 uppercase">Signal</label>

                            {/* Signal Type Tabs */}
                            <div className="text-xs flex gap-2 p-1 bg-slate-100 rounded-lg mb-2">
                                {['HARMONIC', 'STEP', 'PULSE', 'RAMP'].map(t => (
                                    <button
                                        key={t}
                                        onClick={() => updateSignal({ type: t as any })}
                                        className={`flex-1 py-1 rounded-md transition-colors ${signal.type === t ? 'bg-white shadow text-blue-600 font-bold' : 'text-slate-500 hover:text-slate-700'}`}
                                    >
                                        {t[0] + t.slice(1).toLowerCase()}
                                    </button>
                                ))}
                            </div>

                            {/* Amplitude (Always Present) */}
                            <NumberInput
                                label="Amplitude"
                                value={signal.amplitude}
                                onChange={(v: number) => updateSignal({ amplitude: v })}
                                unit={unit}
                            />

                            {/* Start Time (Always Present) */}
                            <NumberInput
                                label="Start Time"
                                value={signal.startTime}
                                onChange={(v: number) => updateSignal({ startTime: v })}
                                unit="s"
                                min={0} step={0.1}
                            />

                            {/* Type Specific Fields */}
                            {signal.type === 'HARMONIC' && (
                                <>
                                    <NumberInput
                                        label="Frequency"
                                        value={(signal as HarmonicSignal).frequency}
                                        onChange={(v: number) => updateSignal({ frequency: v })}
                                        unit="Hz"
                                        min={0.1} step={0.1}
                                    />
                                    <NumberInput
                                        label="Phase"
                                        value={(signal as HarmonicSignal).phase}
                                        onChange={(v: number) => updateSignal({ phase: v })}
                                        unit="rad"
                                        step={0.1}
                                    />
                                </>
                            )}

                            {(signal.type === 'PULSE' || signal.type === 'RAMP') && (
                                <NumberInput
                                    label="End Time"
                                    value={(signal as PulseSignal | RampSignal).endTime}
                                    onChange={(v: number) => updateSignal({ endTime: v })}
                                    unit="s"
                                    min={0} step={0.1}
                                />
                            )}
                        </div>
                    );
                })() : (
                    /* --- STATIC LOAD EDITOR (Value) --- */
                    (() => {
                        const sLoad = load as NodeLoad | MemberPointLoad | MemberDistLoad;

                        return (
                            <div className="space-y-3">
                                <label className="text-xs font-bold text-slate-400 uppercase">Magnitude</label>
                                <NumberInput
                                    label="Value"
                                    value={sLoad.value}
                                    onChange={(v: number) => updateLoad({ value: v } as any)}
                                    unit={unit}
                                />
                                {sLoad.type === 'DISTRIBUTED' && (
                                    <NumberInput
                                        label="End Value"
                                        value={sLoad.endValue ?? sLoad.value}
                                        onChange={(v: number) => updateLoad({ endValue: v } as any)}
                                        unit={unit}
                                    />
                                )}
                            </div>
                        );
                    })()
                )}

                <div className="h-px bg-slate-100" />

                {/* --- GEOMETRY EDITOR --- */}
                <div className="space-y-4">
                    <label className="text-xs font-bold text-slate-400 uppercase">Position & Geometry</label>

                    {/* Angle (Static Point OR Dynamic Force) */}
                    {(load.type === 'POINT' || load.type === 'DYNAMIC_FORCE') && (
                        <NumberInput
                            label="Angle"
                            // Use safe casting or optional chaining.
                            // If it's Dynamic Force, use angle (default 0).
                            // If it's Static Point, use angle (default -90).
                            value={(load as any).angle ?? (isDynamic ? 0 : -90)}
                            onChange={(v: number) => updateLoad({ angle: v } as any)}
                            unit="deg"
                            step={15}
                        />
                    )}

                    {/* Member Load Position (Static Only) */}
                    {load.scope === 'MEMBER' && load.type === 'POINT' && (
                        <RatioInput
                            label="Position along Beam"
                            value={(load as MemberPointLoad).ratio || 0}
                            onChange={(v: number) => updateLoad({ ratio: v } as any)}
                        />
                    )}

                    {/* Distributed Range (Static Only) */}
                    {load.scope === 'MEMBER' && load.type === 'DISTRIBUTED' && (
                        <>
                            <RatioInput
                                label="Start Position"
                                value={(load as MemberDistLoad).startRatio || 0}
                                onChange={(v: number) => updateLoad({ startRatio: v } as any)}
                            />
                            <RatioInput
                                label="End Position"
                                value={(load as MemberDistLoad).endRatio || 1}
                                onChange={(v: number) => updateLoad({ endRatio: v } as any)}
                            />
                        </>
                    )}
                </div>

                {/* INFO BOX */}
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
