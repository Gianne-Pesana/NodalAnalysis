"""Properties editor and mathematical results panel."""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
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

from gui.components import ComponentItem, ExtractionResult
from math_engine.nodal_analysis import SolutionResult


def _format_matrix(matrix: list[list[float]], row_labels: Optional[list[str]] = None) -> str:
    """Format a 2D list of floats into an aligned monospace text block."""
    if not matrix:
        return "(empty)"
    lines: list[str] = []
    for idx, row in enumerate(matrix):
        prefix = f"{row_labels[idx]:>4}: " if row_labels and idx < len(row_labels) else ""
        cells = "  ".join(f"{val:9.4f}" for val in row)
        lines.append(f"{prefix}[ {cells} ]")
    return "\n".join(lines)


class PropertiesPanel(QWidget):
    """Right-hand panel for editing selected component values and viewing solver results."""

    value_changed = Signal(str, float)  # (component_id, new_value)
    flip_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(330)
        self._current_comp_id: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # --- Selected Item Properties ---
        self.prop_group = QGroupBox("Selected Item Properties")
        self.prop_form = QFormLayout(self.prop_group)

        self.lbl_id = QLabel("-")
        self.lbl_type = QLabel("-")
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

        self.prop_form.addRow("ID:", self.lbl_id)
        self.prop_form.addRow("Type:", self.lbl_type)
        self.prop_form.addRow(self.lbl_value_title, self.edit_value)
        self.prop_form.addRow("", self.btn_flip)
        self.prop_form.addRow(self.lbl_extra_1_title, self.lbl_extra_1)
        self.prop_form.addRow(self.lbl_extra_2_title, self.lbl_extra_2)
        self.prop_form.addRow(self.lbl_extra_3_title, self.lbl_extra_3)

        layout.addWidget(self.prop_group)

        # --- Solver Status & Results ---
        self.status_label = QLabel("Status: Not solved")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "padding: 6px; border-radius: 4px; background: #ECEFF1; font-weight: bold;"
        )
        layout.addWidget(self.status_label)

        self.tabs = QTabWidget()
        mono_font = QFont("Consolas", 9)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(mono_font)

        self.branches_text = QTextEdit()
        self.branches_text.setReadOnly(True)
        self.branches_text.setFont(mono_font)

        self.matrices_text = QTextEdit()
        self.matrices_text.setReadOnly(True)
        self.matrices_text.setFont(mono_font)

        self.tabs.addTab(self.summary_text, "Nodes & Verify")
        self.tabs.addTab(self.branches_text, "Branches")
        self.tabs.addTab(self.matrices_text, "Matrices (G, I, U)")
        layout.addWidget(self.tabs, stretch=1)

        self.show_empty_selection()

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
        self.lbl_id.setText("-")
        self.lbl_type.setText("None")
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
                            ("Voltage Drop:", f"{res.voltage_drop:.4f} V ({res.node_a} → {res.node_b})"),
                            ("Current:", f"{res.current:.4f} A"),
                            ("Power:", f"{res.power:.4f} W"),
                        ]
                    )
                    return
            self._set_extra_rows([("Calculated:", "Solve circuit to view")])

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
            self._set_extra_rows([("Voltage:", "0.0000 V")])

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
                voltage_str = "0.0000 V (Ground)"
            elif solution is not None and node_name in solution.node_voltages:
                voltage_str = f"{solution.node_voltages[node_name]:.4f} V"
            else:
                voltage_str = "Not solved"
            self._set_extra_rows(
                [
                    ("Node:", node_name),
                    ("Node Voltage:", voltage_str),
                    ("Connected:", connected),
                ]
            )
        else:
            self._set_extra_rows([("Node:", "Solve circuit to inspect")])

    def clear_results(self, message: str = "Status: Circuit modified — click Solve") -> None:
        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            "padding: 6px; border-radius: 4px; background: #FFF8E1; color: #795548; font-weight: bold;"
        )
        self.summary_text.clear()
        self.branches_text.clear()
        self.matrices_text.clear()

    def show_error(self, error_message: str) -> None:
        self.status_label.setText(f"Error: {error_message}")
        self.status_label.setStyleSheet(
            "padding: 6px; border-radius: 4px; background: #FFEBEE; color: #B71C1C; font-weight: bold;"
        )
        self.summary_text.setPlainText(f"Cannot solve circuit:\n{error_message}")
        self.branches_text.clear()
        self.matrices_text.clear()

    def show_solution(self, solution: SolutionResult, extraction: ExtractionResult) -> None:
        v = solution.verification
        if v.passed:
            self.status_label.setText("Verification: PASSED (G*V = I and KCL satisfied)")
            self.status_label.setStyleSheet(
                "padding: 6px; border-radius: 4px; background: #E8F5E9; color: #1B5E20; font-weight: bold;"
            )
        else:
            self.status_label.setText("Verification: FAILED (numerical residual exceeded tolerance)")
            self.status_label.setStyleSheet(
                "padding: 6px; border-radius: 4px; background: #FFEBEE; color: #B71C1C; font-weight: bold;"
            )

        # 1. Summary & Verification tab
        summary_lines = ["=== Node Voltages ==="]
        for node_name in ["GND"] + solution.non_ground_nodes:
            voltage = solution.node_voltages[node_name]
            summary_lines.append(f"  {node_name:<6} : {voltage:10.6f} V")

        summary_lines.append("\n=== Verification ===")
        summary_lines.append(f"  Passed        : {v.passed}")
        summary_lines.append(f"  Max Residual  : {v.max_residual:.3e}")
        summary_lines.append(f"  Max KCL Error : {v.max_kcl_error:.3e}")
        summary_lines.append("\n  KCL Sum per Node:")
        for node_name, err in v.kcl_errors.items():
            summary_lines.append(f"    {node_name:<6} : {err:+.3e} A")
        self.summary_text.setPlainText("\n".join(summary_lines))

        # 2. Branches tab
        branch_lines = ["=== Resistors (Ohm's Law) ==="]
        if not solution.resistor_results:
            branch_lines.append("  (none)")
        for r in solution.resistor_results:
            branch_lines.append(
                f"  {r.component_id:<4} ({r.node_a} -> {r.node_b}, R={r.resistance:g} Ω):\n"
                f"       V_drop = {r.voltage_drop:9.4f} V | I = {r.current:9.4f} A | P = {r.power:9.4f} W"
            )

        branch_lines.append("\n=== DC Current Sources ===")
        if not extraction.circuit.current_sources:
            branch_lines.append("  (none)")
        for src in extraction.circuit.current_sources:
            branch_lines.append(
                f"  {src.component_id:<4} ({src.node_from} -> {src.node_to}): I = {src.current:9.4f} A"
            )
        self.branches_text.setPlainText("\n".join(branch_lines))

        # 3. Matrices tab
        nodes = solution.non_ground_nodes
        i_col = [[val] for val in solution.vector_i]
        matrix_lines = [
            "=== Conductance Matrix G (S) ===",
            _format_matrix(solution.matrix_g, nodes),
            "\n=== Current Injection Vector I (A) ===",
            _format_matrix(i_col, nodes),
            "\n=== Gaussian Elimination Upper Triangular [U | c] ===",
            _format_matrix(solution.upper_triangular, nodes),
        ]
        self.matrices_text.setPlainText("\n".join(matrix_lines))
