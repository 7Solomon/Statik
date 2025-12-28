/**
 * GEOMETRY & PHYSICS DATA MODELS
 */

export interface Vec2 {
  x: number;
  y: number;
}

export type SupportValue = boolean | number;
export interface Release {
  fx: boolean; // Axial release
  fy: boolean; // Shear release
  mz: boolean; // Moment release (Hinge)
}

export interface Node {
  id: string; // UUID
  position: Vec2; // In meters (World Coordinates)

  // Boundary Conditions (Supports)
  // True = Fixed (Reaction force exists), False = Free
  supports: {
    fixX: SupportValue;
    fixY: SupportValue;
    fixM: SupportValue; // Fixed rotation (Moment clamp)
  };

  // Visual rotation for the support symbol (in degrees)
  rotation: number;
}

export interface Member {
  id: string;
  startNodeId: string;
  endNodeId: string;

  // Material & Section Properties (Required for Stiffness Matrix)
  properties: {
    E: number; // Young's Modulus (kN/m²)
    A: number; // Cross-section Area (m²)
    I: number; // Moment of Inertia (m⁴)
  };

  // Releases (Hinges) at member ends
  // True = Released (Hinge/No Moment), False = Rigid connection
  releases: {
    start: Release;
    end: Release;
  };
}


export type LoadType = 'POINT' | 'MOMENT' | 'DISTRIBUTED';
export type LoadScope = 'NODE' | 'MEMBER';

interface BaseLoad {
  id: string;
  value: number;
  isGlobal?: boolean;
}

export interface NodeLoad extends BaseLoad {
  scope: 'NODE';
  nodeId: string;
  type: 'POINT' | 'MOMENT';
  angle?: number;
}

// 2. Point Load on a Member
export interface MemberPointLoad extends BaseLoad {
  scope: 'MEMBER';
  type: 'POINT';
  memberId: string;
  ratio: number;              // 0.0 to 1.0 (Required)
  angle?: number;
}

// 3. Distributed Load on a Member
export interface MemberDistLoad extends BaseLoad {
  scope: 'MEMBER';
  type: 'DISTRIBUTED';
  memberId: string;
  startRatio: number;         // Required
  endRatio: number;           // Required
  startValue?: number;        // Optional for trapezoids
  endValue?: number;
}

export type Load = NodeLoad | MemberPointLoad | MemberDistLoad;



export interface KinematicMode {
  index: number;
  velocities: Record<string, number[]>;
  member_poles: Record<string, number[] | null>;
  rigid_bodies: any[];
}

export interface StructuralSystem {
  nodes: Node[];
  members: Member[];
  loads: any[];
}


export interface KinematicResult {
  is_kinematic: boolean;
  dof: number;
  modes: KinematicMode[];
  system: StructuralSystem;

}


