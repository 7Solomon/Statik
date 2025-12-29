import { useState } from "react";
import EditorCanvas from "../features/editor/EditorCanvas";
import { useStore } from "../store/useStore";
import { Save, FolderOpen, LayoutDashboard, Calculator } from 'lucide-react';
import { SaveSystemModal } from "~/features/modals/SaveSystemModal";
import { LoadSystemModal } from "~/features/modals/LoadSystemModal";
import { SidePanel } from "~/features/ui/SidePannel";
import AnalysisViewer from "~/features/analysis/AnalysisViewer";

export default function Home() {
  const mode = useStore(state => state.shared.mode);
  const setMode = useStore(state => state.shared.actions.setMode);

  // Editor state to sync to analysis
  const nodes = useStore(s => s.editor.nodes);
  const members = useStore(s => s.editor.members);
  const loads = useStore(s => s.editor.loads);

  const startAnalysis = useStore(state => state.analysis.actions.startAnalysis);
  const clearAnalysis = useStore(state => state.analysis.actions.clearAnalysisSession);

  const [modalOpen, setModalOpen] = useState<'save' | 'load' | null>(null);

  const handleToggleMode = () => {
    if (mode === 'EDITOR') {
      // 1. Initialize Analysis Session with current Editor System

      startAnalysis({ nodes, members, loads });
      // 2. Mode switch is handled automatically by startAnalysis in your store, 
      // but if not, you can call setMode('ANALYSIS') here.
    } else {
      // Switch back to Editor
      clearAnalysis(); // This should set mode to EDITOR
    }
  };

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-50">
      <header className="h-14 border-b border-slate-200 bg-white flex items-center px-4 gap-4 shadow-sm z-20 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-md flex items-center justify-center text-white font-bold">S</div>
          <h1 className="font-bold text-lg text-slate-800 tracking-tight">Statik</h1>
        </div>

        <div className="w-px h-6 bg-slate-200 mx-2"></div>

        {/* Left Actions */}
        <div className="flex items-center gap-1 mr-auto">
          <HeaderButton icon={<FolderOpen size={16} />} label="Open" onClick={() => setModalOpen('load')} />
          <HeaderButton icon={<Save size={16} />} label="Save" onClick={() => setModalOpen('save')} />
        </div>

        {/* Center Mode Switcher */}
        <div className="absolute left-1/2 -translate-x-1/2 bg-slate-100 p-1 rounded-lg flex gap-1 border border-slate-200">
          <button
            onClick={() => mode === 'ANALYSIS' && handleToggleMode()}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-all ${mode === 'EDITOR' ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
          >
            <LayoutDashboard size={14} />
            <span>Editor</span>
          </button>
          <button
            onClick={() => mode === 'EDITOR' && handleToggleMode()}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-all ${mode === 'ANALYSIS' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
          >
            <Calculator size={14} />
            <span>Analysis</span>
          </button>
        </div>

      </header>

      <div className="flex flex-1 relative overflow-hidden">
        <main className="flex-1 relative bg-slate-100/50">
          {mode === 'EDITOR' ? <EditorCanvas /> : <AnalysisViewer />}
        </main>
        {mode === 'EDITOR' && <SidePanel />}
      </div>

      {/* MODALS */}
      {modalOpen === 'save' && <SaveSystemModal onClose={() => setModalOpen(null)} />}
      {modalOpen === 'load' && <LoadSystemModal onClose={() => setModalOpen(null)} />}
    </div>
  );
}

function HeaderButton({ icon, label, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-slate-100 text-slate-600 hover:text-blue-600 transition-colors font-medium text-sm"
    >
      {icon} <span>{label}</span>
    </button>
  )
}
