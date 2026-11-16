"""Nodal analysis matrix construction, solving, and branch current calculation."""

from dataclasses import dataclass

from math_engine.circuit import Circuit, validate_circuit
from math_engine.gaussian_elimination import gaussian_elimination
from math_engine.verification import VerificationReport, verify_solution


@dataclass(frozen=True)
class ResistorResult:
    """Calculated electrical quantities for a single resistor."""

    component_id: str
    node_a: str
    node_b: str
    resistance: float
    voltage_drop: float  # V(node_a) - V(node_b)
    current: float       # Current flowing from node_a to node_b
    power: float


@dataclass(frozen=True)
class SolutionResult:
    """Complete mathematical output of solving a DC circuit."""

    non_ground_nodes: list[str]
    node_voltages: dict[str, float]
    resistor_results: list[ResistorResult]
    matrix_g: list[list[float]]
    vector_i: list[float]
    upper_triangular: list[list[float]]
    verification: VerificationReport


def build_nodal_system(circuit: Circuit) -> tuple[list[str], list[list[float]], list[float]]:
    """Construct the conductance matrix G and current injection vector I for G*V = I."""
    non_ground_nodes = sorted(
        node for node in circuit.nodes if node != circuit.ground_node
    )
    node_to_index = {node: idx for idx, node in enumerate(non_ground_nodes)}
    n = len(non_ground_nodes)

    matrix_g = [[0.0 for _ in range(n)] for _ in range(n)]
    vector_i = [0.0 for _ in range(n)]

    # Stamp resistors into the conductance matrix G using g = 1 / R.
    for resistor in circuit.resistors:
        conductance = 1.0 / resistor.resistance
        a_is_ground = resistor.node_a == circuit.ground_node
        b_is_ground = resistor.node_b == circuit.ground_node

        if a_is_ground and b_is_ground:
            continue
        elif not a_is_ground and b_is_ground:
            i = node_to_index[resistor.node_a]
            matrix_g[i][i] += conductance
        elif a_is_ground and not b_is_ground:
            j = node_to_index[resistor.node_b]
            matrix_g[j][j] += conductance
        else:
            i = node_to_index[resistor.node_a]
            j = node_to_index[resistor.node_b]
            matrix_g[i][i] += conductance
            matrix_g[j][j] += conductance
            matrix_g[i][j] -= conductance
            matrix_g[j][i] -= conductance

    # Stamp independent current sources into the net current injection vector I.
    # Positive current flows from node_from to node_to:
    # it leaves node_from (-I) and enters node_to (+I).
    for source in circuit.current_sources:
        if source.node_from != circuit.ground_node:
            i = node_to_index[source.node_from]
            vector_i[i] -= source.current
        if source.node_to != circuit.ground_node:
            j = node_to_index[source.node_to]
            vector_i[j] += source.current

    return non_ground_nodes, matrix_g, vector_i


def solve_circuit(circuit: Circuit) -> SolutionResult:
    """Validate the circuit, solve G*V = I, compute branch currents, and verify."""
    validate_circuit(circuit)
    non_ground_nodes, matrix_g, vector_i = build_nodal_system(circuit)
    solved_voltages, upper_triangular = gaussian_elimination(matrix_g, vector_i)

    node_voltages: dict[str, float] = {circuit.ground_node: 0.0}  # type: ignore[dict-item]
    for node_name, voltage in zip(non_ground_nodes, solved_voltages):
        node_voltages[node_name] = voltage

    resistor_results: list[ResistorResult] = []
    for resistor in circuit.resistors:
        va = node_voltages[resistor.node_a]
        vb = node_voltages[resistor.node_b]
        voltage_drop = va - vb
        current = voltage_drop / resistor.resistance
        power = voltage_drop * current
        resistor_results.append(
            ResistorResult(
                component_id=resistor.component_id,
                node_a=resistor.node_a,
                node_b=resistor.node_b,
                resistance=resistor.resistance,
                voltage_drop=voltage_drop,
                current=current,
                power=power,
            )
        )

    verification = verify_solution(
        circuit=circuit,
        node_voltages=node_voltages,
        matrix_g=matrix_g,
        vector_i=vector_i,
        non_ground_nodes=non_ground_nodes,
    )

    return SolutionResult(
        non_ground_nodes=non_ground_nodes,
        node_voltages=node_voltages,
        resistor_results=resistor_results,
        matrix_g=matrix_g,
        vector_i=vector_i,
        upper_triangular=upper_triangular,
        verification=verification,
    )
