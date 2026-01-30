from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

@dataclass
class ModalResult:
    """Natural frequency and mode shape"""
    frequency: float  # Hz
    period: Optional[float]  # seconds (None if infinite)
    omega: float  # rad/s
    mode_shape: Dict[str, List[float]]  # {node_id: [u, v, theta]}
    
    def to_dict(self):
        return {
            "frequency": float(self.frequency),
            "period": float(self.period) if self.period is not None and not np.isinf(self.period) else None,
            "omega": float(self.omega),
            "modeShape": {k: [float(x) for x in v] for k, v in self.mode_shape.items()}
        }

@dataclass
class TimeStepResult:
    """State at one time instant"""
    time: float
    displacements: Dict[str, List[float]]  # {node_id: [u, v, theta]}
    velocities: Dict[str, List[float]]
    accelerations: Dict[str, List[float]]
    kinetic_energy: float
    potential_energy: float
    dissipated_energy: float
    total_energy: float
    
    def to_dict(self):
        return {
            "time": float(self.time),
            "displacements": {k: [float(x) for x in v] for k, v in self.displacements.items()},
            "velocities": {k: [float(x) for x in v] for k, v in self.velocities.items()},
            "accelerations": {k: [float(x) for x in v] for k, v in self.accelerations.items()},
            "kineticEnergy": float(self.kinetic_energy),
            "potentialEnergy": float(self.potential_energy),
            "dissipatedEnergy": float(self.dissipated_energy),
            "totalEnergy": float(self.total_energy)
        }

@dataclass
class LagrangianAnalysisResult:
    """Complete dynamic analysis results"""
    success: bool
    message: str
    system: object  # avoiding circular import with StructuralSystem
    
    # Modal analysis
    natural_frequencies: List[ModalResult]
    
    # Time history
    time_history: List[TimeStepResult]
    
    # Matrix forms (for reference)
    mass_matrix: np.ndarray
    stiffness_matrix: np.ndarray
    damping_matrix: np.ndarray
    
    # Stability
    is_stable: bool
    critical_damping_ratio: float
    
    def to_dict(self):
        return {
            "success": bool(self.success),
            "message": self.message,
            "system": self.system.to_dict(),
            "naturalFrequencies": [m.to_dict() for m in self.natural_frequencies],
            "timeHistory": [t.to_dict() for t in self.time_history],
            "massMatrix": self.mass_matrix.tolist(),
            "stiffnessMatrix": self.stiffness_matrix.tolist(),
            "dampingMatrix": self.damping_matrix.tolist(),
            "isStable": bool(self.is_stable),
            "criticalDampingRatio": float(self.critical_damping_ratio)
        }
