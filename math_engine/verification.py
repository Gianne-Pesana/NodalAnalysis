"""Mathematical verification of nodal analysis solutions."""

from dataclasses import dataclass

from math_engine.circuit import Circuit


@dataclass(frozen=True)
class VerificationReport:
    """Results of residual (G*V - I) and node-by-node KCL verification."""

    passed: bool
    max_residual: float
    residuals: dict[str, float]
    max_kcl_error: float
    kcl_errors: dict[str, float]


def verify_solution(
    circuit: Circuit,
    node_voltages: dict[str, float],
    matrix_g: list[list[float]],
    vector_i: list[float],
    non_ground_nodes: list[str],
    tolerance: float = 1e-9,
) -> VerificationReport:
    """Verify the calculated voltages against G*V = I and KCL at every non-ground node."""
    n = len(non_ground_nodes)
    voltage_vector = [node_voltages[node] for node in non_ground_nodes]

    # 1. Check linear system residual: r = G * V - I.
    residuals: dict[str, float] = {}
    max_residual = 0.0
    for row in range(n):
        gv_row = 0.0
        for col in range(n):
            gv_row += matrix_g[row][col] * voltage_vector[col]
        residual_value = gv_row - vector_i[row]
        node_name = non_ground_nodes[row]
        residuals[node_name] = residual_value
        max_residual = max(max_residual, abs(residual_value))

    # 2. Check KCL at every non-ground node: sum of currents leaving the node = 0.
    kcl_sums: dict[str, float] = {node: 0.0 for node in non_ground_nodes}

    for resistor in circuit.resistors:
        va = node_voltages[resistor.node_a]
        vb = node_voltages[resistor.node_b]
        current_a_to_b = (va - vb) / resistor.resistance
        if resistor.node_a in kcl_sums:
            kcl_sums[resistor.node_a] += current_a_to_b
        if resistor.node_b in kcl_sums:
            kcl_sums[resistor.node_b] -= current_a_to_b

    for source in circuit.current_sources:
        # Positive source current flows from node_from to node_to.
        if source.node_from in kcl_sums:
            kcl_sums[source.node_from] += source.current
        if source.node_to in kcl_sums:
            kcl_sums[source.node_to] -= source.current

    max_kcl_error = 0.0
    for error in kcl_sums.values():
        max_kcl_error = max(max_kcl_error, abs(error))

    passed = (max_residual < tolerance) and (max_kcl_error < tolerance)
    return VerificationReport(
        passed=passed,
        max_residual=max_residual,
        residuals=residuals,
        max_kcl_error=max_kcl_error,
        kcl_errors=kcl_sums,
    )
