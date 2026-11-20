This file is a merged representation of a subset of the codebase, containing files not matching ignore patterns, combined into a single document by Repomix.

# File Summary

## Purpose
This file contains a packed representation of a subset of the repository's contents that is considered the most important context.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Files matching these patterns are excluded: venv/**, .venv/**, __pycache__/**, *.pyc, .pytest_cache/**, .git/**, node_modules/**, dist/**, build/**
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
gui/
  __init__.py
  circuit_canvas.py
  components.py
  main_window.py
  matrix_view.py
  number_format.py
  properties_panel.py
  theme.py
math_engine/
  __init__.py
  circuit.py
  gaussian_elimination.py
  nodal_analysis.py
  verification.py
saved_circuits/
  test1.json
tests/
  test_gui_integration.py
  test_math_engine.py
utils/
  __init__.py
  circuit_io.py
main.py
requirements.txt
```

# Files

## File: gui/__init__.py
```python
"""PySide6 graphical user interface for the DC circuit simulator."""
```

## File: gui/matrix_view.py
```python
"""Typeset matrix display for the Matrices tab."""

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from gui import theme
from gui.number_format import format_entry

SCALE = 2.0


def matrix_cells(matrix: list[list[float]]) -> list[list[tuple[str, bool]]]:
    """(text, is_fraction) for every entry, using the display rule in number_format."""
    return [[format_entry(val) for val in row] for row in matrix]


def render_matrix(
    matrix: list[list[float]],
    augmented: bool = False,
    unit: str = "",
    lead_label: str = "",
    side_labels: Optional[list[str]] = None,
) -> QImage:
    """Return an image of the matrix."""
    cells = matrix_cells(matrix)
    n_rows = len(cells)
    n_cols = max((len(r) for r in cells), default=0)

    num_font = theme.mono_font(10.0)
    lead_font = theme.ui_font(11.0, QFont.Weight.DemiBold)
    side_font = theme.ui_font(theme.SIZE_SMALL)
    num_m = QFontMetricsF(num_font)
    lead_m = QFontMetricsF(lead_font)
    side_m = QFontMetricsF(side_font)

    unit_text = f" {unit}" if unit else ""
    unit_w = num_m.horizontalAdvance(unit_text) if unit else 0.0

    col_gap = num_m.horizontalAdvance("0") * 2.6
    aug_gap = col_gap * 1.3
    bracket_pad = num_m.horizontalAdvance("0") * 1.9
    serif = 6.0
    bracket_w = 2.0
    row_h = num_m.height() * 1.55
    margin_v = 4.0

    col_w = [0.0] * n_cols
    for row in cells:
        for c, (text, _) in enumerate(row):
            col_w[c] = max(col_w[c], num_m.horizontalAdvance(text) + unit_w)

    gaps = [aug_gap if (augmented and c == n_cols - 2) else col_gap for c in range(max(n_cols - 1, 0))]

    lead_w = lead_m.horizontalAdvance(lead_label) + 12.0 if lead_label else 0.0
    left_x = lead_w + bracket_w
    content_x = left_x + bracket_pad
    content_w = sum(col_w) + sum(gaps)
    right_x = content_x + content_w + bracket_pad
    side_w = max((side_m.horizontalAdvance(s) for s in (side_labels or [])), default=0.0)
    width = right_x + bracket_w + (14.0 + side_w if side_labels else 2.0)
    height = margin_v * 2 + n_rows * row_h

    image = QImage(
        int(width * SCALE) + 2, int(height * SCALE) + 2, QImage.Format.Format_ARGB32_Premultiplied
    )
    image.fill(Qt.GlobalColor.transparent)
    image.setDevicePixelRatio(SCALE)

    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    top, bottom = margin_v, height - margin_v

    left_mid = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    right_mid = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    if lead_label:
        theme.draw_text(p, QRectF(0, top, lead_w, bottom - top), lead_label, lead_font, theme.TEXT, left_mid)

    pen = QPen(QColor(theme.BRACKET), bracket_w)
    pen.setCapStyle(Qt.PenCapStyle.SquareCap)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for x, d in ((left_x, 1), (right_x, -1)):
        p.drawPolyline([QPointF(x + d * serif, top), QPointF(x, top), QPointF(x, bottom), QPointF(x + d * serif, bottom)])

    if augmented and n_cols >= 2:
        x = content_x + sum(col_w[:-1]) + sum(gaps[:-1]) + aug_gap / 2
        p.setPen(QPen(QColor(theme.ACCENT), 2.0))
        p.drawLine(QPointF(x, top + 4.0), QPointF(x, bottom - 4.0))

    for r, row in enumerate(cells):
        y = margin_v + r * row_h
        x = content_x
        for c, (text, is_fraction) in enumerate(row):
            if unit:
                theme.draw_text(p, QRectF(x, y, col_w[c], row_h), unit_text, num_font, theme.TEXT_MUTED, right_mid)
            cell = QRectF(x, y, col_w[c] - unit_w, row_h)
            theme.draw_text(p, cell, text, num_font, theme.FRACTION if is_fraction else theme.TEXT, right_mid)
            if c < len(gaps):
                x += col_w[c] + gaps[c]
        if side_labels and r < len(side_labels):
            rect = QRectF(right_x + bracket_w + 14.0, y, side_w + 2, row_h)
            theme.draw_text(p, rect, side_labels[r], side_font, theme.TEXT_FAINT, left_mid)
    p.end()
    return image


