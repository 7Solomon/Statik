import React, { useEffect, useState } from 'react';
import { X, Search, FileText, Trash2, Loader2, AlertCircle, FolderOpen, AlertTriangle } from 'lucide-react'; // Added AlertTriangle
import { useStore } from '~/store/useStore';

interface SystemMeta {
    name: string;
    slug: string;
    saved_at: string;
}

interface LoadSystemModalProps {
    onClose: () => void;
}

export function LoadSystemModal({ onClose }: LoadSystemModalProps) {
    const [systems, setSystems] = useState<SystemMeta[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [search, setSearch] = useState('');

    const loadSystemIntoStore = useStore(state => state.editor.actions.loadStructuralSystem);

    useEffect(() => {
        fetchSystems();
    }, []);

    const fetchSystems = async () => {
        try {
            const res = await fetch('api/systems_management/list');
            if (!res.ok) throw new Error("Failed to fetch systems");
            const data = await res.json();
            setSystems(data);
        } catch (err) {
            setError("Could not load saved systems");
        } finally {
            setLoading(false);
        }
    };

    const handleLoad = async (slug: string, name: string) => { // Added name parameter
        // 1. Warning Confirmation
        const isConfirmed = confirm(
            `Loading "${name}" will overwrite your current workspace.\n\nAny unsaved changes will be lost. Do you want to continue?`
        );

        if (!isConfirmed) return;

        try {
            setLoading(true);
            const res = await fetch(`api/systems_management/load/${slug}`);
            if (!res.ok) throw new Error("Failed to load system");

            const systemData = await res.json();

            loadSystemIntoStore(systemData);

            onClose();
        } catch (err) {
            setError("Failed to load selected system");
            setLoading(false);
        }
    };

    const handleDelete = async (slug: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm("Are you sure you want to delete this system? This cannot be undone.")) return; // Enhanced message

        try {
            const res = await fetch(`api/systems_management/delete/${slug}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                setSystems(prev => prev.filter(s => s.slug !== slug));
            }
        } catch (err) {
            alert("Failed to delete system");
        }
    };

    const filteredSystems = systems.filter(sys =>
        sys.name.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="w-full max-w-2xl bg-white rounded-xl shadow-2xl flex flex-col max-h-[80vh] animate-in fade-in zoom-in duration-200">

                {/* Header */}
                <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                    <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                        <FolderOpen className="w-5 h-5 text-blue-600" />
                        Load System
                    </h2>
                    <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded-full text-slate-500">
                        <X size={20} />
                    </button>
                </div>

                {/* INFO BANNER - Added Warning Visual */}
                <div className="bg-amber-50 px-4 py-2 border-b border-amber-100 flex items-center gap-2 text-sm text-amber-800">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>Loading a saved system will clear your current workspace.</span>
                </div>

                {/* Search Bar */}
                <div className="p-4 border-b border-slate-100 bg-white">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
                        <input
                            type="text"
                            placeholder="Search saved systems..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-sm"
                        />
                    </div>
                </div>

                {/* List Content */}
                <div className="flex-1 overflow-y-auto p-2 bg-slate-50/30">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center h-40 text-slate-500 gap-2">
                            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                            <span className="text-sm">Loading systems...</span>
                        </div>
                    ) : error ? (
                        <div className="flex flex-col items-center justify-center h-40 text-red-500 gap-2">
                            <AlertCircle className="w-6 h-6" />
                            <span className="text-sm">{error}</span>
                        </div>
                    ) : filteredSystems.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-40 text-slate-400 gap-2">
                            <FolderOpen className="w-8 h-8 opacity-20" />
                            <span className="text-sm">No systems found</span>
                        </div>
                    ) : (
                        <div className="grid gap-2">
                            {filteredSystems.map((sys) => (
                                <div
                                    key={sys.slug}
                                    onClick={() => handleLoad(sys.slug, sys.name)} // Pass name here
                                    className="group flex items-center justify-between p-3 bg-white border border-slate-200 hover:border-blue-300 hover:shadow-md rounded-lg cursor-pointer transition-all duration-200"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">
                                            <FileText size={20} />
                                        </div>
                                        <div>
                                            <h3 className="font-medium text-slate-800 group-hover:text-blue-700 transition-colors">{sys.name}</h3>
                                            <p className="text-xs text-slate-500">
                                                {new Date(sys.saved_at).toLocaleDateString()} at {new Date(sys.saved_at).toLocaleTimeString()}
                                            </p>
                                        </div>
                                    </div>

                                    <button
                                        onClick={(e) => handleDelete(sys.slug, e)}
                                        className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                                        title="Delete system"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
