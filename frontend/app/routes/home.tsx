import { PropertiesPanel } from "~/features/ui/PropertiesPannel";
import EditorCanvas from "../features/editor/EditorCanvas";
import { useStore } from "../store/useStore";
import type { Route } from ".react-router.gen";

export function meta({ }: Route.MetaArgs) {
  return [
    { title: "Statik React Editor" },
    { name: "description", content: "Structural Analysis Editor" },
  ];
}

export default function Home() {
  const activeTool = useStore(state => state.interaction.activeTool);
  const setTool = useStore(state => state.actions.setTool);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden">
      {/* HEADER / TOOLBAR */}
      <header className="h-14 border-b border-slate-200 bg-white flex items-center px-4 gap-4 shadow-sm z-10 shrink-0">
        <h1 className="font-bold text-slate-700">Statik</h1>
        <div className="w-px h-6 bg-slate-300 mx-2"></div>

        {/* Tools */}
        <div className="flex gap-2">
          <ToolButton
            label="Select"
            isActive={activeTool === 'select'}
            onClick={() => setTool('select')}
          />
          <ToolButton
            label="Node"
            isActive={activeTool === 'node'}
            onClick={() => setTool('node')}
          />
          <ToolButton
            label="Member"
            isActive={activeTool === 'member'}
            onClick={() => setTool('member')}
          />
          <div className="w-px h-6 bg-slate-300 mx-1"></div>
          <ToolButton
            label="Fix Support"
            isActive={activeTool === 'support_fixed'}
            onClick={() => setTool('support_fixed')}
          />
          <ToolButton
            label="Pin Support"
            isActive={activeTool === 'support_pin'}
            onClick={() => setTool('support_pin')}
          />
        </div>
      </header>

      <div className="flex flex-1 relative overflow-hidden">
        {/* Main Canvas Area */}
        <main className="flex-1 relative bg-slate-50">
          <EditorCanvas />
        </main>

        {/* Right Sidebar */}
        <PropertiesPanel />
      </div>
    </div>
  );
}

// Helper Component for the buttons
function ToolButton({ label, isActive, onClick }: { label: string, isActive: boolean, onClick: () => void }) {
  return (
    <button
      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${isActive
        ? 'bg-blue-600 text-white shadow-sm'
        : 'text-slate-600 hover:bg-slate-100'
        }`}
      onClick={onClick}
    >
      {label}
    </button>
  );
}
