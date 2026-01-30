import { AlertTriangle, CheckCircle, Zap } from "lucide-react";
import type { DynamicAnalysisResult } from "~/types/model";

export default function DynamicInsights({ result }: { result: DynamicAnalysisResult }) {

    // 1. Calculate Max Displacement
    let maxDisp = 0;
    result.timeHistory.forEach(s => {
        Object.values(s.displacements).forEach(d => {
            const mag = Math.sqrt(d[0] ** 2 + d[1] ** 2);
            if (mag > maxDisp) maxDisp = mag;
        });
    });

    // 2. Check Resonance (Input vs Eigen)
    // INPUT FREQU NEEDS TO BE DYNAMIC
    const inputFreq = 1.0;
    const firstEigen = result.naturalFrequencies[0]?.frequency || 0;
    const ratio = firstEigen > 0 ? inputFreq / firstEigen : 0;
    const isResonance = Math.abs(ratio - 1.0) < 0.15; // Within 15%

    return (
        <div className="absolute top-4 right-4 w-64 flex flex-col gap-3 z-20">
            {/* Stability Card */}
            <div className={`p-4 rounded-xl shadow-sm border bg-white ${result.isStable ? 'border-green-200' : 'border-red-200'}`}>
                <div className="flex items-center gap-2 mb-2">
                    {result.isStable ? <CheckCircle size={16} className="text-green-600" /> : <AlertTriangle size={16} className="text-red-600" />}
                    <span className="font-bold text-sm text-slate-700">System Stability</span>
                </div>
                <div className="text-xs text-slate-500">
                    Damping Ratio: <span className="font-mono text-slate-700">{(result.criticalDampingRatio * 100).toFixed(2)}%</span>
                </div>
            </div>

            {/* Resonance Warning */}
            {isResonance && (
                <div className="p-4 rounded-xl shadow-sm border bg-amber-50 border-amber-200">
                    <div className="flex items-center gap-2 mb-1 text-amber-700">
                        <Zap size={16} />
                        <span className="font-bold text-sm">Resonance Risk</span>
                    </div>
                    <p className="text-[11px] text-amber-800 leading-tight">
                        Forcing frequency (1.0Hz) is close to natural frequency ({firstEigen.toFixed(2)}Hz). Large amplitudes expected.
                    </p>
                </div>
            )}

            {/* Max Stats */}
            <div className="p-4 rounded-xl shadow-sm border bg-white border-slate-100">
                <h4 className="text-xs font-bold text-slate-400 uppercase mb-3">Peak Response</h4>

                <div className="flex justify-between items-end mb-2">
                    <span className="text-xs text-slate-500">Max Disp:</span>
                    <span className="font-mono text-sm font-bold text-slate-700">
                        {(maxDisp * 1000).toFixed(2)} mm
                    </span>
                </div>
            </div>
        </div>
    );
}
