// SidePannel.tsx
import React from 'react';
import { useStore } from '~/store/useStore';
import { ToolsPanel } from './pannel/ToolsPannel';
import { LoadEditor } from './pannel/LoadEditor';
import { NodeEditor, MemberEditor, ScheibeEditor, ConstraintEditor } from './pannel/ElementEditor'; // Import new ones

export const SidePanel = () => {
    const { selectedId, selectedType } = useStore(s => s.editor.interaction);
    const containerClass = "w-80 h-full border-l border-slate-200 bg-white flex flex-col shadow-xl z-10 shrink-0 relative";

    if (!selectedId) {
        return <div className={containerClass}><ToolsPanel /></div>;
    }

    if (selectedType === 'load') {
        return <div className={containerClass}><LoadEditor loadId={selectedId} /></div>;
    }

    // Routing for Structural Elements
    let editorContent = null;
    if (selectedType === 'node') editorContent = <NodeEditor nodeId={selectedId} />;
    else if (selectedType === 'member') editorContent = <MemberEditor memberId={selectedId} />;
    else if (selectedType === 'scheibe') editorContent = <ScheibeEditor scheibeId={selectedId} />;
    else if (selectedType === 'constraint') editorContent = <ConstraintEditor constraintId={selectedId} />;

    return (
        <div className={containerClass}>
            {editorContent}
        </div>
    );
};
