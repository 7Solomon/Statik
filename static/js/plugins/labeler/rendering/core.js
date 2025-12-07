import { GridSystem } from '../gridSystem.js';
import { SystemState } from '../structureData.js';
import { drawMembers, drawGhostMember, drawLoads, drawNodes, drawNodeSymbol, COLORS } from './shapes.js';

let SYMBOL_DEFINITIONS = {};

export function setSymbolDefinitions(defs) {
    SYMBOL_DEFINITIONS = defs;
}
export function getSymbolDefinitions() {
    return SYMBOL_DEFINITIONS;
}


export function renderScene(ctx, canvas, interactionState, currentTool, currentRotation = 0) {
    if (!ctx) return;
    const { width, height } = canvas;
    const gridSize = SystemState.gridSize;

    ctx.clearRect(0, 0, width, height);

    if (interactionState.showGrid) {
        GridSystem.draw(ctx, canvas, gridSize, COLORS);
    }

    drawMembers(ctx, canvas, gridSize);
    drawGhostMember(ctx, canvas, interactionState, gridSize);
    drawLoads(ctx, canvas, gridSize, SYMBOL_DEFINITIONS);
    drawNodes(ctx, canvas, interactionState.hoveredNodeId, gridSize, SYMBOL_DEFINITIONS);

    if (currentTool && interactionState.mousePos) {
        drawPreview(ctx, canvas, interactionState, currentTool, gridSize, currentRotation);
    }

    drawSnapMarker(ctx, interactionState.mousePos);
}

function drawPreview(ctx, canvas, interactionState, currentTool, gridSize, currentRotation) {
    const { mousePos } = interactionState;
    if (!mousePos) return;

    ctx.save();
    ctx.globalAlpha = 0.5;

    if (currentTool.category === 'connection' && currentTool.name === 'member') {
        ctx.fillStyle = COLORS.member;
        ctx.beginPath();
        ctx.arc(mousePos.x, mousePos.y, 4, 0, Math.PI * 2);
        ctx.fill();
    }
    else if (['support', 'hinge', 'load'].includes(currentTool.category)) {
        const symbolName = currentTool.name;
        if (SYMBOL_DEFINITIONS[symbolName]) {
            drawNodeSymbol(ctx, mousePos, symbolName, currentRotation, SYMBOL_DEFINITIONS);
        }
    }
    ctx.restore();
}

function drawSnapMarker(ctx, mousePos) {
    if (mousePos && !mousePos.isNode && mousePos.realX !== undefined) {
        ctx.fillStyle = 'rgba(59, 130, 246, 0.3)';
        ctx.beginPath();
        ctx.arc(mousePos.x, mousePos.y, 4, 0, Math.PI * 2);
        ctx.fill();
    }
}
