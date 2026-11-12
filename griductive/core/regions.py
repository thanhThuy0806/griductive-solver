"""Resolve structured regions in deterministic row-major order."""

from griductive.core.constants import RegionKind
from griductive.core.types import Region


def resolve_region(region: Region, size: int) -> tuple[str, ...]:
    """Return region cells, validating its fields and board references."""
    if type(size) is not int or size not in (3, 4, 5):
        raise ValueError("size: expected an integer in {3, 4, 5}")
    board = tuple(f"{chr(65 + col)}{row}" for row in range(1, size + 1)
                  for col in range(size))
    if region.kind == RegionKind.ROW:
        if region.of_cell is not None or region.cells is not None:
            raise ValueError("ROW: only index is allowed")
        if type(region.index) is not int or not 1 <= region.index <= size:
            raise ValueError(f"index: expected an integer in 1..{size}")
        return tuple(cell for cell in board if int(cell[1:]) == region.index)
    if region.kind == RegionKind.COL:
        if region.of_cell is not None or region.cells is not None:
            raise ValueError("COL: only index is allowed")
        if not isinstance(region.index, str) or region.index not in [
            chr(65 + col) for col in range(size)
        ]:
            raise ValueError(f"index: expected a column in A..{chr(64 + size)}")
        return tuple(cell for cell in board if cell[0] == region.index)
    if region.kind == RegionKind.NEIGHBORS:
        if region.index is not None or region.cells is not None:
            raise ValueError("NEIGHBORS: only of_cell is allowed")
        if region.of_cell not in board:
            raise ValueError("of: expected a cell on the board")
        col, row = ord(region.of_cell[0]), int(region.of_cell[1:])
        return tuple(cell for cell in board if cell != region.of_cell
                     and abs(ord(cell[0]) - col) <= 1 and abs(int(cell[1:]) - row) <= 1)
    if region.kind == RegionKind.CELLS:
        if region.index is not None or region.of_cell is not None:
            raise ValueError("CELLS: only cells is allowed")
        if not isinstance(region.cells, tuple) or any(cell not in board for cell in region.cells):
            raise ValueError("cells: expected a tuple of board cell identifiers")
        if len(set(region.cells)) != len(region.cells):
            raise ValueError("cells: duplicate cell identifiers")
        return tuple(cell for cell in board if cell in region.cells)
    raise ValueError("kind: unsupported region kind")
