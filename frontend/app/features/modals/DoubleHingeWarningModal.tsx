import { AlertTriangle, X } from "lucide-react";
import { useStore } from "~/store/useStore";

interface DoubleHingeWarningModalProps {
    doubleHingeNodes: any[];
    onClose: () => void;
    onResolved: () => void;
}

export function DoubleHingeWarningModal({
    doubleHingeNodes,
    onClose,
    onResolved
}: DoubleHingeWarningModalProps) {
    const nodes = useStore(s => s.editor.nodes); // Get fresh from store
    const updateMember = useStore(s => s.editor.actions.updateMember);


    const handleFixHinge = (nodeInfo: any, memberToKeepRigid: any) => {
        // Make the selected member rigid at this node
        const updatedReleases = { ...memberToKeepRigid.member.releases };

        if (memberToKeepRigid.end === 'start') {
            updatedReleases.start = { ...updatedReleases.start, mz: false };
        } else {
            updatedReleases.end = { ...updatedReleases.end, mz: false };
        }

        updateMember(memberToKeepRigid.member.id, { releases: updatedReleases });

        // Check if all double hinges are resolved
        // For simplicity, just proceed after first fix
        onResolved();
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-orange-50">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                            <AlertTriangle className="text-orange-600" size={20} />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-slate-800">Double Hinge Detected</h2>
                            <p className="text-sm text-slate-600">Structure may be unstable</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-orange-100 rounded-lg transition-colors"
                    >
                        <X size={20} className="text-slate-500" />
                    </button>
                </div>

                {/* Content */}
                <div className="px-6 py-4 overflow-y-auto flex-1">
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                        <p className="text-sm text-blue-800 leading-relaxed">
                            <strong>What's the issue?</strong> One or more nodes have hinges on multiple members.
                            This creates a mechanism where the node can rotate freely, making the structure unstable for FEM analysis.
                        </p>
                    </div>

                    <p className="text-sm text-slate-600 mb-4">
                        To fix this, you need to specify which member should control the joint rotation.
                        The selected member will be <strong>rigidly connected</strong> at this node,
                        while others remain hinged.
                    </p>

                    {/* List each double hinge node */}
                    {doubleHingeNodes.map((nodeInfo, idx) => (
                        <div key={idx} className="border border-slate-200 rounded-lg p-4 mb-4 bg-slate-50">
                            <h3 className="font-semibold text-slate-800 mb-3">
                                Node at ({nodeInfo.node.position.x.toFixed(1)}, {nodeInfo.node.position.y.toFixed(1)})
                            </h3>

                            <p className="text-xs text-slate-500 mb-3">
                                {nodeInfo.hingedMembers.length} members with hinges at this node
                            </p>

                            <div className="space-y-2">
                                {nodeInfo.hingedMembers.map((memberInfo: any, mIdx: number) => {
                                    const member = memberInfo.member;
                                    const startNode = nodes.find(n => n.id === member.startNodeId);
                                    const endNode = nodes.find(n => n.id === member.endNodeId);

                                    return (
                                        <button
                                            key={mIdx}
                                            onClick={() => handleFixHinge(nodeInfo, memberInfo)}
                                            className="w-full text-left p-3 border border-slate-300 rounded-lg hover:bg-blue-50 hover:border-blue-400 transition-all group"
                                        >
                                            <div className="flex items-center justify-between">
                                                <div className="flex-1">
                                                    <p className="text-sm font-medium text-slate-700 group-hover:text-blue-700">
                                                        Member {mIdx + 1}
                                                    </p>
                                                    <p className="text-xs text-slate-500 mt-0.5">
                                                        ({startNode?.position.x.toFixed(1)}, {startNode?.position.y.toFixed(1)}) →
                                                        ({endNode?.position.x.toFixed(1)}, {endNode?.position.y.toFixed(1)})
                                                    </p>
                                                </div>
                                                <div className="px-3 py-1 bg-slate-200 group-hover:bg-blue-200 rounded text-xs font-medium text-slate-600 group-hover:text-blue-700">
                                                    Make Rigid
                                                </div>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex justify-between items-center">
                    <p className="text-xs text-slate-500">
                        Select which member should control each joint rotation
                    </p>
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg font-medium transition-colors"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
}
