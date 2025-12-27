import { create } from 'zustand';
import { createEditorSlice } from './editorSlice';
import { createAnalysisSlice } from './analysisSlice';
import type { AppStore } from './types';

export const useStore = create<AppStore>()((...a) => {
    const [set, get, api] = a;

    // 1. Create the slice objects
    const editorSlice = createEditorSlice(...a);
    const analysisSlice = createAnalysisSlice(...a);

    return {
        ...editorSlice,
        ...analysisSlice,

        mode: 'EDITOR',

        actions: {
            ...editorSlice.actions,
            ...analysisSlice.actions,

            setMode: (mode) => set({ mode }),
        }
    };
});
