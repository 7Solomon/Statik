import type { DynamicAnalysisResult, StructuralSystem } from "~/types/model";

// --- DEFORMATION LOGIC ---
export const getDeformedSystem = (
    system: StructuralSystem,
    dynamicResult: DynamicAnalysisResult | null,
    activeTab: 'modal' | 'transient',
    activeModeIndex: number,
    timeIndex: number,
    modeAmplitude: number,
    t_vis: number
) => {
    if (!system || !dynamicResult) return null;

    let nodeDisplacements: Record<string, number[]> = {};
    let scheibeRotations: Record<string, { dx: number, dy: number, dTheta: number }> = {};

    // 1. Calculate Node Displacements
    // NEW (Safe)
    if (activeTab === 'modal') {
        // 1. Safety Check: Does the mode exist?
        const mode = dynamicResult.naturalFrequencies[activeModeIndex];
        if (!mode) return null;

        if (!mode.modeShape) {
            return null;
        }

        const phase = t_vis * 3;
        const scale = Math.sin(phase) * modeAmplitude;

        system.nodes.forEach(node => {
            // Safe access with fallback
            const dofs = mode.modeShape[node.id];
            if (dofs) {
                nodeDisplacements[node.id] = [
                    dofs[0] * scale,
                    dofs[1] * scale,
                    (dofs[2] || 0) * scale
                ];
            } else {
                nodeDisplacements[node.id] = [0, 0, 0];
            }
        });
    }
    else {
        // Transient
        const step = dynamicResult.timeHistory[timeIndex];
        if (!step) return null;

        // Auto-Scale Logic
        const maxDisp = dynamicResult.timeHistory.reduce((max, s) => {
            let sMax = 0;
            Object.values(s.displacements).forEach(d => {
                const mag = Math.sqrt(d[0] * d[0] + d[1] * d[1]);
                if (mag > sMax) sMax = mag;
            });
            return Math.max(max, sMax);
        }, 0) || 1.0;

        const scaleFactor = (maxDisp > 1e-9) ? (1.0 / maxDisp) * modeAmplitude : 1.0;

        system.nodes.forEach(node => {
            const dofs = step.displacements[node.id];
            if (dofs) {
                nodeDisplacements[node.id] = [
                    dofs[0] * scaleFactor,
                    dofs[1] * scaleFactor,
                    (dofs[2] || 0) * scaleFactor
                ];
            } else {
                nodeDisplacements[node.id] = [0, 0, 0];
            }
        });
    }

    // 2. Create Deformed Nodes
    const deformedNodes = system.nodes.map(node => {
        const disp = nodeDisplacements[node.id] || [0, 0, 0];
        return {
            ...node,
            position: {
                x: node.position.x + disp[0],
                y: node.position.y + disp[1]
            },
            rotation: node.rotation + (disp[2] * (180 / Math.PI)) // Visual rotation
        };
    });

    // 3. Create Deformed Scheiben (Rigid Body Motion)
    // We infer the Scheibe motion from its connected nodes
    const deformedScheiben = system.scheiben.map(scheibe => {
        if (scheibe.type !== 'RIGID') return scheibe;

        // Find a connected node to use as a "handle"
        // In a rigid body, the motion of one node + rotation defines the whole body
        const handleNodeId = scheibe.connections[0]?.nodeId;
        if (!handleNodeId) return scheibe;

        const disp = nodeDisplacements[handleNodeId];
        if (!disp) return scheibe;

        const [dx_node, dy_node, dTheta_rad] = disp;

        // Calculate original center
        const old_cx = (scheibe.corner1.x + scheibe.corner2.x) / 2;
        const old_cy = (scheibe.corner1.y + scheibe.corner2.y) / 2;

        // Find handle node original position
        const originalNode = system.nodes.find(n => n.id === handleNodeId);
        if (!originalNode) return scheibe;

        // Distance from Node to Center
        const rx = old_cx - originalNode.position.x;
        const ry = old_cy - originalNode.position.y;

        // New Center Position = Old Center + Translation of Node + Rotation effect
        // u_center = u_node - ry * theta
        // v_center = v_node + rx * theta
        const move_x = dx_node - ry * dTheta_rad;
        const move_y = dy_node + rx * dTheta_rad;

        // Apply to corners (Rotate around NEW center or translate)
        // Easiest approach for visualizer: 
        // 1. Translate center
        const new_cx = old_cx + move_x;
        const new_cy = old_cy + move_y;

        // 2. Re-calculate corners relative to new center, rotated by dTheta
        const rotatePoint = (px: number, py: number, cx: number, cy: number, ang: number) => {
            const cos = Math.cos(ang);
            const sin = Math.sin(ang);
            const dx = px - cx;
            const dy = py - cy;
            return {
                x: cx + dx * cos - dy * sin,
                y: cy + dx * sin + dy * cos
            };
        };

        // We rotate the original corner relative to the ORIGINAL center, 
        // then shift it to the NEW center location.
        // Actually, simpler: Just rotate vectors.

        const halfW = Math.abs(scheibe.corner2.x - scheibe.corner1.x) / 2;
        const halfH = Math.abs(scheibe.corner2.y - scheibe.corner1.y) / 2;

        // Original vector from center to corner1
        // (Assuming rectangle is axis aligned initially, or we use corner1 - center)
        const dx1 = scheibe.corner1.x - old_cx;
        const dy1 = scheibe.corner1.y - old_cy;
        const dx2 = scheibe.corner2.x - old_cx;
        const dy2 = scheibe.corner2.y - old_cy;

        const c1_rot = rotatePoint(dx1, dy1, 0, 0, dTheta_rad);
        const c2_rot = rotatePoint(dx2, dy2, 0, 0, dTheta_rad);

        return {
            ...scheibe,
            corner1: { x: new_cx + c1_rot.x, y: new_cy + c1_rot.y },
            corner2: { x: new_cx + c2_rot.x, y: new_cy + c2_rot.y },
            rotation: scheibe.rotation + (dTheta_rad * 180 / Math.PI)
        };
    });

    return {
        system: { ...system, nodes: deformedNodes, scheiben: deformedScheiben },
        nodes: deformedNodes
    };
};
