"""Manual Gaussian elimination with partial pivoting for solving G * V = I."""

from math_engine.circuit import InvalidCircuitError


def gaussian_elimination(
    matrix_g: list[list[float]],
    vector_i: list[float],
    pivot_tolerance: float = 1e-12,
) -> tuple[list[float], list[list[float]]]:
    """Solve the linear system G * V = I using Gaussian elimination with partial pivoting.

    Returns:
        voltages: Calculated node voltage vector V.
        augmented: Upper-triangular augmented matrix [U | c] after forward elimination.
    """
    n = len(vector_i)
    if n == 0 or len(matrix_g) != n:
        raise InvalidCircuitError("System dimensions are invalid or empty.")

    for row in matrix_g:
        if len(row) != n:
            raise InvalidCircuitError("Conductance matrix G must be square.")

    # Step 1 & 2: Build the augmented matrix [G | I] without modifying caller data.
    augmented: list[list[float]] = []
    for row_index in range(n):
        row_copy = [float(value) for value in matrix_g[row_index]]
        row_copy.append(float(vector_i[row_index]))
        augmented.append(row_copy)

    # Step 3-7: Forward elimination with partial pivoting.
    for col in range(n):
        # Find the row at or below 'col' with the largest absolute pivot candidate.
        pivot_row = col
        max_abs_value = abs(augmented[col][col])
        for candidate_row in range(col + 1, n):
            candidate_abs = abs(augmented[candidate_row][col])
            if candidate_abs > max_abs_value:
                max_abs_value = candidate_abs
                pivot_row = candidate_row

        if max_abs_value < pivot_tolerance:
            raise InvalidCircuitError(
                "Singular conductance matrix: the circuit has a floating node "
                "(e.g., connected only to current sources) or no unique solution."
            )

        # Swap the current row with the best pivot row if needed.
        if pivot_row != col:
            augmented[col], augmented[pivot_row] = augmented[pivot_row], augmented[col]

        # Eliminate all entries below the pivot in the current column.
        pivot_value = augmented[col][col]
        for row in range(col + 1, n):
            factor = augmented[row][col] / pivot_value
            if factor == 0.0:
                continue
            augmented[row][col] = 0.0
            for k in range(col + 1, n + 1):
                augmented[row][k] -= factor * augmented[col][k]

    # Step 8: Back substitution from the bottom row up.
    voltages = [0.0] * n
    for row in range(n - 1, -1, -1):
        rhs = augmented[row][n]
        for col in range(row + 1, n):
            rhs -= augmented[row][col] * voltages[col]

        diagonal = augmented[row][row]
        if abs(diagonal) < pivot_tolerance:
            raise InvalidCircuitError(
                "Zero diagonal encountered during back substitution; circuit is singular."
            )
        voltages[row] = rhs / diagonal

    return voltages, augmented
