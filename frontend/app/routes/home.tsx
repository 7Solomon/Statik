import { useState, useEffect, useRef } from "react";
import { PropertiesPanel } from "~/features/ui/PropertiesPannel";
import EditorCanvas from "../features/editor/EditorCanvas";
import { useStore } from "../store/useStore";
import { MousePointer2, Circle, Route, Save, FileDown, Loader2, X, FolderOpen } from 'lucide-react';

import supportLibraryRaw from '~/assets/support_symbols.json';
import type { ToolType } from "~/types/app";
import type { JSX } from "react";
import { AnalyzeSystemModal } from "~/features/modals/AnalyzeSystemModal";
import { LoadSystemModal } from "~/features/modals/LoadSystemModal";
import { SaveSystemModal } from "~/features/modals/SaveSystemModal";
import AnalysisViewer from "~/features/analysis/AnalysisViewer";

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
]

export default function Home() {
  const mode = useStore(state => state.mode);
  const setMode = useStore(state => state.actions.setMode);

  const activeTool = useStore(state => state.interaction.activeTool);
  const setTool = useStore(state => state.actions.setTool);
  const analyzeSystem = useStore(state => state.actions.analyzeSystem);


  // Modal States
  const [modalOpen, setModalOpen] = useState<'save' | 'load' | 'analyze' | null>(null);
  const [currentProjectName, setCurrentProjectName] = useState("Structure 01");

  const handleAnalysisComplete = (result: any) => {
    setMode('ANALYSIS');
    setModalOpen(null); // Close modal
  };

  const handleLoadConfirm = async (slug: string) => {
    // You'll need to implement a `loadSystem` action in your store later
    console.log("Loading slug:", slug);
    // await store.actions.loadSystem(slug);
    //setModalOpen(null);
  }

  const handleSaveConfirm = async (slug: string) => {
    // You'll need to implement a `loadSystem` action in your store later
    console.log("Loading slug:", slug);
    // await store.actions.loadSystem(slug);
    //setModalOpen(null);
  }
  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-50">
      <header className="h-16 border-b border-slate-200 bg-white flex items-center px-6 gap-6 shadow-sm z-20 shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="font-bold text-xl text-slate-800 tracking-tight">Statik</h1>
          <div className="w-px h-8 bg-slate-200"></div>
        </div>

        {/* Clean File Menu */}
        <div className="flex items-center gap-1 mr-auto">
          <HeaderButton icon={<FolderOpen size={16} />} label="Open" onClick={() => setModalOpen('load')} />
          <HeaderButton icon={<Save size={16} />} label="Save" onClick={() => setModalOpen('save')} />
          <div className="w-px h-4 bg-slate-200 mx-2"></div>
          <HeaderButton icon={<FileDown size={16} />} label="Analyze System" onClick={() => setModalOpen('analyze')} />
        </div>

        {/* 3. Drawing Tools */}
        <div className="flex gap-6">
          {TOOL_GROUPS.map((group, idx) => (
            <div key={idx} className="flex gap-2 items-center">
              <span className="text-xs text-slate-400 font-medium uppercase tracking-wider mr-2 hidden xl:block">{group.title}</span>
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

          {/* VIEW SWITCHER */}
          {mode === 'EDITOR' ? (
            <EditorCanvas />
          ) : (
            <AnalysisViewer />
          )}

        </main>

        {/* Hide Properties Panel during Analysis to give full screen to results */}
        {mode === 'EDITOR' && <PropertiesPanel />}
      </div>

      {/* MODALS */}
      {modalOpen === 'save' && (
        <div></div>
        //<SaveSystemModal
        //  onConfirm={handleSaveConfirm}
        //  onClose={() => setModalOpen(null)}
        ///>
      )}

      {modalOpen === 'load' && (
        <LoadSystemModal
          onClose={() => setModalOpen(null)}
          onLoad={handleLoadConfirm}
        />
      )}

      {modalOpen === 'analyze' && (
        <AnalyzeSystemModal
          onClose={() => setModalOpen(null)}
          onAnalysisComplete={handleAnalysisComplete}
        />
      )}
    </div>
  );
}

// Small helper for the top menu to keep JSX clean
function HeaderButton({ icon, label, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-slate-100 text-slate-600 hover:text-blue-600 transition-colors font-medium text-sm"
    >
      {icon}
      {label}
    </button>
  )
}

// --- Helper Components ---

function ToolButton({ label, isActive, onClick, icon, symbolKey }: any) {
  return (
    <button
      onClick={onClick}
      title={label}
      className={`
        flex flex-col items-center justify-center w-10 h-10 lg:w-12 lg:h-12 rounded-lg transition-all duration-200 border
        ${isActive
          ? 'bg-blue-50 border-blue-200 text-blue-600 shadow-inner'
          : 'bg-white border-transparent text-slate-500 hover:bg-slate-50 hover:border-slate-200 hover:text-slate-700'
        }
      `}
    >
      {icon ? icon : <SymbolIcon symbolKey={symbolKey} isActive={isActive} />}
    </button>
  );
}

function SymbolIcon({ symbolKey, isActive }: { symbolKey: string, isActive: boolean }) {
  const paths = (supportLibraryRaw as any)[symbolKey] || [];
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
}
