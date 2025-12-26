
import { useState, useRef, useEffect } from "react";
import { X, Loader2, Save } from "lucide-react";

interface SaveSystemModalProps {
    onClose: () => void;
    onConfirm: (name: string) => Promise<void>;
}

export function SaveSystemModal({ onClose, onConfirm }: SaveSystemModalProps) {
    const [name, setName] = useState("Project");
    const [loading, setLoading] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        inputRef.current?.select();
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!name.trim()) return;

        setLoading(true);
        try {
            await onConfirm(name);
            // We don't close here automatically; the parent handles it on success
        } catch (error) {
            console.error(error);
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/20 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-sm bg-white rounded-xl shadow-2xl border border-slate-100 p-6 scale-100 animate-in zoom-in-95 duration-200">
                <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center gap-2 text-slate-800">
                        <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                            <Save size={20} />
                        </div>
                        <h3 className="text-lg font-semibold">Save System</h3>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="mb-6">
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                            Project Name
                        </label>
                        <input
                            ref={inputRef}
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                            placeholder="e.g. Bridge Design V1"
                        />
                    </div>

                    <div className="flex gap-3 justify-end">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-lg transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading || !name.trim()}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm disabled:opacity-50"
                        >
                            {loading && <Loader2 size={16} className="animate-spin" />}
                            {loading ? 'Saving...' : 'Save'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

