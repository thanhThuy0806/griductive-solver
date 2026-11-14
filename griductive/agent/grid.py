"""Tiny grid helpers used by the Agent (Owner: A).

Cell ids follow docs/interface.md: column letter + row number, e.g. "A1", "C2".
Rows go top to bottom (1..N), columns left to right (A..).
"""
from __future__ import annotations

from string import ascii_uppercase


def row_major_cells(size: int) -> list[str]:
    """All cell ids in row-major order: A1, B1, C1, A2, B2, ..."""
    if not 1 <= size <= len(ascii_uppercase):
        raise ValueError(f"size must be between 1 and {len(ascii_uppercase)}, got {size}")
    return [f"{ascii_uppercase[c]}{r}" for r in range(1, size + 1) for c in range(size)]
