import { useState } from "react";
import EditorCanvas from "../features/editor/EditorCanvas";
import { useStore } from "../store/useStore";
import { Save, FileDown, FolderOpen } from 'lucide-react';
// Updated imports
import { SaveSystemModal } from "~/features/modals/SaveSystemModal";
import { LoadSystemModal } from "~/features/modals/LoadSystemModal";
import { AnalyzeSystemModal } from "~/features/modals/AnalyzeSystemModal";
import { SidePanel } from "~/features/ui/SidePannel";
import AnalysisViewer from "~/features/analysis/AnalysisViewer";

export default function Home() {
  const mode = useStore(state => state.shared.mode);
  const setAppMode = useStore(state => state.shared.actions.setMode);

  // Result setters
  const setKinematicResult = useStore(state => state.analysis.actions.setKinematicResult);
  const setSimplifyResult = useStore(state => state.analysis.actions.setSimplifyResult);
  const setSolutionResult = useStore(state => state.analysis.actions.setSolutionResult);
  const setViewMode = useStore(state => state.analysis.actions.setViewMode);

  const [modalOpen, setModalOpen] = useState<'save' | 'load' | 'analyze' | null>(null);

  const handleAnalysisComplete = (result: any, type: any) => {
    setAppMode('ANALYSIS');
    if (type === 'KINEMATIC') {
      setKinematicResult(result);
      setViewMode('KINEMATIC');
    } else if (type === 'SIMPLIFIED') {
      setSimplifyResult(result);
      setViewMode('SIMPLIFIED');
    } else if (type === 'SOLUTION') {
      setSolutionResult(result);
      setViewMode('SOLUTION');
    }
    setModalOpen(null);
  };

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-50">
      <header className="h-14 border-b border-slate-200 bg-white flex items-center px-4 gap-4 shadow-sm z-20 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-md flex items-center justify-center text-white font-bold">S</div>
          <h1 className="font-bold text-lg text-slate-800 tracking-tight">Statik</h1>
        </div>
        <div className="w-px h-6 bg-slate-200 mx-2"></div>
        <div className="flex items-center gap-1 mr-auto">
          <HeaderButton icon={<FolderOpen size={16} />} label="Open" onClick={() => setModalOpen('load')} />
          <HeaderButton icon={<Save size={16} />} label="Save" onClick={() => setModalOpen('save')} />
          <div className="w-px h-4 bg-slate-200 mx-2"></div>
          <HeaderButton icon={<FileDown size={16} />} label="Analyze" onClick={() => setModalOpen('analyze')} />
        </div>
      </header>

      <div className="flex flex-1 relative overflow-hidden">
        <main className="flex-1 relative bg-slate-100/50">
          {mode === 'EDITOR' ? <EditorCanvas /> : <AnalysisViewer />}
        </main>
        {mode === 'EDITOR' && <SidePanel />}
      </div>

      {/* MODALS */}
      {modalOpen === 'save' && (
        <SaveSystemModal onClose={() => setModalOpen(null)} />
      )}

      {modalOpen === 'load' && (
        <LoadSystemModal onClose={() => setModalOpen(null)} />
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
