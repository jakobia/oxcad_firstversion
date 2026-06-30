"""Dataclasses for sketch constraints and geometry references."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from cadapp.constraints.constraint_types import ConstraintType


@dataclass(slots=True, frozen=True)
class GeometryRef:
    """Reference to a geometry entity in the sketch document."""

    kind: str
    entity_id: int


@dataclass(slots=True)
class Constraint:
    """A geometric or dimensional relation between sketch entities."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "Constraint"
    constraint_type: ConstraintType = ConstraintType.COINCIDENT
    references: list[GeometryRef] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    icon_id: str = ""
    enabled: bool = True
    suppressed: bool = False

    def is_active(self) -> bool:
        """Return True if the constraint should be solved."""

        return self.enabled and not self.suppressed
