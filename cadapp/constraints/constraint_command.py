"""Undo/redo commands for constraint edits."""

from __future__ import annotations

from copy import deepcopy

from PySide6.QtGui import QUndoCommand

from cadapp.constraints.constraint import Constraint


class AddConstraintCommand(QUndoCommand):
    """Add a constraint and support undo/redo."""

    def __init__(self, document, constraint: Constraint, text: str = "Add Constraint") -> None:
        super().__init__(text)
        self._document = document
        self._constraint = deepcopy(constraint)

    def redo(self) -> None:
        self._document.constraint_manager.add_constraint(deepcopy(self._constraint))
        self._document.solve_constraints()

    def undo(self) -> None:
        self._document.constraint_manager.remove_constraint(self._constraint.id)
        self._document.solve_constraints()


class RemoveConstraintCommand(QUndoCommand):
    """Remove a constraint and support undo/redo."""

    def __init__(self, document, constraint_id: str, text: str = "Remove Constraint") -> None:
        super().__init__(text)
        self._document = document
        self._constraint_id = constraint_id
        self._snapshot = None

    def redo(self) -> None:
        self._snapshot = self._document.constraint_manager.remove_constraint(self._constraint_id)
        self._document.solve_constraints()

    def undo(self) -> None:
        if self._snapshot is not None:
            self._document.constraint_manager.add_constraint(deepcopy(self._snapshot))
            self._document.solve_constraints()


class UpdateConstraintCommand(QUndoCommand):
    """Update a constraint and support undo/redo."""

    def __init__(self, document, constraint_id: str, updates: dict, text: str = "Update Constraint") -> None:
        super().__init__(text)
        self._document = document
        self._constraint_id = constraint_id
        self._updates = deepcopy(updates)
        self._old_snapshot = None

    def redo(self) -> None:
        self._old_snapshot = self._document.constraint_manager.update_constraint(self._constraint_id, **self._updates)
        self._document.solve_constraints()

    def undo(self) -> None:
        if self._old_snapshot is None:
            return
        self._document.constraint_manager.update_constraint(
            self._constraint_id,
            name=self._old_snapshot.name,
            constraint_type=self._old_snapshot.constraint_type,
            references=deepcopy(self._old_snapshot.references),
            parameters=deepcopy(self._old_snapshot.parameters),
            icon_id=self._old_snapshot.icon_id,
            enabled=self._old_snapshot.enabled,
            suppressed=self._old_snapshot.suppressed,
        )
        self._document.solve_constraints()
