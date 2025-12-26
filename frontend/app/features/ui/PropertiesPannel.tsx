import React from 'react';
import { useStore } from '../../store/useStore';

export const PropertiesPanel = () => {
    const { selectedId, selectedType } = useStore(s => s.interaction);
    const nodes = useStore(s => s.nodes);
    const members = useStore(s => s.members);
    const actions = useStore(s => s.actions);

    if (!selectedId || !selectedType) {
        return (
            <div className="w-64 bg-white border-l border-slate-200 p-4 text-slate-400 text-sm">
                Select an element to edit properties.
            </div>
        );
    }

    // --- NODE EDITOR ---
    if (selectedType === 'node') {
        const node = nodes.find(n => n.id === selectedId);
        if (!node) return null;

        return (
            <div className="w-80 bg-white border-l border-slate-200 p-4 flex flex-col gap-6 shadow-xl z-20">
                <h2 className="font-bold text-lg text-slate-800 border-b pb-2">Node Properties</h2>

                {/* Coordinates */}
                <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-500 uppercase">Position</label>
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <span className="text-xs text-slate-400">X (m)</span>
                            <input
                                type="number"
                                className="w-full border rounded px-2 py-1 text-sm"
                                value={node.position.x}
                                onChange={(e) => actions.updateNode(node.id, { position: { ...node.position, x: parseFloat(e.target.value) } })}
                            />
                        </div>
                        <div>
                            <span className="text-xs text-slate-400">Y (m)</span>
                            <input
                                type="number"
                                className="w-full border rounded px-2 py-1 text-sm"
                                value={node.position.y}
                                onChange={(e) => actions.updateNode(node.id, { position: { ...node.position, y: parseFloat(e.target.value) } })}
                            />
                        </div>
                    </div>
                </div>

                {/* Support Configuration */}
                <div className="space-y-3">
                    <label className="text-xs font-semibold text-slate-500 uppercase">Support Conditions</label>
                    <div className="flex flex-col gap-2">
                        <label className="flex items-center gap-2 text-sm">
                            <input type="checkbox" checked={node.supports.fixX}
                                onChange={e => actions.updateNode(node.id, { supports: { ...node.supports, fixX: e.target.checked } })} />
                            Fixed X
                        </label>
                        <label className="flex items-center gap-2 text-sm">
                            <input type="checkbox" checked={node.supports.fixY}
                                onChange={e => actions.updateNode(node.id, { supports: { ...node.supports, fixY: e.target.checked } })} />
                            Fixed Y
                        </label>
                        <label className="flex items-center gap-2 text-sm">
                            <input type="checkbox" checked={node.supports.fixM}
                                onChange={e => actions.updateNode(node.id, { supports: { ...node.supports, fixM: e.target.checked } })} />
                            Fixed Rotation (Moment)
                        </label>
                    </div>
                </div>

                {/* ROTATION (Your Request) */}
                {(node.supports.fixX || node.supports.fixY) && (
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-500 uppercase">Support Rotation</label>
                        <div className="flex items-center gap-2">
                            <input
                                type="range" min="0" max="360"
                                value={node.rotation || 0}
                                onChange={(e) => actions.updateNode(node.id, { rotation: parseInt(e.target.value) })}
                                className="flex-1"
                            />
                            <input
                                type="number"
                                className="w-16 border rounded px-2 py-1 text-sm text-center"
                                value={node.rotation || 0}
                                onChange={(e) => actions.updateNode(node.id, { rotation: parseFloat(e.target.value) })}
                            />
                            <span className="text-sm text-slate-500">deg</span>
                        </div>
                    </div>
                )}
            </div>
        );
    }

    // --- MEMBER EDITOR ---
    if (selectedType === 'member') {
        const member = members.find(m => m.id === selectedId);
        if (!member) return null;

        return (
            <div className="w-80 bg-white border-l border-slate-200 p-4 flex flex-col gap-6 shadow-xl z-20">
                <h2 className="font-bold text-lg text-slate-800 border-b pb-2">Member Properties</h2>

                {/* RELEASES (Your Request) */}
                <div className="space-y-4">
                    <label className="text-xs font-semibold text-slate-500 uppercase">Hinges / Releases</label>

                    {/* Start Node Connection */}
                    <div className="bg-slate-50 p-3 rounded border border-slate-200">
                        <div className="text-xs font-bold text-slate-600 mb-2">Start Node</div>
                        <div className="flex gap-4">
                            <label className="flex items-center gap-2 text-sm cursor-pointer" title="Moment Free">
                                <input type="checkbox" checked={member.releases.start.mz}
                                    onChange={e => actions.updateMember(member.id, {
                                        releases: { ...member.releases, start: { ...member.releases.start, mz: e.target.checked } }
                                    })} />
                                <span>Hinge (Mz)</span>
                            </label>
                            {/* Advanced Releases (hidden for now or added if needed) */}
                        </div>
                    </div>

                    {/* End Node Connection */}
                    <div className="bg-slate-50 p-3 rounded border border-slate-200">
                        <div className="text-xs font-bold text-slate-600 mb-2">End Node</div>
                        <div className="flex gap-4">
                            <label className="flex items-center gap-2 text-sm cursor-pointer">
                                <input type="checkbox" checked={member.releases.end.mz}
                                    onChange={e => actions.updateMember(member.id, {
                                        releases: { ...member.releases, end: { ...member.releases.end, mz: e.target.checked } }
                                    })} />
                                <span>Hinge (Mz)</span>
                            </label>
                        </div>
                    </div>
                </div>

                {/* Stiffness Properties */}
                <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-500 uppercase">Stiffness</label>
                    <div className="grid grid-cols-1 gap-2">
                        <div className="flex justify-between items-center">
                            <span className="text-sm text-slate-600">E (Young's)</span>
                            <input type="number" className="w-24 border rounded px-2 py-1 text-sm"
                                value={member.properties.E}
                                onChange={(e) => actions.updateMember(member.id, { properties: { ...member.properties, E: parseFloat(e.target.value) } })} />
                        </div>
                        <div className="flex justify-between items-center">
                            <span className="text-sm text-slate-600">I (Inertia)</span>
                            <input type="number" className="w-24 border rounded px-2 py-1 text-sm"
                                value={member.properties.I}
                                onChange={(e) => actions.updateMember(member.id, { properties: { ...member.properties, I: parseFloat(e.target.value) } })} />
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return null;
};
