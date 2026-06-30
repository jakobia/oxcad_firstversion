"""Unit tests for OXCAD sketch constraints."""

from __future__ import annotations

from math import isclose

from PySide6.QtCore import QPointF

from cadapp.constraints.constraint import Constraint, GeometryRef
from cadapp.constraints.constraint_types import ConstraintType
from cadapp.core.sketch_document import SketchDocument


def _doc_with_two_lines() -> SketchDocument:
    doc = SketchDocument()
    doc.set_geometry(
        [QPointF(0, 0), QPointF(10, 2), QPointF(0, 3), QPointF(7, 8)],
        [(0, 1), (2, 3)],
    )
    return doc


def _doc_with_two_circles() -> SketchDocument:
    doc = SketchDocument()
    doc.set_geometry([QPointF(0, 0), QPointF(10, 0)], [])
    doc.circles = [
        {"center": QPointF(0, 0), "radius": 5.0},
        {"center": QPointF(10, 0), "radius": 3.0},
    ]
    return doc


def test_coincident_constraint() -> None:
    doc = SketchDocument()
    doc.set_geometry([QPointF(0, 0), QPointF(5, 5)], [])
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.COINCIDENT,
            references=[GeometryRef("point", 0), GeometryRef("point", 1)],
        )
    )
    doc.solve_constraints()
    assert doc.points[1] == doc.points[0]


def test_horizontal_constraint() -> None:
    doc = _doc_with_two_lines()
    doc.constraint_manager.add_constraint(
        Constraint(constraint_type=ConstraintType.HORIZONTAL, references=[GeometryRef("line", 0)])
    )
    doc.solve_constraints()
    p1 = doc.points[0]
    p2 = doc.points[1]
    assert isclose(p1.y(), p2.y(), abs_tol=1e-6)


def test_vertical_constraint() -> None:
    doc = _doc_with_two_lines()
    doc.constraint_manager.add_constraint(
        Constraint(constraint_type=ConstraintType.VERTICAL, references=[GeometryRef("line", 0)])
    )
    doc.solve_constraints()
    p1 = doc.points[0]
    p2 = doc.points[1]
    assert isclose(p1.x(), p2.x(), abs_tol=1e-6)


def test_parallel_constraint() -> None:
    doc = _doc_with_two_lines()
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.PARALLEL,
            references=[GeometryRef("line", 0), GeometryRef("line", 1)],
        )
    )
    doc.solve_constraints()
    a1, b1 = doc.lines[0]
    a2, b2 = doc.lines[1]
    dx1 = doc.points[b1].x() - doc.points[a1].x()
    dy1 = doc.points[b1].y() - doc.points[a1].y()
    dx2 = doc.points[b2].x() - doc.points[a2].x()
    dy2 = doc.points[b2].y() - doc.points[a2].y()
    assert isclose(dx1 * dy2 - dy1 * dx2, 0.0, abs_tol=1e-6)


def test_perpendicular_constraint() -> None:
    doc = _doc_with_two_lines()
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.PERPENDICULAR,
            references=[GeometryRef("line", 0), GeometryRef("line", 1)],
        )
    )
    doc.solve_constraints()
    a1, b1 = doc.lines[0]
    a2, b2 = doc.lines[1]
    dx1 = doc.points[b1].x() - doc.points[a1].x()
    dy1 = doc.points[b1].y() - doc.points[a1].y()
    dx2 = doc.points[b2].x() - doc.points[a2].x()
    dy2 = doc.points[b2].y() - doc.points[a2].y()
    assert isclose(dx1 * dx2 + dy1 * dy2, 0.0, abs_tol=1e-6)


def test_tangent_line_circle_constraint() -> None:
    doc = SketchDocument()
    doc.set_geometry([QPointF(2, 1), QPointF(6, 1)], [(0, 1)])
    doc.circles = [{"center": QPointF(0, 0), "radius": 2.0}]
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.TANGENT,
            references=[GeometryRef("line", 0), GeometryRef("circle", 0)],
        )
    )
    doc.solve_constraints()
    p = doc.points[0]
    d = ((p.x() - 0.0) ** 2 + (p.y() - 0.0) ** 2) ** 0.5
    assert isclose(d, 2.0, abs_tol=1e-6)


def test_equal_line_length_constraint() -> None:
    doc = _doc_with_two_lines()
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.EQUAL,
            references=[GeometryRef("line", 0), GeometryRef("line", 1)],
        )
    )
    doc.solve_constraints()
    a1, b1 = doc.lines[0]
    a2, b2 = doc.lines[1]
    l1 = ((doc.points[b1].x() - doc.points[a1].x()) ** 2 + (doc.points[b1].y() - doc.points[a1].y()) ** 2) ** 0.5
    l2 = ((doc.points[b2].x() - doc.points[a2].x()) ** 2 + (doc.points[b2].y() - doc.points[a2].y()) ** 2) ** 0.5
    assert isclose(l1, l2, abs_tol=1e-6)


def test_midpoint_constraint() -> None:
    doc = SketchDocument()
    doc.set_geometry([QPointF(0, 0), QPointF(10, 0), QPointF(3, 4)], [(0, 1)])
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.MIDPOINT,
            references=[GeometryRef("point", 2), GeometryRef("line", 0)],
        )
    )
    doc.solve_constraints()
    assert doc.points[2] == QPointF(5, 0)


def test_concentric_constraint() -> None:
    doc = _doc_with_two_circles()
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.CONCENTRIC,
            references=[GeometryRef("circle", 0), GeometryRef("circle", 1)],
        )
    )
    doc.solve_constraints()
    assert doc.circles[1]["center"] == doc.circles[0]["center"]


