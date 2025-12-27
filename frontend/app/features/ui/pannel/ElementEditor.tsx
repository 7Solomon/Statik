import React from 'react';
import { useStore } from '~/store/useStore';
import { ChevronLeft, RotateCcw, RotateCw, Trash2, Anchor } from 'lucide-react';
import type { Node, Member } from '~/types/model';

// Helper to map UI options to your "fixX/fixY/fixM" support model
const applySupportPreset = (node: Node, type: string | null) => {
    // Default: Free
    const newSupports = { fixX: false, fixY: false, fixM: false };

    switch (type) {
        case 'festlager': // Pin
            newSupports.fixX = true; newSupports.fixY = true; break;
        case 'loslager': // Roller (vertical restraint)
            newSupports.fixY = true; break; // Assumes rolling in X
        case 'feste_einspannung': // Fixed
            newSupports.fixX = true; newSupports.fixY = true; newSupports.fixM = true; break;
        case 'gleitlager': // Slider (Horizontal restraint, vertical free)
            newSupports.fixX = true; newSupports.fixM = true; break;
        // Note: For springs ('feder'), you likely set a number instead of boolean
        // This is a simplified mapping.
    }
    return newSupports;
};

// --- Shared Components ---

const EditorHeader = ({ title, type, onDelete, onBack }: any) => (
    <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-white sticky top-0 z-10">
        <div className="flex items-center gap-2">
            <button onClick={onBack} className="p-1.5 hover:bg-slate-100 rounded-md text-slate-500">
                <ChevronLeft size={18} />
            </button>
            <div>
                <h2 className="font-semibold text-slate-800 text-sm">{title}</h2>
                <p className="text-[10px] text-slate-500 uppercase font-bold">{type}</p>
            </div>
        </div>
        <button onClick={onDelete} className="p-2 text-red-400 hover:bg-red-50 hover:text-red-600 rounded-md">
            <Trash2 size={16} />
        </button>
    </div>
);

const NumberInput = ({ label, value, onChange, unit, step = 0.1 }: any) => (
    <div className="flex items-center justify-between gap-2 text-sm">
        <label className="text-slate-500 w-20 shrink-0 truncate">{label}</label>
        <div className="flex items-center relative w-full">
            <input
                type="number" step={step} value={value}
                onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1.5 text-right pr-7 font-mono text-xs"
            />
            {unit && <span className="absolute right-2 text-slate-400 text-[10px] pointer-events-none">{unit}</span>}
        </div>
    </div>
);

// --- NODE EDITOR ---

