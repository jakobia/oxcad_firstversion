"""Constraint type definitions and selection-based availability rules."""

from __future__ import annotations

from enum import StrEnum


class ConstraintType(StrEnum):
    """Supported geometric and dimensional constraints."""

    COINCIDENT = "coincident"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"
    TANGENT = "tangent"
    EQUAL = "equal"
    MIDPOINT = "midpoint"
    CONCENTRIC = "concentric"
    SYMMETRY = "symmetry"
    DISTANCE = "distance"
    LENGTH = "length"
    RADIUS = "radius"
    DIAMETER = "diameter"
    ANGLE = "angle"


def available_constraints_for_selection(kinds: list[str]) -> list[ConstraintType]:
    """Return available constraints for a selection signature.

    Kinds are entity strings: point, line, circle, arc.
    """

    if len(kinds) == 1:
        if kinds[0] == "line":
            return [ConstraintType.HORIZONTAL, ConstraintType.VERTICAL, ConstraintType.LENGTH]
        if kinds[0] in {"circle", "arc"}:
            return [ConstraintType.RADIUS, ConstraintType.DIAMETER]
        return []

    if len(kinds) != 2:
        return []

    k1, k2 = sorted(kinds)
    pair = (k1, k2)

    mapping: dict[tuple[str, str], list[ConstraintType]] = {
        ("line", "line"): [
            ConstraintType.PARALLEL,
            ConstraintType.PERPENDICULAR,
            ConstraintType.EQUAL,
            ConstraintType.ANGLE,
            ConstraintType.SYMMETRY,
        ],
        ("point", "point"): [ConstraintType.COINCIDENT, ConstraintType.DISTANCE, ConstraintType.SYMMETRY],
        ("line", "point"): [ConstraintType.MIDPOINT, ConstraintType.COINCIDENT],
        ("circle", "line"): [ConstraintType.TANGENT],
        ("circle", "circle"): [ConstraintType.CONCENTRIC, ConstraintType.EQUAL, ConstraintType.TANGENT],
        ("arc", "line"): [ConstraintType.TANGENT],
        ("arc", "arc"): [ConstraintType.CONCENTRIC, ConstraintType.EQUAL, ConstraintType.TANGENT],
        ("arc", "circle"): [ConstraintType.CONCENTRIC, ConstraintType.EQUAL, ConstraintType.TANGENT],
    }
    return mapping.get(pair, [])
