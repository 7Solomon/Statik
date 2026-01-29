import type { Vec2 } from '~/types/model';
import * as Geo from '../../../lib/geometry';
import * as Coords from '../../../lib/coordinates';
import type { EditorState, EditorActions } from '~/store/types';
import type { ViewportState } from '~/types/app';

export interface MouseEventData {
    raw: Vec2;
    snapped: Vec2;
    snappedNodeId: string | null;
}

export interface InteractionContext {
    state: EditorState;
    actions: EditorActions;
    viewport: ViewportState;
    canvasRef: React.RefObject<HTMLCanvasElement>;
}

export abstract class BaseInteractionHandler {
    protected context: InteractionContext;

    constructor(context: InteractionContext) {
        this.context = context;
    }

    protected getWorldPos(e: React.MouseEvent): MouseEventData {
        const { canvasRef, viewport, state, actions } = this.context;

        if (!canvasRef.current) {
            return { raw: { x: 0, y: 0 }, snapped: { x: 0, y: 0 }, snappedNodeId: null };
        }

        const rect = canvasRef.current.getBoundingClientRect();
        const raw = Coords.screenToWorld(
            e.clientX - rect.left,
            e.clientY - rect.top,
            viewport,
            canvasRef.current.height
        );

        const snappedNodeId = Geo.getNearestNode(raw, state.nodes, viewport.zoom);
        let snapped = raw;

        if (snappedNodeId) {
            const node = state.nodes.find(n => n.id === snappedNodeId);
            if (node) snapped = node.position;
            if (state.interaction.hoveredNodeId !== snappedNodeId) {
                actions.setHoveredNode(snappedNodeId);
            }
        } else {
            snapped = Geo.snapToGrid(raw, viewport.gridSize);
            if (state.interaction.hoveredNodeId !== null) {
                actions.setHoveredNode(null);
            }
        }

        return { raw, snapped, snappedNodeId };
    }

    abstract handleMouseDown(e: React.MouseEvent, data: MouseEventData): void;
    abstract handleMouseMove(e: React.MouseEvent, data: MouseEventData): void;
    abstract handleMouseUp(e: React.MouseEvent, data: MouseEventData): void;
}
