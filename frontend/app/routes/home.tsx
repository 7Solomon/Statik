import { PropertiesPanel } from "~/features/ui/PropertiesPannel";
import EditorCanvas from "../features/editor/EditorCanvas";
import { useStore } from "../store/useStore";
import { MousePointer2, Circle, PenTool, Route } from 'lucide-react';

import supportLibraryRaw from '~/assets/support_symbols.json';
import type { ToolType } from "~/types/app";
import type { JSX } from "react";

export function meta() {
  return [
    { title: "Statik React Editor" },
    { name: "description", content: "Structural Analysis Editor" },
  ];
}

type ToolConfig = {
  id: ToolType;
  label: string;
  icon?: JSX.Element;
  symbol?: string;
};

const TOOL_GROUPS: { title: string, tools: ToolConfig[] }[] = [
  {
    title: "Edit",
    tools: [
      { id: 'select', label: 'Select', icon: <MousePointer2 size={18} /> },
      { id: 'node', label: 'Node', icon: <Circle size={18} /> },
      { id: 'member', label: 'Member', icon: <Route size={18} /> },
    ]
  },
  {
    title: "Supports",
    tools: [
      { id: 'support_festlager', label: 'Festlager', symbol: 'SUPPORT_FESTLAGER' },
      { id: 'support_loslager', label: 'Loslager', symbol: 'SUPPORT_LOSLAGER' },
      { id: 'support_feste_einspannung', label: 'Einspannung', symbol: 'SUPPORT_FESTE_EINSPANNUNG' },
      { id: 'support_gleitlager', label: 'Gleitlager', symbol: 'SUPPORT_GLEITLAGER' },
      { id: 'support_feder', label: 'Feder', symbol: 'SUPPORT_FEDER' },
      { id: 'support_torsionsfeder', label: 'Drehfeder', symbol: 'SUPPORT_TORSIONSFEDER' },
    ]
  }
];

export default function Home() {
  const activeTool = useStore(state => state.interaction.activeTool);
  const setTool = useStore(state => state.actions.setTool);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-50">
      {/* HEADER / TOOLBAR */}
      <header className="h-16 border-b border-slate-200 bg-white flex items-center px-6 gap-6 shadow-sm z-20 shrink-0">
        <h1 className="font-bold text-xl text-slate-800 tracking-tight">Statik</h1>
        <div className="w-px h-8 bg-slate-200"></div>

        <div className="flex gap-6">
          {TOOL_GROUPS.map((group, idx) => (
            <div key={idx} className="flex gap-2 items-center">
              {/* Optional Group Label */}
              <span className="text-xs text-slate-400 font-medium uppercase tracking-wider mr-2">{group.title}</span>

              {group.tools.map(tool => (
                <ToolButton
                  key={tool.id}
                  label={tool.label}
                  isActive={activeTool === tool.id}
                  onClick={() => setTool(tool.id)}
                  icon={tool.icon}
                  symbolKey={tool.symbol}
                />
              ))}

              {idx < TOOL_GROUPS.length - 1 && <div className="w-px h-8 bg-slate-200 mx-2"></div>}
            </div>
          ))}
        </div>
      </header>

      <div className="flex flex-1 relative overflow-hidden">
        <main className="flex-1 relative bg-slate-100/50">
          <EditorCanvas />
        </main>
        <PropertiesPanel />
      </div>
    </div>
  );
}

// --- Helper Components ---

function ToolButton({ label, isActive, onClick, icon, symbolKey }: any) {
  return (
    <button
      onClick={onClick}
      title={label}
      className={`
        flex flex-col items-center justify-center w-12 h-12 rounded-lg transition-all duration-200 border
        ${isActive
          ? 'bg-blue-50 border-blue-200 text-blue-600 shadow-inner'
          : 'bg-white border-transparent text-slate-500 hover:bg-slate-50 hover:border-slate-200 hover:text-slate-700'
        }
      `}
    >
      {icon ? icon : <SymbolIcon symbolKey={symbolKey} isActive={isActive} />}
      {/* <span className="text-[10px] mt-0.5 font-medium opacity-80">{label}</span> */}
    </button>
  );
}

function SymbolIcon({ symbolKey, isActive }: { symbolKey: string, isActive: boolean }) {
  // Find the paths from the JSON library
  const paths = (supportLibraryRaw as any)[symbolKey] || [];

  // Calculate bounding box roughly to center SVG (0,0 is origin of symbol)
  // Our symbols are approx 40x40 area centered at 0,0.
  // ViewBox -20 -20 40 40 puts 0,0 in center.

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
          vectorEffect="non-scaling-stroke" // Keeps lines sharp even if scaled
        />
      ))}
    </svg>
  );
}
