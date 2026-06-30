"""Extensible sketch constraint solver.

This initial solver applies constraints iteratively with deterministic rules.
It is intentionally modular so a future DOF-based solver can replace internals.
"""

from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from typing import Callable

from PySide6.QtCore import QPointF

from cadapp.constraints.constraint import Constraint
from cadapp.constraints.constraint_types import ConstraintType


EPSILON = 1e-9


class ConstraintSolver:
    """Simple iterative solver for sketch constraints."""

    def __init__(self) -> None:
        self._handlers: dict[ConstraintType, Callable] = {
            ConstraintType.COINCIDENT: self._solve_coincident,
            ConstraintType.HORIZONTAL: self._solve_horizontal,
            ConstraintType.VERTICAL: self._solve_vertical,
            ConstraintType.PARALLEL: self._solve_parallel,
            ConstraintType.PERPENDICULAR: self._solve_perpendicular,
            ConstraintType.TANGENT: self._solve_tangent,
            ConstraintType.EQUAL: self._solve_equal,
            ConstraintType.MIDPOINT: self._solve_midpoint,
            ConstraintType.CONCENTRIC: self._solve_concentric,
            ConstraintType.SYMMETRY: self._solve_symmetry,
            ConstraintType.DISTANCE: self._solve_distance,
            ConstraintType.LENGTH: self._solve_length,
            ConstraintType.RADIUS: self._solve_radius,
            ConstraintType.DIAMETER: self._solve_diameter,
            ConstraintType.ANGLE: self._solve_angle,
        }

    def solve(self, document, iterations: int = 3) -> None:
        """Solve all active constraints in the document."""

        constraints = [c for c in document.constraint_manager.all() if c.is_active()]
        if not constraints:
            return

        for _ in range(max(1, iterations)):
            for constraint in constraints:
                handler = self._handlers.get(constraint.constraint_type)
                if handler is not None:
                    handler(document, constraint)

    def _point(self, document, point_id: int) -> QPointF:
        return document.points[point_id]

    def _set_point(self, document, point_id: int, p: QPointF) -> None:
        document.points[point_id] = QPointF(p)

    def _line_points(self, document, line_id: int) -> tuple[int, int]:
        return document.lines[line_id]

    def _circular_entity(self, document, kind: str, entity_id: int) -> dict | None:
        if kind == "circle" and 0 <= entity_id < len(document.circles):
            return document.circles[entity_id]
        if kind == "arc" and 0 <= entity_id < len(document.arcs):
            return document.arcs[entity_id]
        return None

    def _line_vector(self, document, line_id: int) -> tuple[QPointF, QPointF, float, float, float]:
        p1_idx, p2_idx = self._line_points(document, line_id)
        p1 = self._point(document, p1_idx)
        p2 = self._point(document, p2_idx)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = sqrt(dx * dx + dy * dy)
        return p1, p2, dx, dy, length

    def _arc_endpoints(self, arc: dict) -> tuple[QPointF, QPointF]:
        center = QPointF(arc["center"])
        radius = float(arc.get("radius", 0.0))
        start_angle = radians(float(arc.get("start_angle", 0.0)))
        end_angle = radians(float(arc.get("start_angle", 0.0)) + float(arc.get("span_angle", 0.0)))
        start = QPointF(center.x() + cos(start_angle) * radius, center.y() - sin(start_angle) * radius)
        end = QPointF(center.x() + cos(end_angle) * radius, center.y() - sin(end_angle) * radius)
        return start, end

    def _safe_normalize(self, dx: float, dy: float) -> tuple[float, float] | None:
        d = sqrt(dx * dx + dy * dy)
        if d <= EPSILON:
            return None
        return dx / d, dy / d

    def _solve_coincident(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 2:
            return
        a, b = constraint.references
        if a.kind == "point" and b.kind == "point":
            self._set_point(document, b.entity_id, self._point(document, a.entity_id))

    def _solve_horizontal(self, document, constraint: Constraint) -> None:
        if not constraint.references:
            return
        line_ref = constraint.references[0]
        if line_ref.kind != "line":
            return
        p1_idx, p2_idx = self._line_points(document, line_ref.entity_id)
        p1 = self._point(document, p1_idx)
        p2 = self._point(document, p2_idx)
        self._set_point(document, p2_idx, QPointF(p2.x(), p1.y()))

    def _solve_vertical(self, document, constraint: Constraint) -> None:
        if not constraint.references:
            return
        line_ref = constraint.references[0]
        if line_ref.kind != "line":
            return
        p1_idx, p2_idx = self._line_points(document, line_ref.entity_id)
        p1 = self._point(document, p1_idx)
        p2 = self._point(document, p2_idx)
        self._set_point(document, p2_idx, QPointF(p1.x(), p2.y()))

    def _solve_parallel(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 2:
            return
        l1, l2 = constraint.references
        if l1.kind != "line" or l2.kind != "line":
            return

        _, _, dx1, dy1, len1 = self._line_vector(document, l1.entity_id)
        p21, _, _, _, len2 = self._line_vector(document, l2.entity_id)
        if len1 <= EPSILON or len2 <= EPSILON:
            return
        ux = dx1 / len1
        uy = dy1 / len1
        p2_idx = self._line_points(document, l2.entity_id)[1]
        self._set_point(document, p2_idx, QPointF(p21.x() + ux * len2, p21.y() + uy * len2))

    def _solve_perpendicular(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 2:
            return
        l1, l2 = constraint.references
        if l1.kind != "line" or l2.kind != "line":
            return

        _, _, dx1, dy1, len1 = self._line_vector(document, l1.entity_id)
        p21, _, _, _, len2 = self._line_vector(document, l2.entity_id)
        if len1 <= EPSILON or len2 <= EPSILON:
            return

        ux = -dy1 / len1
        uy = dx1 / len1
        p2_idx = self._line_points(document, l2.entity_id)[1]
        self._set_point(document, p2_idx, QPointF(p21.x() + ux * len2, p21.y() + uy * len2))

    def _solve_tangent(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 2:
            return
        a, b = constraint.references

        if {a.kind, b.kind}.issubset({"line", "circle", "arc"}) and "line" in {a.kind, b.kind}:
            line_ref = a if a.kind == "line" else b
            circle_ref = a if a.kind in {"circle", "arc"} else b
            circle = self._circular_entity(document, circle_ref.kind, circle_ref.entity_id)
            if circle is None:
                return

            p1_idx, p2_idx = self._line_points(document, line_ref.entity_id)
            p1 = self._point(document, p1_idx)
            p2 = self._point(document, p2_idx)
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            dir_uv = self._safe_normalize(dx, dy)
            if dir_uv is None:
                return

            line_length = sqrt(dx * dx + dy * dy)
            ux, uy = dir_uv

            if circle_ref.kind == "arc":
                arc_start, arc_end = self._arc_endpoints(circle)
                use_end = False
                if constraint.parameters.get("arc_endpoint") in {"start", "end"}:
                    use_end = constraint.parameters.get("arc_endpoint") == "end"
                else:
                    # Default to nearest endpoint for stable interactive behavior.
                    use_end = (
                        (p1.x() - arc_end.x()) ** 2 + (p1.y() - arc_end.y()) ** 2
                        < (p1.x() - arc_start.x()) ** 2 + (p1.y() - arc_start.y()) ** 2
                    )
                tangent_point = arc_end if use_end else arc_start
                center = QPointF(circle["center"])
                rx = tangent_point.x() - center.x()
                ry = tangent_point.y() - center.y()
                radial_uv = self._safe_normalize(rx, ry)
                if radial_uv is None:
                    return
                # Tangent direction is perpendicular to radius at the endpoint.
                tx = -radial_uv[1]
                ty = radial_uv[0]
                if ux * tx + uy * ty < 0.0:
                    tx, ty = -tx, -ty
                self._set_point(document, p1_idx, tangent_point)
                self._set_point(document, p2_idx, QPointF(tangent_point.x() + tx * line_length, tangent_point.y() + ty * line_length))
                return

            center = QPointF(circle["center"])
            radius = float(circle["radius"])
            nx = -uy
            ny = ux
            candidates = [
                QPointF(center.x() + nx * radius, center.y() + ny * radius),
                QPointF(center.x() - nx * radius, center.y() - ny * radius),
            ]
            target = min(candidates, key=lambda c: (c.x() - p1.x()) ** 2 + (c.y() - p1.y()) ** 2)
            self._set_point(document, p1_idx, target)
            self._set_point(document, p2_idx, QPointF(target.x() + ux * line_length, target.y() + uy * line_length))
            return

        if a.kind in {"circle", "arc"} and b.kind in {"circle", "arc"}:
            c1 = self._circular_entity(document, a.kind, a.entity_id)
            c2 = self._circular_entity(document, b.kind, b.entity_id)
            if c1 is None or c2 is None:
                return
            p1 = c1["center"]
            p2 = c2["center"]
            r1 = float(c1["radius"])
            r2 = float(c2["radius"])
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            d = sqrt(dx * dx + dy * dy)
            if d <= EPSILON:
                dx, dy, d = 1.0, 0.0, 1.0
            ux = dx / d
            uy = dy / d
            c2["center"] = QPointF(p1.x() + ux * (r1 + r2), p1.y() + uy * (r1 + r2))

    def _solve_equal(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 2:
            return
        a, b = constraint.references

        if a.kind == "line" and b.kind == "line":
            _, _, dx2, dy2, len2 = self._line_vector(document, b.entity_id)
            _, _, _, _, len1 = self._line_vector(document, a.entity_id)
            if len2 <= EPSILON:
                return
            scale = len1 / len2
            p1_idx, p2_idx = self._line_points(document, b.entity_id)
            p1 = self._point(document, p1_idx)
            self._set_point(document, p2_idx, QPointF(p1.x() + dx2 * scale, p1.y() + dy2 * scale))
            return

        if a.kind in {"circle", "arc"} and b.kind in {"circle", "arc"}:
            e1 = self._circular_entity(document, a.kind, a.entity_id)
            e2 = self._circular_entity(document, b.kind, b.entity_id)
            if e1 is None or e2 is None:
                return
            r = float(e1["radius"])
            e2["radius"] = r

    def _solve_midpoint(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 2:
            return
        a, b = constraint.references
        point_ref = a if a.kind == "point" else b
        line_ref = a if a.kind == "line" else b
        if point_ref.kind != "point" or line_ref.kind != "line":
            return
        p1_idx, p2_idx = self._line_points(document, line_ref.entity_id)
        p1 = self._point(document, p1_idx)
        p2 = self._point(document, p2_idx)
        self._set_point(document, point_ref.entity_id, QPointF((p1.x() + p2.x()) / 2.0, (p1.y() + p2.y()) / 2.0))

    def _solve_concentric(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 2:
            return
        a, b = constraint.references
        if a.kind not in {"circle", "arc"} or b.kind not in {"circle", "arc"}:
            return
        e1 = self._circular_entity(document, a.kind, a.entity_id)
        e2 = self._circular_entity(document, b.kind, b.entity_id)
        if e1 is None or e2 is None:
            return
        center = QPointF(e1["center"])
        e2["center"] = center

    def _solve_symmetry(self, document, constraint: Constraint) -> None:
        if len(constraint.references) < 2:
            return
        axis_line_id = constraint.parameters.get("axis_line_id")
        if axis_line_id is None:
            return
        p1_idx, p2_idx = self._line_points(document, int(axis_line_id))
        a = self._point(document, p1_idx)
        b = self._point(document, p2_idx)
        dx = b.x() - a.x()
        dy = b.y() - a.y()
        length_sq = dx * dx + dy * dy
        if length_sq <= EPSILON:
            return

        refs = [ref for ref in constraint.references if ref.kind == "point"]
        if len(refs) != 2:
            return
        src = self._point(document, refs[0].entity_id)

        t = ((src.x() - a.x()) * dx + (src.y() - a.y()) * dy) / length_sq
        proj = QPointF(a.x() + t * dx, a.y() + t * dy)
        mirrored = QPointF(2 * proj.x() - src.x(), 2 * proj.y() - src.y())
        self._set_point(document, refs[1].entity_id, mirrored)

    def _solve_distance(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 2:
            return
        a, b = constraint.references
        if a.kind != "point" or b.kind != "point":
            return
        target = float(constraint.parameters.get("value", 0.0))
        p1 = self._point(document, a.entity_id)
        p2 = self._point(document, b.entity_id)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        d = sqrt(dx * dx + dy * dy)
        if d <= EPSILON:
            self._set_point(document, b.entity_id, QPointF(p1.x() + target, p1.y()))
            return
        self._set_point(document, b.entity_id, QPointF(p1.x() + dx * target / d, p1.y() + dy * target / d))

    def _solve_length(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 1 or constraint.references[0].kind != "line":
            return
        target = float(constraint.parameters.get("value", 0.0))
        line_id = constraint.references[0].entity_id
        p1, _, dx, dy, d = self._line_vector(document, line_id)
        p2_idx = self._line_points(document, line_id)[1]
        if d <= EPSILON:
            self._set_point(document, p2_idx, QPointF(p1.x() + target, p1.y()))
            return
        self._set_point(document, p2_idx, QPointF(p1.x() + dx * target / d, p1.y() + dy * target / d))

    def _solve_radius(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 1 or constraint.references[0].kind not in {"circle", "arc"}:
            return
        target = float(constraint.parameters.get("value", 0.0))
        entity = self._circular_entity(document, constraint.references[0].kind, constraint.references[0].entity_id)
        if entity is None:
            return
        entity["radius"] = max(0.0, target)

    def _solve_diameter(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 1 or constraint.references[0].kind not in {"circle", "arc"}:
            return
        target = float(constraint.parameters.get("value", 0.0))
        entity = self._circular_entity(document, constraint.references[0].kind, constraint.references[0].entity_id)
        if entity is None:
            return
        entity["radius"] = max(0.0, target / 2.0)

    def _solve_angle(self, document, constraint: Constraint) -> None:
        if len(constraint.references) != 2:
            return
        l1, l2 = constraint.references
        if l1.kind != "line" or l2.kind != "line":
            return

        desired_angle = radians(float(constraint.parameters.get("value", 0.0)))
        p1a, p1b = self._line_points(document, l1.entity_id)
        a1 = self._point(document, p1a)
        b1 = self._point(document, p1b)
        base_angle = atan2(b1.y() - a1.y(), b1.x() - a1.x())

        p2a, p2b = self._line_points(document, l2.entity_id)
        a2 = self._point(document, p2a)
        _, _, _, _, length = self._line_vector(document, l2.entity_id)
        if length <= EPSILON:
            return

        final_angle = base_angle + desired_angle
        new_end = QPointF(a2.x() + cos(final_angle) * length, a2.y() + sin(final_angle) * length)
        self._set_point(document, p2b, new_end)