class MatrixPanel(QScrollArea):
    """Scrollable list of captioned, typeset matrices."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("MatrixPanel")
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self._body = QWidget()
        self._body.setObjectName("MatrixPanelBody")
        self._layout = QVBoxLayout(self._body)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(6)
        self._layout.addStretch(1)
        self.setWidget(self._body)

    def clear(self) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _add(self, widget: QWidget) -> None:
        self._layout.insertWidget(self._layout.count() - 1, widget)

    def add_matrix(self, caption: str, image: QImage, first: bool = False) -> None:
        if not first:
            self._layout.insertSpacing(self._layout.count() - 1, 12)
        self._add(theme.label(caption, "SectionTitle", theme.caption_font(uppercase=False)))
        picture = QLabel()
        picture.setPixmap(QPixmap.fromImage(image))
        picture.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._add(picture)

    def show_matrices(
        self,
        matrix_g: list[list[float]],
        vector_i: list[float],
        upper_triangular: list[list[float]],
        node_names: list[str],
        node_voltages: list[float],
    ) -> None:
        self.clear()
        g_aug = [list(row) + [vector_i[i]] for i, row in enumerate(matrix_g)]
        self.add_matrix("AUGMENTED MATRIX [G | I]", render_matrix(g_aug, augmented=True), first=True)
        self.add_matrix("AFTER ELIMINATION [U | c]", render_matrix(upper_triangular, augmented=True))
        self.add_matrix(
            "SOLUTION",
            render_matrix([[v] for v in node_voltages], unit="V", lead_label="V =", side_labels=node_names),
        )
```

## File: gui/number_format.py
```python
"""Display-only number formatting: exact fractions for repeating decimals."""

import math
from fractions import Fraction

MAX_DENOMINATOR = 1000
TOLERANCE = 1e-9
MAX_FRACTION_CHARS = 7
MINUS = "−"


def exact_fraction(value: float) -> Fraction | None:
    """Return the exact fraction for a repeating decimal, or None if not applicable."""
    if not math.isfinite(value):
        return None
    frac = Fraction(value).limit_denominator(MAX_DENOMINATOR)
    if frac.denominator == 1:
        return None
    if abs(float(frac) - value) > TOLERANCE * max(1.0, abs(value)):
        return None
    d = frac.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    if d == 1:
        return None  # terminating decimal: the decimal is already exact
    if len(f"{frac.numerator}/{frac.denominator}") > MAX_FRACTION_CHARS:
        return None
    return frac


def fraction_suffix(value: float) -> str:
    """" (7/6)" for repeating decimals, "" otherwise. Used next to a decimal."""
    frac = exact_fraction(value)
    if frac is None:
        return ""
    return f" ({frac.numerator}/{frac.denominator})"


def fixed(value: float, decimals: int, width: int = 0) -> str:
    """Format to `decimals` places, then cut trailing zeros (100.000000 -> "100")."""
    text = f"{value:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("-0", ""):
        text = "0"
    return text.rjust(width)


def format_entry(value: float) -> tuple[str, bool]:
    """Text for one matrix entry and whether it is an exact fraction."""
    frac = exact_fraction(value)
    if frac is not None:
        text = f"{abs(frac.numerator)}/{frac.denominator}"
        return (MINUS + text if frac < 0 else text), True
    return fixed(value, 4).replace("-", MINUS), False
```

## File: math_engine/__init__.py
```python
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
```

## File: math_engine/circuit.py
```python
"""Circuit data structures and validation for DC nodal analysis."""

from dataclasses import dataclass
import math


class InvalidCircuitError(Exception):
    """Raised when a circuit is invalid, disconnected, or has no unique solution."""


@dataclass(frozen=True)
class Resistor:
    """Represents a linear resistor connected between two electrical nodes."""

    component_id: str
    node_a: str
    node_b: str
    resistance: float


@dataclass(frozen=True)
class CurrentSource:
    """Represents an independent DC current source.

    Positive current flows from node_from to node_to.
    """

    component_id: str
    node_from: str
    node_to: str
    current: float


@dataclass(frozen=True)
class Circuit:
    """Complete electrical representation passed from the GUI to the math engine."""

    nodes: list[str]
    ground_node: str | None
    resistors: list[Resistor]
    current_sources: list[CurrentSource]


def validate_circuit(circuit: Circuit) -> None:
    """Validate circuit topology and component values before building matrices."""
    if not circuit.ground_node:
        raise InvalidCircuitError("No ground reference is connected to the circuit.")

    if circuit.ground_node not in circuit.nodes:
        raise InvalidCircuitError(
            f"Ground node '{circuit.ground_node}' is not in the circuit node list."
        )

    non_ground_nodes = [node for node in circuit.nodes if node != circuit.ground_node]
    if not non_ground_nodes:
        raise InvalidCircuitError(
            "Circuit must contain at least one non-ground node to solve."
        )

    node_set = set(circuit.nodes)
    adjacency: dict[str, set[str]] = {node: set() for node in circuit.nodes}

    for resistor in circuit.resistors:
        if not math.isfinite(resistor.resistance) or resistor.resistance <= 0.0:
            raise InvalidCircuitError(
                f"Resistor '{resistor.component_id}' must have a finite positive resistance "
                f"(got {resistor.resistance})."
            )
        if resistor.node_a not in node_set or resistor.node_b not in node_set:
            raise InvalidCircuitError(
                f"Resistor '{resistor.component_id}' references an unknown node."
            )
        adjacency[resistor.node_a].add(resistor.node_b)
        adjacency[resistor.node_b].add(resistor.node_a)

    for source in circuit.current_sources:
        if not math.isfinite(source.current):
            raise InvalidCircuitError(
                f"Current source '{source.component_id}' must have a finite current "
                f"(got {source.current})."
            )
        if source.node_from not in node_set or source.node_to not in node_set:
            raise InvalidCircuitError(
                f"Current source '{source.component_id}' references an unknown node."
            )
        adjacency[source.node_from].add(source.node_to)
        adjacency[source.node_to].add(source.node_from)

    # Check that every node is reachable from ground (catches completely floating islands).
    visited: set[str] = {circuit.ground_node}
    stack: list[str] = [circuit.ground_node]
    while stack:
        current = stack.pop()
        for neighbor in adjacency[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                stack.append(neighbor)

    disconnected = [node for node in non_ground_nodes if node not in visited]
    if disconnected:
        joined = ", ".join(disconnected)
        raise InvalidCircuitError(
            f"Floating or disconnected node(s) detected: {joined}. "
            "All nodes must have a path to ground."
        )
```

## File: math_engine/gaussian_elimination.py
```python
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
```

## File: math_engine/nodal_analysis.py
```python
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
```

## File: math_engine/verification.py
```python
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
```

## File: saved_circuits/test1.json
```json
{
  "version": 1,
  "components": [
    {
      "component_id": "I1",
      "kind": "current_source",
      "x": -40.0,
      "y": 120.0,
      "rotation": 270,
      "value": 0.8
    },
    {
      "component_id": "R1",
      "kind": "resistor",
      "x": 100.0,
      "y": 120.0,
      "rotation": 90,
      "value": 180.0
    },
    {
      "component_id": "R2",
      "kind": "resistor",
      "x": 200.0,
      "y": 120.0,
      "rotation": 90,
      "value": 30.0
    },
    {
      "component_id": "GND2",
      "kind": "ground",
      "x": -40.0,
      "y": 240.0,
      "rotation": 0,
      "value": 0.0
    }
  ],
  "junctions": [],
  "wires": [
    {
      "wire_id": "W1",
      "start": [
        "terminal",
        "I1",
        1
      ],
      "end": [
        "terminal",
        "R1",
        0
      ]
    },
    {
      "wire_id": "W2",
      "start": [
        "terminal",
        "R1",
        0
      ],
      "end": [
        "terminal",
        "R2",
        0
      ]
    },
    {
      "wire_id": "W3",
      "start": [
        "terminal",
        "R2",
        1
      ],
      "end": [
        "terminal",
        "R1",
        1
      ]
    },
    {
      "wire_id": "W6",
      "start": [
        "terminal",
        "R1",
        1
      ],
      "end": [
        "terminal",
        "I1",
        0
      ]
    },
    {
      "wire_id": "W8",
      "start": [
        "terminal",
        "I1",
        0
      ],
      "end": [
        "terminal",
        "GND2",
        0
      ]
    }
  ]
}
```

## File: tests/test_math_engine.py
```python
"""Independent unit tests for the DC nodal analysis mathematical engine."""

import unittest

from math_engine.circuit import Circuit, CurrentSource, InvalidCircuitError, Resistor
from math_engine.nodal_analysis import solve_circuit


class TestMathEngine(unittest.TestCase):
    """Verify matrix construction, Gaussian elimination, branch currents, and validation."""

    def test_1_single_resistor_and_current_source(self) -> None:
        """2 A current source into a 4 ohm resistor to ground -> V = 8 V."""
        circuit = Circuit(
            nodes=["GND", "N1"],
            ground_node="GND",
            resistors=[Resistor("R1", "N1", "GND", 4.0)],
            current_sources=[CurrentSource("I1", "GND", "N1", 2.0)],
        )
        result = solve_circuit(circuit)

        self.assertAlmostEqual(result.node_voltages["GND"], 0.0, places=9)
        self.assertAlmostEqual(result.node_voltages["N1"], 8.0, places=9)
        self.assertAlmostEqual(result.resistor_results[0].current, 2.0, places=9)
        self.assertAlmostEqual(result.resistor_results[0].voltage_drop, 8.0, places=9)
        self.assertTrue(result.verification.passed)
        self.assertLess(result.verification.max_residual, 1e-9)
        self.assertLess(result.verification.max_kcl_error, 1e-9)

    def test_2_parallel_resistors(self) -> None:
        """2 A current source into parallel 4 ohm and 6 ohm resistors -> V = 4.8 V."""
        circuit = Circuit(
            nodes=["GND", "N1"],
            ground_node="GND",
            resistors=[
                Resistor("R1", "N1", "GND", 4.0),
                Resistor("R2", "N1", "GND", 6.0),
            ],
            current_sources=[CurrentSource("I1", "GND", "N1", 2.0)],
        )
        result = solve_circuit(circuit)

        self.assertAlmostEqual(result.node_voltages["N1"], 4.8, places=9)
        currents = {r.component_id: r.current for r in result.resistor_results}
        self.assertAlmostEqual(currents["R1"], 1.2, places=9)
        self.assertAlmostEqual(currents["R2"], 0.8, places=9)
        self.assertTrue(result.verification.passed)

    def test_3_multiple_interconnected_nodes(self) -> None:
        """Hand-calculated 3-node interconnected resistor network."""
        circuit = Circuit(
            nodes=["GND", "N1", "N2", "N3"],
            ground_node="GND",
            resistors=[
                Resistor("R1", "N1", "GND", 2.0),
                Resistor("R2", "N1", "N2", 4.0),
                Resistor("R3", "N2", "GND", 2.0),
                Resistor("R4", "N2", "N3", 2.0),
                Resistor("R5", "N3", "GND", 1.0),
            ],
            current_sources=[
                CurrentSource("I1", "GND", "N1", 6.0),
                CurrentSource("I2", "GND", "N3", 3.0),
            ],
        )
        result = solve_circuit(circuit)

        self.assertAlmostEqual(result.node_voltages["N1"], 9.0, places=9)
        self.assertAlmostEqual(result.node_voltages["N2"], 3.0, places=9)
        self.assertAlmostEqual(result.node_voltages["N3"], 3.0, places=9)

        currents = {r.component_id: r.current for r in result.resistor_results}
        self.assertAlmostEqual(currents["R1"], 4.5, places=9)
        self.assertAlmostEqual(currents["R2"], 1.5, places=9)
        self.assertAlmostEqual(currents["R3"], 1.5, places=9)
        self.assertAlmostEqual(currents["R4"], 0.0, places=9)
        self.assertAlmostEqual(currents["R5"], 3.0, places=9)
        self.assertTrue(result.verification.passed)

    def test_4_current_source_between_non_ground_nodes(self) -> None:
        """Current source from N1 to N2 respects sign convention (-I at N1, +I at N2)."""
        circuit = Circuit(
            nodes=["GND", "N1", "N2"],
            ground_node="GND",
            resistors=[
                Resistor("R1", "N1", "GND", 2.0),
                Resistor("R2", "N2", "GND", 2.0),
                Resistor("R3", "N1", "N2", 4.0),
            ],
            current_sources=[CurrentSource("I1", "N1", "N2", 3.0)],
        )
        result = solve_circuit(circuit)

        self.assertAlmostEqual(result.node_voltages["N1"], -3.0, places=9)
        self.assertAlmostEqual(result.node_voltages["N2"], 3.0, places=9)
        self.assertTrue(result.verification.passed)

    def test_5_floating_and_singular_nodes_raise_error(self) -> None:
        """Disconnected nodes or nodes with no conductive path to ground fail cleanly."""
        disconnected_circuit = Circuit(
            nodes=["GND", "N1", "N_FLOAT"],
            ground_node="GND",
            resistors=[Resistor("R1", "N1", "GND", 10.0)],
            current_sources=[CurrentSource("I1", "GND", "N1", 1.0)],
        )
        with self.assertRaises(InvalidCircuitError):
            solve_circuit(disconnected_circuit)

        # Node connected only to a current source has a zero row/col in G -> singular.
        current_only_island = Circuit(
            nodes=["GND", "N1"],
            ground_node="GND",
            resistors=[],
            current_sources=[CurrentSource("I1", "GND", "N1", 2.0)],
        )
        with self.assertRaises(InvalidCircuitError):
            solve_circuit(current_only_island)

    def test_invalid_values_and_missing_ground(self) -> None:
        """Zero/negative resistance and missing ground are rejected."""
        no_ground = Circuit(
            nodes=["N1", "N2"],
            ground_node=None,
            resistors=[Resistor("R1", "N1", "N2", 5.0)],
            current_sources=[],
        )
        with self.assertRaises(InvalidCircuitError):
            solve_circuit(no_ground)

        zero_resistor = Circuit(
            nodes=["GND", "N1"],
            ground_node="GND",
            resistors=[Resistor("R1", "N1", "GND", 0.0)],
            current_sources=[CurrentSource("I1", "GND", "N1", 1.0)],
        )
        with self.assertRaises(InvalidCircuitError):
            solve_circuit(zero_resistor)


if __name__ == "__main__":
    unittest.main()
```

## File: utils/__init__.py
```python

```

## File: utils/circuit_io.py
```python
"""Lightweight JSON serialization for saving and loading GUI circuits."""

import json
from pathlib import Path
from typing import Iterable

from gui.components import ComponentItem, EndpointKey, WireJunction, WireSegment


def _parse_endpoint(raw: object) -> EndpointKey:
    if not isinstance(raw, list) or len(raw) != 3:
        raise ValueError(f"Invalid wire endpoint: {raw!r}")
    kind, owner_id, term_idx = raw
    return (str(kind), str(owner_id), int(term_idx))


def save_circuit(
    file_path: str | Path,
    components: Iterable[ComponentItem],
    junctions: Iterable[WireJunction],
    wires: Iterable[WireSegment],
) -> None:
    """Save components, junctions, and wires to a JSON file."""
    payload = {
        "version": 1,
        "components": [
            {
                "component_id": c.component_id,
                "kind": c.kind,
                "x": c.x,
                "y": c.y,
                "rotation": c.rotation,
                "value": c.value,
            }
            for c in components
        ],
        "junctions": [
            {
                "junction_id": j.junction_id,
                "x": j.x,
                "y": j.y,
            }
            for j in junctions
        ],
        "wires": [
            {
                "wire_id": w.wire_id,
                "start": list(w.start),
                "end": list(w.end),
            }
            for w in wires
        ],
    }
    Path(file_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_circuit(
    file_path: str | Path,
) -> tuple[list[ComponentItem], list[WireJunction], list[WireSegment]]:
    """Load components, junctions, and wires from a JSON file."""
    try:
        data = json.loads(Path(file_path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid circuit JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Invalid circuit file format.")

    try:
        components = [
            ComponentItem(
                component_id=str(c["component_id"]),
                kind=str(c["kind"]),
                x=float(c["x"]),
                y=float(c["y"]),
                rotation=int(c.get("rotation", 0)),
                value=float(c.get("value", 0.0)),
            )
            for c in data.get("components", [])
        ]
        junctions = [
            WireJunction(
                junction_id=str(j["junction_id"]),
                x=float(j["x"]),
                y=float(j["y"]),
            )
            for j in data.get("junctions", [])
        ]
        wires = [
            WireSegment(
                wire_id=str(w["wire_id"]),
                start=_parse_endpoint(w["start"]),
                end=_parse_endpoint(w["end"]),
            )
            for w in data.get("wires", [])
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid circuit file contents: {exc}") from exc

    return components, junctions, wires
```

## File: requirements.txt
```
PySide6>=6.5.0
```

## File: gui/components.py
```python
"""Visual circuit data models and conversion from GUI elements to math_engine.Circuit."""

from collections import deque
from dataclasses import dataclass

from math_engine.circuit import Circuit, CurrentSource, InvalidCircuitError, Resistor
from math_engine.nodal_analysis import SolutionResult

EndpointKey = tuple[str, str, int]  # (kind: "terminal"|"junction", owner_id, terminal_index)


@dataclass
class ComponentItem:
    """Visual component placed on the circuit canvas."""

    component_id: str
    kind: str  # "resistor", "current_source", or "ground"
    x: float
    y: float
    rotation: int = 0  # 0, 90, 180, or 270 degrees
    value: float = 0.0  # Ohms for resistor, Amperes for current_source

    def terminal_count(self) -> int:
        return 1 if self.kind == "ground" else 2

    def terminal_positions(self) -> list[tuple[float, float]]:
        """Return world (x, y) coordinates of each terminal after rotation."""
        if self.kind == "ground":
            base_offsets = [(0.0, -24.0)]
        else:
            # Terminal 0 is left (-45, 0), Terminal 1 is right (+45, 0) at 0 deg.
            base_offsets = [(-45.0, 0.0), (45.0, 0.0)]

        steps = (self.rotation // 90) % 4
        positions: list[tuple[float, float]] = []
        for dx, dy in base_offsets:
            rx, ry = dx, dy
            for _ in range(steps):
                rx, ry = -ry, rx
            positions.append((self.x + rx, self.y + ry))
        return positions


@dataclass
class WireJunction:
    """Explicit junction dot where multiple wire segments meet."""

    junction_id: str
    x: float
    y: float


@dataclass
class WireSegment:
    """Ideal zero-resistance wire connecting two endpoints."""

    wire_id: str
    start: EndpointKey
    end: EndpointKey


@dataclass
class ExtractionResult:
    """Result of converting GUI components and wires into a math_engine Circuit."""

    circuit: Circuit
    endpoint_to_node: dict[EndpointKey, str]
    wire_to_node: dict[str, str]
    wire_to_components: dict[str, list[str]]


def resolve_endpoint_position(
    endpoint: EndpointKey,
    components_by_id: dict[str, ComponentItem],
    junctions_by_id: dict[str, WireJunction],
) -> tuple[float, float]:
    """Return the current (x, y) canvas position of a wire endpoint."""
    ep_kind, owner_id, term_idx = endpoint
    if ep_kind == "terminal":
        comp = components_by_id[owner_id]
        return comp.terminal_positions()[term_idx]
    junction = junctions_by_id[owner_id]
    return (junction.x, junction.y)


def extract_circuit_from_gui(
    components: list[ComponentItem],
    junctions: list[WireJunction],
    wires: list[WireSegment],
) -> ExtractionResult:
    """Group electrically connected terminals/junctions into nodes and build a Circuit."""
    if not components:
        raise InvalidCircuitError("The circuit is empty. Place components and connect them.")

    # Build adjacency graph of all endpoints (component terminals + wire junctions).
    adjacency: dict[EndpointKey, set[EndpointKey]] = {}
    ground_endpoints: set[EndpointKey] = set()

    for comp in components:
        for term_idx in range(comp.terminal_count()):
            key: EndpointKey = ("terminal", comp.component_id, term_idx)
            adjacency[key] = set()
            if comp.kind == "ground":
                ground_endpoints.add(key)

    for junction in junctions:
        key = ("junction", junction.junction_id, 0)
        adjacency[key] = set()

    for wire in wires:
        if wire.start in adjacency and wire.end in adjacency:
            adjacency[wire.start].add(wire.end)
            adjacency[wire.end].add(wire.start)

    # Find connected components (each connected group is one electrical node).
    visited: set[EndpointKey] = set()
    groups: list[list[EndpointKey]] = []

    for endpoint in adjacency:
        if endpoint in visited:
            continue
        group: list[EndpointKey] = []
        queue: deque[EndpointKey] = deque([endpoint])
        visited.add(endpoint)
        while queue:
            current = queue.popleft()
            group.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        groups.append(group)

    # Identify which groups contain a ground component terminal.
    ground_group_indices: list[int] = []
    for idx, group in enumerate(groups):
        if any(ep in ground_endpoints for ep in group):
            ground_group_indices.append(idx)

    if len(ground_group_indices) == 0:
        raise InvalidCircuitError("No ground reference is connected to the circuit.")
    if len(ground_group_indices) > 1:
        raise InvalidCircuitError(
            "Multiple disconnected ground references found. "
            "Connect all ground symbols to the same electrical node."
        )

    ground_idx = ground_group_indices[0]
    endpoint_to_node: dict[EndpointKey, str] = {}
    nodes: list[str] = ["GND"]

    for ep in groups[ground_idx]:
        endpoint_to_node[ep] = "GND"

    non_ground_counter = 1
    for idx, group in enumerate(groups):
        if idx == ground_idx:
            continue
        # Skip isolated junctions with no component terminals attached.
        has_terminal = any(ep[0] == "terminal" for ep in group)
        if not has_terminal:
            continue
        node_name = f"N{non_ground_counter}"
        non_ground_counter += 1
        nodes.append(node_name)
        for ep in group:
            endpoint_to_node[ep] = node_name

    resistors: list[Resistor] = []
    current_sources: list[CurrentSource] = []

    for comp in components:
        if comp.kind == "resistor":
            node_a = endpoint_to_node[("terminal", comp.component_id, 0)]
            node_b = endpoint_to_node[("terminal", comp.component_id, 1)]
            resistors.append(
                Resistor(
                    component_id=comp.component_id,
                    node_a=node_a,
                    node_b=node_b,
                    resistance=comp.value,
                )
            )
        elif comp.kind == "current_source":
            node_from = endpoint_to_node[("terminal", comp.component_id, 0)]
            node_to = endpoint_to_node[("terminal", comp.component_id, 1)]
            current_sources.append(
                CurrentSource(
                    component_id=comp.component_id,
                    node_from=node_from,
                    node_to=node_to,
                    current=comp.value,
                )
            )

    # Map each wire to its electrical node and connected component IDs for the inspector.
    node_to_components: dict[str, set[str]] = {node: set() for node in nodes}
    for ep, node_name in endpoint_to_node.items():
        if ep[0] == "terminal":
            node_to_components[node_name].add(ep[1])

    wire_to_node: dict[str, str] = {}
    wire_to_components: dict[str, list[str]] = {}
    for wire in wires:
        node_name = endpoint_to_node.get(wire.start) or endpoint_to_node.get(wire.end)
        if node_name:
            wire_to_node[wire.wire_id] = node_name
            wire_to_components[wire.wire_id] = sorted(node_to_components[node_name])

    circuit = Circuit(
        nodes=nodes,
        ground_node="GND",
        resistors=resistors,
        current_sources=current_sources,
    )
    return ExtractionResult(
        circuit=circuit,
        endpoint_to_node=endpoint_to_node,
        wire_to_node=wire_to_node,
        wire_to_components=wire_to_components,
    )


def _solve_linear_system(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Solve a small dense linear system Ax = b via Gaussian elimination with partial pivoting."""
    n = len(rhs)
    if n == 0:
        return []
    aug = [row[:] + [rhs[idx]] for idx, row in enumerate(matrix)]

    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-15:
            continue
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_val = aug[col][col]
        for row in range(col + 1, n):
            factor = aug[row][col] / pivot_val
            if factor == 0.0:
                continue
            for c in range(col, n + 1):
                aug[row][c] -= factor * aug[col][c]

    x = [0.0] * n
    for row in range(n - 1, -1, -1):
        diag = aug[row][row]
        if abs(diag) < 1e-15:
            continue
        total = aug[row][n] - sum(aug[row][c] * x[c] for c in range(row + 1, n))
        x[row] = total / diag
    return x


