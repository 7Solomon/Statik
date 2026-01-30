import { useCallback } from 'react';
import { useStore } from '../../store/useStore';
import type { InteractionContext } from './interaction/BaseInteractionHandler';
import { HingeInteractionHandler } from './interaction/HingeInteractionHandler';
import { LoadInteractionHandler } from './interaction/LoadInteractionHandler';
import { MemberInteractionHandler } from './interaction/MemberInteractionHandler';
import { NodeInteractionHandler } from './interaction/NodeInteractionHandler';
import { ScheibeInteractionHandler } from './interaction/ScheibenInteractionHandler';
import { SelectInteractionHandler } from './interaction/SelectInteractionHandler';
import { ConstraintInteractionHandler } from './interaction/ConstraintInteractionHandler';


export const useCanvasInteraction = (canvasRef: React.RefObject<HTMLCanvasElement>) => {
    const state = useStore((s) => s.editor);
    const { actions, viewport, interaction } = state;
    const tool = interaction.activeTool;

    // Create interaction context
    const context: InteractionContext = {
        state,
        actions,
        viewport,
        canvasRef
    };

    // Instantiate handlers
    const handlers = {
        node: new NodeInteractionHandler(context),
        member: new MemberInteractionHandler(context),
        hinge: new HingeInteractionHandler(context),
        load: new LoadInteractionHandler(context),
        scheibe: new ScheibeInteractionHandler(context),
        constraint: new ConstraintInteractionHandler(context),
        select: new SelectInteractionHandler(context)
    };

    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        const handler = handlers[tool];
        if (handler) {
            const data = handler['getWorldPos'](e);  // Access protected method via bracket notation
            handler.handleMouseDown(e, data);
        }
    }, [tool, state, actions, viewport]);

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        const handler = handlers[tool];
        if (handler) {
            const data = handler['getWorldPos'](e);
            actions.setInteraction({ mousePos: data.snapped });
            handler.handleMouseMove(e, data);
        }
    }, [tool, state, actions, viewport]);

    const handleMouseUp = useCallback((e: React.MouseEvent) => {
        const handler = handlers[tool];
        if (handler) {
            const data = handler['getWorldPos'](e);
            handler.handleMouseUp(e, data);
        }

        // Always reset creation state on mouse up
        actions.setInteraction({
            creationState: {
                mode: 'idle',
                startPos: null,
                activeId: null
            }
        });
    }, [tool, state, actions, viewport]);

    return { handleMouseDown, handleMouseMove, handleMouseUp };
};
