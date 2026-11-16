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