def compute_wire_currents(
    wires: list[WireSegment],
    extraction: ExtractionResult,
    solution: SolutionResult,
) -> dict[str, float]:
    """Compute signed conventional current for each wire (positive: start -> end).

    For each electrical node, solves KCL on the node's wire graph using the
    graph Laplacian L * p = b, where b is the net current injected into the wire
    graph at each component terminal.
    """
    injected: dict[EndpointKey, float] = {}

    # Positive resistor current flows from node_a (T0) -> resistor -> node_b (T1).
    for res in solution.resistor_results:
        t0: EndpointKey = ("terminal", res.component_id, 0)
        t1: EndpointKey = ("terminal", res.component_id, 1)
        injected[t0] = injected.get(t0, 0.0) - res.current
        injected[t1] = injected.get(t1, 0.0) + res.current

    # Positive source current flows from node_from (T0) -> source -> node_to (T1).
    for src in extraction.circuit.current_sources:
        t0 = ("terminal", src.component_id, 0)
        t1 = ("terminal", src.component_id, 1)
        injected[t0] = injected.get(t0, 0.0) - src.current
        injected[t1] = injected.get(t1, 0.0) + src.current

    # Group wires by electrical node.
    node_wires: dict[str, list[WireSegment]] = {}
    for wire in wires:
        node_name = extraction.wire_to_node.get(wire.wire_id)
        if node_name is not None:
            node_wires.setdefault(node_name, []).append(wire)

    wire_currents: dict[str, float] = {wire.wire_id: 0.0 for wire in wires}

    for segs in node_wires.values():
        adj: dict[EndpointKey, list[tuple[EndpointKey, str]]] = {}
        for seg in segs:
            adj.setdefault(seg.start, []).append((seg.end, seg.wire_id))
            adj.setdefault(seg.end, []).append((seg.start, seg.wire_id))

        visited: set[EndpointKey] = set()
        for root in adj:
            if root in visited:
                continue
            comp_verts: list[EndpointKey] = []
            queue: deque[EndpointKey] = deque([root])
            visited.add(root)
            while queue:
                curr = queue.popleft()
                comp_verts.append(curr)
                for nbr, _ in adj[curr]:
                    if nbr not in visited:
                        visited.add(nbr)
                        queue.append(nbr)

            if len(comp_verts) <= 1:
                continue

            vert_idx = {ep: i for i, ep in enumerate(comp_verts)}
            k = len(comp_verts)
            laplacian = [[0.0] * k for _ in range(k)]
            comp_segs: list[WireSegment] = []
            for seg in segs:
                if seg.start in vert_idx and seg.end in vert_idx:
                    u, v = vert_idx[seg.start], vert_idx[seg.end]
                    laplacian[u][u] += 1.0
                    laplacian[v][v] += 1.0
                    laplacian[u][v] -= 1.0
                    laplacian[v][u] -= 1.0
                    comp_segs.append(seg)

            # Fix gauge p[0] = 0.0 and solve the (k-1) x (k-1) reduced system.
            reduced_l = [row[1:] for row in laplacian[1:]]
            reduced_b = [injected.get(ep, 0.0) for ep in comp_verts[1:]]
            p_rest = _solve_linear_system(reduced_l, reduced_b)
            potentials = [0.0] + p_rest

            for seg in comp_segs:
                u, v = vert_idx[seg.start], vert_idx[seg.end]
                current = potentials[u] - potentials[v]
                wire_currents[seg.wire_id] = 0.0 if abs(current) < 1e-12 else current

    return wire_currents
```

## File: gui/properties_panel.py
```python
"""Properties editor and mathematical results panel."""

import html
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui import theme
from gui.components import ComponentItem, ExtractionResult
from gui.matrix_view import MatrixPanel
from gui.number_format import fixed, fraction_suffix
from math_engine.nodal_analysis import SolutionResult


def _report_html(text: str) -> str:
    """Present a plain-text report with real headings."""
    heading_style = (
        f"font-family: '{theme.UI_FONT_FAMILY}'; font-size: {theme.SIZE_SMALL}pt; "
        f"font-weight: bold; color: {theme.TEXT_MUTED};"
    )
    mono_families = ", ".join(f"'{f}'" for f in theme.MONO_FONT_FAMILIES)
    pre_style = f"font-family: {mono_families}, monospace; font-size: {theme.SIZE_MONO}pt; color: {theme.TEXT}; margin: 0;"
    parts: list[str] = []
    block: list[str] = []
    first_heading = True

    def flush() -> None:
        while block and not block[-1].strip():
            block.pop()
        while block and not block[0].strip():
            block.pop(0)
        if block:
            parts.append(f'<pre style="{pre_style}">{html.escape(chr(10).join(block))}</pre>')
        block.clear()

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("===") and stripped.endswith("===") and len(stripped) > 6:
            flush()
            top, first_heading = (0 if first_heading else 14), False
            title = html.escape(stripped.strip("= "))
            parts.append(f'<p style="{heading_style} margin-top: {top}px; margin-bottom: 4px;">{title}</p>')
        else:
            block.append(line)
    flush()
    return "".join(parts)


class PropertiesPanel(QWidget):
    """Right-hand panel for editing selected component values and viewing solver results."""

    value_changed = Signal(str, float)  # (component_id, new_value)
    flip_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PropertiesPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(360)
        self._current_comp_id: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(6)

        # --- Selected Item Properties ---
        layout.addWidget(theme.label("Selected Item", "SectionTitle", theme.caption_font()))

        self.prop_group = QGroupBox()
        self.prop_form = QFormLayout(self.prop_group)
        self.prop_form.setHorizontalSpacing(14)
        self.prop_form.setVerticalSpacing(7)
        self.prop_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.lbl_id = QLabel("—")
        self.lbl_type = QLabel("—")
        self.lbl_value_title = QLabel("Value:")
        self.edit_value = QLineEdit()
        self.edit_value.setVisible(False)
        self.edit_value.editingFinished.connect(self._on_value_edited)

        self.btn_flip = QPushButton("Flip Direction (180°)")
        self.btn_flip.setVisible(False)
        self.btn_flip.clicked.connect(self.flip_requested.emit)

        self.lbl_extra_1_title = QLabel("")
        self.lbl_extra_1 = QLabel("")
        self.lbl_extra_2_title = QLabel("")
        self.lbl_extra_2 = QLabel("")
        self.lbl_extra_3_title = QLabel("")
        self.lbl_extra_3 = QLabel("")

        id_title = QLabel("ID:")
        type_title = QLabel("Type:")
        for title_lbl in (
            id_title,
            type_title,
            self.lbl_value_title,
            self.lbl_extra_1_title,
            self.lbl_extra_2_title,
            self.lbl_extra_3_title,
        ):
            title_lbl.setObjectName("FormLabel")
        self.lbl_id.setObjectName("SelectionId")
        self.lbl_type.setObjectName("SelectionType")
        for value_lbl in (self.lbl_extra_1, self.lbl_extra_2, self.lbl_extra_3):
            value_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.prop_form.addRow(id_title, self.lbl_id)
        self.prop_form.addRow(type_title, self.lbl_type)
        self.prop_form.addRow(self.lbl_value_title, self.edit_value)
        self.prop_form.addRow("", self.btn_flip)
        self.prop_form.addRow(self.lbl_extra_1_title, self.lbl_extra_1)
        self.prop_form.addRow(self.lbl_extra_2_title, self.lbl_extra_2)
        self.prop_form.addRow(self.lbl_extra_3_title, self.lbl_extra_3)

        layout.addWidget(self.prop_group)
        layout.addSpacing(10)

        # --- Solver Status & Results ---
        layout.addWidget(theme.label("Results", "SectionTitle", theme.caption_font()))
        self.status_label = theme.label(wrap=True)
        self._set_status("Status: Not Solved", theme.STATUS_NEUTRAL)
        layout.addWidget(self.status_label)
        layout.addSpacing(4)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)
        self.summary_text, self.branches_text = QTextEdit(), QTextEdit()
        for box in (self.summary_text, self.branches_text):
            box.setReadOnly(True)
            box.setFont(theme.mono_font())
            box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.matrices_view = MatrixPanel()

        self.tabs.addTab(self.summary_text, "Nodes && Verify")
        self.tabs.addTab(self.branches_text, "Branches")
        self.tabs.addTab(self.matrices_view, "Matrices (G, I, U)")
        layout.addWidget(self.tabs, stretch=1)

        self.show_empty_selection()

    def _set_status(self, text: str, variant: tuple[str, str, str]) -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(theme.status_style(variant))

    def _on_value_edited(self) -> None:
        if self._current_comp_id is None:
            return
        try:
            val = float(self.edit_value.text().strip())
        except ValueError:
            return
        self.value_changed.emit(self._current_comp_id, val)

    def _set_extra_rows(self, rows: list[tuple[str, str]]) -> None:
        widgets = [
            (self.lbl_extra_1_title, self.lbl_extra_1),
            (self.lbl_extra_2_title, self.lbl_extra_2),
            (self.lbl_extra_3_title, self.lbl_extra_3),
        ]
        for idx, (title_lbl, val_lbl) in enumerate(widgets):
            if idx < len(rows):
                title_lbl.setText(rows[idx][0])
                val_lbl.setText(rows[idx][1])
                title_lbl.setVisible(True)
                val_lbl.setVisible(True)
            else:
                title_lbl.setVisible(False)
                val_lbl.setVisible(False)

    def show_empty_selection(self) -> None:
        self._current_comp_id = None
        self.lbl_id.setText("—")
        self.lbl_type.setText("Nothing Selected")
        self.lbl_value_title.setVisible(False)
        self.edit_value.setVisible(False)
        self.btn_flip.setVisible(False)
        self._set_extra_rows([])

    def show_component(
        self,
        comp: ComponentItem,
        solution: Optional[SolutionResult],
        extraction: Optional[ExtractionResult],
    ) -> None:
        self._current_comp_id = comp.component_id
        self.lbl_id.setText(comp.component_id)

        if comp.kind == "resistor":
            self.lbl_type.setText("Resistor")
            self.lbl_value_title.setText("Resistance (Ω):")
            self.lbl_value_title.setVisible(True)
            self.edit_value.setText(f"{comp.value:g}")
            self.edit_value.setVisible(True)
            self.btn_flip.setVisible(False)

            if solution is not None:
                res = next(
                    (r for r in solution.resistor_results if r.component_id == comp.component_id),
                    None,
                )
                if res is not None:
                    self._set_extra_rows(
                        [
                            ("Voltage Drop:", f"{fixed(res.voltage_drop, 4)} V ({res.node_a} → {res.node_b})"),
                            ("Current:", f"{fixed(res.current, 4)} A"),
                            ("Power:", f"{fixed(res.power, 4)} W"),
                        ]
                    )
                    return
            self._set_extra_rows([("Calculated:", "Click Solve Circuit to view")])

        elif comp.kind == "current_source":
            self.lbl_type.setText("DC Current Source")
            self.lbl_value_title.setText("Current (A):")
            self.lbl_value_title.setVisible(True)
            self.edit_value.setText(f"{comp.value:g}")
            self.edit_value.setVisible(True)
            self.btn_flip.setVisible(True)

            direction_str = "T1 → T2 (arrow direction)"
            if extraction is not None:
                n_from = extraction.endpoint_to_node.get(("terminal", comp.component_id, 0), "?")
                n_to = extraction.endpoint_to_node.get(("terminal", comp.component_id, 1), "?")
                direction_str = f"{n_from} → {n_to}"
            self._set_extra_rows([("Direction:", direction_str)])

        elif comp.kind == "ground":
            self.lbl_type.setText("Ground Reference")
            self.lbl_value_title.setVisible(False)
            self.edit_value.setVisible(False)
            self.btn_flip.setVisible(False)
            self._set_extra_rows([("Voltage:", "0 V")])

    def show_wire(
        self,
        wire_id: str,
        solution: Optional[SolutionResult],
        extraction: Optional[ExtractionResult],
    ) -> None:
        self._current_comp_id = None
        self.lbl_id.setText(wire_id)
        self.lbl_type.setText("Ideal Wire (0 Ω)")
        self.lbl_value_title.setVisible(False)
        self.edit_value.setVisible(False)
        self.btn_flip.setVisible(False)

        if extraction is not None and wire_id in extraction.wire_to_node:
            node_name = extraction.wire_to_node[wire_id]
            connected = ", ".join(extraction.wire_to_components.get(wire_id, [])) or "None"
            if node_name == "GND":
                voltage_str = "0 V (Ground)"
            elif solution is not None and node_name in solution.node_voltages:
                voltage = solution.node_voltages[node_name]
                voltage_str = f"{fixed(voltage, 4)} V{fraction_suffix(voltage)}"
            else:
                voltage_str = "Not Solved"
            self._set_extra_rows(
                [
                    ("Node:", node_name),
                    ("Node Voltage:", voltage_str),
                    ("Connected:", connected),
                ]
            )
        else:
            self._set_extra_rows([("Node:", "Click Solve Circuit to inspect")])

    def clear_results(self, message: str = "Status: Circuit Modified — Click Solve Circuit") -> None:
        self._set_status(message, theme.STATUS_WARNING)
        self.summary_text.clear()
        self.branches_text.clear()
        self.matrices_view.clear()

    def show_error(self, error_message: str) -> None:
        self._set_status(f"Error: {error_message}", theme.STATUS_ERROR)
        self.summary_text.setPlainText(f"Cannot solve circuit:\n{error_message}")
        self.branches_text.clear()
        self.matrices_view.clear()

    def show_solution(self, solution: SolutionResult, extraction: ExtractionResult) -> None:
        v = solution.verification
        if v.passed:
            self._set_status("Verification: PASSED (G*V = I and KCL satisfied)", theme.STATUS_SUCCESS)
        else:
            self._set_status("Verification: FAILED (numerical residual exceeded tolerance)", theme.STATUS_ERROR)

        # 1. Summary & Verification tab
        summary_lines = ["=== Node Voltages ==="]
        all_nodes = ["GND"] + solution.non_ground_nodes
        v_width = max(len(fixed(solution.node_voltages[n], 6)) for n in all_nodes)
        for node_name in all_nodes:
            voltage = solution.node_voltages[node_name]
            summary_lines.append(
                f"  {node_name:<6} : {fixed(voltage, 6, v_width)} V{fraction_suffix(voltage)}"
            )

        summary_lines.append("\n=== Verification ===")
        summary_lines.append(f"  Passed        : {v.passed}")
        summary_lines.append(f"  Max Residual  : {v.max_residual:.3e}")
        summary_lines.append(f"  Max KCL Error : {v.max_kcl_error:.3e}")
        summary_lines.append("\n  KCL Sum per Node:")
        for node_name, err in v.kcl_errors.items():
            summary_lines.append(f"    {node_name:<6} : {err:+.3e} A")
        self.summary_text.setHtml(_report_html("\n".join(summary_lines)))

        # 2. Branches tab
        branch_lines = ["=== Resistors (Ohm's Law) ==="]
        if not solution.resistor_results:
            branch_lines.append("  (None)")
        results = solution.resistor_results
        vd_w = max((len(fixed(r.voltage_drop, 4)) for r in results), default=0)
        i_w = max((len(fixed(r.current, 4)) for r in results), default=0)
        p_w = max((len(fixed(r.power, 4)) for r in results), default=0)
        for r in results:
            branch_lines.append(
                f"  {r.component_id:<4} ({r.node_a} -> {r.node_b}, R={r.resistance:g} Ω):\n"
                f"       V_drop = {fixed(r.voltage_drop, 4, vd_w)} V | I = {fixed(r.current, 4, i_w)} A"
                f" | P = {fixed(r.power, 4, p_w)} W"
            )

        branch_lines.append("\n=== DC Current Sources ===")
        if not extraction.circuit.current_sources:
            branch_lines.append("  (None)")
        sources = extraction.circuit.current_sources
        src_w = max((len(fixed(src.current, 4)) for src in sources), default=0)
        for src in sources:
            branch_lines.append(
                f"  {src.component_id:<4} ({src.node_from} -> {src.node_to}): I = {fixed(src.current, 4, src_w)} A"
            )
        self.branches_text.setHtml(_report_html("\n".join(branch_lines)))

        # 3. Matrices tab
        nodes = solution.non_ground_nodes
        self.matrices_view.show_matrices(
            matrix_g=solution.matrix_g,
            vector_i=solution.vector_i,
            upper_triangular=solution.upper_triangular,
            node_names=nodes,
            node_voltages=[solution.node_voltages[n] for n in nodes],
        )
