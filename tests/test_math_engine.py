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
