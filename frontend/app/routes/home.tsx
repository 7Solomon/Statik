import { useState } from "react";
import EditorCanvas from "../features/editor/EditorCanvas";
import { useStore } from "../store/useStore";
import { Save, FolderOpen, LayoutDashboard, Calculator, Database } from 'lucide-react';
import { SaveSystemModal } from "~/features/modals/SaveSystemModal";
import { LoadSystemModal } from "~/features/modals/LoadSystemModal";
import { SidePanel } from "~/features/ui/SidePannel";
import AnalysisViewer from "~/features/analysis/AnalysisViewer";
import ModelManagement from "~/features/model_management/ModelManager";
import { DoubleHingeWarningModal } from "~/features/modals/DoubleHingeWarningModal";

export default function Home() {
  const mode = useStore(state => state.shared.mode);
  const setMode = useStore(state => state.shared.actions.setMode);

  const startAnalysis = useStore(state => state.analysis.actions.startAnalysis);
  const clearAnalysis = useStore(state => state.analysis.actions.clearAnalysisSession);

  const [modalOpen, setModalOpen] = useState<'save' | 'load' | 'double-hinge' | null>(null);
  const [doubleHingeNodes, setDoubleHingeNodes] = useState<any[]>([]);

  const handleToggleMode = (targetMode: 'EDITOR' | 'ANALYSIS' | 'MODELS') => {
    if (targetMode === 'ANALYSIS') {
      // Get CURRENT state (don't capture in variables)
      const currentState = useStore.getState().editor;

      // Check for double hinges
      const doubleHinges = detectDoubleHinges(currentState.nodes, currentState.members);

      if (doubleHinges.length > 0) {
        setDoubleHingeNodes(doubleHinges);
        setModalOpen('double-hinge');
        return;
      }

      // No issues - start analysis
      startAnalysisWithCurrentState();
    } else {
      if (mode === 'ANALYSIS') {
        clearAnalysis();
      }
      setMode(targetMode);
    }
  };

  const startAnalysisWithCurrentState = () => {
    // Always get fresh state from store
    const { nodes, members, loads, scheiben, constraints } = useStore.getState().editor;
    startAnalysis({ nodes, members, loads, scheiben, constraints });
  };

  const handleDoubleHingeResolved = () => {
    setModalOpen(null);
    // Use the fresh state getter
    startAnalysisWithCurrentState();
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
        </div>

        <div className="absolute left-1/2 -translate-x-1/2 bg-slate-100 p-1 rounded-lg flex gap-1 border border-slate-200">
          <ModeButton
            active={mode === 'EDITOR'}
            onClick={() => handleToggleMode('EDITOR')}
            icon={<LayoutDashboard size={14} />}
            label="Editor"
          />
          <ModeButton
            active={mode === 'ANALYSIS'}
            onClick={() => handleToggleMode('ANALYSIS')}
            icon={<Calculator size={14} />}
            label="Analysis"
          />
          <div className="w-px bg-slate-200 my-1 mx-1"></div>
          <ModeButton
            active={mode === 'MODELS'}
            onClick={() => handleToggleMode('MODELS')}
            icon={<Database size={14} />}
            label="Models"
          />
        </div>
      </header>

      <div className="flex flex-1 relative overflow-hidden">
        <main className="flex-1 relative bg-slate-100/50">
          {mode === 'EDITOR' && <EditorCanvas />}
          {mode === 'ANALYSIS' && <AnalysisViewer />}
          {mode === 'MODELS' && <ModelManagement />}
        </main>
        {mode === 'EDITOR' && <SidePanel />}
      </div>

      {modalOpen === 'save' && <SaveSystemModal onClose={() => setModalOpen(null)} />}
      {modalOpen === 'load' && <LoadSystemModal onClose={() => setModalOpen(null)} />}
      {modalOpen === 'double-hinge' && (
        <DoubleHingeWarningModal
          doubleHingeNodes={doubleHingeNodes}
          onClose={() => setModalOpen(null)}
          onResolved={handleDoubleHingeResolved}
        />
      )}
    </div>
  );
}

// Helper: Detect double hinges
function detectDoubleHinges(nodes: any[], members: any[]) {
  const nodeHinges: Record<string, any[]> = {};

  for (const member of members) {
    if (member.releases.end.mz) {
      const nodeId = member.endNodeId;
      if (!nodeHinges[nodeId]) nodeHinges[nodeId] = [];
      nodeHinges[nodeId].push({ member, end: 'end' });
    }

    if (member.releases.start.mz) {
      const nodeId = member.startNodeId;
      if (!nodeHinges[nodeId]) nodeHinges[nodeId] = [];
      nodeHinges[nodeId].push({ member, end: 'start' });
    }
  }

  const doubleHinges = [];
  for (const [nodeId, hingedMembers] of Object.entries(nodeHinges)) {
    if (hingedMembers.length >= 2) {
      const node = nodes.find(n => n.id === nodeId);
      doubleHinges.push({ node, hingedMembers });
    }
  }

  return doubleHinges;
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

function ModeButton({ active, onClick, icon, label }: any) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-all ${active
        ? 'bg-white text-blue-700 shadow-sm ring-1 ring-slate-200'
        : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
        }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
