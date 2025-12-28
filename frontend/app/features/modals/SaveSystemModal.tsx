import React, { useState } from 'react';
import { X, Save, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useStore } from '~/store/useStore';

interface SaveSystemModalProps {
    onClose: () => void;
}

export function SaveSystemModal({ onClose }: SaveSystemModalProps) {
    const [name, setName] = useState('');
    const [status, setStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');

    const getCurrentSystem = useStore(state => state.editor.actions.exportStructuralSystem);

    const handleSave = async () => {
        if (!name.trim()) return;

        setStatus('saving');
        setErrorMessage('');

        try {
            const currentSystem = getCurrentSystem()
            // 2. Prepare the payload
            const payload = {
                name: name,
                system: currentSystem
            };

            // 3. Call your backend
            const response = await fetch('api/systems_management/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error('Failed to save system');
            }

            const data = await response.json();
            console.log("Saved with slug:", data.slug);

            setStatus('success');

            // Close after a brief delay so user sees success
            setTimeout(() => {
                onClose();
            }, 1000);

        } catch (error) {
            console.error(error);
            setStatus('error');
            setErrorMessage('Could not save system. Please try again.');
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="w-full max-w-md bg-white rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">

                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-slate-50/50">
                    <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                        <Save className="w-5 h-5 text-blue-600" />
                        Save System
                    </h2>
                    <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded-full transition-colors text-slate-500">
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">System Name</label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g. Cantilever Beam V1"
                            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                            autoFocus
                            disabled={status === 'saving' || status === 'success'}
                        />
                    </div>

                    {/* Status Messages */}
                    {status === 'error' && (
                        <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 p-3 rounded-lg">
                            <AlertCircle size={16} />
                            {errorMessage}
                        </div>
                    )}

                    {status === 'success' && (
                        <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 p-3 rounded-lg">
                            <CheckCircle size={16} />
                            Saved successfully!
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-200 rounded-lg transition-colors"
                    >
                        Cancel
                    </button>

                    <button
                        onClick={handleSave}
                        disabled={!name.trim() || status === 'saving' || status === 'success'}
                        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {status === 'saving' ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Saving...
                            </>
                        ) : status === 'success' ? (
                            <>
                                <CheckCircle className="w-4 h-4" />
                                Saved
                            </>
                        ) : (
                            'Save System'
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
