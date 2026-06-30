"""
sketch_canvas.py - Simple 2D sketch editor for CAD app

Allows line drawing with point placement and optional horizontal/vertical constraint.
"""

from PySide6.QtWidgets import QWidget, QApplication, QInputDialog
from PySide6.QtGui import QPainter, QColor, QPen, QMouseEvent, QKeyEvent, QPolygonF, QBrush
from PySide6.QtCore import Qt, QPointF


class SketchCanvas(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.points: list[QPointF] = []
        self.lines: list[tuple[int, int]] = []
        self.constraints: list[dict] = []
        self.current_tool = "line"
        self.constraint_mode = "free"
        self.constraint_selection: tuple[str, int] | None = None
        self.rubber_point: QPointF | None = None
        self.closed = False
        self.snap_threshold = 12.0

    def set_tool(self, tool: str) -> None:
        self.current_tool = tool
        if tool != "constraint":
            self.constraint_selection = None
        self.update()

    def set_constraint(self, enabled: bool) -> None:
        self.constraint_mode = "horizontal" if enabled else "free"
        self.update()

    def set_constraint_mode(self, mode: str) -> None:
        if mode in {"free", "horizontal", "vertical"}:
            self.constraint_mode = mode
        self.update()

    def _is_close_to_first_point(self, point: QPointF) -> bool:
        if not self.points:
            return False
        first = self.points[0]
        dx = point.x() - first.x()
        dy = point.y() - first.y()
        return (dx * dx + dy * dy) <= (self.snap_threshold * self.snap_threshold)

    def clear(self) -> None:
        self.points.clear()
        self.lines.clear()
        self.rubber_point = None
        self.closed = False
        self.update()

    def get_sketch(self) -> dict:
        origin_points = [self._widget_to_origin(p) for p in self.points]
        xs = [float(p.x()) for p in origin_points]
        ys = [float(p.y()) for p in origin_points]
        width = max(xs) - min(xs) if xs else 0.0
        height = max(ys) - min(ys) if ys else 0.0
        line_lengths = [self._distance(self.points[start], self.points[end]) for start, end in self.lines]
        return {
            "type": "polyline",
            "points": [(float(p.x()), float(p.y())) for p in origin_points],
            "lines": [[start, end] for start, end in self.lines],
            "line_lengths": [float(length) for length in line_lengths],
            "constraints": [self._serialize_constraint(constraint) for constraint in self.constraints],
            "width": width,
            "height": height,
            "closed": self.closed,
            "dimensioned": self.closed,
        }

    def load_sketch(self, sketch: dict) -> None:
        self.points = [self._origin_to_widget(QPointF(float(x), float(y))) for x, y in sketch.get("points", [])]
        self.lines = [(int(start), int(end)) for start, end in sketch.get("lines", [])]
        self.constraints = [self._deserialize_constraint(constraint) for constraint in sketch.get("constraints", [])]
        self.closed = sketch.get("closed", False)
        self.rubber_point = None
        self._apply_constraints()
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        pos = event.position()
        point = QPointF(pos.x(), pos.y())

        if self.current_tool == "measure" and self.points and self.lines:
            point_index = self._find_point_for_click(point)
            if point_index is not None:
                self._set_point_coordinates(point_index)
                return
            selected_line = self._find_line_for_point(point)
            if selected_line is not None:
                start_idx, end_idx = selected_line
                self._set_line_length(start_idx, end_idx)
            return

        if self.current_tool == "constraint" and self.points and self.lines:
            point_index = self._find_point_for_click(point)
            line_index = self._find_line_index_for_click(point)
            if self.constraint_selection is None:
                if point_index is not None:
                    self.constraint_selection = ("point", point_index)
                    self.update()
                    return
                if line_index is not None and self.constraint_mode in {"horizontal", "vertical"}:
                    self._add_line_direction_constraint(line_index, self.constraint_mode)
                    self._apply_constraints()
                    self.constraint_selection = None
                    self.update()
                    return
                if line_index is not None:
                    self.constraint_selection = ("line", line_index)
                    self.update()
                    return
                return

            sel_type, sel_index = self.constraint_selection
            if sel_type == "point" and point_index is not None and point_index != sel_index:
                self._add_coincident_constraint(sel_index, point_index)
                self._apply_constraints()
                self.constraint_selection = None
                self.update()
                return
            if sel_type == "point" and line_index is not None:
                self._add_point_to_line_constraint(sel_index, self.lines[line_index])
                self._apply_constraints()
                self.constraint_selection = None
                self.update()
                return
            if sel_type == "line" and point_index is not None:
                self._add_point_to_line_constraint(point_index, self.lines[sel_index])
                self._apply_constraints()
                self.constraint_selection = None
                self.update()
                return
            if sel_type == "line" and line_index is not None and self.constraint_mode in {"horizontal", "vertical"}:
                self._add_line_direction_constraint(line_index, self.constraint_mode)
                self._apply_constraints()
                self.constraint_selection = None
                self.update()
                return
            return

        if self.points and self.current_tool == "line":
            if self._is_close_to_first_point(point) and len(self.points) >= 3:
                self.lines.append((len(self.points) - 1, 0))
                self.closed = True
                self.rubber_point = None
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
        else:
            self.points.append(point)
        self.rubber_point = None
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        if self.points:
            self.rubber_point = QPointF(pos.x(), pos.y())
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

    def _add_coincident_constraint(self, p1_idx: int, p2_idx: int) -> None:
        self.constraints.append({
            "type": "coincident",
            "points": [p1_idx, p2_idx],
        })

    def _add_point_to_line_constraint(self, point_idx: int, line: tuple[int, int]) -> None:
        self.constraints.append({
            "type": "point_on_line",
            "point": point_idx,
            "line": line,
        })

    def _add_line_direction_constraint(self, line_index: int, direction: str) -> None:
        self.constraints.append({
            "type": "line_direction",
            "line_index": line_index,
            "direction": direction,
        })

    def _apply_constraints(self) -> None:
        for constraint in self.constraints:
            if constraint["type"] == "coincident":
                p1, p2 = constraint["points"]
                if 0 <= p1 < len(self.points) and 0 <= p2 < len(self.points):
                    self.points[p2] = QPointF(self.points[p1])
            elif constraint["type"] == "point_on_line":
                point_idx = constraint["point"]
                start_idx, end_idx = constraint["line"]
                if 0 <= point_idx < len(self.points) and 0 <= start_idx < len(self.points) and 0 <= end_idx < len(self.points):
                    pt = self.points[point_idx]
                    a = self.points[start_idx]
                    b = self.points[end_idx]
                    if a != b:
                        t = ((pt.x() - a.x()) * (b.x() - a.x()) + (pt.y() - a.y()) * (b.y() - a.y())) / ((b.x() - a.x())**2 + (b.y() - a.y())**2)
                        t = max(0.0, min(1.0, t))
                        self.points[point_idx] = QPointF(a.x() + t * (b.x() - a.x()), a.y() + t * (b.y() - a.y()))
            elif constraint["type"] == "line_direction":
                line_idx = constraint["line_index"]
                direction = constraint["direction"]
                if 0 <= line_idx < len(self.lines):
                    start_idx, end_idx = self.lines[line_idx]
                    a = self.points[start_idx]
                    b = self.points[end_idx]
                    if direction == "horizontal":
                        self.points[end_idx] = QPointF(b.x(), a.y())
                    elif direction == "vertical":
                        self.points[end_idx] = QPointF(a.x(), b.y())

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
        marker_pen.setWidth(4)
        painter.setPen(marker_pen)
        for constraint in self.constraints:
            if constraint["type"] == "coincident":
                p1, p2 = constraint["points"]
                if 0 <= p1 < len(self.points) and 0 <= p2 < len(self.points):
                    mid = QPointF((self.points[p1].x() + self.points[p2].x()) / 2,
                                  (self.points[p1].y() + self.points[p2].y()) / 2)
                    painter.drawPoint(mid)
            elif constraint["type"] == "point_on_line":
                point_idx = constraint["point"]
                start_idx, end_idx = constraint["line"]
                if 0 <= point_idx < len(self.points) and 0 <= start_idx < len(self.points) and 0 <= end_idx < len(self.points):
                    painter.drawPoint(self.points[point_idx])
            elif constraint["type"] == "line_direction":
                line_idx = constraint["line_index"]
                if 0 <= line_idx < len(self.lines):
                    start_idx, end_idx = self.lines[line_idx]
                    painter.drawLine(self.points[start_idx], self.points[end_idx])

    def _set_point_coordinates(self, point_index: int) -> None:
        origin_point = self._widget_to_origin(self.points[point_index])
        x_value, ok_x = QInputDialog.getDouble(self, "Set Point X", "X coordinate from origin:", float(origin_point.x()), -1000.0, 1000.0, 2)
        if not ok_x:
            return
        y_value, ok_y = QInputDialog.getDouble(self, "Set Point Y", "Y coordinate from origin:", float(origin_point.y()), -1000.0, 1000.0, 2)
        if not ok_y:
            return
        self.points[point_index] = self._origin_to_widget(QPointF(x_value, y_value))
        self._apply_constraints()
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
        self._apply_constraints()
        self.update()

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

        line_pen = QPen(QColor(220, 220, 220))
        line_pen.setWidth(2)
        painter.setPen(line_pen)

        for idx, (start_idx, end_idx) in enumerate(self.lines):
            start = self.points[start_idx]
            end = self.points[end_idx]
            if any(c.get("type") == "line_direction" and c.get("line_index") == idx for c in self.constraints):
                direction_pen = QPen(QColor(100, 255, 100))
                direction_pen.setWidth(3)
                painter.setPen(direction_pen)
                painter.drawLine(start, end)
                painter.setPen(line_pen)
            else:
                painter.drawLine(start, end)

        self._draw_constraint_markers(painter)

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

        point_pen = QPen(QColor(255, 165, 0))
        point_pen.setWidth(6)
        painter.setPen(point_pen)

        for point in self.points:
            painter.drawPoint(point)

        if self.rubber_point is not None:
            preview_pen = QPen(QColor(160, 160, 160))
            preview_pen.setWidth(4)
            painter.setPen(preview_pen)
            painter.drawPoint(self.rubber_point)