def test_symmetry_constraint() -> None:
    doc = SketchDocument()
    doc.set_geometry([QPointF(0, 0), QPointF(10, 0), QPointF(4, 3), QPointF(0, 0)], [(0, 1)])
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.SYMMETRY,
            references=[GeometryRef("point", 2), GeometryRef("point", 3)],
            parameters={"axis_line_id": 0},
        )
    )
    doc.solve_constraints()
    assert isclose(doc.points[3].x(), 4.0, abs_tol=1e-6)
    assert isclose(doc.points[3].y(), -3.0, abs_tol=1e-6)


def test_distance_constraint() -> None:
    doc = SketchDocument()
    doc.set_geometry([QPointF(0, 0), QPointF(3, 4)], [])
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.DISTANCE,
            references=[GeometryRef("point", 0), GeometryRef("point", 1)],
            parameters={"value": 10.0},
        )
    )
    doc.solve_constraints()
    p1, p2 = doc.points
    d = ((p2.x() - p1.x()) ** 2 + (p2.y() - p1.y()) ** 2) ** 0.5
    assert isclose(d, 10.0, abs_tol=1e-6)


def test_radius_constraint() -> None:
    doc = _doc_with_two_circles()
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.RADIUS,
            references=[GeometryRef("circle", 0)],
            parameters={"value": 12.0},
        )
    )
    doc.solve_constraints()
    assert isclose(doc.circles[0]["radius"], 12.0, abs_tol=1e-6)


def test_diameter_constraint() -> None:
    doc = _doc_with_two_circles()
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.DIAMETER,
            references=[GeometryRef("circle", 0)],
            parameters={"value": 14.0},
        )
    )
    doc.solve_constraints()
    assert isclose(doc.circles[0]["radius"], 7.0, abs_tol=1e-6)


def test_angle_constraint() -> None:
    doc = _doc_with_two_lines()
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.ANGLE,
            references=[GeometryRef("line", 0), GeometryRef("line", 1)],
            parameters={"value": 90.0},
        )
    )
    doc.solve_constraints()
    a1, b1 = doc.lines[0]
    a2, b2 = doc.lines[1]
    dx1 = doc.points[b1].x() - doc.points[a1].x()
    dy1 = doc.points[b1].y() - doc.points[a1].y()
    dx2 = doc.points[b2].x() - doc.points[a2].x()
    dy2 = doc.points[b2].y() - doc.points[a2].y()
    assert isclose(dx1 * dx2 + dy1 * dy2, 0.0, abs_tol=1e-6)


def test_tangent_circle_circle_constraint() -> None:
    doc = _doc_with_two_circles()
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.TANGENT,
            references=[GeometryRef("circle", 0), GeometryRef("circle", 1)],
        )
    )
    doc.solve_constraints()
    c1 = doc.circles[0]
    c2 = doc.circles[1]
    d = ((c2["center"].x() - c1["center"].x()) ** 2 + (c2["center"].y() - c1["center"].y()) ** 2) ** 0.5
    assert isclose(d, c1["radius"] + c2["radius"], abs_tol=1e-6)


def test_equal_circle_radius_constraint() -> None:
    doc = _doc_with_two_circles()
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.EQUAL,
            references=[GeometryRef("circle", 0), GeometryRef("circle", 1)],
        )
    )
    doc.solve_constraints()
    assert isclose(doc.circles[0]["radius"], doc.circles[1]["radius"], abs_tol=1e-6)


def test_radius_constraint_on_arc() -> None:
    doc = SketchDocument()
    doc.set_geometry([], [], [], [{"center": QPointF(0, 0), "radius": 4.0, "start_angle": 0.0, "span_angle": 90.0}])
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.RADIUS,
            references=[GeometryRef("arc", 0)],
            parameters={"value": 9.0},
        )
    )
    doc.solve_constraints()
    assert isclose(doc.arcs[0]["radius"], 9.0, abs_tol=1e-6)


def test_dof_conflict_detection() -> None:
    doc = SketchDocument()
    doc.set_geometry([QPointF(0, 0), QPointF(10, 0)], [(0, 1)])
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.HORIZONTAL,
            references=[GeometryRef("line", 0)],
        )
    )
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.VERTICAL,
            references=[GeometryRef("line", 0)],
        )
    )
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.LENGTH,
            references=[GeometryRef("line", 0)],
            parameters={"value": 10.0},
        )
    )
    doc.solve_constraints()
    status = doc.last_dof_status
    assert status["status"] == "over-constrained"
    assert status["conflicts"]
    assert status["conflict_items"]
    assert status["conflict_items"][0]["constraint_ids"]


def test_tangent_line_arc_endpoint_constraint() -> None:
    doc = SketchDocument()
    doc.set_geometry(
        [QPointF(6, 0), QPointF(10, 0)],
        [(0, 1)],
        [],
        [{"center": QPointF(0, 0), "radius": 5.0, "start_angle": 0.0, "span_angle": 90.0}],
    )
    doc.constraint_manager.add_constraint(
        Constraint(
            constraint_type=ConstraintType.TANGENT,
            references=[GeometryRef("line", 0), GeometryRef("arc", 0)],
            parameters={"arc_endpoint": "start"},
        )
    )
    doc.solve_constraints()

    start = doc.points[0]
    end = doc.points[1]
    assert isclose(start.x(), 5.0, abs_tol=1e-6)
    assert isclose(start.y(), 0.0, abs_tol=1e-6)

    radius_vec = (start.x() - 0.0, start.y() - 0.0)
    line_vec = (end.x() - start.x(), end.y() - start.y())
    dot = radius_vec[0] * line_vec[0] + radius_vec[1] * line_vec[1]
    assert isclose(dot, 0.0, abs_tol=1e-6)
