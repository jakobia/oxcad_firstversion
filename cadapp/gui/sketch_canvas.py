"""2D sketch canvas with modular constraint and selection systems."""

from __future__ import annotations

from copy import deepcopy
from math import atan2, degrees
from typing import Any

from PySide6.QtCore import QPointF, Qt, QRectF, Signal
from PySide6.QtGui import QBrush, QKeyEvent, QMouseEvent, QPainter, QColor, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QInputDialog, QWidget

from cadapp.constraints.constraint import Constraint, GeometryRef
from cadapp.constraints.constraint_command import AddConstraintCommand, UpdateConstraintCommand
from cadapp.constraints.constraint_types import ConstraintType
from cadapp.core.sketch_document import SketchDocument
from cadapp.gui.selection_manager import SelectionManager


class SketchCanvas(QWidget):
    """Interactive sketch editor and constraint view for OXCAD."""

    available_constraints_changed = Signal(list)
    constraints_changed = Signal()
    dof_status_changed = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

        self.document = SketchDocument(self)
        self.selection_manager = SelectionManager(self)
        self.undo_stack = None

        self.points = self.document.points
        self.lines = self.document.lines
        self.circles = self.document.circles
        self.arcs = self.document.arcs

        self.current_tool = "line"
        self.constraint_mode = "free"
        self.quick_constraint_type: ConstraintType | None = None
        self.rubber_point: QPointF | None = None
        self._circle_center: QPointF | None = None
        self._arc_center: QPointF | None = None
        self._arc_start: QPointF | None = None
        self._drag_reference: GeometryRef | None = None
        self._drag_last_pos: QPointF | None = None
        self._is_dragging = False
        self._selected_geometry: GeometryRef | None = None
        self._point_axis_locks: dict[int, dict[str, float]] = {}
        self._center_axis_locks: dict[tuple[str, int], dict[str, float]] = {}
        self.closed = False
        self.snap_threshold = 12.0

        self._connect_observers()

    def _connect_observers(self) -> None:
        self.document.geometry_changed.connect(self._sync_from_document)
        self.document.geometry_changed.connect(self.update)
        self.document.constraints_changed.connect(self.constraints_changed.emit)
        self.document.constraints_changed.connect(self.update)
        self.document.dof_status_changed.connect(self.dof_status_changed.emit)
        self.selection_manager.available_constraints_changed.connect(self.available_constraints_changed.emit)

    def _sync_from_document(self) -> None:
        self.points = self.document.points
        self.lines = self.document.lines
        self.circles = self.document.circles
        self.arcs = self.document.arcs

    def set_undo_stack(self, undo_stack) -> None:
        """Connect a QUndoStack from the main window."""

        self.undo_stack = undo_stack

    def set_tool(self, tool: str) -> None:
        self.current_tool = tool
        if tool != "constraint":
            self.selection_manager.clear()
        if tool != "select":
            self._selected_geometry = None
        self._circle_center = None
        self._arc_center = None
        self._arc_start = None
        self.update()

    def set_constraint(self, enabled: bool) -> None:
        self.set_constraint_mode("horizontal" if enabled else "free")

    def set_constraint_mode(self, mode: str) -> None:
        if mode not in {"free", "horizontal", "vertical"}:
            return
        self.constraint_mode = mode
        if mode == "horizontal":
            self.quick_constraint_type = ConstraintType.HORIZONTAL
        elif mode == "vertical":
            self.quick_constraint_type = ConstraintType.VERTICAL
        else:
            self.quick_constraint_type = None
        self.update()

    def set_active_constraint_type(self, constraint_type: ConstraintType | None) -> None:
        """Set active constraint tool from toolbar actions."""

        self.quick_constraint_type = constraint_type

    def _is_close_to_first_point(self, point: QPointF) -> bool:
        if not self.points:
            return False
        first = self.points[0]
        dx = point.x() - first.x()
        dy = point.y() - first.y()
        return (dx * dx + dy * dy) <= (self.snap_threshold * self.snap_threshold)

    def clear(self) -> None:
        self.document.clear()
        self.rubber_point = None
        self._circle_center = None
        self._arc_center = None
        self._arc_start = None
        self._drag_reference = None
        self._drag_last_pos = None
        self._is_dragging = False
        self._selected_geometry = None
        self._point_axis_locks.clear()
        self._center_axis_locks.clear()
        self.closed = False
        self.selection_manager.clear()
        self.update()

    def get_sketch(self) -> dict:
        origin_points = [self._widget_to_origin(p) for p in self.points]
        xs = [float(p.x()) for p in origin_points]
        ys = [float(p.y()) for p in origin_points]
        width = max(xs) - min(xs) if xs else 0.0
        height = max(ys) - min(ys) if ys else 0.0
        line_lengths = [self._distance(self.points[start], self.points[end]) for start, end in self.lines]
        origin_circles = []
        for circle in self.circles:
            center = self._widget_to_origin(QPointF(circle.get("center", QPointF())))
            origin_circles.append(
                {
                    "center": (float(center.x()), float(center.y())),
                    "radius": float(circle.get("radius", 0.0)),
                }
            )
        origin_arcs = []
        for arc in self.arcs:
            center = self._widget_to_origin(QPointF(arc.get("center", QPointF())))
            origin_arcs.append(
                {
                    "center": (float(center.x()), float(center.y())),
                    "radius": float(arc.get("radius", 0.0)),
                    "start_angle": float(arc.get("start_angle", 0.0)),
                    "span_angle": float(arc.get("span_angle", 0.0)),
                }
            )
        return {
            "type": "polyline",
            "points": [(float(p.x()), float(p.y())) for p in origin_points],
            "lines": [[start, end] for start, end in self.lines],
            "circles": origin_circles,
            "arcs": origin_arcs,
            "line_lengths": [float(length) for length in line_lengths],
            "constraints": [self._serialize_constraint(constraint) for constraint in self.document.constraint_manager.all()],
            "width": width,
            "height": height,
            "closed": self.closed,
            "dimensioned": self.closed,
        }

    def load_sketch(self, sketch: dict) -> None:
        points = [self._origin_to_widget(QPointF(float(x), float(y))) for x, y in sketch.get("points", [])]
        lines = [(int(start), int(end)) for start, end in sketch.get("lines", [])]

        circles = []
        for circle in sketch.get("circles", []):
            center = circle.get("center", (0.0, 0.0))
            center_pt = self._origin_to_widget(QPointF(float(center[0]), float(center[1])))
            circles.append({"center": center_pt, "radius": float(circle.get("radius", 0.0))})

        arcs = []
        for arc in sketch.get("arcs", []):
            center = arc.get("center", (0.0, 0.0))
            center_pt = self._origin_to_widget(QPointF(float(center[0]), float(center[1])))
            arcs.append(
                {
                    "center": center_pt,
                    "radius": float(arc.get("radius", 0.0)),
                    "start_angle": float(arc.get("start_angle", 0.0)),
                    "span_angle": float(arc.get("span_angle", 0.0)),
                }
            )

        self.document.set_geometry(points, lines, circles, arcs)

        for existing in list(self.document.constraint_manager.all()):
            self.document.constraint_manager.remove_constraint(existing.id)
        for payload in sketch.get("constraints", []):
            constraint = self._deserialize_constraint(payload)
            if constraint is not None:
                self.document.constraint_manager.add_constraint(constraint)

        self.closed = sketch.get("closed", False)
        self.rubber_point = None
        self.document.solve_constraints()
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        pos = event.position()
        point = QPointF(pos.x(), pos.y())

        if self.current_tool == "measure" and (self.points or self.lines or self.circles or self.arcs):
            drag_ref = self._pick_geometry_ref(point)
            if drag_ref is not None:
                self._drag_reference = drag_ref
                self._drag_last_pos = QPointF(point)
                self._is_dragging = False
                return

            self._handle_measure_click(point)
            return

        if self.current_tool == "select" and (self.points or self.lines or self.circles or self.arcs):
            drag_ref = self._pick_geometry_ref(point)
            self._selected_geometry = drag_ref
            if drag_ref is not None:
                self._drag_reference = drag_ref
                self._drag_last_pos = QPointF(point)
                self._is_dragging = False
            self.update()
            return

        if self.current_tool == "constraint" and (self.points or self.lines or self.circles or self.arcs):
            geometry_ref = self._pick_geometry_ref(point)
            if geometry_ref is None:
                return

            ctrl = bool(event.modifiers() & Qt.ControlModifier)
            shift = bool(event.modifiers() & Qt.ShiftModifier)
            self.selection_manager.select(geometry_ref, ctrl=ctrl, shift=shift)

            if self.quick_constraint_type is not None:
                available = self.selection_manager.get_available_constraints()
                if self.quick_constraint_type in available:
                    self.apply_constraint(self.quick_constraint_type)
            return

        if self.current_tool == "circle":
            if self._circle_center is None:
                self._circle_center = QPointF(point)
            else:
                radius = self._distance(self._circle_center, point)
                if radius > 0.01:
                    self.circles.append({"center": QPointF(self._circle_center), "radius": float(radius)})
                    self.document.geometry_changed.emit()
                self._circle_center = None
            self.update()
            return

        if self.current_tool == "arc":
            if self._arc_center is None:
                self._arc_center = QPointF(point)
                self.update()
                return
            if self._arc_start is None:
                self._arc_start = QPointF(point)
                self.update()
                return

            radius = self._distance(self._arc_center, self._arc_start)
            if radius > 0.01:
                start_angle = self._point_angle_deg(self._arc_center, self._arc_start)
                end_angle = self._point_angle_deg(self._arc_center, point)
                span_angle = end_angle - start_angle
                if span_angle > 180.0:
                    span_angle -= 360.0
                if span_angle < -180.0:
                    span_angle += 360.0
                self.arcs.append(
                    {
                        "center": QPointF(self._arc_center),
                        "radius": float(radius),
                        "start_angle": float(start_angle),
                        "span_angle": float(span_angle),
                    }
                )
                self.document.geometry_changed.emit()

            self._arc_center = None
            self._arc_start = None
            self.update()
            return

        if self.points and self.current_tool == "line":
            if self._is_close_to_first_point(point) and len(self.points) >= 3:
                self.lines.append((len(self.points) - 1, 0))
                self.closed = True
                self.rubber_point = None
                self.document.geometry_changed.emit()
                self.update()
                return

            last_point = self.points[-1]
            new_point = QPointF(point)
            if self.constraint_mode != "free" or (event.modifiers() & Qt.ShiftModifier):
                dx = new_point.x() - last_point.x()
                dy = new_point.y() - last_point.y()
                if self.constraint_mode == "horizontal" or (self.constraint_mode == "free" and abs(dx) >= abs(dy)):
                    new_point.setY(last_point.y())
                elif self.constraint_mode == "vertical" or (self.constraint_mode == "free" and abs(dy) > abs(dx)):
                    new_point.setX(last_point.x())
            self.points.append(new_point)
            self.lines.append((len(self.points) - 2, len(self.points) - 1))
            self.document.geometry_changed.emit()
        elif self.current_tool == "point":
            self.points.append(point)
            self.document.geometry_changed.emit()
        self.rubber_point = None
        self.update()

    def _handle_measure_click(self, point: QPointF) -> None:
        point_index = self._find_point_for_click(point)
        if point_index is not None:
            self._set_point_coordinates(point_index)
            return
        circle_center_index = self._find_circle_center_index_for_click(point)
        if circle_center_index is not None:
            self._set_circular_center_coordinates("circle", circle_center_index)
            return
        arc_center_index = self._find_arc_center_index_for_click(point)
        if arc_center_index is not None:
            self._set_circular_center_coordinates("arc", arc_center_index)
            return
        selected_line = self._find_line_for_point(point)
        if selected_line is not None:
            start_idx, end_idx = selected_line
            self._set_line_length(start_idx, end_idx)
            return
        circle_index = self._find_circle_index_for_click(point)
        if circle_index is not None:
            self._set_circular_radius("circle", circle_index)
            return
        arc_index = self._find_arc_index_for_click(point)
        if arc_index is not None:
            self._set_circular_radius("arc", arc_index)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            if self.current_tool == "measure" and self._drag_reference is not None:
                if not self._is_dragging:
                    pos = event.position()
                    self._handle_measure_click(QPointF(pos.x(), pos.y()))
                self._drag_reference = None
                self._drag_last_pos = None
                self._is_dragging = False
                self.update()
            elif self.current_tool == "select" and self._drag_reference is not None:
                self._drag_reference = None
                self._drag_last_pos = None
                self._is_dragging = False
                self.update()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        current = QPointF(pos.x(), pos.y())
        if self.current_tool in {"measure", "select"} and self._drag_reference is not None and self._drag_last_pos is not None and (event.buttons() & Qt.LeftButton):
            delta = QPointF(current.x() - self._drag_last_pos.x(), current.y() - self._drag_last_pos.y())
            if abs(delta.x()) + abs(delta.y()) > 0.01:
                self._is_dragging = True
                self._apply_drag_delta(self._drag_reference, delta)
                self._drag_last_pos = current
                self.document.solve_constraints()
                self.update()
            return

        if self.points or self.current_tool in {"circle", "arc"}:
            self.rubber_point = current
            self.update()

    def leaveEvent(self, event) -> None:
        self.rubber_point = None
        self.update()

    def _find_point_for_click(self, point: QPointF) -> int | None:
        for index, existing in enumerate(self.points):
            dx = point.x() - existing.x()
            dy = point.y() - existing.y()
            if (dx * dx + dy * dy) <= (self.snap_threshold * self.snap_threshold):
                return index
        return None

    def _find_line_for_point(self, point: QPointF) -> tuple[int, int] | None:
        for start_idx, end_idx in self.lines:
            start = self.points[start_idx]
            end = self.points[end_idx]
            if self._is_point_near_line(point, start, end):
                return (start_idx, end_idx)
        return None

    def _find_line_index_for_click(self, point: QPointF) -> int | None:
        for index, (start_idx, end_idx) in enumerate(self.lines):
            start = self.points[start_idx]
            end = self.points[end_idx]
            if self._is_point_near_line(point, start, end):
                return index
        return None

    def _is_point_near_line(self, point: QPointF, start: QPointF, end: QPointF) -> bool:
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        if dx == 0 and dy == 0:
            return self._distance(point, start) <= self.snap_threshold
        t = ((point.x() - start.x()) * dx + (point.y() - start.y()) * dy) / (dx*dx + dy*dy)
        t = max(0.0, min(1.0, t))
        proj = QPointF(start.x() + t * dx, start.y() + t * dy)
        return self._distance(point, proj) <= self.snap_threshold

    def _distance(self, a: QPointF, b: QPointF) -> float:
        return ((a.x() - b.x())**2 + (a.y() - b.y())**2) ** 0.5

    def _pick_geometry_ref(self, point: QPointF) -> GeometryRef | None:
        point_index = self._find_point_for_click(point)
        if point_index is not None:
            return GeometryRef("point", point_index)

        line_index = self._find_line_index_for_click(point)
        if line_index is not None:
            return GeometryRef("line", line_index)

        circle_index = self._find_circle_index_for_click(point)
        if circle_index is not None:
            return GeometryRef("circle", circle_index)

        arc_index = self._find_arc_index_for_click(point)
        if arc_index is not None:
            return GeometryRef("arc", arc_index)

        return None

    def _find_circle_index_for_click(self, point: QPointF) -> int | None:
        for idx, circle in enumerate(self.circles):
            center = QPointF(circle.get("center", QPointF()))
            radius = float(circle.get("radius", 0.0))
            if abs(self._distance(point, center) - radius) <= self.snap_threshold:
                return idx
        return None

    def _find_circle_center_index_for_click(self, point: QPointF) -> int | None:
        for idx, circle in enumerate(self.circles):
            center = QPointF(circle.get("center", QPointF()))
            if self._distance(point, center) <= self.snap_threshold:
                return idx
        return None

    def _find_arc_center_index_for_click(self, point: QPointF) -> int | None:
        for idx, arc in enumerate(self.arcs):
            center = QPointF(arc.get("center", QPointF()))
            if self._distance(point, center) <= self.snap_threshold:
                return idx
        return None

    def _find_arc_index_for_click(self, point: QPointF) -> int | None:
        for idx, arc in enumerate(self.arcs):
            center = QPointF(arc.get("center", QPointF()))
            radius = float(arc.get("radius", 0.0))
            if abs(self._distance(point, center) - radius) > self.snap_threshold:
                continue
            point_angle = self._point_angle_deg(center, point)
            if self._angle_in_span(point_angle, float(arc.get("start_angle", 0.0)), float(arc.get("span_angle", 0.0))):
                return idx
        return None

    def _point_angle_deg(self, center: QPointF, point: QPointF) -> float:
        return degrees(atan2(-(point.y() - center.y()), point.x() - center.x()))

    def _normalize_angle(self, angle: float) -> float:
        while angle < 0.0:
            angle += 360.0
        while angle >= 360.0:
            angle -= 360.0
        return angle

    def _angle_in_span(self, angle: float, start_angle: float, span_angle: float) -> bool:
        angle = self._normalize_angle(angle)
        start = self._normalize_angle(start_angle)
        end = self._normalize_angle(start_angle + span_angle)
        if span_angle >= 0.0:
            if start <= end:
                return start <= angle <= end
            return angle >= start or angle <= end
        if end <= start:
            return end <= angle <= start
        return angle >= end or angle <= start

    def _build_constraint_parameters(self, constraint_type: ConstraintType) -> dict[str, Any]:
        if constraint_type in {ConstraintType.DISTANCE, ConstraintType.LENGTH, ConstraintType.RADIUS, ConstraintType.DIAMETER}:
            value, ok = QInputDialog.getDouble(self, "Constraint Value", "Value:", 10.0, 0.0, 100000.0, 2)
            if not ok:
                return {}
            return {"value": float(value)}

        if constraint_type == ConstraintType.ANGLE:
            value, ok = QInputDialog.getDouble(self, "Angle", "Degrees:", 45.0, -360.0, 360.0, 2)
            if not ok:
                return {}
            return {"value": float(value)}

        if constraint_type == ConstraintType.SYMMETRY:
            axis_idx, ok = QInputDialog.getInt(self, "Symmetry", "Axis line index:", 0, 0, max(0, len(self.lines) - 1), 1)
            if not ok:
                return {}
            return {"axis_line_id": int(axis_idx)}

        return {}

    def apply_constraint(self, constraint_type: ConstraintType) -> None:
        """Create and solve a constraint from current selection."""

        selection = self.selection_manager.selection
        if not selection:
            return

        parameters = self._build_constraint_parameters(constraint_type)
        if constraint_type in {ConstraintType.DISTANCE, ConstraintType.LENGTH, ConstraintType.RADIUS, ConstraintType.DIAMETER, ConstraintType.ANGLE, ConstraintType.SYMMETRY} and not parameters:
            return

        icon_map = {
            ConstraintType.HORIZONTAL: "H",
            ConstraintType.VERTICAL: "V",
            ConstraintType.PERPENDICULAR: "⊥",
            ConstraintType.PARALLEL: "∥",
            ConstraintType.RADIUS: "R",
            ConstraintType.ANGLE: "°",
            ConstraintType.DISTANCE: "M",
            ConstraintType.LENGTH: "L",
            ConstraintType.COINCIDENT: "C",
            ConstraintType.MIDPOINT: "Mid",
            ConstraintType.EQUAL: "=",
            ConstraintType.CONCENTRIC: "◎",
            ConstraintType.TANGENT: "T",
            ConstraintType.DIAMETER: "D",
            ConstraintType.SYMMETRY: "SYM",
        }

        new_constraint = Constraint(
            name=f"{constraint_type.name.title()} Constraint",
            constraint_type=constraint_type,
            references=deepcopy(selection),
            parameters=parameters,
            icon_id=icon_map.get(constraint_type, constraint_type.value),
            enabled=True,
            suppressed=False,
        )

        if self.undo_stack is not None:
            self.undo_stack.push(AddConstraintCommand(self.document, new_constraint))
        else:
            self.document.constraint_manager.add_constraint(new_constraint)
            self.document.solve_constraints()

        self.selection_manager.clear()
        self.update()

    def toggle_suppress_constraint(self, constraint_id: str) -> None:
        existing = self.document.constraint_manager.get(constraint_id)
        if existing is None:
            return
        updates = {"suppressed": not existing.suppressed}
        if self.undo_stack is not None:
            self.undo_stack.push(UpdateConstraintCommand(self.document, constraint_id, updates, text="Toggle Suppress"))
        else:
            self.document.constraint_manager.update_constraint(constraint_id, **updates)
            self.document.solve_constraints()

    def delete_constraint(self, constraint_id: str) -> None:
        existing = self.document.constraint_manager.get(constraint_id)
        if existing is None:
            return
        if self.undo_stack is not None:
            from cadapp.constraints.constraint_command import RemoveConstraintCommand

            self.undo_stack.push(RemoveConstraintCommand(self.document, constraint_id))
        else:
            self.document.constraint_manager.remove_constraint(constraint_id)
            self.document.solve_constraints()

    def rename_constraint(self, constraint_id: str) -> None:
        existing = self.document.constraint_manager.get(constraint_id)
        if existing is None:
            return
        name, ok = QInputDialog.getText(self, "Rename Constraint", "New name:", text=existing.name)
        if not ok or not name.strip():
            return
        updates = {"name": name.strip()}
        if self.undo_stack is not None:
            self.undo_stack.push(UpdateConstraintCommand(self.document, constraint_id, updates, text="Rename Constraint"))
        else:
            self.document.constraint_manager.update_constraint(constraint_id, **updates)

    def edit_constraint(self, constraint_id: str) -> None:
        existing = self.document.constraint_manager.get(constraint_id)
        if existing is None:
            return
        if existing.constraint_type in {
            ConstraintType.DISTANCE,
            ConstraintType.LENGTH,
            ConstraintType.RADIUS,
            ConstraintType.DIAMETER,
            ConstraintType.ANGLE,
        }:
            value, ok = QInputDialog.getDouble(
                self,
                "Edit Constraint",
                "Value:",
                float(existing.parameters.get("value", 0.0)),
                -100000.0,
                100000.0,
                2,
            )
            if not ok:
                return
            updates = {"parameters": {**existing.parameters, "value": float(value)}}
            if self.undo_stack is not None:
                self.undo_stack.push(UpdateConstraintCommand(self.document, constraint_id, updates, text="Edit Constraint"))
            else:
                self.document.constraint_manager.update_constraint(constraint_id, **updates)
                self.document.solve_constraints()

    def _widget_to_origin(self, point: QPointF) -> QPointF:
        width = self.width() or 1.0
        height = self.height() or 1.0
        origin = QPointF(width / 2.0, height / 2.0)
        return QPointF(point.x() - origin.x(), origin.y() - point.y())

    def _origin_to_widget(self, point: QPointF) -> QPointF:
        width = self.width() or 1.0
        height = self.height() or 1.0
        origin = QPointF(width / 2.0, height / 2.0)
        return QPointF(origin.x() + point.x(), origin.y() - point.y())

    def _draw_constraint_markers(self, painter: QPainter) -> None:
        marker_pen = QPen(QColor(255, 255, 0))
        marker_pen.setWidth(2)
        conflict_pen = QPen(QColor(255, 90, 90))
        conflict_pen.setWidth(2)
        occupancy: dict[tuple[int, int], int] = {}
        conflict_constraints = self._conflict_constraint_ids()

        for constraint in self.document.constraint_manager.all():
            if not constraint.enabled or constraint.suppressed:
                continue
            anchor = self._constraint_anchor(constraint)
            if anchor is None:
                continue

            key = (int(anchor.x() // 24), int(anchor.y() // 20))
            overlap_index = occupancy.get(key, 0)
            occupancy[key] = overlap_index + 1

            draw_at = QPointF(anchor.x() + overlap_index * 14, anchor.y() - overlap_index * 12)
            text = self._constraint_label(constraint)
            painter.setPen(conflict_pen if constraint.id in conflict_constraints else marker_pen)
            painter.drawText(draw_at, text)

    def _draw_selected_geometry(self, painter: QPainter) -> None:
        ref = self._selected_geometry
        if ref is None:
            return

        pen = QPen(QColor(120, 210, 255))
        pen.setWidth(3)
        painter.setPen(pen)

        if ref.kind == "point" and 0 <= ref.entity_id < len(self.points):
            painter.drawEllipse(self.points[ref.entity_id], 8, 8)
            return

        if ref.kind == "line" and 0 <= ref.entity_id < len(self.lines):
            a, b = self.lines[ref.entity_id]
            painter.drawLine(self.points[a], self.points[b])
            return

        if ref.kind == "circle" and 0 <= ref.entity_id < len(self.circles):
            circle = self.circles[ref.entity_id]
            center = QPointF(circle.get("center", QPointF()))
            radius = float(circle.get("radius", 0.0))
            painter.drawEllipse(QRectF(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0))
            return

        if ref.kind == "arc" and 0 <= ref.entity_id < len(self.arcs):
            arc = self.arcs[ref.entity_id]
            center = QPointF(arc.get("center", QPointF()))
            radius = float(arc.get("radius", 0.0))
            rect = QRectF(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)
            start_angle = int(float(arc.get("start_angle", 0.0)) * 16.0)
            span_angle = int(float(arc.get("span_angle", 0.0)) * 16.0)
            painter.drawArc(rect, start_angle, span_angle)

    def _conflict_constraint_ids(self) -> set[str]:
        ids: set[str] = set()
        for item in self.document.last_dof_status.get("conflict_items", []):
            for constraint_id in item.get("constraint_ids", []):
                ids.add(str(constraint_id))
        return ids

    def _conflict_geometry_refs(self) -> set[tuple[str, int]]:
        refs: set[tuple[str, int]] = set()
        conflict_ids = self._conflict_constraint_ids()
        if not conflict_ids:
            return refs
        for constraint in self.document.constraint_manager.all():
            if constraint.id not in conflict_ids:
                continue
            for ref in constraint.references:
                refs.add((ref.kind, ref.entity_id))
        return refs

    def _constraint_anchor(self, constraint: Constraint) -> QPointF | None:
        refs = constraint.references
        if not refs:
            return None
        if refs[0].kind == "line":
            line_idx = refs[0].entity_id
            if 0 <= line_idx < len(self.lines):
                a_idx, b_idx = self.lines[line_idx]
                a = self.points[a_idx]
                b = self.points[b_idx]
                return QPointF((a.x() + b.x()) / 2.0, (a.y() + b.y()) / 2.0)
        if refs[0].kind == "point":
            point_idx = refs[0].entity_id
            if 0 <= point_idx < len(self.points):
                return QPointF(self.points[point_idx])
        if refs[0].kind in {"circle", "arc"}:
            entity_idx = refs[0].entity_id
            if refs[0].kind == "circle" and 0 <= entity_idx < len(self.circles):
                return QPointF(self.circles[entity_idx].get("center", QPointF()))
            if refs[0].kind == "arc" and 0 <= entity_idx < len(self.arcs):
                return QPointF(self.arcs[entity_idx].get("center", QPointF()))
        return None

    def _constraint_label(self, constraint: Constraint) -> str:
        ct = constraint.constraint_type
        if ct == ConstraintType.HORIZONTAL:
            return "H"
        if ct == ConstraintType.VERTICAL:
            return "V"
        if ct == ConstraintType.PERPENDICULAR:
            return "⊥"
        if ct == ConstraintType.PARALLEL:
            return "∥"
        if ct == ConstraintType.RADIUS:
            return f"R{constraint.parameters.get('value', '')}"
        if ct == ConstraintType.ANGLE:
            return f"{constraint.parameters.get('value', '')}°"
        if ct == ConstraintType.DISTANCE:
            return f"M{constraint.parameters.get('value', '')}"
        if ct == ConstraintType.LENGTH:
            return f"L{constraint.parameters.get('value', '')}"
        return constraint.icon_id or constraint.name

    def _set_point_coordinates(self, point_index: int) -> None:
        origin_point = self._widget_to_origin(self.points[point_index])
        old_x = float(origin_point.x())
        old_y = float(origin_point.y())
        x_value, ok_x = QInputDialog.getDouble(self, "Set Point X", "X coordinate from origin:", float(origin_point.x()), -1000.0, 1000.0, 2)
        if not ok_x:
            return
        y_value, ok_y = QInputDialog.getDouble(self, "Set Point Y", "Y coordinate from origin:", float(origin_point.y()), -1000.0, 1000.0, 2)
        if not ok_y:
            return
        self.points[point_index] = self._origin_to_widget(QPointF(x_value, y_value))
        self._set_axis_lock(self._point_axis_locks, point_index, "x", old_x, float(x_value))
        self._set_axis_lock(self._point_axis_locks, point_index, "y", old_y, float(y_value))
        self.document.solve_constraints()
        self.update()

    def _set_line_length(self, start_idx: int, end_idx: int) -> None:
        start = self.points[start_idx]
        end = self.points[end_idx]
        current_length = self._distance(start, end)
        new_length, ok = QInputDialog.getDouble(self, "Set Line Length", "Length:", float(current_length), 0.1, 10000.0, 2)
        if not ok:
            return
        if current_length <= 0:
            return
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        scale = new_length / current_length
        self.points[end_idx] = QPointF(start.x() + dx * scale, start.y() + dy * scale)
        existing = self._find_constraint_for_line(ConstraintType.LENGTH, start_idx, end_idx)
        if existing is not None:
            self.document.constraint_manager.update_constraint(existing.id, parameters={"value": float(new_length)})
        else:
            line_idx = self._line_index_from_points(start_idx, end_idx)
            if line_idx is not None:
                self.document.constraint_manager.add_constraint(
                    Constraint(
                        name="Length Constraint",
                        constraint_type=ConstraintType.LENGTH,
                        references=[GeometryRef("line", line_idx)],
                        parameters={"value": float(new_length)},
                        icon_id="L",
                    )
                )
        self.document.solve_constraints()
        self.update()

    def _set_circular_radius(self, kind: str, entity_idx: int) -> None:
        entities = self.circles if kind == "circle" else self.arcs
        if not (0 <= entity_idx < len(entities)):
            return
        entity = entities[entity_idx]
        current_radius = float(entity.get("radius", 0.0))
        new_radius, ok = QInputDialog.getDouble(
            self,
            "Set Radius",
            "Radius:",
            current_radius,
            0.1,
            10000.0,
            2,
        )
        if not ok:
            return
        entity["radius"] = float(new_radius)
        self.document.solve_constraints()
        self.update()

    def _set_circular_center_coordinates(self, kind: str, entity_idx: int) -> None:
        entities = self.circles if kind == "circle" else self.arcs
        if not (0 <= entity_idx < len(entities)):
            return

        center = QPointF(entities[entity_idx].get("center", QPointF()))
        origin_center = self._widget_to_origin(center)
        old_x = float(origin_center.x())
        old_y = float(origin_center.y())
        x_value, ok_x = QInputDialog.getDouble(
            self,
            "Set Center X",
            "X coordinate from origin:",
            float(origin_center.x()),
            -10000.0,
            10000.0,
            2,
        )
        if not ok_x:
            return
        y_value, ok_y = QInputDialog.getDouble(
            self,
            "Set Center Y",
            "Y coordinate from origin:",
            float(origin_center.y()),
            -10000.0,
            10000.0,
            2,
        )
        if not ok_y:
            return

        entities[entity_idx]["center"] = self._origin_to_widget(QPointF(x_value, y_value))
        lock_key = (kind, entity_idx)
        self._set_axis_lock(self._center_axis_locks, lock_key, "x", old_x, float(x_value))
        self._set_axis_lock(self._center_axis_locks, lock_key, "y", old_y, float(y_value))
        self.document.solve_constraints()
        self.update()

    def _set_axis_lock(self, lock_table: dict, key, axis: str, old_value: float, new_value: float) -> None:
        axis_locks = lock_table.setdefault(key, {})
        if abs(new_value - old_value) > 1e-6:
            axis_locks[axis] = new_value
        else:
            axis_locks.pop(axis, None)
        if not axis_locks:
            lock_table.pop(key, None)

    def _apply_drag_delta(self, reference: GeometryRef, delta: QPointF) -> None:
        if reference.kind == "point" and 0 <= reference.entity_id < len(self.points):
            old = self.points[reference.entity_id]
            candidate = QPointF(old.x() + delta.x(), old.y() + delta.y())
            self.points[reference.entity_id] = self._apply_point_lock(reference.entity_id, candidate)
            return

        if reference.kind == "line" and 0 <= reference.entity_id < len(self.lines):
            start_idx, end_idx = self.lines[reference.entity_id]
            for idx in (start_idx, end_idx):
                old = self.points[idx]
                candidate = QPointF(old.x() + delta.x(), old.y() + delta.y())
                self.points[idx] = self._apply_point_lock(idx, candidate)
            return

        if reference.kind in {"circle", "arc"}:
            entities = self.circles if reference.kind == "circle" else self.arcs
            if not (0 <= reference.entity_id < len(entities)):
                return
            center = QPointF(entities[reference.entity_id].get("center", QPointF()))
            candidate = QPointF(center.x() + delta.x(), center.y() + delta.y())
            entities[reference.entity_id]["center"] = self._apply_center_lock(reference.kind, reference.entity_id, candidate)

    def _apply_point_lock(self, point_idx: int, candidate: QPointF) -> QPointF:
        locks = self._point_axis_locks.get(point_idx)
        if not locks:
            return candidate
        if "x" in locks or "y" in locks:
            lock_origin = QPointF(float(locks.get("x", 0.0)), float(locks.get("y", 0.0)))
            lock_widget = self._origin_to_widget(lock_origin)
            if "x" in locks:
                candidate.setX(lock_widget.x())
            if "y" in locks:
                candidate.setY(lock_widget.y())
        return candidate

    def _apply_center_lock(self, kind: str, entity_idx: int, candidate: QPointF) -> QPointF:
        locks = self._center_axis_locks.get((kind, entity_idx))
        if not locks:
            return candidate
        if "x" in locks or "y" in locks:
            lock_origin = QPointF(float(locks.get("x", 0.0)), float(locks.get("y", 0.0)))
            lock_widget = self._origin_to_widget(lock_origin)
            if "x" in locks:
                candidate.setX(lock_widget.x())
            if "y" in locks:
                candidate.setY(lock_widget.y())
        return candidate

    def _draw_measurement_labels(self, painter: QPainter) -> None:
        label_pen = QPen(QColor(210, 230, 255))
        painter.setPen(label_pen)

        # Point coordinates relative to canvas origin.
        for point in self.points:
            origin_point = self._widget_to_origin(point)
            painter.drawText(
                QPointF(point.x() + 8.0, point.y() - 8.0),
                f"({origin_point.x():.1f}, {origin_point.y():.1f})",
            )

        # Line lengths.
        for start_idx, end_idx in self.lines:
            start = self.points[start_idx]
            end = self.points[end_idx]
            mid = QPointF((start.x() + end.x()) / 2.0, (start.y() + end.y()) / 2.0)
            length = self._distance(start, end)
            painter.drawText(QPointF(mid.x() + 8.0, mid.y() - 6.0), f"L={length:.1f}")

        # Circle/arc radius and center coordinates.
        for circle in self.circles:
            center = QPointF(circle.get("center", QPointF()))
            radius = float(circle.get("radius", 0.0))
            origin_center = self._widget_to_origin(center)
            painter.drawText(QPointF(center.x() + 8.0, center.y() - 8.0), f"C({origin_center.x():.1f}, {origin_center.y():.1f})")
            painter.drawText(QPointF(center.x() + radius + 6.0, center.y()), f"R={radius:.1f}")

        for arc in self.arcs:
            center = QPointF(arc.get("center", QPointF()))
            radius = float(arc.get("radius", 0.0))
            origin_center = self._widget_to_origin(center)
            painter.drawText(QPointF(center.x() + 8.0, center.y() - 8.0), f"C({origin_center.x():.1f}, {origin_center.y():.1f})")
            painter.drawText(QPointF(center.x() + radius + 6.0, center.y()), f"R={radius:.1f}")

    def _line_index_from_points(self, start_idx: int, end_idx: int) -> int | None:
        for idx, (a, b) in enumerate(self.lines):
            if (a, b) == (start_idx, end_idx):
                return idx
        return None

    def _find_constraint_for_line(self, constraint_type: ConstraintType, start_idx: int, end_idx: int) -> Constraint | None:
        line_idx = self._line_index_from_points(start_idx, end_idx)
        if line_idx is None:
            return None
        for constraint in self.document.constraint_manager.all():
            if constraint.constraint_type == constraint_type and constraint.references:
                ref = constraint.references[0]
                if ref.kind == "line" and ref.entity_id == line_idx:
                    return constraint
        return None

    def _serialize_constraint(self, constraint: Constraint) -> dict:
        return {
            "id": constraint.id,
            "name": constraint.name,
            "constraint_type": str(constraint.constraint_type),
            "references": [
                {"kind": ref.kind, "entity_id": ref.entity_id}
                for ref in constraint.references
            ],
            "parameters": deepcopy(constraint.parameters),
            "icon_id": constraint.icon_id,
            "enabled": constraint.enabled,
            "suppressed": constraint.suppressed,
        }

    def _deserialize_constraint(self, payload: dict) -> Constraint | None:
        try:
            return Constraint(
                id=str(payload.get("id")) if payload.get("id") else Constraint().id,
                name=str(payload.get("name", "Constraint")),
                constraint_type=ConstraintType(str(payload.get("constraint_type", ConstraintType.COINCIDENT.value))),
                references=[
                    GeometryRef(str(ref.get("kind")), int(ref.get("entity_id")))
                    for ref in payload.get("references", [])
                ],
                parameters=dict(payload.get("parameters", {})),
                icon_id=str(payload.get("icon_id", "")),
                enabled=bool(payload.get("enabled", True)),
                suppressed=bool(payload.get("suppressed", False)),
            )
        except (ValueError, TypeError):
            return None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape and self.points:
            if self.closed and self.parent() and hasattr(self.parent(), "finish_sketch"):
                self.parent().finish_sketch()
                return
            if self.parent() and hasattr(self.parent(), "cancel_sketch"):
                self.parent().cancel_sketch()
                return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(20, 20, 20))

        origin = QPointF(self.width() / 2.0, self.height() / 2.0)
        axis_pen = QPen(QColor(100, 220, 220))
        axis_pen.setWidth(1)
        axis_pen.setStyle(Qt.DashLine)
        painter.setPen(axis_pen)
        painter.drawLine(0, origin.y(), self.width(), origin.y())
        painter.drawLine(origin.x(), 0, origin.x(), self.height())

        axis_label_pen = QPen(QColor(200, 240, 240))
        painter.setPen(axis_label_pen)
        painter.drawText(origin.x() + 6, origin.y() - 6, "0")
        painter.drawText(self.width() - 30, origin.y() - 6, "X")
        painter.drawText(origin.x() + 6, 20, "Y")
        painter.setPen(QPen(QColor(180, 255, 255), 6))
        painter.drawPoint(origin)

        line_pen = QPen(QColor(220, 220, 220))
        line_pen.setWidth(2)
        painter.setPen(line_pen)
        conflict_refs = self._conflict_geometry_refs()

        for idx, (start_idx, end_idx) in enumerate(self.lines):
            start = self.points[start_idx]
            end = self.points[end_idx]
            highlighted = False
            is_conflict = ("line", idx) in conflict_refs
            for constraint in self.document.constraint_manager.all():
                if not constraint.enabled or constraint.suppressed:
                    continue
                if constraint.constraint_type in {ConstraintType.HORIZONTAL, ConstraintType.VERTICAL}:
                    if constraint.references and constraint.references[0].kind == "line" and constraint.references[0].entity_id == idx:
                        highlighted = True
                        break
            if highlighted:
                direction_pen = QPen(QColor(100, 255, 100))
                direction_pen.setWidth(3)
                painter.setPen(direction_pen)
                painter.drawLine(start, end)
                painter.setPen(line_pen)
            elif is_conflict:
                conflict_line_pen = QPen(QColor(255, 90, 90))
                conflict_line_pen.setWidth(4)
                painter.setPen(conflict_line_pen)
                painter.drawLine(start, end)
                painter.setPen(line_pen)
            else:
                painter.drawLine(start, end)

        circle_pen = QPen(QColor(180, 220, 255))
        circle_pen.setWidth(2)
        painter.setPen(circle_pen)
        for circle in self.circles:
            center = QPointF(circle.get("center", QPointF()))
            radius = float(circle.get("radius", 0.0))
            rect = QRectF(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)
            painter.drawEllipse(rect)

        center_pen = QPen(QColor(255, 210, 80))
        center_pen.setWidth(5)
        painter.setPen(center_pen)
        for circle in self.circles:
            center = QPointF(circle.get("center", QPointF()))
            painter.drawPoint(center)

        for idx, circle in enumerate(self.circles):
            if ("circle", idx) not in conflict_refs:
                continue
            center = QPointF(circle.get("center", QPointF()))
            radius = float(circle.get("radius", 0.0))
            rect = QRectF(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)
            painter.setPen(QPen(QColor(255, 90, 90), 3))
            painter.drawEllipse(rect)
            painter.setPen(circle_pen)

        arc_pen = QPen(QColor(255, 210, 140))
        arc_pen.setWidth(2)
        painter.setPen(arc_pen)
        for idx, arc in enumerate(self.arcs):
            center = QPointF(arc.get("center", QPointF()))
            radius = float(arc.get("radius", 0.0))
            rect = QRectF(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)
            start_angle = int(float(arc.get("start_angle", 0.0)) * 16.0)
            span_angle = int(float(arc.get("span_angle", 0.0)) * 16.0)
            if ("arc", idx) in conflict_refs:
                painter.setPen(QPen(QColor(255, 90, 90), 3))
                painter.drawArc(rect, start_angle, span_angle)
                painter.setPen(arc_pen)
            painter.drawArc(rect, start_angle, span_angle)

        painter.setPen(center_pen)
        for arc in self.arcs:
            center = QPointF(arc.get("center", QPointF()))
            painter.drawPoint(center)

        self._draw_measurement_labels(painter)

        self._draw_constraint_markers(painter)
        self._draw_selected_geometry(painter)

        if self.closed and len(self.points) > 2:
            brush = QBrush(QColor(120, 200, 150, 80))
            painter.setBrush(brush)
            painter.setPen(Qt.NoPen)
            polygon = QPolygonF(self.points)
            painter.drawPolygon(polygon)
            painter.setBrush(Qt.NoBrush)

        if self.points and self.rubber_point is not None and not self.closed:
            last_point = self.points[-1]
            preview_point = QPointF(self.rubber_point)
            if self.constraint_mode != "free":
                if self.constraint_mode == "horizontal":
                    preview_point.setY(last_point.y())
                else:
                    preview_point.setX(last_point.x())
            elif QApplication.keyboardModifiers() & Qt.ShiftModifier:
                dx = preview_point.x() - last_point.x()
                dy = preview_point.y() - last_point.y()
                if abs(dx) >= abs(dy):
                    preview_point.setY(last_point.y())
                else:
                    preview_point.setX(last_point.x())
            painter.setPen(QPen(QColor(120, 200, 250), 1, Qt.DashLine))
            painter.drawLine(last_point, preview_point)

        if self.current_tool == "circle" and self._circle_center is not None and self.rubber_point is not None:
            preview_radius = self._distance(self._circle_center, self.rubber_point)
            painter.setPen(QPen(QColor(120, 200, 250), 1, Qt.DashLine))
            preview_rect = QRectF(
                self._circle_center.x() - preview_radius,
                self._circle_center.y() - preview_radius,
                preview_radius * 2.0,
                preview_radius * 2.0,
            )
            painter.drawEllipse(preview_rect)

        if self.current_tool == "arc" and self._arc_center is not None and self.rubber_point is not None:
            if self._arc_start is None:
                painter.setPen(QPen(QColor(120, 200, 250), 1, Qt.DashLine))
                painter.drawLine(self._arc_center, self.rubber_point)
            else:
                preview_radius = self._distance(self._arc_center, self._arc_start)
                preview_start = self._point_angle_deg(self._arc_center, self._arc_start)
                preview_end = self._point_angle_deg(self._arc_center, self.rubber_point)
                preview_span = preview_end - preview_start
                if preview_span > 180.0:
                    preview_span -= 360.0
                if preview_span < -180.0:
                    preview_span += 360.0
                painter.setPen(QPen(QColor(120, 200, 250), 1, Qt.DashLine))
                preview_rect = QRectF(
                    self._arc_center.x() - preview_radius,
                    self._arc_center.y() - preview_radius,
                    preview_radius * 2.0,
                    preview_radius * 2.0,
                )
                painter.drawArc(preview_rect, int(preview_start * 16.0), int(preview_span * 16.0))

        point_pen = QPen(QColor(255, 165, 0))
        point_pen.setWidth(6)
        painter.setPen(point_pen)

        for idx, point in enumerate(self.points):
            if ("point", idx) in conflict_refs:
                painter.setPen(QPen(QColor(255, 90, 90), 8))
                painter.drawPoint(point)
                painter.setPen(point_pen)
            painter.drawPoint(point)

        if self.rubber_point is not None:
            preview_pen = QPen(QColor(160, 160, 160))
            preview_pen.setWidth(4)
            painter.setPen(preview_pen)
            painter.drawPoint(self.rubber_point)
