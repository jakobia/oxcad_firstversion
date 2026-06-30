"""Constraint collection manager with observer-style change notifications."""

from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QObject, Signal

from cadapp.constraints.constraint import Constraint


class ConstraintManager(QObject):
    """Store and mutate sketch constraints."""

    constraint_added = Signal(object)
    constraint_removed = Signal(str)
    constraint_updated = Signal(object)
    constraints_changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._constraints: dict[str, Constraint] = {}

    def all(self) -> list[Constraint]:
        """Return all constraints in insertion order."""

        return list(self._constraints.values())

    def get(self, constraint_id: str) -> Constraint | None:
        """Fetch one constraint by id."""

        return self._constraints.get(constraint_id)

    def add_constraint(self, constraint: Constraint) -> None:
        """Add a new constraint."""

        self._constraints[constraint.id] = constraint
        self.constraint_added.emit(constraint)
        self.constraints_changed.emit()

    def remove_constraint(self, constraint_id: str) -> Constraint | None:
        """Remove and return a constraint if it exists."""

        removed = self._constraints.pop(constraint_id, None)
        if removed is not None:
            self.constraint_removed.emit(constraint_id)
            self.constraints_changed.emit()
        return removed

    def update_constraint(self, constraint_id: str, **updates) -> Constraint | None:
        """Update mutable fields on a constraint."""

        existing = self._constraints.get(constraint_id)
        if existing is None:
            return None

        snapshot = deepcopy(existing)
        for field_name, value in updates.items():
            if hasattr(existing, field_name):
                setattr(existing, field_name, value)

        self.constraint_updated.emit(existing)
        self.constraints_changed.emit()
        return snapshot
