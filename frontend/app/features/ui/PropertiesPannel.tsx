import React from 'react';
import { useStore } from '../../store/useStore';
import { RotateCcw, RotateCw, Move, Anchor, Sliders } from 'lucide-react';
import type { Node, SupportValue } from '~/types/model';

export const PropertiesPanel = () => {
    const { selectedId, selectedType } = useStore(s => s.interaction);
    const nodes = useStore(s => s.nodes);
    const members = useStore(s => s.members);
    const actions = useStore(s => s.actions);

    if (!selectedId || !selectedType) {
        return (
            <div className="w-80 bg-slate-50 border-l border-slate-200 p-8 flex flex-col items-center justify-center text-slate-400 text-sm gap-2 h-full">
                <Sliders className="w-8 h-8 opacity-50" />
                <span>Select an element to edit</span>
            </div>
        );
    }

    // --- NODE EDITOR ---
    if (selectedType === 'node') {
        const node = nodes.find(n => n.id === selectedId);
        if (!node) return null;

        const handleRotationStep = (step: number) => {
            let newRot = (node.rotation + step) % 360;
            if (newRot < 0) newRot += 360;
            actions.updateNode(node.id, { rotation: newRot });
        };

        return (
            <div className="w-80 bg-white border-l border-slate-200 flex flex-col shadow-xl h-full overflow-y-auto">
                <div className="p-4 border-b border-slate-100 bg-slate-50">
                    <h2 className="font-bold text-slate-800 flex items-center gap-2">
                        <Anchor className="w-4 h-4 text-blue-500" />
                        Node Properties
                    </h2>
                    <div className="text-xs text-slate-500 mt-1 font-mono">{node.id.slice(0, 8)}...</div>
                </div>

                <div className="p-4 space-y-6">
                    {/* Position */}
                    <Section title="Position" icon={<Move className="w-3 h-3" />}>
                        <div className="grid grid-cols-2 gap-3">
                            <InputGroup label="X" unit="m" value={node.position.x}
                                onChange={(v) => actions.updateNode(node.id, { position: { ...node.position, x: v } })} />
                            <InputGroup label="Y" unit="m" value={node.position.y}
                                onChange={(v) => actions.updateNode(node.id, { position: { ...node.position, y: v } })} />
                        </div>
                    </Section>

                    {/* Support Configuration */}
                    <Section title="Support Conditions">
                        <div className="space-y-3 bg-slate-50 p-3 rounded-lg border border-slate-100">
                            <SupportRow label="Translation X" value={node.supports.fixX}
                                onChange={(v) => actions.updateNode(node.id, { supports: { ...node.supports, fixX: v } })} />

                            <SupportRow label="Translation Y" value={node.supports.fixY}
                                onChange={(v) => actions.updateNode(node.id, { supports: { ...node.supports, fixY: v } })} />

                            <SupportRow label="Rotation M" value={node.supports.fixM} unit="kNm/rad"
                                onChange={(v) => actions.updateNode(node.id, { supports: { ...node.supports, fixM: v } })} />
                        </div>
                    </Section>

                    {/* Rotation Control */}
                    <Section title="Support Rotation">
                        <div className="flex flex-col gap-3">
                            <div className="flex items-center gap-2">
                                <button onClick={() => handleRotationStep(-45)}
                                    className="p-2 hover:bg-slate-100 rounded text-slate-600 border border-slate-200 shadow-sm" title="-45°">
                                    <RotateCcw className="w-4 h-4" />
                                </button>

                                <div className="flex-1 relative">
                                    <input
                                        type="number"
                                        value={Math.round(node.rotation)}
                                        onChange={(e) => actions.updateNode(node.id, { rotation: parseFloat(e.target.value) || 0 })}
                                        className="w-full text-center border-slate-200 border rounded py-1.5 text-sm font-medium focus:ring-2 focus:ring-blue-500 outline-none"
                                    />
                                    <span className="absolute right-3 top-1.5 text-slate-400 text-xs">deg</span>
                                </div>

                                <button onClick={() => handleRotationStep(45)}
                                    className="p-2 hover:bg-slate-100 rounded text-slate-600 border border-slate-200 shadow-sm" title="+45°">
                                    <RotateCw className="w-4 h-4" />
                                </button>
                            </div>
                            <input
                                type="range" min="0" max="360" step="15"
                                value={node.rotation}
                                onChange={(e) => actions.updateNode(node.id, { rotation: parseFloat(e.target.value) })}
                                className="w-full accent-blue-500 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                            />
                        </div>
                    </Section>
                </div>
            </div>
        );
    }

    // --- MEMBER EDITOR ---
    if (selectedType === 'member') {
        const member = members.find(m => m.id === selectedId);
        if (!member) return null;

        return (
            <div className="w-80 bg-white border-l border-slate-200 flex flex-col shadow-xl h-full overflow-y-auto">
                <div className="p-4 border-b border-slate-100 bg-slate-50">
                    <h2 className="font-bold text-slate-800 flex items-center gap-2">
                        <div className="w-4 h-0.5 bg-slate-800 rounded-full"></div>
                        Member Properties
                    </h2>
                    <div className="text-xs text-slate-500 mt-1 font-mono">{member.id.slice(0, 8)}...</div>
                </div>

                <div className="p-4 space-y-6">
                    {/* Stiffness */}
                    <Section title="Material & Section">
                        <div className="grid grid-cols-1 gap-3">
                            <InputGroup label="Young's Modulus (E)" unit="Pa" value={member.properties.E}
                                onChange={(v) => actions.updateMember(member.id, { properties: { ...member.properties, E: v } })} />
                            <InputGroup label="Area (A)" unit="m²" value={member.properties.A}
                                onChange={(v) => actions.updateMember(member.id, { properties: { ...member.properties, A: v } })} />
                            <InputGroup label="Inertia (I)" unit="m⁴" value={member.properties.I}
                                onChange={(v) => actions.updateMember(member.id, { properties: { ...member.properties, I: v } })} />
                        </div>
                    </Section>

                    // Inside PropertiesPanel, specifically the `if (selectedType === 'member')` block:

                    {/* Releases */}
                    <Section title="Hinges / Releases">
                        <div className="space-y-3">
                            {/* Start Node */}
                            <ReleaseGroup
                                label="Start Node"
                                releases={member.releases.start}
                                onChange={(newStart) => actions.updateMember(member.id, {
                                    releases: { ...member.releases, start: newStart }
                                })}
                            />

                            {/* End Node */}
                            <ReleaseGroup
                                label="End Node"
                                releases={member.releases.end}
                                onChange={(newEnd) => actions.updateMember(member.id, {
                                    releases: { ...member.releases, end: newEnd }
                                })}
                            />
                        </div>
                    </Section>

                </div>
            </div>
        );
    }

    return null;
};

