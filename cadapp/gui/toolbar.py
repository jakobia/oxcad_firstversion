"""
toolbar.py - CAD toolbar for main window

Defines the main toolbar with basic CAD tools.
"""

from PySide6.QtWidgets import QToolBar, QToolButton, QButtonGroup
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QSize


class CADToolbar(QToolBar):
    """
    Main toolbar for CAD tools.
    """
    def __init__(self, parent=None) -> None:
        super().__init__("CAD Tools", parent)
        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QSize(24, 24))
        self._init_actions()

    def _init_actions(self) -> None:
        """
        Initialize toolbar actions.
        """
        # Placeholder icons and actions
        self.new_action = QAction(QIcon(), "New", self)
        self.open_action = QAction(QIcon(), "Open", self)
        self.save_action = QAction(QIcon(), "Save", self)
        self.sketch_action = QAction(QIcon(), "Sketch", self)
        self.extrude_action = QAction(QIcon(), "Extrude", self)
        self.measure_action = QAction(QIcon(), "Dimension", self)
        self.fillet_action = QAction(QIcon(), "Fillet", self)
        self.chamfer_action = QAction(QIcon(), "Chamfer", self)
        self.export_step_action = QAction(QIcon(), "Export STEP", self)
        self.export_stl_action = QAction(QIcon(), "Export STL", self)

        self.line_tool_button = QToolButton(self)
        self.line_tool_button.setText("Line")
        self.line_tool_button.setCheckable(True)
        self.line_tool_button.setChecked(True)

        self.point_tool_button = QToolButton(self)
        self.point_tool_button.setText("Point")
        self.point_tool_button.setCheckable(True)

        self.constraint_tool_button = QToolButton(self)
        self.constraint_tool_button.setText("Constraint")
        self.constraint_tool_button.setCheckable(True)

        self.tool_button_group = QButtonGroup(self)
        self.tool_button_group.setExclusive(True)
        self.tool_button_group.addButton(self.line_tool_button)
        self.tool_button_group.addButton(self.point_tool_button)
        self.tool_button_group.addButton(self.constraint_tool_button)

        self.constraint_none_button = QToolButton(self)
        self.constraint_none_button.setText("Free")
        self.constraint_none_button.setCheckable(True)
        self.constraint_none_button.setChecked(True)

        self.constraint_horizontal_button = QToolButton(self)
        self.constraint_horizontal_button.setText("Horizontal")
        self.constraint_horizontal_button.setCheckable(True)

        self.constraint_vertical_button = QToolButton(self)
        self.constraint_vertical_button.setText("Vertical")
        self.constraint_vertical_button.setCheckable(True)

        self.constraint_button_group = QButtonGroup(self)
        self.constraint_button_group.setExclusive(True)
        self.constraint_button_group.addButton(self.constraint_none_button)
        self.constraint_button_group.addButton(self.constraint_horizontal_button)
        self.constraint_button_group.addButton(self.constraint_vertical_button)

        self.addAction(self.new_action)
        self.addAction(self.open_action)
        self.addAction(self.save_action)
        self.addSeparator()
        self.addAction(self.sketch_action)
        self.addWidget(self.line_tool_button)
        self.addWidget(self.point_tool_button)
        self.addWidget(self.constraint_tool_button)
        self.addSeparator()
        self.addWidget(self.constraint_none_button)
        self.addWidget(self.constraint_horizontal_button)
        self.addWidget(self.constraint_vertical_button)
        self.addAction(self.extrude_action)
        self.addAction(self.measure_action)
        self.edit_action = QAction(QIcon(), "Edit", self)
        self.addAction(self.edit_action)
        self.addAction(self.fillet_action)
        self.addAction(self.chamfer_action)
        self.addSeparator()
        self.addAction(self.export_step_action)
        self.addAction(self.export_stl_action)
