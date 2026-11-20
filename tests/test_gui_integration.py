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
