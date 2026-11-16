"""Mathematical engine for DC nodal analysis."""

from math_engine.circuit import (
    Circuit,
    CurrentSource,
    InvalidCircuitError,
    Resistor,
    validate_circuit,
)
from math_engine.nodal_analysis import (
    ResistorResult,
    SolutionResult,
    build_nodal_system,
    solve_circuit,
)

__all__ = [
    "Circuit",
    "CurrentSource",
    "InvalidCircuitError",
    "Resistor",
    "ResistorResult",
    "SolutionResult",
    "build_nodal_system",
    "solve_circuit",
    "validate_circuit",
]
