import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface SystemValidationModalProps {
    isOpen: boolean;
    onClose: () => void;
    title?: string;
    messages: string[];
}

export const SystemValidationModal = ({ isOpen, onClose, title = "Action Not Allowed", messages }: SystemValidationModalProps) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="bg-amber-50 border-b border-amber-100 p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-amber-100 text-amber-600 rounded-lg">
                            <AlertTriangle size={20} />
                        </div>
                        <h3 className="font-bold text-slate-800">{title}</h3>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6">
                    <p className="text-sm text-slate-600 mb-4">
                        The current system configuration contains elements that are not supported by this analysis type:
                    </p>
                    <ul className="space-y-3">
                        {messages.map((msg, i) => (
                            <li key={i} className="flex items-start gap-3 text-sm bg-slate-50 p-3 rounded border border-slate-100 text-slate-700">
                                <span className="mt-0.5 w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
                                {msg}
                            </li>
                        ))}
                    </ul>
                </div>

                {/* Footer */}
                <div className="p-4 bg-slate-50 border-t border-slate-100 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-slate-800 text-white text-sm font-medium rounded-lg hover:bg-slate-900 transition-colors"
                    >
                        Understood
                    </button>
                </div>
            </div>
        </div>
    );
};
