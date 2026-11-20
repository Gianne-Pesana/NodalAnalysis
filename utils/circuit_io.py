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