```

## File: gui/theme.py
```python
"""Visual theme: colour tokens, fonts, small styling helpers and the app-wide Qt stylesheet."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette
from PySide6.QtWidgets import QApplication, QLabel, QStyleFactory


WINDOW_BG = "#1B1E23"
SURFACE = "#23272E"
SURFACE_ALT = "#2A2F37"
SURFACE_PRESSED = "#30363F"
BORDER = "#343A44"
BORDER_STRONG = "#545C69"
TEXT = "#DCE0E4"
TEXT_MUTED = "#A3ABB6"
TEXT_FAINT = "#949CA8"

ACCENT = "#6AA4E0"
ACCENT_FILL = "#2F6CAD"
ACCENT_HOVER = "#3573B3"
ACCENT_PRESSED = "#285E98"
ACCENT_SOFT = "#243447"

CANVAS_BG = "#1F2329"
GRID_DOT = "#363C46"
INK = "#D6DBE1"
WIRE = "#A9B2BE"
FLOW_DOT = "#F0B455"
SELECTED = ACCENT
SELECTED_OUTLINE = "#4B739E"
TERMINAL_RING = "#8C95A2"
TERMINAL_ACTIVE = "#62B57F"
NODE_LABEL_TEXT = "#93D3A3"
NODE_LABEL_BG = "#1E3027"
NODE_LABEL_BORDER = "#2F5239"

FRACTION = "#F0B455"
BRACKET = "#AEB5C0"

STATUS_NEUTRAL = ("#2A2F37", "#B4BCC6", "#3A404A")
STATUS_WARNING = ("#352D1E", "#E5C27C", "#56482A")
STATUS_SUCCESS = ("#1E3027", "#93D3A3", "#2F5239")
STATUS_ERROR = ("#3A2326", "#F0A6A2", "#5E3438")

UI_FONT_FAMILY = "Segoe UI"
MONO_FONT_FAMILIES = ["Cascadia Mono", "Consolas"]

SIZE_BASE = 9.5
SIZE_SMALL = 9.0
SIZE_CAPTION = 8.0
SIZE_FOCUS = 12.0
SIZE_MONO = 9.0


def status_style(variant: tuple[str, str, str]) -> str:
    """Stylesheet for the solver status banner in the given colour variant."""
    bg, fg, border = variant
    return (
        f"padding: 8px 10px; border-radius: 4px; background: {bg}; color: {fg}; "
        f"border: 1px solid {border}; font-weight: 600;"
    )


def ui_font(point_size: float = SIZE_BASE, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(UI_FONT_FAMILY)
    font.setPointSizeF(point_size)
    font.setWeight(weight)
    return font


def mono_font(point_size: float = SIZE_MONO) -> QFont:
    font = QFont()
    font.setFamilies(MONO_FONT_FAMILIES)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPointSizeF(point_size)
    return font


def caption_font(uppercase: bool = True) -> QFont:
    """Small, letter-spaced heading font for panel sections (all caps unless told otherwise)."""
    font = ui_font(SIZE_CAPTION, QFont.Weight.DemiBold)
    font.setCapitalization(
        QFont.Capitalization.AllUppercase if uppercase else QFont.Capitalization.MixedCase
    )
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 112)
    return font


def label(text: str = "", name: str = "", font: QFont | None = None, wrap: bool = False) -> QLabel:
    """A QLabel with a stylesheet object name and optional font / word wrap."""
    lbl = QLabel(text)
    if name:
        lbl.setObjectName(name)
    if font is not None:
        lbl.setFont(font)
    lbl.setWordWrap(wrap)
    return lbl


def draw_text(
    painter: QPainter,
    rect: QRectF,
    text: str,
    font: QFont,
    color: str,
    align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter,
) -> None:
    """Draw text in a rectangle with the given font and colour."""
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(rect, align, text)


STYLESHEET = f"""
QMainWindow, QWidget#PaletteSidebar, QWidget#PropertiesPanel {{
    background: {WINDOW_BG};
    color: {TEXT};
}}

QToolTip {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    padding: 4px 6px;
}}

QToolBar {{
    background: {SURFACE};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    spacing: 6px;
}}
QToolBar::separator {{ background: {BORDER}; width: 1px; margin: 4px 8px; }}

QPushButton {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 4px;
    padding: 5px 12px;
    min-height: 20px;
}}
QPushButton:hover {{ background: {SURFACE_ALT}; border-color: {TEXT_FAINT}; }}
QPushButton:pressed {{ background: {SURFACE_PRESSED}; }}
QPushButton:checked {{
    background: {ACCENT_SOFT};
    color: {ACCENT};
    border-color: {ACCENT};
    font-weight: 600;
}}
QPushButton:focus {{ outline: none; }}

QPushButton#PrimaryButton {{
    background: {ACCENT_FILL};
    color: #FFFFFF;
    border: 1px solid {ACCENT_FILL};
    font-weight: 600;
    padding: 5px 18px;
}}
QPushButton#PrimaryButton:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton#PrimaryButton:pressed {{ background: {ACCENT_PRESSED}; }}

QWidget#PaletteSidebar {{ border-right: 1px solid {BORDER}; }}
QLabel#SectionTitle {{ color: {TEXT_MUTED}; }}
QLabel#SectionHint {{ color: {TEXT_FAINT}; font-size: {SIZE_SMALL}pt; }}
QPushButton#PaletteButton {{ text-align: left; padding: 6px 10px; min-height: 30px; }}
QPushButton#PaletteButton:hover {{ border-color: {ACCENT}; background: {SURFACE}; }}
QLabel#HelpText {{
    color: {TEXT_MUTED};
    font-size: {SIZE_SMALL}pt;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 8px 10px;
}}

QGroupBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 4px;
    margin-top: 0px;
    padding: 10px 10px 8px 10px;
}}
QLabel#FormLabel {{ color: {TEXT_MUTED}; font-size: {SIZE_SMALL}pt; }}
QLabel#SelectionId {{ font-size: {SIZE_FOCUS}pt; font-weight: 600; color: {TEXT}; }}
QLabel#SelectionType {{ color: {TEXT_MUTED}; }}

QLineEdit {{
    background: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: {ACCENT_FILL};
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}

QTabWidget::pane {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 4px; top: -1px; }}
QTabBar::tab {{
    font-size: {SIZE_SMALL}pt;
    background: transparent;
    color: {TEXT_MUTED};
    border: 1px solid transparent;
    border-bottom: none;
    padding: 6px 12px;
    margin-right: 2px;
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{
    background: {SURFACE};
    color: {TEXT};
    border-color: {BORDER};
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-weight: 600;
}}

QTextEdit {{
    background: {SURFACE};
    color: {TEXT};
    border: none;
    padding: 6px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT};
}}
QScrollArea#MatrixPanel, QWidget#MatrixPanelBody {{ background: {SURFACE}; border: none; }}

QSplitter::handle {{ background: {BORDER}; }}
QSplitter::handle:horizontal {{ width: 1px; }}

