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

export interface Load {
  id: string;

  // What is this load applied to?
  target: 'node' | 'member';
  targetId: string;

  type: 'point_force' | 'distributed_force' | 'moment';

  // Values
  // For distributed: [startValue, endValue]
  // For point/moment: [value]
  values: number[];

  // Position along member (0.0 to 1.0)
  // Only relevant for member loads
  t_start?: number;
  t_end?: number;

  // Coordinate System for the load direction
  // global: x=horizontal, y=vertical (Gravity)
  // local: x=along member, y=perpendicular (Wind/Pressure)
  system: 'global' | 'local';

  // The angle of the load vector relative to the chosen system
  angle: number;
}
