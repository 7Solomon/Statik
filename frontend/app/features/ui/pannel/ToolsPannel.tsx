import React from 'react';
import { MousePointer2, Circle, Route, Square, ArrowDown, RotateCw, Waves } from 'lucide-react';
import { useStore } from '~/store/useStore';
import supportLibraryRaw from '~/assets/support_symbols.json';
import hingeLibraryRaw from '~/assets/hinge_symbols.json';
import type { ToolType, SupportType, HingeType, LoadType } from '~/types/app';

// Merge symbol libraries
const UI_SYMBOL_LIBRARY = {
    ...(supportLibraryRaw as any),
    ...(hingeLibraryRaw as any)
};

// --- Types ---
type ToolItemConfig = {
    label: string;
    tool: ToolType;
    subType: SupportType | HingeType | LoadType | null;
    icon?: React.ReactNode;
    symbolKey?: string;
    description?: string;
};

type ToolGroupConfig = {
    title: string;
    items: ToolItemConfig[];
};

// --- Configuration ---
const TOOL_GROUPS: ToolGroupConfig[] = [
    {
        title: "Tools",
        items: [
            {
                label: 'Select',
                tool: 'select',
                subType: null,
                icon: <MousePointer2 size={20} />,
                description: "Select and edit elements"
            },
            {
                label: 'Member',
                tool: 'member',
                subType: null,
                icon: <Route size={20} />,
                description: "Draw beams and columns"
            },
            {
                label: 'Node',
                tool: 'node',
                subType: null,
                icon: <Circle size={20} />,
                description: "Place free nodes"
            },
        ]
    },
    {
        title: "Supports",
        items: [
            { label: 'Festlager', tool: 'node', subType: 'festlager', symbolKey: 'FESTLAGER' },
            { label: 'Loslager', tool: 'node', subType: 'loslager', symbolKey: 'LOSLAGER' },
            { label: 'Einspannung', tool: 'node', subType: 'feste_einspannung', symbolKey: 'FESTE_EINSPANNUNG' },
            { label: 'Gleitlager', tool: 'node', subType: 'gleitlager', symbolKey: 'GLEITLAGER' },
            // { label: 'Feder', tool: 'node', subType: 'feder', symbolKey: 'FEDER' },
        ]
    },
    {
        title: "Hinges (Member Ends)",
        items: [
            { label: 'Vollgelenk', tool: 'hinge', subType: 'vollgelenk', symbolKey: 'VOLLGELENK' },
            { label: 'Schubgelenk', tool: 'hinge', subType: 'schubgelenk', symbolKey: 'SCHUBGELENK' },
            { label: 'Normalkraft', tool: 'hinge', subType: 'normalkraftgelenk', symbolKey: 'NORMALKRAFTGELENK' },
            { label: 'Rigid Reset', tool: 'hinge', subType: 'biegesteife_ecke', icon: <Square size={18} className="text-slate-400 fill-slate-200" /> },
        ]
    },
    {
        title: "Loads",
        items: [
            {
                label: 'Point Load',
                tool: 'load',
                subType: 'point',
                icon: <ArrowDown size={20} />,
                description: "Force on a Node (10kN)"
            },
            {
                label: 'Moment',
                tool: 'load',
                subType: 'moment',
                icon: <RotateCw size={20} />,
                description: "Moment on a Node (10kNm)"
            },
            {
                label: 'Dist. Load',
                tool: 'load',
                subType: 'distributed',
                icon: <Waves size={20} />,
                description: "Line load on Member (5kN/m)"
            },
        ]
    },
];

export const ToolsPanel = () => {
    const activeTool = useStore(state => state.editor.interaction.activeTool);
    const activeSubType = useStore(state => state.editor.interaction.activeSubTypeTool);
    const actions = useStore(state => state.editor.actions);

    const handleToolClick = (item: ToolItemConfig) => {
        // 1. Set the main tool (e.g., 'node' or 'member')
        actions.setTool(item.tool);
        // 2. Set the specific type (e.g., 'festlager')
        actions.setInteraction({ activeSubTypeTool: item.subType });
        // 3. Clear selection so we don't accidentally edit while trying to place
        actions.setInteraction({ selectedId: null, selectedType: null });
    };

    return (
        <div className="flex flex-col h-full w-full bg-white">
            <div className="p-5 border-b border-slate-100">
                <h2 className="font-bold text-slate-800 text-lg">Toolbox</h2>
                <p className="text-xs text-slate-400 mt-1">Select a tool to interact with the canvas</p>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-8 scrollbar-thin scrollbar-thumb-slate-200">
                {TOOL_GROUPS.map((group, idx) => (
                    <div key={idx} className="flex flex-col gap-3">
                        <div className="flex items-center gap-2">
                            <div className="h-px bg-slate-200 flex-1"></div>
                            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                                {group.title}
                            </span>
                            <div className="h-px bg-slate-200 flex-1"></div>
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                            {group.items.map((item, i) => {
                                // Logic: Is this button active?
                                // If it has a subtype, both tool AND subtype must match.
                                // If it has NO subtype (like Select), only tool must match.
                                const isActive = item.subType
                                    ? activeTool === item.tool && activeSubType === item.subType
                                    : activeTool === item.tool && activeSubType === null;

                                return (
                                    <ToolButton
                                        key={i}
                                        item={item}
                                        isActive={isActive}
                                        onClick={() => handleToolClick(item)}
                                    />
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 text-xs text-slate-400 text-center">
                Statik Editor v1.0
            </div>
        </div>
    );
};

// --- Sub Components ---

const ToolButton = ({ item, isActive, onClick }: { item: ToolItemConfig, isActive: boolean, onClick: () => void }) => {
    return (
        <button
            onClick={onClick}
            className={`
                flex flex-col items-center justify-center p-3 rounded-xl transition-all duration-200 border relative group
                ${isActive
                    ? 'bg-blue-50 border-blue-500 text-blue-600 shadow-sm ring-1 ring-blue-500 z-10'
                    : 'bg-white border-slate-200 text-slate-500 hover:border-blue-300 hover:shadow-md hover:-translate-y-0.5'
                }
            `}
        >
            <div className="mb-2">
                {item.icon ? item.icon : <SymbolIcon symbolKey={item.symbolKey!} isActive={isActive} />}
            </div>
            <span className="text-xs font-medium text-center leading-tight">
                {item.label}
            </span>

            {/* Tooltip for description if available */}
            {item.description && (
                <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity bg-slate-800 text-white text-[10px] px-2 py-1 rounded top-full mt-2 z-50 whitespace-nowrap pointer-events-none">
                    {item.description}
                </div>
            )}
        </button>
    );
};

const SymbolIcon = ({ symbolKey, isActive }: { symbolKey: string, isActive: boolean }) => {
    const paths = UI_SYMBOL_LIBRARY[symbolKey] || [];

    // Fallback if JSON is missing the key
    if (paths.length === 0) return <div className="w-6 h-6 bg-slate-100 rounded border border-slate-300 border-dashed" />;

    return (
        <svg width="28" height="28" viewBox="-25 -25 50 50" className="overflow-visible pointer-events-none">
            {paths.map((op: any, i: number) => (
                <path
                    key={i}
                    d={op.d}
                    fill={op.type === 'fill' ? (isActive ? '#2563eb' : '#94a3b8') : 'none'}
                    stroke={op.type === 'stroke' ? (isActive ? '#2563eb' : '#475569') : 'none'}
                    strokeWidth={op.width || 2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    vectorEffect="non-scaling-stroke"
                />
            ))}
        </svg>
    );
};
