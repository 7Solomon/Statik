import React from 'react';
import { Square, Triangle, Circle, Hexagon } from 'lucide-react';
import { useStore } from '~/store/useStore';
import type { ScheibeShape } from '~/types/app';

const SHAPES = [
    { type: 'rectangle' as ScheibeShape, label: 'Rechteck', icon: <Square size={24} /> },
    { type: 'triangle' as ScheibeShape, label: 'Dreieck', icon: <Triangle size={24} /> },
    { type: 'circle' as ScheibeShape, label: 'Kreis', icon: <Circle size={24} /> },
    //{ type: 'polygon' as ScheibeShape, label: 'Polygon', icon: <Hexagon size={24} /> },
];

export const ShapeSelector = () => {
    const activeTool = useStore(state => state.editor.interaction.activeTool);
    const activeSubType = useStore(state => state.editor.interaction.activeSubTypeTool);
    const actions = useStore(state => state.editor.actions);

    // Only show if Scheibe tool is active
    if (activeTool !== 'scheibe') return null;

    const handleShapeSelect = (shape: ScheibeShape) => {
        actions.setInteraction({ activeSubTypeTool: shape });
    };

    return (
        <div className="absolute top-4 left-4 bg-white rounded-xl shadow-lg border border-slate-200 p-3 z-50">
            <div className="mb-2">
                <span className="text-xs font-bold text-slate-600 uppercase tracking-wide">
                    Scheibe Form
                </span>
            </div>

            <div className="flex gap-2">
                {SHAPES.map((shape) => (
                    <button
                        key={shape.type}
                        onClick={() => handleShapeSelect(shape.type)}
                        className={`
                            flex flex-col items-center justify-center p-3 rounded-lg 
                            transition-all duration-200 border min-w-[64px]
                            ${activeSubType === shape.type
                                ? 'bg-blue-50 border-blue-500 text-blue-600 shadow-sm'
                                : 'bg-white border-slate-200 text-slate-500 hover:border-blue-300 hover:bg-slate-50'
                            }
                        `}
                        title={shape.label}
                    >
                        <div className="mb-1">{shape.icon}</div>
                        <span className="text-[10px] font-medium">{shape.label}</span>
                    </button>
                ))}
            </div>
        </div>
    );
};
