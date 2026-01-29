import type { Release } from '~/types/model';
import { BaseInteractionHandler, type MouseEventData } from './BaseInteractionHandler';

const HINGE_CONFIGS: Record<string, Partial<Release>> = {
    'vollgelenk': { fx: false, fy: false, mz: true },
    'schubgelenk': { fx: false, fy: true, mz: false },
    'normalkraftgelenk': { fx: true, fy: false, mz: false },
    'biegesteife_ecke': { fx: false, fy: false, mz: false },
};

export class HingeInteractionHandler extends BaseInteractionHandler {
    handleMouseDown(e: React.MouseEvent, data: MouseEventData): void {
        const { actions, state } = this.context;
        const { snappedNodeId } = data;
        const subType = state.interaction.activeSubTypeTool;

        if (snappedNodeId && subType && HINGE_CONFIGS[subType]) {
            actions.addHingeAtNode(snappedNodeId, HINGE_CONFIGS[subType]);
        }
    }

    handleMouseMove(e: React.MouseEvent, data: MouseEventData): void {
        // No move behavior
    }

    handleMouseUp(e: React.MouseEvent, data: MouseEventData): void {
        // No up behavior
    }
}
