"""Sketch document model with observer notifications and constraint solving."""

from __future__ import annotations

from math import isclose

from PySide6.QtCore import QObject, QPointF, Signal

from cadapp.constraints.constraint_types import ConstraintType
from cadapp.constraints.constraint_manager import ConstraintManager
from cadapp.constraints.solver import ConstraintSolver


class SketchDocument(QObject):
    """In-memory sketch model shared by view, selection, and constraint logic."""

    geometry_changed = Signal()
    constraints_changed = Signal()
    solved = Signal()
    dof_status_changed = Signal(dict)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.points: list[QPointF] = []
        self.lines: list[tuple[int, int]] = []
        self.circles: list[dict] = []
        self.arcs: list[dict] = []

        self.constraint_manager = ConstraintManager(self)
        self.solver = ConstraintSolver()
        self.last_dof_status: dict = {
            "total_dof": 0,
            "removed_dof": 0,
            "remaining_dof": 0,
            "status": "under-constrained",
            "conflicts": [],
            "conflict_items": [],
        }

        self.constraint_manager.constraints_changed.connect(self.constraints_changed.emit)

    def clear(self) -> None:
        """Clear all geometry and constraints."""

        self.points.clear()
        self.lines.clear()
        self.circles.clear()
        self.arcs.clear()

        for constraint in list(self.constraint_manager.all()):
            self.constraint_manager.remove_constraint(constraint.id)

        self.geometry_changed.emit()
        self._emit_dof_status()

    def set_geometry(
        self,
        points: list[QPointF],
        lines: list[tuple[int, int]],
        circles: list[dict] | None = None,
        arcs: list[dict] | None = None,
    ) -> None:
        """Replace geometry payload from a sketch source."""

        self.points = [QPointF(p) for p in points]
        self.lines = [(int(a), int(b)) for a, b in lines]
        self.circles = [
            {
                "center": QPointF(circle.get("center", QPointF())),
                "radius": float(circle.get("radius", 0.0)),
            }
            for circle in (circles or [])
        ]
        self.arcs = [
            {
                "center": QPointF(arc.get("center", QPointF())),
                "radius": float(arc.get("radius", 0.0)),
                "start_angle": float(arc.get("start_angle", 0.0)),
                "span_angle": float(arc.get("span_angle", 90.0)),
            }
            for arc in (arcs or [])
        ]
        self.geometry_changed.emit()
        self._emit_dof_status()

    def solve_constraints(self) -> None:
        """Solve all active constraints and emit update events."""

        self.solver.solve(self)
        self.geometry_changed.emit()
        self._emit_dof_status()
        self.solved.emit()

    def _emit_dof_status(self) -> None:
        self.last_dof_status = self.compute_dof_status()
        self.dof_status_changed.emit(self.last_dof_status)

    def compute_dof_status(self) -> dict:
        """Compute a simple DOF/conflict indicator for the current sketch.

        This is a lightweight estimator used by the UI and can be replaced later
        by a full algebraic DOF analysis.
        """

        total_dof = len(self.points) * 2 + len(self.circles) * 3 + len(self.arcs) * 5
        active_constraints = [c for c in self.constraint_manager.all() if c.is_active()]

        dof_per_constraint = {
            ConstraintType.COINCIDENT: 2,
            ConstraintType.HORIZONTAL: 1,
            ConstraintType.VERTICAL: 1,
            ConstraintType.PARALLEL: 1,
            ConstraintType.PERPENDICULAR: 1,
            ConstraintType.TANGENT: 1,
            ConstraintType.EQUAL: 1,
            ConstraintType.MIDPOINT: 2,
            ConstraintType.CONCENTRIC: 2,
            ConstraintType.SYMMETRY: 2,
            ConstraintType.DISTANCE: 1,
            ConstraintType.LENGTH: 1,
            ConstraintType.RADIUS: 1,
            ConstraintType.DIAMETER: 1,
            ConstraintType.ANGLE: 1,
        }
        removed_dof = sum(dof_per_constraint.get(c.constraint_type, 0) for c in active_constraints)
        remaining_dof = total_dof - removed_dof

        conflict_items = self._find_conflicts(active_constraints)
        conflicts = [item["reason"] for item in conflict_items]
        status = "under-constrained"
        if remaining_dof == 0 and not conflicts:
            status = "fully-constrained"
        elif remaining_dof < 0 or conflicts:
            status = "over-constrained"

        return {
            "total_dof": total_dof,
            "removed_dof": removed_dof,
            "remaining_dof": remaining_dof,
            "status": status,
            "conflicts": conflicts,
            "conflict_items": conflict_items,
        }

    def _find_conflicts(self, active_constraints: list) -> list[dict]:
        conflicts: list[dict] = []

        distance_map: dict[tuple[int, int], tuple[float, str]] = {}
        length_map: dict[int, tuple[float, str]] = {}
        radius_map: dict[tuple[str, int], tuple[float, str]] = {}
        horizontal_lines: dict[int, list[str]] = {}
        vertical_lines: dict[int, list[str]] = {}
        length_ids_by_line: dict[int, list[str]] = {}

        def add_conflict(reason: str, constraint_ids: list[str]) -> None:
            unique_ids = [cid for cid in dict.fromkeys(constraint_ids) if cid]
            conflicts.append(
                {
                    "reason": reason,
                    "constraint_ids": unique_ids,
                }
            )

        for constraint in active_constraints:
            ctype = constraint.constraint_type
            refs = constraint.references
            params = constraint.parameters
            cid = constraint.id

            if ctype == ConstraintType.DISTANCE and len(refs) == 2 and refs[0].kind == "point" and refs[1].kind == "point":
                key = tuple(sorted((refs[0].entity_id, refs[1].entity_id)))
                value = float(params.get("value", 0.0))
                if key in distance_map and not isclose(distance_map[key][0], value, rel_tol=1e-6, abs_tol=1e-6):
                    add_conflict(
                        f"Distance mismatch for points {key[0]}-{key[1]}.",
                        [distance_map[key][1], cid],
                    )
                distance_map[key] = (value, cid)

            if ctype == ConstraintType.LENGTH and refs and refs[0].kind == "line":
                line_id = refs[0].entity_id
                value = float(params.get("value", 0.0))
                if line_id in length_map and not isclose(length_map[line_id][0], value, rel_tol=1e-6, abs_tol=1e-6):
                    add_conflict(
                        f"Length mismatch on line {line_id}.",
                        [length_map[line_id][1], cid],
                    )
                length_map[line_id] = (value, cid)
                length_ids_by_line.setdefault(line_id, []).append(cid)

            if ctype in {ConstraintType.RADIUS, ConstraintType.DIAMETER} and refs:
                first = refs[0]
                if first.kind in {"circle", "arc"}:
                    key = (first.kind, first.entity_id)
                    radius_value = float(params.get("value", 0.0))
                    if ctype == ConstraintType.DIAMETER:
                        radius_value /= 2.0
                    if key in radius_map and not isclose(radius_map[key][0], radius_value, rel_tol=1e-6, abs_tol=1e-6):
                        add_conflict(
                            f"Radius mismatch on {first.kind} {first.entity_id}.",
                            [radius_map[key][1], cid],
                        )
                    radius_map[key] = (radius_value, cid)

            if ctype == ConstraintType.HORIZONTAL and refs and refs[0].kind == "line":
                horizontal_lines.setdefault(refs[0].entity_id, []).append(cid)
            if ctype == ConstraintType.VERTICAL and refs and refs[0].kind == "line":
                vertical_lines.setdefault(refs[0].entity_id, []).append(cid)

        for line_id in set(horizontal_lines).intersection(vertical_lines):
            if line_id in length_map and length_map[line_id][0] > 1e-6:
                add_conflict(
                    f"Line {line_id} is both horizontal and vertical with non-zero length.",
                    horizontal_lines[line_id] + vertical_lines[line_id] + length_ids_by_line.get(line_id, []),
                )

        return conflicts
