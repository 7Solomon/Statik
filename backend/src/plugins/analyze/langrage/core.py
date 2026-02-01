from typing import Tuple, Optional, Dict, List
import numpy as np

from src.models.langrage import LagrangianAnalysisResult
from src.plugins.analyze.langrage.assebly import assemble_matrices, build_dof_map, create_force_function
from src.models.analyze_models import StructuralSystem

from .solver import apply_boundary_conditions, solve_eigenvalues, check_stability, integrate_time_history

def analyze_lagrangian_dynamics(
    system: StructuralSystem,
    t_span: Tuple[float, float] = (0.0, 5.0),
    dt: float = 0.01,
) -> LagrangianAnalysisResult:
    
    #  Setup
    dof_map, n_dof = build_dof_map(system)
    external_force_func = create_force_function(system, dof_map)
    M, C, K = assemble_matrices(system, dof_map, n_dof)
    
    # Get Reduced Matrices AND the Transformation Matrix
    M_red, C_red, K_red, free_dofs, fixed_dofs, T_global = apply_boundary_conditions(M, C, K, system, dof_map)

    #  Pass T_global to the solver
    modes = solve_eigenvalues(M_red, K_red, system, dof_map, free_dofs, T_global)
    
    #  Stability
    stable, damping = check_stability(M_red, C_red, K_red)
    print(stable, damping)
    # Transient
    history = integrate_time_history(M_red, C_red, K_red, system, dof_map, free_dofs, t_span, dt, external_force_func)
    
    return LagrangianAnalysisResult(
        success=True,
        message=f"Solved {len(modes)} modes",
        system=system,
        natural_frequencies=modes,
        time_history=history,
        mass_matrix=M,
        stiffness_matrix=K,
        damping_matrix=C,
        is_stable=stable,
        critical_damping_ratio=damping
    )
