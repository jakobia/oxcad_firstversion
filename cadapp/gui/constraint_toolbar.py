"""Constraint-specific toolbar with dynamic action enablement."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QToolBar

from cadapp.constraints.constraint_types import ConstraintType


class ConstraintToolbar(QToolBar):
    """Toolbar for creating geometric and dimensional constraints."""

    constraint_requested = Signal(object)

    _LABELS = {
        ConstraintType.COINCIDENT: "Coincident",
        ConstraintType.HORIZONTAL: "Horizontal",
        ConstraintType.VERTICAL: "Vertical",
        ConstraintType.PARALLEL: "Parallel",
        ConstraintType.PERPENDICULAR: "Perpendicular",
        ConstraintType.TANGENT: "Tangent",
        ConstraintType.EQUAL: "Equal",
        ConstraintType.MIDPOINT: "Midpoint",
        ConstraintType.CONCENTRIC: "Concentric",
        ConstraintType.SYMMETRY: "Symmetry",
        ConstraintType.DISTANCE: "Distance",
        ConstraintType.LENGTH: "Length",
        ConstraintType.RADIUS: "Radius",
        ConstraintType.DIAMETER: "Diameter",
        ConstraintType.ANGLE: "Angle",
    }

    _ICON_FILES = {
        ConstraintType.COINCIDENT: "constraint_coincident.svg",
        ConstraintType.HORIZONTAL: "constraint_horizontal.svg",
        ConstraintType.VERTICAL: "constraint_vertical.svg",
        ConstraintType.PARALLEL: "constraint_parallel.svg",
        ConstraintType.PERPENDICULAR: "constraint_perpendicular.svg",
        ConstraintType.TANGENT: "constraint_tangent.svg",
        ConstraintType.EQUAL: "constraint_equal.svg",
        ConstraintType.MIDPOINT: "constraint_midpoint.svg",
        ConstraintType.CONCENTRIC: "constraint_concentric.svg",
        ConstraintType.SYMMETRY: "constraint_symmetry.svg",
        ConstraintType.DISTANCE: "constraint_distance.svg",
        ConstraintType.LENGTH: "constraint_length.svg",
        ConstraintType.RADIUS: "constraint_radius.svg",
        ConstraintType.DIAMETER: "constraint_diameter.svg",
        ConstraintType.ANGLE: "constraint_angle.svg",
    }

    def __init__(self, parent=None) -> None:
        super().__init__("Constraints", parent)
        self.setMovable(True)
        self.setFloatable(False)
        self.setIconSize(QSize(20, 20))
        self.setToolButtonStyle(Qt.ToolButtonIconOnly)

        icons_dir = Path(__file__).resolve().parent.parent / "data" / "icons"

        self.actions_by_type: dict[ConstraintType, QAction] = {}
        for constraint_type in ConstraintType:
            icon_file = icons_dir / self._ICON_FILES[constraint_type]
            action = QAction(QIcon(str(icon_file)), self._LABELS[constraint_type], self)
            action.setEnabled(False)
            action.setToolTip(self._LABELS[constraint_type])
            action.triggered.connect(lambda checked=False, c=constraint_type: self.constraint_requested.emit(c))
            self.actions_by_type[constraint_type] = action
            self.addAction(action)

    def set_available(self, available: list[ConstraintType]) -> None:
        """Enable actions for currently valid selection signatures."""

        available_set = set(available)
        for constraint_type, action in self.actions_by_type.items():
            action.setEnabled(constraint_type in available_set)