QScrollBar {{ background: transparent; margin: 2px; }}
QScrollBar:vertical {{ width: 10px; }}
QScrollBar:horizontal {{ height: 10px; }}
QScrollBar::handle {{ background: {BORDER_STRONG}; border-radius: 3px; }}
QScrollBar::handle:vertical {{ min-height: 24px; }}
QScrollBar::handle:horizontal {{ min-width: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {TEXT_FAINT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
"""

_PALETTE = {
    QPalette.ColorRole.Window: WINDOW_BG,
    QPalette.ColorRole.WindowText: TEXT,
    QPalette.ColorRole.Base: SURFACE,
    QPalette.ColorRole.AlternateBase: SURFACE_ALT,
    QPalette.ColorRole.Text: TEXT,
    QPalette.ColorRole.Button: SURFACE,
    QPalette.ColorRole.ButtonText: TEXT,
    QPalette.ColorRole.Highlight: ACCENT_FILL,
    QPalette.ColorRole.HighlightedText: "#FFFFFF",
    QPalette.ColorRole.ToolTipBase: SURFACE,
    QPalette.ColorRole.ToolTipText: TEXT,
    QPalette.ColorRole.PlaceholderText: TEXT_FAINT,
    QPalette.ColorRole.Light: BORDER_STRONG,
    QPalette.ColorRole.Midlight: BORDER,
    QPalette.ColorRole.Mid: BORDER,
    QPalette.ColorRole.Dark: WINDOW_BG,
    QPalette.ColorRole.Shadow: "#000000",
}


def apply_theme(app: QApplication) -> None:
    """Apply a consistent dark theme regardless of the OS light/dark setting."""
    fusion = QStyleFactory.create("Fusion")
    if fusion is not None:
        app.setStyle(fusion)

    palette = QPalette()
    for role, color in _PALETTE.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(TEXT_FAINT))
    app.setPalette(palette)
    app.setFont(ui_font(SIZE_BASE))
    app.setStyleSheet(STYLESHEET)
```

## File: main.py
```python
"""Entry point for the DC Circuit Simulator and Nodal Analysis Solver."""

import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

## File: gui/circuit_canvas.py
```python
"""Interactive PySide6 circuit workspace canvas with drag-and-drop, wiring, zoom, and pan."""

import math
from typing import Optional

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from gui import theme
from gui.number_format import fixed, fraction_suffix
from gui.components import (
    ComponentItem,
    EndpointKey,
    ExtractionResult,
    WireJunction,
    WireSegment,
    compute_wire_currents,
    resolve_endpoint_position,
)
from math_engine.nodal_analysis import SolutionResult

GRID_SIZE = 20.0
MIME_TYPE = "application/x-circuit-component"
FLOW_DOT_SPACING = 22.0
FLOW_DOT_RADIUS = 2.6
FLOW_FPS_MS = 30


def _snap(value: float) -> float:
    return round(value / GRID_SIZE) * GRID_SIZE


def _distance_point_to_segment(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    """Return shortest Euclidean distance from point (px, py) to segment (x1, y1)-(x2, y2)."""
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


class CircuitCanvas(QWidget):
    """2D schematic editor supporting drag-and-drop placement, wiring, selection, zoom, and pan."""

    selection_changed = Signal(object, object)  # (kind: "component"|"wire"|None, id: str|None)
    circuit_modified = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.components: dict[str, ComponentItem] = {}
        self.junctions: dict[str, WireJunction] = {}
        self.wires: dict[str, WireSegment] = {}

        self._counters = {"resistor": 0, "current_source": 0, "ground": 0, "wire": 0, "junction": 0}

        self.selected_kind: Optional[str] = None  # "component" | "wire" | "junction"
        self.selected_id: Optional[str] = None

        # Active wiring state
        self._wire_start_endpoint: Optional[EndpointKey] = None
        self._hover_endpoint: Optional[EndpointKey] = None
        self._mouse_world = QPointF(0.0, 0.0)

        # Dragging / panning state
        self._dragging_item: Optional[tuple[str, str]] = None  # ("component"|"junction", id)
        self._pending_junction_press: Optional[tuple[str, QPointF]] = None
        self._drag_offset = QPointF(0.0, 0.0)
        self._panning = False
        self._pan_last_screen = QPointF(0.0, 0.0)

        # View transform
        self.zoom: float = 1.0
        self.pan_offset = QPointF(400.0, 300.0)

        # Latest solved state (cleared when circuit changes)
        self.solution: Optional[SolutionResult] = None
        self.extraction: Optional[ExtractionResult] = None

        # Wire current flow animation state
        self._wire_currents: dict[str, float] = {}
        self._wire_phases: dict[str, float] = {}
        self._elapsed_timer = QElapsedTimer()
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(FLOW_FPS_MS)
        self._anim_timer.timeout.connect(self._advance_flow_animation)

    def set_solution(
        self, solution: Optional[SolutionResult], extraction: Optional[ExtractionResult]
    ) -> None:
        self.solution = solution
        self.extraction = extraction
        if solution is not None and extraction is not None and solution.verification.passed:
            self._wire_currents = compute_wire_currents(
                list(self.wires.values()), extraction, solution
            )
            self._wire_phases = {wid: 0.0 for wid in self._wire_currents}
            self._elapsed_timer.start()
            if any(abs(c) > 1e-9 for c in self._wire_currents.values()):
                self._anim_timer.start()
            else:
                self._anim_timer.stop()
        else:
            self._stop_flow_animation()
        self.update()

    def clear_solution(self) -> None:
        self._stop_flow_animation()
        if self.solution is not None or self.extraction is not None:
            self.solution = None
            self.extraction = None
            self.update()

    def _stop_flow_animation(self) -> None:
        self._anim_timer.stop()
        self._wire_currents.clear()
        self._wire_phases.clear()

    def _advance_flow_animation(self) -> None:
        if not self._wire_currents:
            self._anim_timer.stop()
            return
        dt = min(self._elapsed_timer.restart() / 1000.0, 0.1)
        for wid, current in self._wire_currents.items():
            mag = abs(current)
            if mag <= 1e-9:
                continue
            speed = 24.0 + 42.0 * min(math.sqrt(mag), 2.5)
            phase = (self._wire_phases.get(wid, 0.0) + speed * dt) % FLOW_DOT_SPACING
            self._wire_phases[wid] = phase
        self.update()

    def clear_all(self) -> None:
        self.components.clear()
        self.junctions.clear()
        self.wires.clear()
        self._counters = {k: 0 for k in self._counters}
        self.selected_kind = None
        self.selected_id = None
        self._wire_start_endpoint = None
        self.clear_solution()
        self.selection_changed.emit(None, None)
        self.circuit_modified.emit()
        self.update()

    def load_circuit_data(
        self,
        components: list[ComponentItem],
        junctions: list[WireJunction],
        wires: list[WireSegment],
    ) -> None:
        """Replace the canvas contents with loaded components, junctions, and wires."""
        self.components = {c.component_id: c for c in components}
        self.junctions = {j.junction_id: j for j in junctions}
        self.wires = {w.wire_id: w for w in wires}

        self._counters = {k: 0 for k in self._counters}
        prefix_to_key = {
            "R": "resistor",
            "I": "current_source",
            "GND": "ground",
            "W": "wire",
            "J": "junction",
        }
        for item_id in [*self.components, *self.junctions, *self.wires]:
            for prefix, counter_key in prefix_to_key.items():
                if item_id.startswith(prefix) and item_id[len(prefix) :].isdigit():
                    num = int(item_id[len(prefix) :])
                    self._counters[counter_key] = max(self._counters[counter_key], num)
                    break

        self.selected_kind = None
        self.selected_id = None
        self._wire_start_endpoint = None
        self._pending_junction_press = None
        self._dragging_item = None
        self.clear_solution()
        self.selection_changed.emit(None, None)
        self.circuit_modified.emit()
        self.update()

    def screen_to_world(self, pos: QPointF) -> QPointF:
        return QPointF(
            (pos.x() - self.pan_offset.x()) / self.zoom,
            (pos.y() - self.pan_offset.y()) / self.zoom,
        )

    def add_component(self, kind: str, world_x: float, world_y: float) -> ComponentItem:
        self._counters[kind] += 1
        prefix = {"resistor": "R", "current_source": "I", "ground": "GND"}[kind]
        comp_id = f"{prefix}{self._counters[kind]}"
        default_val = 100.0 if kind == "resistor" else (1.0 if kind == "current_source" else 0.0)
        comp = ComponentItem(
            component_id=comp_id,
            kind=kind,
            x=_snap(world_x),
            y=_snap(world_y),
            rotation=0,
            value=default_val,
        )
        self.components[comp_id] = comp
        self._select("component", comp_id)
        self.circuit_modified.emit()
        self.update()
        return comp

    def rotate_selected(self) -> None:
        if self.selected_kind == "component" and self.selected_id in self.components:
            comp = self.components[self.selected_id]
            comp.rotation = (comp.rotation + 90) % 360
            self.circuit_modified.emit()
            self.update()

    def flip_selected_current_source(self) -> None:
        if self.selected_kind == "component" and self.selected_id in self.components:
            comp = self.components[self.selected_id]
            if comp.kind == "current_source":
                # Swap terminal indices on the attached wires: the wires stay put on screen while
                # the source's from/to nodes (and so its current direction) are reversed.
                comp.rotation = (comp.rotation + 180) % 360
                swap = {0: 1, 1: 0}
                for wire in self.wires.values():
                    if wire.start[0] == "terminal" and wire.start[1] == comp.component_id:
                        wire.start = ("terminal", comp.component_id, swap[wire.start[2]])
                    if wire.end[0] == "terminal" and wire.end[1] == comp.component_id:
                        wire.end = ("terminal", comp.component_id, swap[wire.end[2]])
                self._wire_start_endpoint = None
                self.circuit_modified.emit()
                self.update()

    def delete_selected(self) -> None:
        if self.selected_kind == "component" and self.selected_id in self.components:
            comp_id = self.selected_id
            del self.components[comp_id]
            # Remove any wires connected to this component's terminals.
            to_remove = [
                wid
                for wid, w in self.wires.items()
                if (w.start[0] == "terminal" and w.start[1] == comp_id)
                or (w.end[0] == "terminal" and w.end[1] == comp_id)
            ]
            for wid in to_remove:
                del self.wires[wid]
            self._prune_orphan_junctions()
            self._select(None, None)
            self.circuit_modified.emit()
            self.update()
        elif self.selected_kind == "wire" and self.selected_id in self.wires:
            del self.wires[self.selected_id]
            self._prune_orphan_junctions()
            self._select(None, None)
            self.circuit_modified.emit()
            self.update()
        elif self.selected_kind == "junction" and self.selected_id in self.junctions:
            jid = self.selected_id
            del self.junctions[jid]
            to_remove = [
                wid
                for wid, w in self.wires.items()
                if (w.start[0] == "junction" and w.start[1] == jid)
                or (w.end[0] == "junction" and w.end[1] == jid)
            ]
            for wid in to_remove:
                del self.wires[wid]
            self._select(None, None)
            self.circuit_modified.emit()
            self.update()

    def _prune_orphan_junctions(self) -> None:
        used = set()
        for w in self.wires.values():
            if w.start[0] == "junction":
                used.add(w.start[1])
            if w.end[0] == "junction":
                used.add(w.end[1])
        for jid in list(self.junctions.keys()):
            if jid not in used:
                del self.junctions[jid]

    def _select(self, kind: Optional[str], item_id: Optional[str]) -> None:
        self.selected_kind = kind
        self.selected_id = item_id
        self.selection_changed.emit(kind, item_id)

    def _find_endpoint_at(self, wx: float, wy: float, radius: float = 12.0) -> Optional[EndpointKey]:
        for comp in self.components.values():
            for idx, (tx, ty) in enumerate(comp.terminal_positions()):
                if math.hypot(wx - tx, wy - ty) <= radius:
                    return ("terminal", comp.component_id, idx)
        for junction in self.junctions.values():
            if math.hypot(wx - junction.x, wy - junction.y) <= radius:
                return ("junction", junction.junction_id, 0)
        return None

    def _find_component_at(self, wx: float, wy: float) -> Optional[str]:
        for comp in reversed(list(self.components.values())):
            if abs(wx - comp.x) <= 34.0 and abs(wy - comp.y) <= 28.0:
                return comp.component_id
        return None

    def _find_wire_at(self, wx: float, wy: float, threshold: float = 8.0) -> Optional[str]:
        for wid, wire in self.wires.items():
            x1, y1 = resolve_endpoint_position(wire.start, self.components, self.junctions)
            x2, y2 = resolve_endpoint_position(wire.end, self.components, self.junctions)
            if _distance_point_to_segment(wx, wy, x1, y1, x2, y2) <= threshold:
                return wid
        return None

    def _create_wire(self, start: EndpointKey, end: EndpointKey) -> None:
        if start == end:
            return
        # Avoid duplicate wire between the exact same two endpoints.
        for wire in self.wires.values():
            if (wire.start == start and wire.end == end) or (
                wire.start == end and wire.end == start
            ):
                return
        self._counters["wire"] += 1
        wid = f"W{self._counters['wire']}"
        self.wires[wid] = WireSegment(wire_id=wid, start=start, end=end)
        self.circuit_modified.emit()

    def _create_junction(self, wx: float, wy: float) -> EndpointKey:
        """Create a grid-snapped wire junction/waypoint at (wx, wy) and return its endpoint key."""
        self._counters["junction"] += 1
        jid = f"J{self._counters['junction']}"
        self.junctions[jid] = WireJunction(junction_id=jid, x=_snap(wx), y=_snap(wy))
        self.circuit_modified.emit()
        return ("junction", jid, 0)

    def _split_wire_with_junction(self, wire_id: str, wx: float, wy: float) -> EndpointKey:
        """Split an existing wire segment at (wx, wy) by inserting an explicit junction."""
        old_wire = self.wires.pop(wire_id)
        j_ep = self._create_junction(wx, wy)
        self._create_wire(old_wire.start, j_ep)
        self._create_wire(j_ep, old_wire.end)
        return j_ep

    # --- Drag & Drop from Toolbar ---

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(MIME_TYPE):
            kind = bytes(event.mimeData().data(MIME_TYPE)).decode("utf-8")
            world_pos = self.screen_to_world(event.position())
            self.add_component(kind, world_pos.x(), world_pos.y())
            event.acceptProposedAction()

    # --- Mouse & Keyboard Events ---

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self.setFocus()
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton):
            if self._wire_start_endpoint is not None and event.button() == Qt.MouseButton.RightButton:
                self._wire_start_endpoint = None
                self.update()
                return
            self._panning = True
            self._pan_last_screen = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        world_pos = self.screen_to_world(event.position())
        wx, wy = world_pos.x(), world_pos.y()

        # 1. Clicking an endpoint (terminal or junction) starts or finishes a wire.
        ep = self._find_endpoint_at(wx, wy)
        if ep is not None:
            if self._wire_start_endpoint is None:
                if ep[0] == "junction":
                    # Defer starting a wire so dragging a junction moves it cleanly.
                    self._pending_junction_press = (ep[1], event.position())
                else:
                    self._wire_start_endpoint = ep
            else:
                self._create_wire(self._wire_start_endpoint, ep)
                self._wire_start_endpoint = None
            self.update()
            return

        # 2. If currently drawing a wire:
        #    - clicking an existing wire splits it with a junction and finishes the wire;
        #    - clicking blank canvas creates a new point/junction and continues routing from it.
        if self._wire_start_endpoint is not None:
            wid = self._find_wire_at(wx, wy)
            if wid is not None:
                j_ep = self._split_wire_with_junction(wid, wx, wy)
                self._create_wire(self._wire_start_endpoint, j_ep)
                self._wire_start_endpoint = None
                self.update()
                return
            j_ep = self._create_junction(wx, wy)
            self._create_wire(self._wire_start_endpoint, j_ep)
            self._wire_start_endpoint = j_ep
            self.update()
            return

        # 3. Select & drag component
        comp_id = self._find_component_at(wx, wy)
        if comp_id is not None:
            comp = self.components[comp_id]
            self._select("component", comp_id)
            self._dragging_item = ("component", comp_id)
            self._drag_offset = QPointF(wx - comp.x, wy - comp.y)
            self.update()
            return

        # 5. Select wire
        wid = self._find_wire_at(wx, wy)
        if wid is not None:
            self._select("wire", wid)
            self.update()
            return

        self._select(None, None)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._panning:
            delta = event.position() - self._pan_last_screen
            self.pan_offset += delta
            self._pan_last_screen = event.position()
            self.update()
            return

        world_pos = self.screen_to_world(event.position())
        self._mouse_world = world_pos
        self._hover_endpoint = self._find_endpoint_at(world_pos.x(), world_pos.y())

        if self._pending_junction_press is not None:
            jid, press_pos = self._pending_junction_press
            if (event.position() - press_pos).manhattanLength() >= 5.0 and jid in self.junctions:
                self._pending_junction_press = None
                junc = self.junctions[jid]
                press_world = self.screen_to_world(press_pos)
                self._select("junction", jid)
                self._dragging_item = ("junction", jid)
                self._drag_offset = QPointF(press_world.x() - junc.x, press_world.y() - junc.y)

        if self._dragging_item is not None:
            kind, item_id = self._dragging_item
            if kind == "component" and item_id in self.components:
                comp = self.components[item_id]
                new_x = _snap(world_pos.x() - self._drag_offset.x())
                new_y = _snap(world_pos.y() - self._drag_offset.y())
                if new_x != comp.x or new_y != comp.y:
                    comp.x = new_x
                    comp.y = new_y
                    self.circuit_modified.emit()
            elif kind == "junction" and item_id in self.junctions:
                junc = self.junctions[item_id]
                new_x = _snap(world_pos.x() - self._drag_offset.x())
                new_y = _snap(world_pos.y() - self._drag_offset.y())
                if new_x != junc.x or new_y != junc.y:
                    junc.x = new_x
                    junc.y = new_y
                    self.circuit_modified.emit()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._panning and event.button() in (
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.RightButton,
        ):
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        if event.button() == Qt.MouseButton.LeftButton:
            if self._pending_junction_press is not None:
                jid, _ = self._pending_junction_press
                self._pending_junction_press = None
                if jid in self.junctions:
                    self._wire_start_endpoint = ("junction", jid, 0)
                    self.update()
            self._dragging_item = None

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        factor = 1.12 if event.angleDelta().y() > 0 else 1.0 / 1.12
        new_zoom = max(0.35, min(2.5, self.zoom * factor))
        if new_zoom == self.zoom:
            return
        mouse_pos = event.position()
        world_before = self.screen_to_world(mouse_pos)
        self.zoom = new_zoom
        self.pan_offset = QPointF(
            mouse_pos.x() - world_before.x() * self.zoom,
            mouse_pos.y() - world_before.y() * self.zoom,
        )
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
        elif event.key() == Qt.Key.Key_R:
            self.rotate_selected()
        elif event.key() == Qt.Key.Key_Escape:
            self._wire_start_endpoint = None
            self.update()

    # --- Painting ---

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.CANVAS_BG))

        painter.translate(self.pan_offset)
        painter.scale(self.zoom, self.zoom)

        self._draw_grid(painter)
        self._draw_wires(painter)
        self._draw_wire_flow(painter)
        self._draw_active_wire_preview(painter)
        self._draw_junctions(painter)
        self._draw_components(painter)

    def _draw_grid(self, painter: QPainter) -> None:
        top_left = self.screen_to_world(QPointF(0.0, 0.0))
        bottom_right = self.screen_to_world(QPointF(float(self.width()), float(self.height())))
        start_x = int(math.floor(top_left.x() / GRID_SIZE) * GRID_SIZE)
        end_x = int(math.ceil(bottom_right.x() / GRID_SIZE) * GRID_SIZE)
        start_y = int(math.floor(top_left.y() / GRID_SIZE) * GRID_SIZE)
        end_y = int(math.ceil(bottom_right.y() / GRID_SIZE) * GRID_SIZE)

        painter.setPen(QPen(QColor(theme.GRID_DOT), 1.4 / max(self.zoom, 0.5)))
        for gx in range(start_x, end_x + 1, int(GRID_SIZE)):
            for gy in range(start_y, end_y + 1, int(GRID_SIZE)):
                painter.drawPoint(gx, gy)

    def _draw_wires(self, painter: QPainter) -> None:
        for wid, wire in self.wires.items():
            x1, y1 = resolve_endpoint_position(wire.start, self.components, self.junctions)
            x2, y2 = resolve_endpoint_position(wire.end, self.components, self.junctions)
            is_selected = self.selected_kind == "wire" and self.selected_id == wid
            color = QColor(theme.SELECTED) if is_selected else QColor(theme.WIRE)
            pen = QPen(color, 3.0 if is_selected else 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_wire_flow(self, painter: QPainter) -> None:
        if not self._wire_currents:
            return
        dot_color = QColor(theme.FLOW_DOT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(dot_color))

        for wid, wire in self.wires.items():
            current = self._wire_currents.get(wid, 0.0)
            if abs(current) <= 1e-9:
                continue
            x1, y1 = resolve_endpoint_position(wire.start, self.components, self.junctions)
            x2, y2 = resolve_endpoint_position(wire.end, self.components, self.junctions)
            # Negative current flows from wire.end to wire.start.
            if current < 0.0:
                x1, y1, x2, y2 = x2, y2, x1, y1

            dx = x2 - x1
            dy = y2 - y1
            length = math.hypot(dx, dy)
            if length < 1e-3:
                continue
            ux = dx / length
            uy = dy / length

            d = self._wire_phases.get(wid, 0.0) % FLOW_DOT_SPACING
            while d < length:
                painter.drawEllipse(QPointF(x1 + ux * d, y1 + uy * d), FLOW_DOT_RADIUS, FLOW_DOT_RADIUS)
                d += FLOW_DOT_SPACING

    def _draw_active_wire_preview(self, painter: QPainter) -> None:
        if self._wire_start_endpoint is None:
            return
        sx, sy = resolve_endpoint_position(
            self._wire_start_endpoint, self.components, self.junctions
        )
        pen = QPen(QColor(theme.SELECTED), 1.8, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(sx, sy), self._mouse_world)

    def _draw_junctions(self, painter: QPainter) -> None:
        for jid, junction in self.junctions.items():
            ep: EndpointKey = ("junction", jid, 0)
            is_selected = self.selected_kind == "junction" and self.selected_id == jid
            is_hover = ep == self._hover_endpoint or ep == self._wire_start_endpoint
            if is_hover:
                color, radius = QColor(theme.TERMINAL_ACTIVE), 5.0
            elif is_selected:
                color, radius = QColor(theme.SELECTED), 5.5
            else:
                color, radius = QColor(theme.WIRE), 4.0
            painter.setPen(QPen(color, 1.0))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(junction.x, junction.y), radius, radius)

    def _draw_node_tag(
        self, painter: QPainter, tx: float, ty: float, dx: float, dy: float, text: str, is_ground: bool
    ) -> None:
        """Draw a small voltage tag next to a terminal, on the side facing away from the part."""
        metrics = painter.fontMetrics()
        width = metrics.horizontalAdvance(text) + 8.0
        height = metrics.height() + 2.0
        gap = 6.0

        if abs(dx) >= abs(dy):
            left = tx + gap if dx > 0 else tx - gap - width
            top = ty - gap - height
        else:
            left = tx + gap
            top = ty - gap - height if dy < 0 else ty + gap

        rect = QRectF(left, top, width, height)

        drawn = getattr(self, "_drawn_tags", None)
        if drawn is not None:
            def collides(r: QRectF) -> list[tuple[QRectF, str]]:
                padded = r.adjusted(-2.0, -1.0, 2.0, 1.0)
                return [(other, other_text) for other, other_text in drawn if padded.intersects(other)]

            if any(other_text == text for _, other_text in collides(rect)):
                return
            step = -(height + 2.0) if rect.center().y() <= ty else (height + 2.0)
            for _ in range(3):
                if not collides(rect):
                    break
                rect.translate(0.0, step)
            drawn.append((QRectF(rect), text))

        bg, border, fg = (
            (theme.SURFACE_ALT, theme.BORDER, theme.TEXT_FAINT)
            if is_ground
            else (theme.NODE_LABEL_BG, theme.NODE_LABEL_BORDER, theme.NODE_LABEL_TEXT)
        )
        painter.setPen(QPen(QColor(border), 0.8))
        painter.setBrush(QBrush(QColor(bg)))
        painter.drawRoundedRect(rect, 3.0, 3.0)
        theme.draw_text(painter, rect, text, painter.font(), fg)

    def _draw_components(self, painter: QPainter) -> None:
        id_font = theme.ui_font(theme.SIZE_SMALL, QFont.Weight.DemiBold)
        value_font = theme.ui_font(8.5)
        node_font = theme.mono_font(7.5)
        self._drawn_tags: list[tuple[QRectF, str]] = []

        for comp in self.components.values():
            is_selected = self.selected_kind == "component" and self.selected_id == comp.component_id
            stroke = QColor(theme.SELECTED) if is_selected else QColor(theme.INK)

            painter.save()
            painter.translate(comp.x, comp.y)
            painter.rotate(comp.rotation)
            pen = QPen(stroke, 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            if comp.kind == "resistor":
                # Leads + classic zig-zag resistor symbol
                path = QPainterPath()
                path.moveTo(-45, 0)
                path.lineTo(-24, 0)
                path.lineTo(-20, -10)
                path.lineTo(-12, 10)
                path.lineTo(-4, -10)
                path.lineTo(4, 10)
                path.lineTo(12, -10)
                path.lineTo(20, 10)
                path.lineTo(24, 0)
                path.lineTo(45, 0)
                painter.drawPath(path)

            elif comp.kind == "current_source":
                # Leads + circle + arrow pointing from T0 (-45) to T1 (+45)
                painter.drawLine(-45, 0, -20, 0)
                painter.drawLine(20, 0, 45, 0)
                painter.setBrush(QBrush(QColor(theme.CANVAS_BG)))
                painter.drawEllipse(QPointF(0, 0), 20, 20)
                painter.drawLine(-12, 0, 12, 0)
                arrow = QPainterPath()
                arrow.moveTo(5, -6)
                arrow.lineTo(12, 0)
                arrow.lineTo(5, 6)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(arrow)

            elif comp.kind == "ground":
                painter.drawLine(0, -24, 0, 0)
                painter.drawLine(-18, 0, 18, 0)
                painter.drawLine(-11, 7, 11, 7)
                painter.drawLine(-5, 14, 5, 14)

            if is_selected:
                painter.setPen(QPen(QColor(theme.SELECTED_OUTLINE), 1.0, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(QRectF(-34, -26, 68, 52), 4.0, 4.0)

            painter.restore()

            # Draw upright text label above/below component
            left_mid = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            right_mid = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if comp.kind in ("resistor", "current_source"):
                value_text = f"{comp.value:g} {'Ω' if comp.kind == 'resistor' else 'A'}"
                if comp.rotation in (90, 270):
                    x = comp.x - (26 if comp.kind == "current_source" else 18) - 80
                    theme.draw_text(painter, QRectF(x, comp.y - 18, 80, 18), comp.component_id, id_font, theme.TEXT, right_mid)
                    theme.draw_text(painter, QRectF(x, comp.y, 80, 18), value_text, value_font, theme.TEXT_MUTED, right_mid)
                else:
                    top = comp.y - (46 if comp.kind == "current_source" else 40)
                    id_w = QFontMetrics(id_font).horizontalAdvance(comp.component_id)
                    value_w = QFontMetrics(value_font).horizontalAdvance(value_text)
                    x = comp.x - (id_w + 6 + value_w) / 2
                    theme.draw_text(painter, QRectF(x, top, id_w + 2, 20), comp.component_id, id_font, theme.TEXT, left_mid)
                    theme.draw_text(painter, QRectF(x + id_w + 6, top, value_w + 2, 20), value_text, value_font, theme.TEXT_MUTED, left_mid)
            else:
                theme.draw_text(painter, QRectF(comp.x - 40, comp.y + 18, 80, 18), comp.component_id, id_font, theme.TEXT_MUTED)

            # Draw terminals and solved node badges
            for idx, (tx, ty) in enumerate(comp.terminal_positions()):
                ep: EndpointKey = ("terminal", comp.component_id, idx)
                is_active = ep == self._hover_endpoint or ep == self._wire_start_endpoint
                ring, fill, radius, width = (
                    (theme.TERMINAL_ACTIVE, theme.TERMINAL_ACTIVE, 5.0, 1.4)
                    if is_active
                    else (theme.TERMINAL_RING, theme.CANVAS_BG, 3.5, 1.3)
                )
                painter.setPen(QPen(QColor(ring), width))
                painter.setBrush(QBrush(QColor(fill)))
                painter.drawEllipse(QPointF(tx, ty), radius, radius)

                if self.solution and self.extraction:
                    node_name = self.extraction.endpoint_to_node.get(ep)
                    if node_name and node_name in self.solution.node_voltages:
                        voltage = self.solution.node_voltages[node_name]
                        painter.setFont(node_font)
                        text = f"{node_name} {fixed(voltage, 2)} V{fraction_suffix(voltage)}"
                        self._draw_node_tag(painter, tx, ty, tx - comp.x, ty - comp.y, text, node_name == "GND")
```

## File: gui/main_window.py
```python
"""Main application window coordinating the component toolbar, canvas, and results panel."""

from typing import Optional

from PySide6.QtCore import QMimeData, QPoint, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QDrag, QIcon, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from gui.circuit_canvas import MIME_TYPE, CircuitCanvas
from gui.components import extract_circuit_from_gui
from gui.properties_panel import PropertiesPanel
from gui import theme
from math_engine.circuit import InvalidCircuitError
from math_engine.nodal_analysis import solve_circuit
from utils.circuit_io import load_circuit, save_circuit


def _symbol_icon(kind: str) -> QIcon:
    """Small schematic symbol drawn with QPainter, used on the palette buttons."""
    size = 28
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2.0)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(theme.INK), 1.6))
    painter.translate(size / 2, size / 2)
    if kind == "resistor":
        path = QPainterPath()
        path.moveTo(-13, 0)
        for x, y in [(-8, 0), (-6, -5), (-2, 5), (2, -5), (6, 5), (8, 0), (13, 0)]:
            path.lineTo(x, y)
        painter.drawPath(path)
        segments = []
    elif kind == "current_source":
        painter.drawEllipse(QPointF(0, 0), 8.5, 8.5)
        segments = [((-5, 0), (5, 0)), ((2, -3), (5, 0)), ((2, 3), (5, 0))]
    else:
        segments = [((0, -10), (0, -2)), ((-9, -2), (9, -2)), ((-5.5, 2.5), (5.5, 2.5)), ((-2, 7), (2, 7))]
    for a, b in segments:
        painter.drawLine(QPointF(*a), QPointF(*b))
    painter.end()
    return QIcon(pixmap)


class DraggableComponentButton(QPushButton):
    """Toolbar button that supports both drag-and-drop onto the canvas and click-to-place."""

    def __init__(self, label: str, kind: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(label, parent)
        self.kind = kind
        self._drag_start_pos: Optional[QPoint] = None
        self.setObjectName("PaletteButton")
        self.setIcon(_symbol_icon(kind))
        self.setIconSize(QSize(28, 28))
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Drag onto the canvas, or click to place in the centre")

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self._drag_start_pos is None:
            return
        if (event.position().toPoint() - self._drag_start_pos).manhattanLength() < 8:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME_TYPE, self.kind.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)
        self._drag_start_pos = None


class MainWindow(QMainWindow):
    """Top-level window for the DC Nodal Analysis Circuit Simulator."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DC Circuit Simulator — Nodal Analysis & Gaussian Elimination")
        self.resize(1320, 800)
        self.setMinimumSize(960, 600)

        self.canvas = CircuitCanvas()
        self.properties_panel = PropertiesPanel()

        self._build_top_toolbar()
        self._build_central_layout()
        self._connect_signals()

    def _build_top_toolbar(self) -> None:
        toolbar = QToolBar("Actions")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.btn_open = QPushButton("Open")
        self.btn_save = QPushButton("Save")
        self.btn_rotate = QPushButton("Rotate (R)")
        self.btn_delete = QPushButton("Delete (Del)")
        self.btn_clear = QPushButton("Clear All")

        self.btn_solve = QPushButton("Solve Circuit")
        self.btn_solve.setObjectName("PrimaryButton")
        self.btn_solve.setToolTip("Build G·V = I and solve it with Gaussian elimination")

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        toolbar.addWidget(self.btn_open)
        toolbar.addWidget(self.btn_save)
        toolbar.addSeparator()
        toolbar.addWidget(self.btn_rotate)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_clear)
        toolbar.addWidget(spacer)
        toolbar.addWidget(self.btn_solve)

    def _build_central_layout(self) -> None:
        # Left Component Palette
        palette = QWidget()
        palette.setObjectName("PaletteSidebar")
        palette.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        palette.setFixedWidth(200)
        palette_layout = QVBoxLayout(palette)
        palette_layout.setContentsMargins(12, 14, 12, 12)
        palette_layout.setSpacing(6)

        palette_layout.addWidget(theme.label("Components", "SectionTitle", theme.caption_font()))
        palette_layout.addWidget(theme.label("Drag onto the canvas or click", "SectionHint"))
        palette_layout.addSpacing(4)

        self.btn_resistor = DraggableComponentButton("Resistor", "resistor")
        self.btn_current_source = DraggableComponentButton("Current Source", "current_source")
        self.btn_ground = DraggableComponentButton("Ground", "ground")

        palette_layout.addWidget(self.btn_resistor)
        palette_layout.addWidget(self.btn_current_source)
        palette_layout.addWidget(self.btn_ground)

        palette_layout.addSpacing(16)
        palette_layout.addWidget(theme.label("How To", "SectionTitle", theme.caption_font()))
        help_text = (
            "Click a terminal to start a wire, then click another terminal, point, or wire to connect."
            "<br><br>Click blank canvas while wiring to place a corner or junction point."
            "<br><br>Drag components or points to reposition. Scroll to zoom; right or middle drag to pan."
            "<br><br><b>R</b> Rotate &nbsp;&middot;&nbsp; <b>Del</b> Delete"
            "<br><b>Esc</b> / Right-click Finish Wire"
        )
        palette_layout.addWidget(theme.label(help_text, "HelpText", wrap=True))
        palette_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(palette)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.properties_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([200, 720, 420])

        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(splitter)
        self.setCentralWidget(container)

    def _connect_signals(self) -> None:
        self.btn_open.clicked.connect(self.open_circuit_file)
        self.btn_save.clicked.connect(self.save_circuit_file)
        self.btn_rotate.clicked.connect(self.canvas.rotate_selected)
        self.btn_delete.clicked.connect(self.canvas.delete_selected)
        self.btn_clear.clicked.connect(self.canvas.clear_all)
        self.btn_solve.clicked.connect(self.solve_current_circuit)

        self.btn_resistor.clicked.connect(lambda: self._place_near_center("resistor"))
        self.btn_current_source.clicked.connect(lambda: self._place_near_center("current_source"))
        self.btn_ground.clicked.connect(lambda: self._place_near_center("ground"))

        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.canvas.circuit_modified.connect(self._on_circuit_modified)
        self.properties_panel.value_changed.connect(self._on_component_value_changed)
        self.properties_panel.flip_requested.connect(self.canvas.flip_selected_current_source)

    def _place_near_center(self, kind: str) -> None:
        center = self.canvas.screen_to_world(self.canvas.rect().center().toPointF())
        self.canvas.add_component(kind, center.x(), center.y())

    def _on_selection_changed(self, kind: Optional[str], item_id: Optional[str]) -> None:
        if kind == "component" and item_id in self.canvas.components:
            self.properties_panel.show_component(
                self.canvas.components[item_id],
                self.canvas.solution,
                self.canvas.extraction,
            )
        elif kind == "wire" and item_id in self.canvas.wires:
            self.properties_panel.show_wire(
                item_id,
                self.canvas.solution,
                self.canvas.extraction,
            )
        else:
            self.properties_panel.show_empty_selection()

    def _on_circuit_modified(self) -> None:
        self.canvas.clear_solution()
        self.properties_panel.clear_results()
        self._on_selection_changed(self.canvas.selected_kind, self.canvas.selected_id)

    def _on_component_value_changed(self, component_id: str, new_value: float) -> None:
        comp = self.canvas.components.get(component_id)
        if comp is None or comp.value == new_value:
            return
        comp.value = new_value
        self.canvas.update()
        self._on_circuit_modified()

    def solve_current_circuit(self) -> None:
        try:
            extraction = extract_circuit_from_gui(
                components=list(self.canvas.components.values()),
                junctions=list(self.canvas.junctions.values()),
                wires=list(self.canvas.wires.values()),
            )
            solution = solve_circuit(extraction.circuit)
        except InvalidCircuitError as exc:
            self.canvas.clear_solution()
            self.properties_panel.show_error(str(exc))
            return

        self.canvas.set_solution(solution, extraction)
        self.properties_panel.show_solution(solution, extraction)
        self._on_selection_changed(self.canvas.selected_kind, self.canvas.selected_id)

    def save_circuit_file(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Circuit",
            "circuit.circuit.json",
            "Circuit Files (*.circuit.json *.json);;All Files (*)",
        )
        if not file_path:
            return
        try:
            save_circuit(
                file_path,
                self.canvas.components.values(),
                self.canvas.junctions.values(),
                self.canvas.wires.values(),
            )
        except OSError as exc:
            QMessageBox.warning(self, "Save Failed", f"Could not save circuit:\n{exc}")

    def open_circuit_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Circuit",
            "",
            "Circuit Files (*.circuit.json *.json);;All Files (*)",
        )
        if not file_path:
            return
        try:
            components, junctions, wires = load_circuit(file_path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Open Failed", f"Could not open circuit:\n{exc}")
            return
        self.canvas.load_circuit_data(components, junctions, wires)
```

## File: tests/test_gui_integration.py
```python
"""Integration tests for GUI-to-math conversion, multiple grounds, and solution invalidation."""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from gui.components import (
    ComponentItem,
    WireJunction,
    WireSegment,
    compute_wire_currents,
    extract_circuit_from_gui,
)
from gui.main_window import MainWindow
from math_engine.circuit import InvalidCircuitError
from math_engine.nodal_analysis import solve_circuit
from utils.circuit_io import load_circuit, save_circuit


class TestGuiIntegration(unittest.TestCase):
    """Verify GUI circuit extraction and MainWindow solve/invalidation lifecycle."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_6_multiple_grounds_on_same_node_vs_disconnected(self) -> None:
        """Multiple grounds wired to the same node act as one GND; disconnected grounds fail."""
        components = [
            ComponentItem("I1", "current_source", 0, 0, value=2.0),
            ComponentItem("R1", "resistor", 100, 0, value=4.0),
            ComponentItem("GND1", "ground", 0, 100),
            ComponentItem("GND2", "ground", 100, 100),
        ]
        # Both grounds connect to I1.T0 and R1.T1 -> same electrical node.
        wires = [
            WireSegment("W1", ("terminal", "I1", 1), ("terminal", "R1", 0)),
            WireSegment("W2", ("terminal", "I1", 0), ("terminal", "GND1", 0)),
            WireSegment("W3", ("terminal", "R1", 1), ("terminal", "GND2", 0)),
            WireSegment("W4", ("terminal", "GND1", 0), ("terminal", "GND2", 0)),
        ]
        extraction = extract_circuit_from_gui(components, [], wires)
        result = solve_circuit(extraction.circuit)
        self.assertAlmostEqual(result.node_voltages["N1"], 8.0, places=9)
        self.assertTrue(result.verification.passed)

        # Remove W4 and W3 so GND2 is disconnected from GND1.
        disconnected_wires = [
            WireSegment("W1", ("terminal", "I1", 1), ("terminal", "R1", 0)),
            WireSegment("W2", ("terminal", "I1", 0), ("terminal", "GND1", 0)),
        ]
        with self.assertRaises(InvalidCircuitError):
            extract_circuit_from_gui(components, [], disconnected_wires)

    def test_wire_junction_connects_three_branches(self) -> None:
        """Parallel resistors joined via an explicit WireJunction solve to 4.8 V."""
        components = [
            ComponentItem("I1", "current_source", 0, 0, value=2.0),
            ComponentItem("R1", "resistor", 100, -40, value=4.0),
            ComponentItem("R2", "resistor", 100, 40, value=6.0),
            ComponentItem("GND1", "ground", 0, 120),
        ]
        junctions = [
            WireJunction("J1", 40, 0),
            WireJunction("J2", 160, 120),
        ]
        wires = [
            WireSegment("W1", ("terminal", "I1", 1), ("junction", "J1", 0)),
            WireSegment("W2", ("junction", "J1", 0), ("terminal", "R1", 0)),
            WireSegment("W3", ("junction", "J1", 0), ("terminal", "R2", 0)),
            WireSegment("W4", ("terminal", "R1", 1), ("junction", "J2", 0)),
            WireSegment("W5", ("terminal", "R2", 1), ("junction", "J2", 0)),
            WireSegment("W6", ("junction", "J2", 0), ("terminal", "GND1", 0)),
            WireSegment("W7", ("terminal", "I1", 0), ("terminal", "GND1", 0)),
        ]
        extraction = extract_circuit_from_gui(components, junctions, wires)
        result = solve_circuit(extraction.circuit)
        self.assertAlmostEqual(result.node_voltages["N1"], 4.8, places=9)
        self.assertTrue(result.verification.passed)

    def test_7_main_window_solve_and_invalidation_on_edit(self) -> None:
        """Modifying a resistor value in MainWindow invalidates previous results until re-solved."""
        window = MainWindow()
        i1 = window.canvas.add_component("current_source", 0, 0)
        i1.value = 2.0
        r1 = window.canvas.add_component("resistor", 140, 0)
        r1.value = 4.0
        gnd = window.canvas.add_component("ground", 0, 100)

        window.canvas._create_wire(("terminal", i1.component_id, 1), ("terminal", r1.component_id, 0))
        window.canvas._create_wire(("terminal", i1.component_id, 0), ("terminal", gnd.component_id, 0))
        window.canvas._create_wire(("terminal", r1.component_id, 1), ("terminal", gnd.component_id, 0))

        window.solve_current_circuit()
        self.assertIsNotNone(window.canvas.solution)
        self.assertAlmostEqual(window.canvas.solution.node_voltages["N1"], 8.0, places=9)

        # Modify resistor value -> previous solution must be invalidated.
        window._on_component_value_changed(r1.component_id, 10.0)
        self.assertIsNone(window.canvas.solution)
        self.assertIn("modified", window.properties_panel.status_label.text().lower())

        # Re-solve -> new voltage = 2 A * 10 ohm = 20 V.
        window.solve_current_circuit()
        self.assertIsNotNone(window.canvas.solution)
        self.assertAlmostEqual(window.canvas.solution.node_voltages["N1"], 20.0, places=9)
        window.close()

    def test_flip_direction_reverses_current_source(self) -> None:
        """Flip Direction reverses the current the solver sees, not just the drawing."""
        window = MainWindow()
        i1 = window.canvas.add_component("current_source", 0, 0)
        i1.value = 2.0
        r1 = window.canvas.add_component("resistor", 140, 0)
        r1.value = 4.0
        gnd = window.canvas.add_component("ground", 0, 100)

        window.canvas._create_wire(("terminal", i1.component_id, 1), ("terminal", r1.component_id, 0))
        window.canvas._create_wire(("terminal", i1.component_id, 0), ("terminal", gnd.component_id, 0))
        window.canvas._create_wire(("terminal", r1.component_id, 1), ("terminal", gnd.component_id, 0))

        def wire_positions() -> list:
            return [
                (
                    window.canvas.components[w.start[1]].terminal_positions()[w.start[2]],
                    window.canvas.components[w.end[1]].terminal_positions()[w.end[2]],
                )
                for w in window.canvas.wires.values()
            ]

        window.solve_current_circuit()
        self.assertAlmostEqual(window.canvas.solution.node_voltages["N1"], 8.0, places=9)
        positions_before = wire_positions()

        window.canvas._select("component", i1.component_id)
        window.canvas.flip_selected_current_source()
        self.assertIsNone(window.canvas.solution)
        # Wires stay where they were drawn.
        self.assertEqual(wire_positions(), positions_before)

        window.solve_current_circuit()
        self.assertAlmostEqual(window.canvas.solution.node_voltages["N1"], -8.0, places=9)

        # Flipping again restores the original direction.
        window.canvas.flip_selected_current_source()
        window.solve_current_circuit()
        self.assertAlmostEqual(window.canvas.solution.node_voltages["N1"], 8.0, places=9)
        window.close()

    def test_wire_currents_and_animation_on_flip_and_rotation(self) -> None:
        """Wire currents match conventional current, split at junctions, and reverse on flip."""
        # 1. Branched junction circuit: I1 = 2 A -> J1 -> (R1 = 4 ohm: 1.2 A, R2 = 6 ohm: 0.8 A)
        components = [
            ComponentItem("I1", "current_source", 0, 0, rotation=90, value=2.0),
            ComponentItem("R1", "resistor", 100, -40, rotation=0, value=4.0),
            ComponentItem("R2", "resistor", 100, 40, rotation=180, value=6.0),
            ComponentItem("GND1", "ground", 0, 120),
        ]
        junctions = [
            WireJunction("J1", 40, 0),
            WireJunction("J2", 160, 120),
        ]
        wires = [
            WireSegment("W1", ("terminal", "I1", 1), ("junction", "J1", 0)),
            WireSegment("W2", ("junction", "J1", 0), ("terminal", "R1", 0)),
            WireSegment("W3", ("junction", "J1", 0), ("terminal", "R2", 0)),
            WireSegment("W4", ("terminal", "R1", 1), ("junction", "J2", 0)),
            WireSegment("W5", ("terminal", "R2", 1), ("junction", "J2", 0)),
            WireSegment("W6", ("junction", "J2", 0), ("terminal", "GND1", 0)),
            WireSegment("W7", ("terminal", "I1", 0), ("terminal", "GND1", 0)),
        ]
        extraction = extract_circuit_from_gui(components, junctions, wires)
        solution = solve_circuit(extraction.circuit)
        wire_currents = compute_wire_currents(wires, extraction, solution)

        self.assertAlmostEqual(wire_currents["W1"], 2.0, places=9)
        self.assertAlmostEqual(wire_currents["W2"], 1.2, places=9)
        self.assertAlmostEqual(wire_currents["W3"], 0.8, places=9)
        self.assertAlmostEqual(wire_currents["W4"], 1.2, places=9)
        self.assertAlmostEqual(wire_currents["W5"], 0.8, places=9)
        self.assertAlmostEqual(wire_currents["W6"], 2.0, places=9)
        # W7 goes from I1.T0 to GND1.T0, while current enters I1.T0 from GND1.T0 -> -2.0 A.
        self.assertAlmostEqual(wire_currents["W7"], -2.0, places=9)

        # 2. MainWindow animation lifecycle + flip reversal
        window = MainWindow()
        i1 = window.canvas.add_component("current_source", 0, 0)
        i1.value = 2.0
        r1 = window.canvas.add_component("resistor", 140, 0)
        r1.value = 4.0
        gnd = window.canvas.add_component("ground", 0, 100)

        # Rotate I1 by 90 degrees before solving; animation should still track terminals.
        window.canvas._select("component", i1.component_id)
        window.canvas.rotate_selected()
        self.assertEqual(i1.rotation, 90)

        window.canvas._create_wire(("terminal", i1.component_id, 1), ("terminal", r1.component_id, 0))
        window.canvas._create_wire(("terminal", i1.component_id, 0), ("terminal", gnd.component_id, 0))
        window.canvas._create_wire(("terminal", r1.component_id, 1), ("terminal", gnd.component_id, 0))

        self.assertFalse(window.canvas._anim_timer.isActive())
        window.solve_current_circuit()
        self.assertTrue(window.canvas._anim_timer.isActive())
        self.assertAlmostEqual(window.canvas._wire_currents["W1"], 2.0, places=9)
        self.assertAlmostEqual(window.canvas._wire_currents["W2"], -2.0, places=9)
        self.assertAlmostEqual(window.canvas._wire_currents["W3"], 2.0, places=9)

        # Flipping stops animation until re-solved, then reverses all wire currents.
        window.canvas._select("component", i1.component_id)
        window.canvas.flip_selected_current_source()
        self.assertFalse(window.canvas._anim_timer.isActive())
        self.assertEqual(window.canvas._wire_currents, {})

        window.solve_current_circuit()
        self.assertTrue(window.canvas._anim_timer.isActive())
        self.assertAlmostEqual(window.canvas._wire_currents["W1"], -2.0, places=9)
        self.assertAlmostEqual(window.canvas._wire_currents["W2"], 2.0, places=9)
        self.assertAlmostEqual(window.canvas._wire_currents["W3"], -2.0, places=9)

        # Zero-current source -> solved and valid, but animation timer stays off.
        i1.value = 0.0
        window.solve_current_circuit()
        self.assertFalse(window.canvas._anim_timer.isActive())
        window.close()

    def test_blank_canvas_junction_routing_and_branching(self) -> None:
        """Clicking blank canvas while wiring places a point/junction that routes and branches cleanly."""
        window = MainWindow()
        self.assertFalse(hasattr(window, "btn_wire_mode"))
        self.assertFalse(hasattr(window, "btn_select_mode"))

        canvas = window.canvas
        i1 = canvas.add_component("current_source", 0, 0)
        i1.value = 2.0
        r1 = canvas.add_component("resistor", 160, -40)
        r1.value = 4.0
        r2 = canvas.add_component("resistor", 160, 40)
        r2.value = 6.0
        gnd = canvas.add_component("ground", 0, 120)

        def to_screen(wx: float, wy: float) -> QPointF:
            return QPointF(wx * canvas.zoom + canvas.pan_offset.x(), wy * canvas.zoom + canvas.pan_offset.y())

        def click_world(wx: float, wy: float, button: Qt.MouseButton = Qt.MouseButton.LeftButton) -> None:
            pos = to_screen(wx, wy)
            press = QMouseEvent(QEvent.Type.MouseButtonPress, pos, pos, button, button, Qt.KeyboardModifier.NoModifier)
            release = QMouseEvent(QEvent.Type.MouseButtonRelease, pos, pos, button, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
            canvas.mousePressEvent(press)
            canvas.mouseReleaseEvent(release)

        # 1. Start wire at I1.T1 (45, 0), click blank canvas at (80, 0) -> creates J1 and keeps wiring active.
        t1_x, t1_y = i1.terminal_positions()[1]
        click_world(t1_x, t1_y)
        self.assertEqual(canvas._wire_start_endpoint, ("terminal", i1.component_id, 1))

        click_world(80, 0)
        self.assertIn("J1", canvas.junctions)
        self.assertEqual(canvas._wire_start_endpoint, ("junction", "J1", 0))

        # 2. Click blank canvas at (80, -40) -> creates J2, then connect to R1.T0 -> finishes wire.
        click_world(80, -40)
        self.assertIn("J2", canvas.junctions)
        r1_t0_x, r1_t0_y = r1.terminal_positions()[0]
        click_world(r1_t0_x, r1_t0_y)
        self.assertIsNone(canvas._wire_start_endpoint)

        # 3. Click J1 (without dragging) to branch to R2.T0.
        click_world(80, 0)
        self.assertEqual(canvas._wire_start_endpoint, ("junction", "J1", 0))
        r2_t0_x, r2_t0_y = r2.terminal_positions()[0]
        click_world(r2_t0_x, r2_t0_y)
        self.assertIsNone(canvas._wire_start_endpoint)

        # 4. Wire return path to ground via another blank-canvas junction J3 at (220, 120).
        r1_t1_x, r1_t1_y = r1.terminal_positions()[1]
        click_world(r1_t1_x, r1_t1_y)
        click_world(220, 120)
        gnd_x, gnd_y = gnd.terminal_positions()[0]
        click_world(gnd_x, gnd_y)

        r2_t1_x, r2_t1_y = r2.terminal_positions()[1]
        click_world(r2_t1_x, r2_t1_y)
        click_world(220, 120)  # connects to existing J3

        i1_t0_x, i1_t0_y = i1.terminal_positions()[0]
        click_world(i1_t0_x, i1_t0_y)
        click_world(gnd_x, gnd_y)

        # Solve and verify exact parallel-resistor voltage (4.8 V) and branch currents.
        window.solve_current_circuit()
        self.assertIsNotNone(canvas.solution)
        self.assertTrue(canvas.solution.verification.passed)
        self.assertAlmostEqual(canvas.solution.node_voltages["N1"], 4.8, places=9)
        self.assertTrue(canvas._anim_timer.isActive())

        # 5. Drag J1 from (80, 0) to (100, 0) -> snaps, invalidates solution, stops animation.
        p_start = to_screen(80, 0)
        p_end = to_screen(100, 0)
        canvas.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, p_start, p_start, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        canvas.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, p_end, p_end, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        canvas.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, p_end, p_end, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))

        self.assertEqual((canvas.junctions["J1"].x, canvas.junctions["J1"].y), (100.0, 0.0))
        self.assertEqual((canvas.selected_kind, canvas.selected_id), ("junction", "J1"))
        self.assertIsNone(canvas.solution)
        self.assertFalse(canvas._anim_timer.isActive())

        # Re-solving after moving J1 still gives 4.8 V.
        window.solve_current_circuit()
        self.assertAlmostEqual(canvas.solution.node_voltages["N1"], 4.8, places=9)

        # 6. Deleting selected junction J1 removes J1 and its attached wires.
        canvas.delete_selected()
        self.assertNotIn("J1", canvas.junctions)
        window.close()

    def test_save_and_load_circuit_roundtrip(self) -> None:
        """Saving and loading a circuit preserves geometry, values, IDs, and solved voltages."""
        window = MainWindow()
        i1 = window.canvas.add_component("current_source", 0, 0)
        i1.value = 2.0
        r1 = window.canvas.add_component("resistor", 140, 0)
        r1.value = 4.0
        r1.rotation = 90
        gnd = window.canvas.add_component("ground", 0, 100)

        j1_ep = window.canvas._create_junction(80, 0)
        window.canvas._create_wire(("terminal", i1.component_id, 1), j1_ep)
        window.canvas._create_wire(j1_ep, ("terminal", r1.component_id, 0))
        window.canvas._create_wire(("terminal", i1.component_id, 0), ("terminal", gnd.component_id, 0))
        window.canvas._create_wire(("terminal", r1.component_id, 1), ("terminal", gnd.component_id, 0))

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "demo.circuit.json"
            save_circuit(
                file_path,
                window.canvas.components.values(),
                window.canvas.junctions.values(),
                window.canvas.wires.values(),
            )

            loaded_window = MainWindow()
            comps, juncs, wires = load_circuit(file_path)
            loaded_window.canvas.load_circuit_data(comps, juncs, wires)

            self.assertEqual(set(loaded_window.canvas.components.keys()), {"I1", "R1", "GND1"})
            self.assertEqual(loaded_window.canvas.components["R1"].rotation, 90)
            self.assertEqual(set(loaded_window.canvas.junctions.keys()), {"J1"})
            self.assertEqual(len(loaded_window.canvas.wires), 4)

            # Counters should be synced so newly added components don't collide.
            r2 = loaded_window.canvas.add_component("resistor", 200, 0)
            self.assertEqual(r2.component_id, "R2")
            loaded_window.canvas.delete_selected()

            loaded_window.solve_current_circuit()
            self.assertIsNotNone(loaded_window.canvas.solution)
            self.assertAlmostEqual(loaded_window.canvas.solution.node_voltages["N1"], 8.0, places=9)
            self.assertTrue(loaded_window.canvas._anim_timer.isActive())
            loaded_window.close()

        window.close()


class TestNumberFormat(unittest.TestCase):
    """Display-only fraction labels for repeating decimals."""

    def test_repeating_decimals_show_fraction_terminating_do_not(self) -> None:
        from gui.number_format import fraction_suffix

        for value, expected in [
            (7 / 6, " (7/6)"),
            (9 / 7, " (9/7)"),
            (27 / 7, " (27/7)"),
            (-5 / 3, " (-5/3)"),
            (0.5, ""),
            (0.25, ""),
            (1.25, ""),
            (0.75, ""),
            (9.0, ""),
            (2 ** 0.5, ""),
        ]:
            self.assertEqual(fraction_suffix(value), expected, value)

    def test_worked_example_upper_triangular_shows_exact_fractions(self) -> None:
        from gui.matrix_view import matrix_cells
        from math_engine.circuit import Circuit, CurrentSource, Resistor

        circuit = Circuit(
            nodes=["GND", "N1", "N2", "N3"],
            ground_node="GND",
            resistors=[
                Resistor("R1", "N1", "GND", 2.0),
                Resistor("R2", "N1", "N2", 4.0),
                Resistor("R3", "N2", "GND", 2.0),
                Resistor("R4", "N2", "N3", 2.0),
                Resistor("R5", "N3", "GND", 1.0),
            ],
            current_sources=[
                CurrentSource("I1", "GND", "N1", 6.0),
                CurrentSource("I2", "GND", "N3", 3.0),
            ],
        )
        result = solve_circuit(circuit)
        cells = matrix_cells(result.upper_triangular)
        # Repeating values become fractions only; everything else has its trailing zeros cut.
        self.assertEqual(cells[0], [("0.75", False), ("−0.25", False), ("0", False), ("6", False)])
        self.assertEqual(cells[1], [("0", False), ("7/6", True), ("−0.5", False), ("2", False)])
        self.assertEqual(cells[2], [("0", False), ("0", False), ("9/7", True), ("27/7", True)])

    def test_entry_format_rules(self) -> None:
        from gui.number_format import format_entry

        self.assertEqual(format_entry(-7 / 6), ("−7/6", True))
        self.assertEqual(format_entry(1.5), ("1.5", False))
        self.assertEqual(format_entry(-0.0), ("0", False))
        self.assertEqual(format_entry(2 ** 0.5), ("1.4142", False))      # irrational: decimal
        self.assertEqual(format_entry(1234 / 567), ("2.1764", False))   # unwieldy fraction: decimal

    def test_trailing_zero_cutting_keeps_every_rounded_digit(self) -> None:
        from gui.number_format import fixed

        self.assertEqual(fixed(100.0, 6), "100")
        self.assertEqual(fixed(8.333333333, 6), "8.333333")   # nothing but zeros is ever removed
        self.assertEqual(fixed(-1.6666666667, 6), "-1.666667")
        self.assertEqual(fixed(0.0012, 4), "0.0012")
        self.assertEqual(fixed(-0.0, 4), "0")
        self.assertEqual(fixed(1.5, 4, 9), "      1.5")


if __name__ == "__main__":
    unittest.main()
```
