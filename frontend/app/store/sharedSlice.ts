import type { StateCreator } from "zustand";
import type { AppStore } from "./types";

export const createSharedSlice: StateCreator<
    AppStore,
    [],
    [],
    Pick<AppStore, 'shared'>
> = (set) => ({
    shared: {
        // 1. STATE
        mode: 'EDITOR',

        // 2. ACTIONS
        actions: {
            setMode: (mode) => set((state) => ({
                shared: {
                    ...state.shared,
                    mode: mode
                }
            })),
        }
    }
});
