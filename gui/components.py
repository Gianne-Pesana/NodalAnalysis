"""Visual circuit data models and conversion from GUI elements to math_engine.Circuit."""

from collections import deque
from dataclasses import dataclass

from math_engine.circuit import Circuit, CurrentSource, InvalidCircuitError, Resistor

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
