"""Constraint browser dock widget for managing sketch constraints."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDockWidget, QMenu, QTreeWidget, QTreeWidgetItem

from cadapp.constraints.constraint import Constraint


class ConstraintBrowser(QDockWidget):
    """Tree view of sketch constraints with context actions."""

    suppress_requested = Signal(str)
    delete_requested = Signal(str)
    edit_requested = Signal(str)
    rename_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__("Constraint Browser", parent)
        self.tree = QTreeWidget(self)
        self.tree.setHeaderLabels(["Constraint", "Type", "Status"])
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.setWidget(self.tree)

        self._sketch_item = QTreeWidgetItem(["Sketch001", "Sketch", "Active"])
        self._dof_item = QTreeWidgetItem(["DOF Status", "Diagnostics", "-"])
        self.tree.addTopLevelItem(self._sketch_item)
        self.tree.addTopLevelItem(self._dof_item)
        self.tree.expandAll()

    def refresh(self, constraints: list[Constraint], dof_status: dict | None = None) -> None:
        """Rebuild the browser list from constraint data."""

        self._sketch_item.takeChildren()
        for constraint in constraints:
            status = "Suppressed" if constraint.suppressed else "Enabled"
            item = QTreeWidgetItem([
                constraint.name,
                str(constraint.constraint_type),
                status,
            ])
            item.setData(0, Qt.UserRole, constraint.id)
            self._sketch_item.addChild(item)

        self._dof_item.takeChildren()
        dof_payload = dof_status or {}
        status_text = str(dof_payload.get("status", "under-constrained"))
        remaining = int(dof_payload.get("remaining_dof", 0))
        self._dof_item.setText(2, f"{status_text} ({remaining})")

        conflict_items = dof_payload.get("conflict_items", [])
        if conflict_items:
            for index, conflict in enumerate(conflict_items, start=1):
                reason = str(conflict.get("reason", "Unknown conflict"))
                ids = conflict.get("constraint_ids", [])
                id_text = ", ".join(ids) if ids else "-"
                child = QTreeWidgetItem([f"Conflict {index}", reason, id_text])
                self._dof_item.addChild(child)
        else:
            self._dof_item.addChild(QTreeWidgetItem(["No conflicts", "Model is consistent", "-"]))

        self.tree.expandAll()

    def _show_context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if item is None:
            return
        constraint_id = item.data(0, Qt.UserRole)
        if not constraint_id:
            return

        menu = QMenu(self)
        suppress_action = menu.addAction("Suppress / Unsuppress")
        rename_action = menu.addAction("Rename")
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")

        chosen = menu.exec(self.tree.mapToGlobal(pos))
        if chosen == suppress_action:
            self.suppress_requested.emit(constraint_id)
        elif chosen == rename_action:
            self.rename_requested.emit(constraint_id)
        elif chosen == edit_action:
            self.edit_requested.emit(constraint_id)
        elif chosen == delete_action:
            self.delete_requested.emit(constraint_id)