// --- Subcomponents for styling ---

const Section = ({ title, icon, children }: { title: string, icon?: React.ReactNode, children: React.ReactNode }) => (
    <div className="space-y-3">
        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            {icon} {title}
        </label>
        {children}
    </div>
);

const InputGroup = ({ label, unit, value, onChange }: { label: string, unit: string, value: number, onChange: (val: number) => void }) => (
    <div>
        <div className="flex justify-between mb-1">
            <span className="text-xs text-slate-500">{label}</span>
        </div>
        <div className="relative">
            <input
                type="number"
                className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                value={value}
                onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
            />
            <span className="absolute right-2 top-1.5 text-xs text-slate-400 pointer-events-none">{unit}</span>
        </div>
    </div>
);

const SupportRow = ({ label, value, unit = "kN/m", onChange }: { label: string, value: SupportValue, unit?: string, onChange: (v: SupportValue) => void }) => {
    // Determine current type
    const type = value === true ? 'fixed' : (typeof value === 'number' ? 'spring' : 'free');

    // Default stiffness if switching to spring
    const DEFAULT_STIFFNESS = 10000;

    return (
        <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-600">{label}</span>
                <select
                    value={type}
                    onChange={(e) => {
                        const newType = e.target.value;
                        if (newType === 'free') onChange(false);
                        else if (newType === 'fixed') onChange(true);
                        else if (newType === 'spring') onChange(DEFAULT_STIFFNESS);
                    }}
                    className="text-xs border border-slate-300 rounded px-1.5 py-1 bg-white focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer"
                >
                    <option value="free">Free</option>
                    <option value="fixed">Fixed</option>
                    <option value="spring">Elastic (Spring)</option>
                </select>
            </div>

            {/* Show stiffness input only if Spring is selected */}
            {type === 'spring' && (
                <div className="relative animate-in fade-in zoom-in-95 duration-200">
                    <input
                        type="number"
                        value={value as number}
                        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
                        className="w-full border border-orange-200 bg-orange-50 rounded px-2 py-1 text-xs text-orange-800 focus:ring-2 focus:ring-orange-500 outline-none"
                    />
                    <span className="absolute right-2 top-1 text-[10px] text-orange-400">{unit}</span>
                </div>
            )}
        </div>
    );
};

const ReleaseGroup = ({ label, releases, onChange }: {
    label: string,
    releases: { fx: boolean, fy: boolean, mz: boolean },
    onChange: (newReleases: { fx: boolean, fy: boolean, mz: boolean }) => void
}) => {
    // 1. Determine current selection state
    let value = 'rigid'; // Default: No release
    if (releases.mz) value = 'moment';
    else if (releases.fy) value = 'shear';
    else if (releases.fx) value = 'axial';

    // 2. Handle change: Set all to false, then enable only the selected one
    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const type = e.target.value;
        const reset = { fx: false, fy: false, mz: false };

        if (type === 'moment') onChange({ ...reset, mz: true });
        else if (type === 'shear') onChange({ ...reset, fy: true });
        else if (type === 'axial') onChange({ ...reset, fx: true });
        else onChange(reset); // 'rigid'
    };

    return (
        <div className="p-3 border border-slate-200 rounded bg-slate-50 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">{label}</span>

            <div className="relative">
                <select
                    value={value}
                    onChange={handleChange}
                    className="
                        appearance-none bg-white border border-slate-300 text-slate-700 
                        text-xs rounded px-3 py-1.5 pr-8 focus:outline-none focus:ring-2 focus:ring-blue-500
                        cursor-pointer shadow-sm min-w-[120px]
                    "
                >
                    <option value="rigid">Rigid (None)</option>
                    <option value="moment">Hinge (M)</option>
                    <option value="shear">Slider (V)</option>
                    <option value="axial">Axial (N)</option>
                </select>

                {/* Custom chevron for better UI */}
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500">
                    <svg className="fill-current h-4 w-4" viewBox="0 0 20 20">
                        <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                    </svg>
                </div>
            </div>
        </div>
    );
};