export const NodeEditor = ({ nodeId }: { nodeId: string }) => {
    const node = useStore(s => s.nodes.find(n => n.id === nodeId));
    const actions = useStore(s => s.actions);

    if (!node) return null;

    const updatePos = (key: 'x' | 'y', val: number) => {
        actions.updateNode(node.id, { position: { ...node.position, [key]: val } });
    };

    const handleSupportChange = (type: string | null) => {
        const newSupports = applySupportPreset(node, type);
        actions.updateNode(node.id, { supports: newSupports });
    };

    return (
        <div className="flex flex-col h-full bg-white">
            <EditorHeader
                title={`Node ${node.id.slice(0, 4)}`} type="Geometry"
                onBack={() => actions.setInteraction({ selectedId: null, selectedType: null })}
                onDelete={() => {
                    actions.removeNode(node.id);
                    actions.setInteraction({ selectedId: null, selectedType: null });
                }}
            />

            <div className="p-4 space-y-6 overflow-y-auto">
                {/* Position */}
                <div className="space-y-3">
                    <label className="text-xs font-bold text-slate-400 uppercase">Coordinates</label>
                    <NumberInput label="X-Pos" value={node.position.x} onChange={(v: number) => updatePos('x', v)} unit="m" />
                    <NumberInput label="Y-Pos" value={node.position.y} onChange={(v: number) => updatePos('y', v)} unit="m" />
                </div>

                <div className="h-px bg-slate-100" />

                {/* Supports Manual Override */}
                <div className="space-y-3">
                    <label className="text-xs font-bold text-slate-400 uppercase flex gap-2 items-center">
                        <Anchor size={12} /> Boundary Conditions
                    </label>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                        {['X', 'Y', 'M'].map((dof) => {
                            const key = `fix${dof}` as keyof typeof node.supports;
                            const isActive = !!node.supports[key]; // force boolean
                            return (
                                <button
                                    key={dof}
                                    onClick={() => actions.updateNode(node.id, {
                                        supports: { ...node.supports, [key]: !isActive }
                                    })}
                                    className={`py-1.5 rounded border ${isActive ? 'bg-blue-100 border-blue-300 text-blue-700' : 'bg-slate-50 border-slate-200 text-slate-500'}`}
                                >
                                    Fix {dof}
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Rotation */}
                <div className="space-y-3">
                    <label className="text-xs font-bold text-slate-400 uppercase">Support Rotation</label>
                    <div className="flex gap-2 mb-2">
                        <button onClick={() => actions.updateNode(node.id, { rotation: (node.rotation - 45) % 360 })} className="btn-icon-sm"><RotateCcw size={14} /></button>
                        <button onClick={() => actions.updateNode(node.id, { rotation: (node.rotation + 45) % 360 })} className="btn-icon-sm"><RotateCw size={14} /></button>
                    </div>
                    <NumberInput label="Angle" value={node.rotation} onChange={(v: number) => actions.updateNode(node.id, { rotation: v })} unit="°" />
                </div>
            </div>
        </div>
    );
};

// --- MEMBER EDITOR ---

export const MemberEditor = ({ memberId }: { memberId: string }) => {
    const member = useStore(s => s.members.find(m => m.id === memberId));
    const actions = useStore(s => s.actions);

    if (!member) return null;

    const updateProp = (key: keyof Member['properties'], val: number) => {
        actions.updateMember(member.id, { properties: { ...member.properties, [key]: val } });
    };

    return (
        <div className="flex flex-col h-full bg-white">
            <EditorHeader
                title="Member" type="Beam Element"
                onBack={() => actions.setInteraction({ selectedId: null, selectedType: null })}
            //onDelete={() => {
            //    actions.removeMember(member.id);
            //    actions.setInteraction({ selectedId: null, selectedType: null });
            //}}
            />

            <div className="p-4 space-y-6 overflow-y-auto">
                <div className="space-y-3">
                    <label className="text-xs font-bold text-slate-400 uppercase">Stiffness Properties</label>
                    <NumberInput
                        label="Young's (E)" value={member.properties.E}
                        onChange={(v: number) => updateProp('E', v)} unit="kN/m²" step={1000}
                    />
                    <NumberInput
                        label="Area (A)" value={member.properties.A}
                        onChange={(v: number) => updateProp('A', v)} unit="m²" step={0.001}
                    />
                    <NumberInput
                        label="Inertia (I)" value={member.properties.I}
                        onChange={(v: number) => updateProp('I', v)} unit="m⁴" step={0.0001}
                    />
                </div>

                <div className="h-px bg-slate-100" />

                <div className="space-y-3">
                    <label className="text-xs font-bold text-slate-400 uppercase">Hinges (Releases)</label>
                    <div className="flex flex-col gap-2">
                        {['start', 'end'].map((loc) => (
                            <div key={loc} className="flex items-center justify-between text-sm">
                                <span className="text-slate-600 capitalize">{loc}:</span>
                                <button
                                    onClick={() => {
                                        const current = member.releases[loc as 'start' | 'end'].mz;
                                        actions.updateMember(member.id, {
                                            releases: {
                                                ...member.releases,
                                                [loc]: { ...member.releases[loc as 'start' | 'end'], mz: !current }
                                            }
                                        });
                                    }}
                                    className={`px-3 py-1 text-xs rounded border ${member.releases[loc as 'start' | 'end'].mz ? 'bg-orange-50 border-orange-200 text-orange-600' : 'bg-slate-50 text-slate-400'}`}
                                >
                                    {member.releases[loc as 'start' | 'end'].mz ? 'Hinged' : 'Rigid'}
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
