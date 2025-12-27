import React from 'react';
import { MousePointer2, Circle, Route, Square } from 'lucide-react';
import { useStore } from '~/store/useStore';
import supportLibraryRaw from '~/assets/support_symbols.json';
import hingeLibraryRaw from '~/assets/hinge_symbols.json';

import type { ToolType, SupportType, HingeType } from '~/types/app';

const UI_SYMBOL_LIBRARY = {
    ...(supportLibraryRaw as any),
    ...(hingeLibraryRaw as any)
};

// 1. Define the shape of a Toolbar Item
type ToolItemConfig = {
    label: string;
    tool: ToolType;
    subType: SupportType | HingeType | null;
    icon?: React.ReactNode;
    symbolKey?: string;
};

type ToolGroupConfig = {
    title: string;
    items: ToolItemConfig[];
};

// 2. Define the Configuration
const TOOL_GROUPS: ToolGroupConfig[] = [
    {
        title: "Edit",
        items: [
            {
                label: 'Select',
                tool: 'select',
                subType: null,
                icon: <MousePointer2 size={18} />
            },
            {
                label: 'Node',
                tool: 'node',
                subType: null,
                icon: <Circle size={18} />
            },
            {
                label: 'Member',
                tool: 'member',
                subType: null,
                icon: <Route size={18} />
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
            { label: 'Feder', tool: 'node', subType: 'feder', symbolKey: 'FEDER' },
            { label: 'Drehfeder', tool: 'node', subType: 'torsionsfeder', symbolKey: 'TORSIONSFEDER' },
        ]
    },
    {
        title: "Gelenke", // Hinges
        items: [
            {
                label: 'Vollgelenk',
                tool: 'hinge',
                subType: 'vollgelenk',
                symbolKey: 'VOLLGELENK'
            },
            {
                label: 'Schubgelenk',
                tool: 'hinge',
                subType: 'schubgelenk',
                symbolKey: 'SCHUBGELENK'
            },
            {
                label: 'Normalkraft',
                tool: 'hinge',
                subType: 'normalkraftgelenk',
                symbolKey: 'NORMALKRAFTGELENK'
            },
            {
                label: 'Rigid (Reset)',
                tool: 'hinge',
                subType: 'biegesteife_ecke',
                icon: <Square size={18} className="text-slate-500 fill-slate-300" />
            },
        ]
    }
];

export const ToolBar = () => {
    const activeTool = useStore(state => state.interaction.activeTool);
    const activeSubType = useStore(state => state.interaction.activeSubTypeTool);
    const actions = useStore(state => state.actions);

    const handleToolClick = (item: ToolItemConfig) => {
        // Set both the main tool and the sub-type
        actions.setTool(item.tool);
        actions.setInteraction({ activeSubTypeTool: item.subType });
    };

    return (
        <div className="flex gap-6">
            {TOOL_GROUPS.map((group, idx) => (
                <div key={idx} className="flex gap-2 items-center">
                    {/* Group Label */}
                    <span className="text-xs text-slate-400 font-medium uppercase tracking-wider mr-2 hidden xl:block">
                        {group.title}
                    </span>

                    {/* Buttons */}
                    {group.items.map((item, i) => {
                        // Determine active state by checking BOTH tool and subType
                        const isActive = activeTool === item.tool && activeSubType === item.subType;

                        return (
                            <ToolButton
                                key={i}
                                item={item}
                                isActive={isActive}
                                onClick={() => handleToolClick(item)}
                            />
                        );
                    })}

                    {/* Separator between groups */}
                    {idx < TOOL_GROUPS.length - 1 && (
                        <div className="w-px h-8 bg-slate-200 mx-2" />
                    )}
                </div>
            ))}
        </div>
    );
};

// --- Sub Components ---

const ToolButton = ({ item, isActive, onClick }: { item: ToolItemConfig, isActive: boolean, onClick: () => void }) => {
    return (
        <button
            onClick={onClick}
            title={item.label}
            className={`
        flex flex-col items-center justify-center w-10 h-10 lg:w-12 lg:h-12 rounded-lg transition-all duration-200 border
        ${isActive
                    ? 'bg-blue-50 border-blue-200 text-blue-600 shadow-inner'
                    : 'bg-white border-transparent text-slate-500 hover:bg-slate-50 hover:border-slate-200 hover:text-slate-700'
                }
      `}
        >
            {item.icon ? item.icon : <SymbolIcon symbolKey={item.symbolKey!} isActive={isActive} />}
        </button>
    );
};

const SymbolIcon = ({ symbolKey, isActive }: { symbolKey: string, isActive: boolean }) => {
    const paths = UI_SYMBOL_LIBRARY[symbolKey] || [];

    // Safety check if path is empty (like for the rigid corner in your JSON)
    if (paths.length === 0) return <div className="w-4 h-4 bg-slate-300 rounded-sm opacity-50" />;

    return (
        <svg width="24" height="24" viewBox="-25 -25 50 50" className="overflow-visible">
            {paths.map((op: any, i: number) => (
                <path
                    key={i}
                    d={op.d}
                    fill={op.type === 'fill' ? (isActive ? '#3b82f6' : '#94a3b8') : 'none'}
                    stroke={op.type === 'stroke' ? (isActive ? '#3b82f6' : '#475569') : 'none'}
                    strokeWidth={op.width || 2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    vectorEffect="non-scaling-stroke"
                />
            ))}
        </svg>
    );
};
