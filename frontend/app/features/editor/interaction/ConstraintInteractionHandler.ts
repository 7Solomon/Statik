import { BaseInteractionHandler, type MouseEventData } from './BaseInteractionHandler';
import type { ConstraintType } from '~/types/app';
import { v4 as uuidv4 } from 'uuid';

export class ConstraintInteractionHandler extends BaseInteractionHandler {
    handleMouseDown(e: React.MouseEvent, data: MouseEventData): void {
        const { actions, state } = this.context;
        const { snapped, snappedNodeId } = data;

        if (snappedNodeId) {
            actions.setInteraction({
                creationState: {
                    mode: 'drawing_constraint',
                    startPos: snapped,
                    activeId: snappedNodeId
                }
            });
        }
    }

    handleMouseMove(e: React.MouseEvent, data: MouseEventData): void {
        // Ghost constraint is rendered automatically via creationState
        const { actions, state } = this.context;
        const { snappedNodeId } = data;

        // Update hovered node for visual feedback
        if (snappedNodeId) {
            actions.setHoveredNode(snappedNodeId);
        } else {
            actions.setHoveredNode(null);
        }
    }

    handleMouseUp(e: React.MouseEvent, data: MouseEventData): void {
        const { actions, state } = this.context;
        const { snappedNodeId } = data;
        const creationState = state.interaction.creationState;
        const constraintType = state.interaction.activeSubTypeTool as ConstraintType;

        if (creationState.mode === 'drawing_constraint' && creationState.activeId) {
            // Check if we're clicking on a different node
            if (snappedNodeId && snappedNodeId !== creationState.activeId) {
                // Check if constraint already exists between these nodes
                const existingConstraint = state.constraints.find(c =>
                    (c.startNodeId === creationState.activeId && c.endNodeId === snappedNodeId) ||
                    (c.startNodeId === snappedNodeId && c.endNodeId === creationState.activeId)
                );

                if (!existingConstraint) {
                    this.addConstraint(creationState.activeId, snappedNodeId, constraintType);
                }
            }
        }
    }

    private addConstraint(startNodeId: string, endNodeId: string, type: ConstraintType): void {
        const { actions } = this.context;

        switch (type) {
            case 'spring':
                actions.addConstraint({
                    id: uuidv4(),
                    type: 'SPRING',
                    startNodeId,
                    endNodeId,
                    k: 1000, // Default spring stiffness (kN/m) // MAYBE HERE LETS TAKE DEFAULT BUT FOR NOW OKAY
                    preload: 0
                });
                break;

            case 'damper':
                actions.addConstraint({
                    id: uuidv4(),
                    type: 'DAMPER',
                    startNodeId,
                    endNodeId,
                    c: 100, // Default damping coefficient (kN·s/m)
                });
                break;

            case 'cable':
                actions.addConstraint({
                    id: uuidv4(),
                    type: 'CABLE',
                    startNodeId,
                    endNodeId,
                    EA: 210000, // Default axial stiffness (kN)
                    prestress: 0
                });
                break;
        }
    }
}
