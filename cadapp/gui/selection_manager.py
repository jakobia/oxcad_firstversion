"""Selection management for sketch entities and constraint availability."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from cadapp.constraints.constraint import GeometryRef
from cadapp.constraints.constraint_types import ConstraintType, available_constraints_for_selection


class SelectionManager(QObject):
    """Track sketch selections and expose available constraints."""

    selection_changed = Signal(list)
    available_constraints_changed = Signal(list)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._selection: list[GeometryRef] = []

    @property
    def selection(self) -> list[GeometryRef]:
        return list(self._selection)

    def clear(self) -> None:
        self._selection.clear()
        self._emit_changes()

    def select(self, item: GeometryRef, ctrl: bool = False, shift: bool = False) -> None:
        """Select an entity with Ctrl/Shift multi-select behavior."""

        if not ctrl and not shift:
            self._selection = [item]
            self._emit_changes()
            return

        if ctrl:
            if item in self._selection:
                self._selection.remove(item)
            else:
                self._selection.append(item)
            self._emit_changes()
            return

        if shift and item not in self._selection:
            self._selection.append(item)
            self._emit_changes()

    def get_available_constraints(self) -> list[ConstraintType]:
        kinds = [ref.kind for ref in self._selection]
        return available_constraints_for_selection(kinds)

    def _emit_changes(self) -> None:
        self.selection_changed.emit(self.selection)
        self.available_constraints_changed.emit(self.get_available_constraints())
