import { useState } from "react";
import EditorCanvas from "../features/editor/EditorCanvas";
import { useStore } from "../store/useStore";
import { Save, FileDown, FolderOpen } from 'lucide-react';
import { AnalyzeSystemModal } from "~/features/modals/AnalyzeSystemModal";
import { LoadSystemModal } from "~/features/modals/LoadSystemModal";
import AnalysisViewer from "~/features/analysis/AnalysisViewer";
import { SidePanel } from "~/features/ui/SidePannel";

export function meta() {
  return [
    { title: "Statik React Editor" },
    { name: "description", content: "Structural Analysis Editor" },
  ];
}

export default function Home() {
  const mode = useStore(state => state.shared.mode);
  const setMode = useStore(state => state.shared.actions.setMode);

  // Modal States
  const [modalOpen, setModalOpen] = useState<'save' | 'load' | 'analyze' | null>(null);

  const handleAnalysisComplete = (result: any) => {
    setMode('ANALYSIS');
    setModalOpen(null);
  };

  const handleLoadConfirm = async (slug: string) => {
    console.log("Loading slug:", slug);
  }

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-50">

      {/* HEADER - No longer contains ToolBar */}
      <header className="h-14 border-b border-slate-200 bg-white flex items-center px-4 gap-4 shadow-sm z-20 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-md flex items-center justify-center text-white font-bold">S</div>
          <h1 className="font-bold text-lg text-slate-800 tracking-tight">Statik</h1>
        </div>

        <div className="w-px h-6 bg-slate-200 mx-2"></div>

        {/* File Menu */}
        <div className="flex items-center gap-1 mr-auto">
          <HeaderButton icon={<FolderOpen size={16} />} label="Open" onClick={() => setModalOpen('load')} />
          <HeaderButton icon={<Save size={16} />} label="Save" onClick={() => setModalOpen('save')} />
          <div className="w-px h-4 bg-slate-200 mx-2"></div>
          <HeaderButton icon={<FileDown size={16} />} label="Analyze" onClick={() => setModalOpen('analyze')} />
        </div>
      </header>

      {/* MAIN CONTENT */}
      <div className="flex flex-1 relative overflow-hidden">

        {/* Left: Canvas */}
        <main className="flex-1 relative bg-slate-100/50">
          {mode === 'EDITOR' ? (
            <EditorCanvas />
          ) : (
            <AnalysisViewer />
          )}
        </main>

        {/* Right: The Dynamic Side Panel */}
        {mode === 'EDITOR' && <SidePanel />}

      </div>

      {/* MODALS */}
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

// UI Helper
function HeaderButton({ icon, label, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-slate-100 text-slate-600 hover:text-blue-600 transition-colors font-medium text-sm"
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}
