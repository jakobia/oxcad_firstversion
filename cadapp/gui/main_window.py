"""
main_window.py - Main application window for CAD app

Defines the main window, menus, toolbars, dock panels, and layout.
"""

from PySide6.QtWidgets import QMainWindow, QDockWidget, QStatusBar, QWidget, QVBoxLayout, QMenu, QMessageBox, QInputDialog, QTreeWidget, QTreeWidgetItem, QStackedWidget, QLabel
from PySide6.QtGui import QIcon, QAction, QUndoStack
from PySide6.QtCore import Qt
from cadapp.gui.viewport_3d import Viewport3D
from cadapp.gui.toolbar import CADToolbar
from cadapp.gui.sketch_canvas import SketchCanvas
from cadapp.gui.constraint_toolbar import ConstraintToolbar
from cadapp.gui.constraint_browser import ConstraintBrowser
from cadapp.constraints.constraint_types import ConstraintType


class MainWindow(QMainWindow):
    """
    Main application window for the CAD application.
    """
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OXCAD - Open CAD Application")
        self.resize(1400, 900)
        self._init_ui()

    def _init_ui(self) -> None:
        """
        Initialize the main UI components.
        """
        # Central stacked widget holding 3D viewport and sketch canvas
        self.central_stack = QStackedWidget(self)
        self.viewport = Viewport3D(self)
        self.sketch_canvas = SketchCanvas(self)
        self.central_stack.addWidget(self.viewport)
        self.central_stack.addWidget(self.sketch_canvas)
        self.setCentralWidget(self.central_stack)

        self.undo_stack = QUndoStack(self)
        self.sketch_canvas.set_undo_stack(self.undo_stack)

        # Toolbar
        self.toolbar = CADToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.new_action.triggered.connect(self.new_document)
        self.toolbar.sketch_action.triggered.connect(self.new_sketch)
        self.toolbar.extrude_action.triggered.connect(self.extrude_sketch)
        self.toolbar.edit_action.triggered.connect(self.edit_sketch)
        self.toolbar.select_tool_button.clicked.connect(self._set_select_tool)
        self.toolbar.line_tool_button.clicked.connect(self._set_line_tool)
        self.toolbar.point_tool_button.clicked.connect(self._set_point_tool)
        self.toolbar.circle_tool_button.clicked.connect(self._set_circle_tool)
        self.toolbar.arc_tool_button.clicked.connect(self._set_arc_tool)
        self.toolbar.constraint_tool_button.clicked.connect(self._set_constraint_tool)
        self.toolbar.measure_action.triggered.connect(self._set_measure_tool)
        self.toolbar.constraint_none_button.clicked.connect(self._set_constraint_free)
        self.toolbar.constraint_horizontal_button.clicked.connect(self._set_constraint_horizontal)
        self.toolbar.constraint_vertical_button.clicked.connect(self._set_constraint_vertical)

        self.constraint_toolbar = ConstraintToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.constraint_toolbar)
        self.constraint_toolbar.constraint_requested.connect(self._on_constraint_requested)
        self.sketch_canvas.available_constraints_changed.connect(self.constraint_toolbar.set_available)

        self.finish_sketch_action = QAction(QIcon(), "Finish Sketch", self)
        self.finish_sketch_action.triggered.connect(self.finish_sketch)
        self.toolbar.addAction(self.finish_sketch_action)

        self.action_new_document = QAction(QIcon(), "New Document", self)
        self.action_new_document.triggered.connect(self.new_document)
        self.action_new_sketch = QAction(QIcon(), "New Sketch", self)
        self.action_new_sketch.triggered.connect(self.new_sketch)
        self.action_finish_sketch = QAction(QIcon(), "Finish Sketch", self)
        self.action_finish_sketch.triggered.connect(self.finish_sketch)
        self.action_cancel_sketch = QAction(QIcon(), "Cancel Sketch", self)
        self.action_cancel_sketch.triggered.connect(self.cancel_sketch)
        self.action_extrude = QAction(QIcon(), "Extrude", self)
        self.action_extrude.triggered.connect(self.extrude_sketch)
        self.action_measure = QAction(QIcon(), "Dimension", self)
        self.action_measure.triggered.connect(self._set_measure_tool)
        self.action_edit_sketch = QAction(QIcon(), "Edit Sketch", self)
        self.action_edit_sketch.triggered.connect(self.edit_sketch)
        self.action_edit_sketch.setEnabled(False)
        self.action_view_reset = QAction(QIcon(), "Reset View", self)
        self.action_view_reset.triggered.connect(self.viewport.reset_view)
        self.action_undo = self.undo_stack.createUndoAction(self, "Undo")
        self.action_redo = self.undo_stack.createRedoAction(self, "Redo")

        self.action_constraint_free = QAction("Free", self, checkable=True)
        self.action_constraint_free.triggered.connect(self._set_constraint_free)
        self.action_constraint_horizontal = QAction("Horizontal", self, checkable=True)
        self.action_constraint_horizontal.triggered.connect(self._set_constraint_horizontal)
        self.action_constraint_vertical = QAction("Vertical", self, checkable=True)
        self.action_constraint_vertical.triggered.connect(self._set_constraint_vertical)

        # Left dock: Feature tree
        self.feature_tree = QDockWidget("Feature Tree", self)
        self.feature_tree_widget = QTreeWidget()
        self.feature_tree_widget.setHeaderLabels(["Name", "Type"])
        self.feature_tree_widget.setColumnCount(2)
        self.feature_tree_widget.setRootIsDecorated(True)
        self.feature_tree_widget.setAlternatingRowColors(True)
        self.feature_tree_widget.itemSelectionChanged.connect(self.on_feature_selected)
        self.feature_tree_widget.setUniformRowHeights(True)
        self.feature_tree.setWidget(self.feature_tree_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.feature_tree)

        # Right dock: Property panel
        self.property_panel = QDockWidget("Properties", self)
        self.property_widget = QWidget()
        self.property_layout = QVBoxLayout(self.property_widget)
        self.property_layout.setContentsMargins(8, 8, 8, 8)
        self.property_label = QLabel("Select a sketch or solid to view parameters.")
        self.property_label.setWordWrap(True)
        self.property_layout.addWidget(self.property_label)
        self.property_panel.setWidget(self.property_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.property_panel)

        self.constraint_browser = ConstraintBrowser(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.constraint_browser)
        self.constraint_browser.suppress_requested.connect(self.sketch_canvas.toggle_suppress_constraint)
        self.constraint_browser.delete_requested.connect(self.sketch_canvas.delete_constraint)
        self.constraint_browser.rename_requested.connect(self.sketch_canvas.rename_constraint)
        self.constraint_browser.edit_requested.connect(self.sketch_canvas.edit_constraint)
        self.sketch_canvas.constraints_changed.connect(self._refresh_constraint_browser)

        # Bottom dock: Console/status (placeholder)
        self.console = QDockWidget("Console", self)
        self.console.setWidget(QWidget())
        self.addDockWidget(Qt.BottomDockWidgetArea, self.console)

        # Status bar
        self.setStatusBar(QStatusBar(self))
        self.dof_status_label = QLabel("DOF: 0 | under-constrained")
        self.statusBar().addPermanentWidget(self.dof_status_label)
        self.sketch_canvas.dof_status_changed.connect(self._update_dof_status)

        self.current_sketch = None
        self.current_sketch_item = None
        self._setup_feature_tree()
        self._set_line_tool()
        self._set_constraint_free()
        self._update_dof_status(self.sketch_canvas.document.last_dof_status)
        self._create_menus()

    def _setup_feature_tree(self) -> None:
        self.feature_tree_widget.clear()
        self.root_item = QTreeWidgetItem(["Document", "Root"])
        self.feature_tree_widget.addTopLevelItem(self.root_item)
        self.feature_tree_widget.expandAll()

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self.action_new_document)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools2d_menu = menu_bar.addMenu("2D Tools")
        sketch_menu = tools2d_menu.addMenu("Sketch")
        sketch_menu.addAction(self.action_new_sketch)
        sketch_menu.addAction(self.action_finish_sketch)
        sketch_menu.addAction(self.action_cancel_sketch)
        sketch_menu.addAction(self.action_edit_sketch)
        sketch_menu.addAction(self.action_measure)

        constraint_menu = tools2d_menu.addMenu("Constraints")
        constraint_menu.addAction(self.action_constraint_free)
        constraint_menu.addAction(self.action_constraint_horizontal)
        constraint_menu.addAction(self.action_constraint_vertical)

        tools3d_menu = menu_bar.addMenu("3D Tools")
        tools3d_menu.addAction(self.action_extrude)

        view_menu = menu_bar.addMenu("View")
        view_menu.addAction(self.action_view_reset)
        view_menu.addSeparator()
        view_menu.addAction(self.action_undo)
        view_menu.addAction(self.action_redo)

        self.action_constraint_free.setChecked(True)

    def _clear_feature_tree(self) -> None:
        self._setup_feature_tree()

    def _add_sketch_feature(self, sketch: dict) -> None:
        if sketch["type"] == "rectangle":
            sketch_name = "Rectangle Sketch"
        elif sketch["type"] == "circle":
            sketch_name = "Circle Sketch"
        else:
            sketch_name = "Polyline Sketch"
        sketch_item = QTreeWidgetItem([sketch_name, "Sketch"])
        sketch_item.setData(0, Qt.UserRole, "sketch")
        self.root_item.addChild(sketch_item)
        self.feature_tree_widget.expandAll()
        self.current_sketch_item = sketch_item

    def _add_solid_feature(self, sketch: dict, depth: float) -> None:
        solid_name = "Extruded Rectangle" if sketch["type"] == "rectangle" else "Extruded Circle"
        solid_item = QTreeWidgetItem([solid_name, "Solid"])
        solid_item.setData(0, Qt.UserRole, "solid")
        if self.current_sketch_item:
            self.current_sketch_item.addChild(solid_item)
            self.current_sketch_item.setExpanded(True)
        else:
            self.root_item.addChild(solid_item)
        self.feature_tree_widget.expandAll()

    def on_feature_selected(self) -> None:
        selected_items = self.feature_tree_widget.selectedItems()
        if not selected_items:
            self.action_edit_sketch.setEnabled(False)
            self._update_properties(None)
            return
        item = selected_items[0]
        feature_type = item.data(0, Qt.UserRole)
        if feature_type == "sketch":
            self.statusBar().showMessage(f"Selected sketch: {item.text(0)}")
            self.action_edit_sketch.setEnabled(True)
            self._update_properties(self.current_sketch)
        elif feature_type == "solid":
            self.statusBar().showMessage(f"Selected solid: {item.text(0)}")
            self.action_edit_sketch.setEnabled(False)
            self._update_properties(self.current_sketch)
        else:
            self.statusBar().showMessage("Selected document root")
            self.action_edit_sketch.setEnabled(False)
            self._update_properties(None)

    def new_document(self) -> None:
        """Start a new CAD document and clear the current scene."""
        self.viewport._clear_scene()
        self._clear_feature_tree()
        self.current_sketch = None
        self.current_sketch_item = None
        self.sketch_canvas.clear()
        self.sketch_canvas.hide()
        self.action_edit_sketch.setEnabled(False)
        self.central_stack.setCurrentWidget(self.viewport)
        self._update_properties(None)
        self.statusBar().showMessage("New document created. Use Sketch to create a profile. Drag to rotate, scroll to zoom.")

    def _set_line_tool(self) -> None:
        self.sketch_canvas.set_tool("line")
        self.toolbar.select_tool_button.setChecked(False)
        self.toolbar.line_tool_button.setChecked(True)
        self.toolbar.point_tool_button.setChecked(False)
        self.toolbar.circle_tool_button.setChecked(False)
        self.toolbar.arc_tool_button.setChecked(False)
        self.toolbar.constraint_tool_button.setChecked(False)

    def _set_point_tool(self) -> None:
        self.sketch_canvas.set_tool("point")
        self.toolbar.select_tool_button.setChecked(False)
        self.toolbar.point_tool_button.setChecked(True)
        self.toolbar.line_tool_button.setChecked(False)
        self.toolbar.circle_tool_button.setChecked(False)
        self.toolbar.arc_tool_button.setChecked(False)
        self.toolbar.constraint_tool_button.setChecked(False)

    def _set_circle_tool(self) -> None:
        self.sketch_canvas.set_tool("circle")
        self.toolbar.select_tool_button.setChecked(False)
        self.toolbar.circle_tool_button.setChecked(True)
        self.toolbar.line_tool_button.setChecked(False)
        self.toolbar.point_tool_button.setChecked(False)
        self.toolbar.arc_tool_button.setChecked(False)
        self.toolbar.constraint_tool_button.setChecked(False)

    def _set_arc_tool(self) -> None:
        self.sketch_canvas.set_tool("arc")
        self.toolbar.select_tool_button.setChecked(False)
        self.toolbar.arc_tool_button.setChecked(True)
        self.toolbar.line_tool_button.setChecked(False)
        self.toolbar.point_tool_button.setChecked(False)
        self.toolbar.circle_tool_button.setChecked(False)
        self.toolbar.constraint_tool_button.setChecked(False)

    def _set_measure_tool(self) -> None:
        self.sketch_canvas.set_tool("measure")
        self.toolbar.select_tool_button.setChecked(False)
        self.toolbar.point_tool_button.setChecked(False)
        self.toolbar.line_tool_button.setChecked(False)
        self.toolbar.circle_tool_button.setChecked(False)
        self.toolbar.arc_tool_button.setChecked(False)
        self.toolbar.constraint_tool_button.setChecked(False)
        self.statusBar().showMessage("Dimension mode active: drag geometry to move free axes, click point/center for coordinates, line for length, circle/arc edge for radius.")

    def _set_constraint_tool(self) -> None:
        self.sketch_canvas.set_tool("constraint")
        self.toolbar.select_tool_button.setChecked(False)
        self.toolbar.point_tool_button.setChecked(False)
        self.toolbar.line_tool_button.setChecked(False)
        self.toolbar.circle_tool_button.setChecked(False)
        self.toolbar.arc_tool_button.setChecked(False)
        self.toolbar.constraint_tool_button.setChecked(True)
        self.statusBar().showMessage("Constraint mode active: select entities, then click a tool in the Constraint toolbar.")

    def _set_select_tool(self) -> None:
        self.sketch_canvas.set_tool("select")
        self.toolbar.select_tool_button.setChecked(True)
        self.toolbar.point_tool_button.setChecked(False)
        self.toolbar.line_tool_button.setChecked(False)
        self.toolbar.circle_tool_button.setChecked(False)
        self.toolbar.arc_tool_button.setChecked(False)
        self.toolbar.constraint_tool_button.setChecked(False)
        self.statusBar().showMessage("Select mode active: click geometry to select and drag to move without drawing.")

    def _set_constraint_free(self) -> None:
        self.sketch_canvas.set_constraint_mode("free")
        self.sketch_canvas.set_active_constraint_type(None)
        self.toolbar.constraint_none_button.setChecked(True)
        self.action_constraint_free.setChecked(True)
        self.action_constraint_horizontal.setChecked(False)
        self.action_constraint_vertical.setChecked(False)

    def _set_constraint_horizontal(self) -> None:
        self.sketch_canvas.set_constraint_mode("horizontal")
        self.sketch_canvas.set_active_constraint_type(ConstraintType.HORIZONTAL)
        self.toolbar.constraint_horizontal_button.setChecked(True)
        self.action_constraint_free.setChecked(False)
        self.action_constraint_horizontal.setChecked(True)
        self.action_constraint_vertical.setChecked(False)

    def _set_constraint_vertical(self) -> None:
        self.sketch_canvas.set_constraint_mode("vertical")
        self.sketch_canvas.set_active_constraint_type(ConstraintType.VERTICAL)
        self.toolbar.constraint_vertical_button.setChecked(True)
        self.action_constraint_free.setChecked(False)
        self.action_constraint_horizontal.setChecked(False)
        self.action_constraint_vertical.setChecked(True)

    def new_sketch(self) -> None:
        """Create a new 2D sketch profile for extrusion."""
        self.sketch_canvas.clear()
        self.sketch_canvas.show()
        self.central_stack.setCurrentWidget(self.sketch_canvas)
        self._refresh_constraint_browser()
        self.statusBar().showMessage("Sketch mode active: click to place points, shift or Constraint for horizontal/vertical lines.")

    def _on_constraint_requested(self, constraint_type: ConstraintType) -> None:
        self.sketch_canvas.apply_constraint(constraint_type)
        self._refresh_constraint_browser()

    def _refresh_constraint_browser(self) -> None:
        self.constraint_browser.refresh(
            self.sketch_canvas.document.constraint_manager.all(),
            self.sketch_canvas.document.last_dof_status,
        )

    def _update_dof_status(self, status: dict) -> None:
        state = status.get("status", "under-constrained")
        remaining = int(status.get("remaining_dof", 0))
        conflicts = status.get("conflicts", [])
        conflict_suffix = ""
        if conflicts:
            conflict_suffix = f" | conflicts: {len(conflicts)}"
        self.dof_status_label.setText(f"DOF: {remaining} | {state}{conflict_suffix}")
        self._refresh_constraint_browser()

    def finish_sketch(self) -> None:
        if not self.sketch_canvas.closed:
            QMessageBox.information(self, "Sketch Not Closed", "Close the sketch loop before finishing.")
            return

        sketch = self.sketch_canvas.get_sketch()
        if not sketch["points"]:
            QMessageBox.information(self, "No Sketch", "Draw a sketch first using the canvas.")
            return

        self.current_sketch = sketch
        self._add_sketch_feature(self.current_sketch)
        self.action_edit_sketch.setEnabled(True)
        self.central_stack.setCurrentWidget(self.viewport)
        self.sketch_canvas.hide()
        self.viewport.add_sketch_preview(self.current_sketch)
        self._update_properties(self.current_sketch)
        self.statusBar().showMessage("Sketch created. Press Extrude to turn it into a solid. Drag to orbit and scroll to zoom.")

    def cancel_sketch(self) -> None:
        self.sketch_canvas.clear()
        self.sketch_canvas.hide()
        self.action_edit_sketch.setEnabled(False)
        self.central_stack.setCurrentWidget(self.viewport)
        self._update_properties(None)
        self.statusBar().showMessage("Sketch cancelled.")

    def edit_sketch(self) -> None:
        if not self.current_sketch:
            QMessageBox.information(self, "No Sketch", "Create a sketch first before editing.")
            return
        self.sketch_canvas.show()
        self.central_stack.setCurrentWidget(self.sketch_canvas)
        self.sketch_canvas.load_sketch(self.current_sketch)
        self.statusBar().showMessage("Edit sketch: change dimensions or lines, then finish sketch.")

    def _update_properties(self, sketch: dict | None) -> None:
        if not sketch:
            self.property_label.setText("Select a sketch or solid to view parameters.")
            return
        if sketch["type"] == "polyline":
            width = sketch.get("width", 0.0)
            height = sketch.get("height", 0.0)
            points = len(sketch.get("points", []))
            self.property_label.setText(
                f"Sketch type: polyline\nPoints: {points}\nWidth: {width:.1f}\nHeight: {height:.1f}\nClosed: {sketch.get('closed', False)}"
            )
        elif sketch["type"] == "rectangle":
            self.property_label.setText(
                f"Sketch type: rectangle\nWidth: {sketch['width']:.1f}\nHeight: {sketch['height']:.1f}"
            )
        elif sketch["type"] == "circle":
            self.property_label.setText(
                f"Sketch type: circle\nRadius: {sketch['radius']:.1f}\nDiameter: {2*sketch['radius']:.1f}"
            )
        else:
            self.property_label.setText("Unknown sketch type")

    def extrude_sketch(self) -> None:
        """Extrude the current sketch into a 3D solid."""
        if not self.current_sketch:
            QMessageBox.information(self, "No Sketch", "Create a sketch first using the Sketch button.")
            return

        depth, ok = QInputDialog.getDouble(self, "Extrude Depth", "Enter extrusion depth:", 10.0, 0.1, 1000.0, 2)
        if not ok:
            return

        self.viewport._clear_scene()
        sketch = self.current_sketch
        if sketch["type"] == "rectangle":
            self.viewport.add_box(sketch["width"], sketch["height"], depth)
        elif sketch["type"] == "circle":
            self.viewport.add_cylinder(sketch["radius"], depth)
        elif sketch["type"] == "polyline":
            if not sketch.get("lines") or len(sketch.get("points", [])) < 4:
                QMessageBox.information(self, "Invalid Sketch", "The sketch must be a closed loop before extrusion.")
                return
            self.viewport.add_polyline_extrusion(sketch, depth)
        else:
            QMessageBox.warning(self, "Unsupported Sketch", "This sketch type cannot be extruded yet.")
            return

        self._add_solid_feature(sketch, depth)
        self.statusBar().showMessage("Sketch extruded to solid.")
