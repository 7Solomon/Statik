import React from 'react';
import { useStore } from '~/store/useStore';
import { ToolsPanel } from './pannel/ToolsPannel';
import { MemberEditor, NodeEditor } from './pannel/ElementEditor';
import { LoadEditor } from './pannel/LoadEditor';

export const SidePanel = () => {
    const { selectedId, selectedType } = useStore(s => s.editor.interaction);
    const containerClass = "w-80 h-full border-l border-slate-200 bg-white flex flex-col shadow-xl z-10 shrink-0 relative";
    console.log(selectedType)
    // 1. If Node Selected -> Show Node Editor
    if (selectedId && selectedType === 'node') {
        return (
            <div className={containerClass}>
                <NodeEditor nodeId={selectedId} />
            </div>
        );
    }

    // 2. If Member Selected -> Show Member Editor
    if (selectedId && selectedType === 'member') {
        return (
            <div className={containerClass}>
                <MemberEditor memberId={selectedId} />
            </div>
        );
    }

    if (selectedId && selectedType === 'load') {
        return (
            <div className={containerClass}>
                <LoadEditor loadId={selectedId} />
            </div>
        );
    }

    // 3. Default -> Show the unified Tools Panel
    return (
        <div className={containerClass}>
            <ToolsPanel />
        </div>
    );
};
