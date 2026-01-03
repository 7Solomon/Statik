import { create } from 'zustand';
import { createEditorSlice } from './editorSlice';
import { createAnalysisSlice } from './analysisSlice';
import type { AppStore } from './types';
import { createSharedSlice } from './sharedSlice';
import { createModelManagementSlice } from './modelsSlice';

export const useStore = create<AppStore>()((...a) => ({
    ...createEditorSlice(...a),
    ...createAnalysisSlice(...a),
    ...createModelManagementSlice(...a),
    ...createSharedSlice(...a),
}));