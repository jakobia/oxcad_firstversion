"""
geometry_engine.py - Core geometry engine using CadQuery

Provides interface to CadQuery modeling and scene management.
"""

import cadquery as cq
from cadquery import Workplane
from typing import Optional


class GeometryEngine:
    """
    Wrapper for CadQuery geometry operations and scene management.
    """
    def __init__(self) -> None:
        self.shapes = []  # type: list[TopoDS_Shape]

    def add_box(self, width: float, height: float, depth: float) -> Optional[object]:
        """
        Create and add a box to the scene.
        """
        if BRepPrimAPI_MakeBox is None:
            return None
        box = BRepPrimAPI_MakeBox(width, height, depth).Shape()
        self.shapes.append(box)
        return box

    def clear(self) -> None:
        """
        Remove all shapes from the scene.
        """
        self.shapes.clear()
