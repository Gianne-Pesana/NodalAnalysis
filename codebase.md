.\codebase.md
```

```
.\main.py
```python
"""Entry point for the DC Circuit Simulator and Nodal Analysis Solver."""

import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

```
.\requirements.txt
```
PySide6>=6.5.0

```
.\gui\__init__.py
```python
"""PySide6 graphical user interface for the DC circuit simulator."""

```
.\gui\circuit_canvas.py
```python
"""Interactive PySide6 circuit workspace canvas with drag-and-drop, wiring, zoom, and pan."""

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from gui.components import (
    ComponentItem,
    EndpointKey,
    ExtractionResult,
    WireJunction,
    WireSegment,
    resolve_endpoint_position,
)
from math_engine.nodal_analysis import SolutionResult

GRID_SIZE = 20.0
MIME_TYPE = "application/x-circuit-component"


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
        self.mode: str = "select"  # "select" or "wire"

        self.selected_kind: Optional[str] = None  # "component" | "wire" | "junction"
        self.selected_id: Optional[str] = None

        # Active wiring state
        self._wire_start_endpoint: Optional[EndpointKey] = None
        self._hover_endpoint: Optional[EndpointKey] = None
        self._mouse_world = QPointF(0.0, 0.0)

        # Dragging / panning state
        self._dragging_item: Optional[tuple[str, str]] = None  # ("component"|"junction", id)
        self._drag_offset = QPointF(0.0, 0.0)
        self._panning = False
        self._pan_last_screen = QPointF(0.0, 0.0)

        # View transform
        self.zoom: float = 1.0
        self.pan_offset = QPointF(400.0, 300.0)

        # Latest solved state (cleared when circuit changes)
        self.solution: Optional[SolutionResult] = None
        self.extraction: Optional[ExtractionResult] = None

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._wire_start_endpoint = None
        self.update()

    def set_solution(
        self, solution: Optional[SolutionResult], extraction: Optional[ExtractionResult]
    ) -> None:
        self.solution = solution
        self.extraction = extraction
        self.update()

    def clear_solution(self) -> None:
        if self.solution is not None or self.extraction is not None:
            self.solution = None
            self.extraction = None
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
                comp.rotation = (comp.rotation + 180) % 360
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

    def _split_wire_with_junction(self, wire_id: str, wx: float, wy: float) -> EndpointKey:
        """Split an existing wire segment at (wx, wy) by inserting an explicit junction."""
        old_wire = self.wires.pop(wire_id)
        self._counters["junction"] += 1
        jid = f"J{self._counters['junction']}"
        self.junctions[jid] = WireJunction(junction_id=jid, x=_snap(wx), y=_snap(wy))
        j_ep: EndpointKey = ("junction", jid, 0)
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
                self._wire_start_endpoint = ep
            else:
                self._create_wire(self._wire_start_endpoint, ep)
                self._wire_start_endpoint = None
            self.update()
            return

        # 2. If currently drawing a wire and user clicks an existing wire, create a junction.
        if self._wire_start_endpoint is not None:
            wid = self._find_wire_at(wx, wy)
            if wid is not None:
                j_ep = self._split_wire_with_junction(wid, wx, wy)
                self._create_wire(self._wire_start_endpoint, j_ep)
                self._wire_start_endpoint = None
                self.update()
                return
            # Clicking empty space cancels active wire drawing.
            self._wire_start_endpoint = None
            self.update()
            return

        # 3. In Wire mode, clicking an existing wire starts a branch from a new junction.
        if self.mode == "wire":
            wid = self._find_wire_at(wx, wy)
            if wid is not None:
                j_ep = self._split_wire_with_junction(wid, wx, wy)
                self._wire_start_endpoint = j_ep
                self.update()
                return

        # 4. Select & drag component
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
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._panning and event.button() in (
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.RightButton,
        ):
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        if event.button() == Qt.MouseButton.LeftButton:
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
        painter.fillRect(self.rect(), QColor("#FAFAFA"))

        painter.translate(self.pan_offset)
        painter.scale(self.zoom, self.zoom)

        self._draw_grid(painter)
        self._draw_wires(painter)
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

        painter.setPen(QPen(QColor("#E0E0E0"), 1.0))
        for gx in range(start_x, end_x + 1, int(GRID_SIZE)):
            for gy in range(start_y, end_y + 1, int(GRID_SIZE)):
                painter.drawPoint(gx, gy)

    def _draw_wires(self, painter: QPainter) -> None:
        for wid, wire in self.wires.items():
            x1, y1 = resolve_endpoint_position(wire.start, self.components, self.junctions)
            x2, y2 = resolve_endpoint_position(wire.end, self.components, self.junctions)
            is_selected = self.selected_kind == "wire" and self.selected_id == wid
            color = QColor("#1976D2") if is_selected else QColor("#263238")
            painter.setPen(QPen(color, 3.0 if is_selected else 2.2))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_active_wire_preview(self, painter: QPainter) -> None:
        if self._wire_start_endpoint is None:
            return
        sx, sy = resolve_endpoint_position(
            self._wire_start_endpoint, self.components, self.junctions
        )
        pen = QPen(QColor("#1976D2"), 2.0, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(sx, sy), self._mouse_world)

    def _draw_junctions(self, painter: QPainter) -> None:
        for jid, junction in self.junctions.items():
            ep: EndpointKey = ("junction", jid, 0)
            is_hover = ep == self._hover_endpoint or ep == self._wire_start_endpoint
            painter.setPen(QPen(QColor("#0D47A1") if is_hover else QColor("#263238"), 1.5))
            painter.setBrush(QBrush(QColor("#42A5F5") if is_hover else QColor("#263238")))
            painter.drawEllipse(QPointF(junction.x, junction.y), 5.0, 5.0)

    def _draw_components(self, painter: QPainter) -> None:
        label_font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        node_font = QFont("Segoe UI", 8)

        for comp in self.components.values():
            is_selected = self.selected_kind == "component" and self.selected_id == comp.component_id
            stroke = QColor("#1976D2") if is_selected else QColor("#1A1A1A")

            painter.save()
            painter.translate(comp.x, comp.y)
            painter.rotate(comp.rotation)
            painter.setPen(QPen(stroke, 2.2))
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
                painter.setBrush(QBrush(QColor("#FFFFFF")))
                painter.drawEllipse(QPointF(0, 0), 20, 20)
                painter.drawLine(-12, 0, 12, 0)
                painter.drawLine(5, -6, 12, 0)
                painter.drawLine(5, 6, 12, 0)

            elif comp.kind == "ground":
                painter.drawLine(0, -24, 0, 0)
                painter.drawLine(-18, 0, 18, 0)
                painter.drawLine(-11, 7, 11, 7)
                painter.drawLine(-5, 14, 5, 14)

            if is_selected:
                painter.setPen(QPen(QColor("#64B5F6"), 1.2, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(QRectF(-34, -26, 68, 52))

            painter.restore()

            # Draw upright text label above/below component
            painter.setFont(label_font)
            painter.setPen(QPen(QColor("#1A1A1A")))
            if comp.kind == "resistor":
                text = f"{comp.component_id} ({comp.value:g} Î©)"
                painter.drawText(QRectF(comp.x - 60, comp.y - 42, 120, 20), Qt.AlignmentFlag.AlignCenter, text)
            elif comp.kind == "current_source":
                text = f"{comp.component_id} ({comp.value:g} A)"
                painter.drawText(QRectF(comp.x - 60, comp.y - 46, 120, 20), Qt.AlignmentFlag.AlignCenter, text)
            else:
                painter.drawText(QRectF(comp.x - 40, comp.y + 16, 80, 18), Qt.AlignmentFlag.AlignCenter, comp.component_id)

            # Draw terminals and solved node badges
            for idx, (tx, ty) in enumerate(comp.terminal_positions()):
                ep: EndpointKey = ("terminal", comp.component_id, idx)
                is_active = ep == self._hover_endpoint or ep == self._wire_start_endpoint
                painter.setPen(QPen(QColor("#0D47A1") if is_active else QColor("#37474F"), 1.5))
                painter.setBrush(QBrush(QColor("#4CAF50") if is_active else QColor("#FFFFFF")))
                painter.drawEllipse(QPointF(tx, ty), 5.0 if is_active else 4.0, 5.0 if is_active else 4.0)

                if self.solution and self.extraction:
                    node_name = self.extraction.endpoint_to_node.get(ep)
                    if node_name and node_name in self.solution.node_voltages:
                        voltage = self.solution.node_voltages[node_name]
                        painter.setFont(node_font)
                        painter.setPen(QPen(QColor("#1B5E20")))
                        painter.drawText(
                            QPointF(tx + 7, ty - 6),
                            f"{node_name}: {voltage:.2f}V",
                        )

```
.\gui\components.py
```python
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

```
.\gui\main_window.py
```python
"""Main application window coordinating the component toolbar, canvas, and results panel."""

from typing import Optional

from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDrag, QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from gui.circuit_canvas import MIME_TYPE, CircuitCanvas
from gui.components import extract_circuit_from_gui
from gui.properties_panel import PropertiesPanel
from math_engine.circuit import InvalidCircuitError
from math_engine.nodal_analysis import solve_circuit


class DraggableComponentButton(QPushButton):
    """Toolbar button that supports both drag-and-drop onto the canvas and click-to-place."""

    def __init__(self, label: str, kind: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(label, parent)
        self.kind = kind
        self._drag_start_pos: Optional[QPoint] = None
        self.setMinimumHeight(40)

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
        self.setWindowTitle("DC Circuit Simulator â€” Nodal Analysis & Gaussian Elimination")
        self.resize(1280, 780)

        self.canvas = CircuitCanvas()
        self.properties_panel = PropertiesPanel()

        self._build_top_toolbar()
        self._build_central_layout()
        self._connect_signals()

    def _build_top_toolbar(self) -> None:
        toolbar = QToolBar("Actions")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.btn_select_mode = QPushButton("Select / Move")
        self.btn_select_mode.setCheckable(True)
        self.btn_select_mode.setChecked(True)

        self.btn_wire_mode = QPushButton("Wire / Junction")
        self.btn_wire_mode.setCheckable(True)

        self.btn_rotate = QPushButton("Rotate (R)")
        self.btn_delete = QPushButton("Delete (Del)")
        self.btn_clear = QPushButton("Clear All")

        self.btn_solve = QPushButton("  Solve Circuit  ")
        self.btn_solve.setStyleSheet(
            "QPushButton { background-color: #2E7D32; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #1B5E20; }"
        )

        toolbar.addWidget(self.btn_select_mode)
        toolbar.addWidget(self.btn_wire_mode)
        toolbar.addSeparator()
        toolbar.addWidget(self.btn_rotate)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_clear)
        toolbar.addSeparator()
        toolbar.addWidget(self.btn_solve)

    def _build_central_layout(self) -> None:
        # Left Component Palette
        palette = QWidget()
        palette.setFixedWidth(185)
        palette_layout = QVBoxLayout(palette)
        palette_layout.setContentsMargins(8, 10, 8, 10)
        palette_layout.setSpacing(8)

        title = QLabel("Components\n(Drag or Click)")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        palette_layout.addWidget(title)

        self.btn_resistor = DraggableComponentButton("Resistor (Î©)", "resistor")
        self.btn_current_source = DraggableComponentButton("Current Source (A)", "current_source")
        self.btn_ground = DraggableComponentButton("Ground (0 V)", "ground")

        palette_layout.addWidget(self.btn_resistor)
        palette_layout.addWidget(self.btn_current_source)
        palette_layout.addWidget(self.btn_ground)

        help_label = QLabel(
            "Tips:\n"
            "â€¢ Drag components onto canvas\n"
            "â€¢ Click a terminal to start/end a wire\n"
            "â€¢ Click an existing wire while wiring to add a junction\n"
            "â€¢ Scroll to zoom, right/middle-drag to pan\n"
            "â€¢ Press R to rotate, Del to delete"
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #546E7A; font-size: 11px; margin-top: 12px;")
        palette_layout.addWidget(help_label)
        palette_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(palette)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.properties_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(splitter)
        self.setCentralWidget(container)

    def _connect_signals(self) -> None:
        self.btn_select_mode.clicked.connect(lambda: self._set_mode("select"))
        self.btn_wire_mode.clicked.connect(lambda: self._set_mode("wire"))
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

    def _set_mode(self, mode: str) -> None:
        self.btn_select_mode.setChecked(mode == "select")
        self.btn_wire_mode.setChecked(mode == "wire")
        self.canvas.set_mode(mode)

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

```
.\gui\properties_panel.py
```python
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

        self.btn_flip = QPushButton("Flip Direction (180Â°)")
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
            self.lbl_value_title.setText("Resistance (Î©):")
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
                            ("Voltage Drop:", f"{res.voltage_drop:.4f} V ({res.node_a} â†’ {res.node_b})"),
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

            direction_str = "T1 â†’ T2 (arrow direction)"
            if extraction is not None:
                n_from = extraction.endpoint_to_node.get(("terminal", comp.component_id, 0), "?")
                n_to = extraction.endpoint_to_node.get(("terminal", comp.component_id, 1), "?")
                direction_str = f"{n_from} â†’ {n_to}"
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
        self.lbl_type.setText("Ideal Wire (0 Î©)")
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

    def clear_results(self, message: str = "Status: Circuit modified â€” click Solve") -> None:
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
                f"  {r.component_id:<4} ({r.node_a} -> {r.node_b}, R={r.resistance:g} Î©):\n"
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

```
.\gui\__pycache__\__init__.cpython-313.pyc
```
ó

    ˆ4÷jE   ã                   ó   • S r g)z>PySide6 graphical user interface for the DC circuit simulator.N)Ú__doc__© ó    ÚXC:\Users\giann\Documents\Programming Stuff\Python Projects\NodalAnalysis\gui\__init__.pyÚ<module>r      s   ðÚ Dr   
```
.\math_engine\__init__.py
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
.\math_engine\circuit.py
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
.\math_engine\gaussian_elimination.py
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
.\math_engine\nodal_analysis.py
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
.\math_engine\verification.py
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
.\tests\test_gui_integration.py
```python
"""Integration tests for GUI-to-math conversion, multiple grounds, and solution invalidation."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.components import (
    ComponentItem,
    WireJunction,
    WireSegment,
    extract_circuit_from_gui,
)
from gui.main_window import MainWindow
from math_engine.circuit import InvalidCircuitError
from math_engine.nodal_analysis import solve_circuit


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


if __name__ == "__main__":
    unittest.main()

```
.\tests\test_math_engine.py
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
