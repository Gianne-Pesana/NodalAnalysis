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
                text = f"{comp.component_id} ({comp.value:g} Ω)"
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
