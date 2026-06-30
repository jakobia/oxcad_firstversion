"""
viewport_3d.py - Embedded 3D viewport for CAD app

Uses CadQuery for 3D model visualization.
"""

from math import acos, degrees, sqrt
from math import acos, degrees, sqrt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QColor, QVector3D, QQuaternion

# Try CadQuery for modern Python-friendly CAD
try:
    import cadquery as cq
    from cadquery import Workplane
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False

# Try Qt3D as fallback
try:
    from PySide6.Qt3DCore import Qt3DCore
    from PySide6.Qt3DExtras import Qt3DExtras
    from PySide6.Qt3DRender import Qt3DRender
    QT3D_AVAILABLE = True
except ImportError:
    QT3D_AVAILABLE = False


class Viewport3D(QWidget):
    """
    3D viewport widget for the CAD application.

    Uses CadQuery as primary backend, falls back to simple visualization.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.root_entity = None
        self.object_entities = []
        self.current_preview_entity = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Try Qt3D first (more reliable), then CadQuery
        if QT3D_AVAILABLE:
            try:
                self._create_qt3d_view(layout)
                return
            except Exception as e:
                print(f"Qt3D Error: {e}")
        
        if CADQUERY_AVAILABLE:
            try:
                self._create_cadquery_view(layout)
                return
            except Exception as e:
                print(f"CadQuery Error: {e}")
        
        # Fallback message
        self._setup_fallback(layout)
        
        self.setLayout(layout)

    def _setup_fallback(self, layout: QVBoxLayout) -> None:
        """Display a fallback message when 3D backends are unavailable."""
        message = f"""
        No 3D Backend Available
        
        CadQuery Available: {CADQUERY_AVAILABLE}
        Qt3D Available: {QT3D_AVAILABLE}
        
        To fix: Run with virtual environment:
        .venv\\Scripts\\python -m cadapp.main
        """
        label = QLabel(message.strip())
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            color: #FFD700;
            background-color: #1a1a1a; 
            padding: 20px; 
            font-size: 11px;
            font-family: monospace;
            border: 1px solid #FF6347;
        """)
        layout.addWidget(label)

    def _create_cadquery_view(self, layout: QVBoxLayout) -> None:
        """Create a simple CadQuery visualization."""
        info_label = QLabel("CadQuery 3D Viewport\n\nCreate CAD objects using CadQuery\nexample usage in tools")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("""
            color: #CCCCCC; 
            background-color: #1a1a1a; 
            padding: 20px; 
            font-size: 12px;
            border: 1px solid #333333;
        """)
        layout.addWidget(info_label)
        
        # Create a simple default object
        self.workplane = Workplane("XY").box(10, 10, 10)

    def _create_qt3d_view(self, layout: QVBoxLayout) -> None:
        """Create the Qt3D view and root entity."""
        from PySide6 import QtCore
        
        self.view = Qt3DExtras.Qt3DWindow()
        self.view.defaultFrameGraph().setClearColor(QColor(25, 25, 25))
        container = self.createWindowContainer(self.view, self)
        container.setMinimumSize(640, 480)
        layout.addWidget(container)

        self.root_entity = Qt3DCore.QEntity()
        self.object_entities = []
        self._setup_camera()
        self._setup_light()
        self._create_default_geometry()
        self.view.setRootEntity(self.root_entity)

    def _clear_scene(self) -> None:
        """Remove all objects from the current Qt3D scene."""
        if not self.root_entity:
            return
        for child in list(self.root_entity.children()):
            child.setParent(None)
        self.object_entities = []
        self._clear_preview()

    def add_box(self, width: float, height: float, depth: float) -> None:
        """Add a cuboid to the Qt3D scene."""
        if not QT3D_AVAILABLE or not self.root_entity:
            return
        material = Qt3DExtras.QPhongMaterial(self.root_entity)
        material.setDiffuse(QColor(70, 130, 180))

        mesh = Qt3DExtras.QCuboidMesh()
        mesh.setXExtent(width)
        mesh.setYExtent(height)
        mesh.setZExtent(depth)

        cube_entity = Qt3DCore.QEntity(self.root_entity)
        cube_entity.addComponent(mesh)
        cube_entity.addComponent(material)
        self.object_entities.append(cube_entity)

    def add_sketch_preview(self, sketch: dict) -> None:
        """Add a 2D sketch preview to the Qt3D scene."""
        if not QT3D_AVAILABLE or not self.root_entity:
            return

        self._clear_preview()

        material = Qt3DExtras.QPhongMaterial(self.root_entity)
        material.setDiffuse(QColor(200, 200, 200))

        if sketch["type"] == "rectangle":
            mesh = Qt3DExtras.QCuboidMesh()
            mesh.setXExtent(sketch["width"])
            mesh.setYExtent(sketch["height"])
            mesh.setZExtent(0.1)
        elif sketch["type"] == "circle":
            mesh = Qt3DExtras.QCylinderMesh()
            mesh.setRadius(sketch["radius"])
            mesh.setLength(0.1)
        else:
            if sketch.get("closed") and len(sketch.get("points", [])) >= 4:
                polyline = sketch["points"]
                min_x = min(p[0] for p in polyline)
                max_x = max(p[0] for p in polyline)
                min_y = min(p[1] for p in polyline)
                max_y = max(p[1] for p in polyline)
                mesh = Qt3DExtras.QCuboidMesh()
                mesh.setXExtent(max(max_x - min_x, 1.0))
                mesh.setYExtent(max(max_y - min_y, 1.0))
                mesh.setZExtent(0.1)
            else:
                mesh = Qt3DExtras.QCuboidMesh()
                mesh.setXExtent(1.0)
                mesh.setYExtent(1.0)
                mesh.setZExtent(0.1)

        preview_entity = Qt3DCore.QEntity(self.root_entity)
        preview_entity.addComponent(mesh)
        preview_entity.addComponent(material)
        self.current_preview_entity = preview_entity

    def _clear_preview(self) -> None:
        if self.current_preview_entity is not None:
            self.current_preview_entity.setParent(None)
            self.current_preview_entity = None

    def add_cylinder(self, radius: float, height: float) -> None:
        """Add a cylinder to the Qt3D scene."""
        if not QT3D_AVAILABLE or not self.root_entity:
            return
        material = Qt3DExtras.QPhongMaterial(self.root_entity)
        material.setDiffuse(QColor(180, 130, 70))

        mesh = Qt3DExtras.QCylinderMesh()
        mesh.setRadius(radius)
        mesh.setLength(height)

        cylinder_entity = Qt3DCore.QEntity(self.root_entity)
        cylinder_entity.addComponent(mesh)
        cylinder_entity.addComponent(material)
        self.object_entities.append(cylinder_entity)

    def add_polyline_extrusion(self, sketch: dict, depth: float) -> None:
        """Add a simple extruded polyline approximation to the Qt3D scene."""
        if not QT3D_AVAILABLE or not self.root_entity:
            return
        if not sketch.get("points"):
            return

        material = Qt3DExtras.QPhongMaterial(self.root_entity)
        material.setDiffuse(QColor(120, 180, 240))

        mesh = Qt3DExtras.QCuboidMesh()
        xs = [float(p[0]) for p in sketch["points"]]
        ys = [float(p[1]) for p in sketch["points"]]
        width = max(xs) - min(xs) if xs else 1.0
        height = max(ys) - min(ys) if ys else 1.0
        mesh.setXExtent(max(width, 1.0))
        mesh.setYExtent(max(height, 1.0))
        mesh.setZExtent(depth)

        extrude_entity = Qt3DCore.QEntity(self.root_entity)
        extrude_entity.addComponent(mesh)
        extrude_entity.addComponent(material)
        self.object_entities.append(extrude_entity)

    def _setup_camera(self) -> None:
        """Setup Qt3D camera."""
        
        camera = self.view.camera()
        camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 1000.0)
        camera.setPosition(QVector3D(0.0, 0.0, 20.0))
        camera.setViewCenter(QVector3D(0.0, 0.0, 0.0))

        self.camera_controller = Qt3DExtras.QOrbitCameraController(self.root_entity)
        self.camera_controller.setLinearSpeed(50.0)
        self.camera_controller.setLookSpeed(180.0)
        self.camera_controller.setCamera(camera)

    def reset_view(self) -> None:
        """Reset the Qt3D camera to the default orientation."""
        if not QT3D_AVAILABLE or not hasattr(self, 'view'):
            return
        camera = self.view.camera()
        camera.setPosition(QVector3D(0.0, 0.0, 20.0))
        camera.setViewCenter(QVector3D(0.0, 0.0, 0.0))

    def _setup_light(self) -> None:
        """Setup Qt3D lighting."""
        light_entity = Qt3DCore.QEntity(self.root_entity)
        light = Qt3DRender.QPointLight(light_entity)
        light.setColor(QColor(255, 255, 255))
        light.setIntensity(1.2)
        light_entity.addComponent(light)

    def _create_default_geometry(self) -> None:
        """Create default Qt3D geometry."""
        material = Qt3DExtras.QPhongMaterial(self.root_entity)
        material.setDiffuse(QColor(70, 130, 180))

        mesh = Qt3DExtras.QCuboidMesh()
        mesh.setXExtent(4.0)
        mesh.setYExtent(4.0)
        mesh.setZExtent(4.0)

        cube_entity = Qt3DCore.QEntity(self.root_entity)
        cube_entity.addComponent(mesh)
        cube_entity.addComponent(material)
