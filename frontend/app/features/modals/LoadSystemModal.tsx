import { useState, useEffect } from "react";
import { X, Loader2, FileText, Trash2 } from "lucide-react";

interface LoadSystemModalProps {
    onClose: () => void;
    onLoad: (slug: string) => Promise<void>;
    onDelete?: (slug: string) => Promise<void>; // Optional delete capability
}

interface SavedSystem {
    name: string;
    slug: string;
    saved_at: string; // ISO string from Python
}

export function LoadSystemModal({ onClose, onLoad, onDelete }: LoadSystemModalProps) {
    const [systems, setSystems] = useState<SavedSystem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch list on mount
    useEffect(() => {
        fetch('http://localhost:5000/analyze/list')
            .then(res => res.json())
            .then(data => {
                setSystems(data);
                setIsLoading(false);
            })
            .catch(err => {
                setError("Failed to fetch saved systems.");
                setIsLoading(false);
            });
    }, []);

    const formatDate = (isoString: string) => {
        return new Date(isoString).toLocaleDateString(undefined, {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/20 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-lg bg-white rounded-xl shadow-2xl border border-slate-100 p-6 flex flex-col max-h-[80vh]">

                {/* Header */}
                <div className="flex justify-between items-center mb-4 shrink-0">
                    <h3 className="text-lg font-semibold text-slate-800">Open Project</h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto pr-1">
                    {isLoading ? (
                        <div className="flex justify-center py-8 text-slate-400">
                            <Loader2 className="animate-spin" />
                        </div>
                    ) : error ? (
                        <div className="text-red-500 text-sm text-center py-4">{error}</div>
                    ) : systems.length === 0 ? (
                        <div className="text-slate-400 text-sm text-center py-8">No saved projects found.</div>
                    ) : (
                        <div className="space-y-2">
                            {systems.map((sys) => (
                                <div
                                    key={sys.slug}
                                    className="group flex items-center justify-between p-3 rounded-lg border border-slate-100 hover:border-blue-200 hover:bg-blue-50 transition-all cursor-pointer"
                                    onClick={() => onLoad(sys.slug)}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-slate-100 text-slate-400 rounded-md group-hover:bg-blue-100 group-hover:text-blue-600">
                                            <FileText size={18} />
                                        </div>
                                        <div>
                                            <div className="font-medium text-slate-700 group-hover:text-blue-700">{sys.name}</div>
                                            <div className="text-xs text-slate-400">{formatDate(sys.saved_at)}</div>
                                        </div>
                                    </div>

                                    {/* Optional Delete Button */}
                                    {onDelete && (
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onDelete(sys.slug);
                                            }}
                                            className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100 transition-all"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
