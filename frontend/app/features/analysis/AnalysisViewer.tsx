import { useStore } from "~/store/useStore";
import { Layers, GitMerge, Zap } from "lucide-react";
import SimplifiedViewer from "./SimplifiedViewer";
import KinematicViewer from "./KinematicsViewer";
import SolutionViewer from "./SolutionViewer";

export default function AnalysisViewer() {
    const analysisSession = useStore((s) => s.analysis.analysisSession);
    const setViewMode = useStore((s) => s.analysis.actions.setViewMode);

    if (!analysisSession) return <div className="flex items-center justify-center h-full text-slate-400">No active analysis session</div>;

    const { viewMode } = analysisSession;

    return (
        <div className="flex flex-col w-full h-full">

            <div className="flex-none flex justify-center p-2 border-b border-slate-200 bg-white z-10 relative">
                {/* Removed 'backdrop-blur' because it's now on a solid white background */}
                <div className="flex gap-1 p-1 bg-slate-100 rounded-lg">
                    <TabButton
                        active={viewMode === 'KINEMATIC'}
                        onClick={() => setViewMode('KINEMATIC')}
                        icon={<Layers size={14} />}
                        label="Kinematics"
                    />
                    <div className="w-px bg-slate-200 my-1"></div>
                    <TabButton
                        active={viewMode === 'SIMPLIFIED'}
                        onClick={() => setViewMode('SIMPLIFIED')}
                        icon={<GitMerge size={14} />}
                        label="Simplified"
                    />
                    <div className="w-px bg-slate-200 my-1"></div>
                    <TabButton
                        active={viewMode === 'SOLUTION'}
                        onClick={() => setViewMode('SOLUTION')}
                        icon={<Zap size={14} />}
                        label="Solution"
                    />
                </div>
            </div>

            {/* 3. Render Sub-Viewers - Takes all remaining space (flex-1) */}
            <div className="flex-1 relative overflow-hidden bg-slate-50">
                {viewMode === 'KINEMATIC' && <KinematicViewer />}
                {viewMode === 'SIMPLIFIED' && <SimplifiedViewer />}
                {viewMode === 'SOLUTION' && <SolutionViewer />}
            </div>
        </div>
    );

}

function TabButton({ active, onClick, icon, label }: any) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-all ${active
                ? 'bg-blue-50 text-blue-700 shadow-sm ring-1 ring-blue-200'
                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                }`}
        >
            {icon}
            <span>{label}</span>
        </button>
    );
}
