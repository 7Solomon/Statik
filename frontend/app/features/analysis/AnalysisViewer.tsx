import { useStore } from '~/store/useStore';
import { Layers, GitMerge } from 'lucide-react';
import SimplifiedViewer from './SimplifiedViewer';
import KinematicViewer from './KinematicsViewer';

export default function AnalysisViewer() {
    // 1. Get the current view mode from your store
    const viewMode = useStore(s => s.analysis.viewMode);
    const setViewMode = useStore(s => s.analysis.actions.setViewMode);

    // 2. Check which results are available (to disable buttons if needed)
    const hasKinematic = useStore(s => !!s.analysis.kinematicResult);
    const hasSimplified = useStore(s => !!s.analysis.simplifyResult);

    return (
        <div className="relative w-full h-full">

            {/* 3. Render the correct sub-viewer */}
            {viewMode === 'KINEMATIC' && <KinematicViewer />}
            {viewMode === 'SIMPLIFIED' && <SimplifiedViewer />}

            {/* 4. Tab Switcher Overlay */}
            {(hasKinematic || hasSimplified) && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 flex gap-1 p-1 bg-white/90 backdrop-blur-sm rounded-lg border border-slate-200 shadow-sm z-10">

                    {/* Kinematic Tab */}
                    <button
                        onClick={() => setViewMode('KINEMATIC')}
                        disabled={!hasKinematic}
                        className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-all
                            ${viewMode === 'KINEMATIC'
                                ? 'bg-blue-50 text-blue-700 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'}
                            ${!hasKinematic ? 'opacity-50 cursor-not-allowed' : ''}
                        `}
                    >
                        <Layers size={14} />
                        <span>Kinematic</span>
                    </button>

                    <div className="w-px bg-slate-200 my-1"></div>

                    {/* Simplified Tab */}
                    <button
                        onClick={() => setViewMode('SIMPLIFIED')}
                        disabled={!hasSimplified}
                        className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-all
                            ${viewMode === 'SIMPLIFIED'
                                ? 'bg-blue-50 text-blue-700 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'}
                            ${!hasSimplified ? 'opacity-50 cursor-not-allowed' : ''}
                        `}
                    >
                        <GitMerge size={14} />
                        <span>Simplified</span>
                    </button>
                </div>
            )}
        </div>
    );
}
