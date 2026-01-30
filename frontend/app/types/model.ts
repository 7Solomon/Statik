import type { ScheibeShape } from "./app";

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
    fixN: SupportValue;
    fixV: SupportValue;
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
    m: number; // mass
  };

  // Releases (Hinges) at member ends
  // True = Released (Hinge/No Moment), False = Rigid connection
  releases: {
    start: Release;
    end: Release;
  };
}


export interface ScheibeConnection {
  nodeId: string;
  releases?: Release;
}

export interface Scheibe {
  id: string;
  shape: ScheibeShape;

  // Geometry
  corner1: Vec2;
  corner2: Vec2;
  additionalPoints?: Vec2[];
  rotation: number;

  // Analysis Type
  type: 'RIGID' | 'ELASTIC';

  // Properties
  properties: {
    E: number;
    nu: number;
    thickness: number;
    rho: number;
  };

  connections: ScheibeConnection[]; // NODES ON SCHEIBE

  meshLevel?: 1 | 2 | 3 | 4 | 5;
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


////////////////////////////////////////////////////////////
////////     LINKS / constraints ka was besser ist    ///////
////////////////////////////////////////////////////////////

export type Constraint = SpringConstraint | DamperConstraint | CableConstraint;

interface BaseConstraint {
  id: string;
  startNodeId: string;
  endNodeId: string;
  rotation?: number;
}

export interface SpringConstraint extends BaseConstraint {
  type: 'SPRING';
  k: number;
  preload?: number;
}

export interface DamperConstraint extends BaseConstraint {
  type: 'DAMPER';
  c: number;
  k?: number;
}

export interface CableConstraint extends BaseConstraint {
  type: 'CABLE';
  EA: number;
  prestress?: number;
  weightPerLength?: number;
}



/////////////////////////////
/////////////////////////////
/////////////////////////////



export interface KinematicMode {
  index: number;
  node_velocities: Record<string, number[]>;
  scheibe_velocities: Record<string, number[]>;
  member_poles: Record<string, number[] | null>;
  rigid_bodies: any[];
}

export interface StructuralSystem {
  nodes: Node[];
  members: Member[];
  loads: any[];
  scheiben: Scheibe[];
  constraints: Constraint[];
}


export interface KinematicResult {
  is_kinematic: boolean;
  dof: number;
  modes: KinematicMode[];
}


///////////////////////
///////////////////////
///////////////////////
///////////////////////

export interface StationResult {
  x: number;      // Distance from start node (in meters)
  N: number;      // Axial Force
  V: number;      // Shear Force
  M: number;      // Bending Moment
}

export interface MemberResult {
  memberId: string;
  stations: StationResult[]; // Array of values along the beam
  maxM: number; // Helpers for auto-scaling visualization
  minM: number;
  maxN: number;
  minN: number;
  maxV: number;
  minV: number;

}

export interface FEMResult {
  success: boolean;
  error?: string;
  displacements?: Record<string, [number, number, number]>;
  reactions?: Record<string, [number, number, number]>;
  memberResults?: Record<string, MemberResult>;
}



//////////////////////////////////////

export interface ModalResult {
  frequency: number;
  period: number;
  modeShape: Record<string, number[]>; // node_id -> [u, v, theta]
}

export interface TimeStepResult {
  time: number;
  displacements: Record<string, number[]>; // node_id -> [u, v, theta]
  velocities: Record<string, number[]>;
  accelerations: Record<string, number[]>;
  kineticEnergy: number;
  potentialEnergy: number;
  dissipatedEnergy: number;
  total_energy: number;
}
export interface DynamicAnalysisResult {
  success: boolean;
  message: string;
  naturalFrequencies: ModalResult[];
  timeHistory: TimeStepResult[];
  isStable: boolean;
  criticalDampingRatio: number;
}