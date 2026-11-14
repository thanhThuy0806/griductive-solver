"""Cell ids, the grid, and region resolution."""

import re
from typing import Callable, Dict, List, Tuple

from griductive.core.constants import MAX_GRID, RegionKind
from griductive.core.types import CellId, ClueError, Region

_CELL_RE = re.compile(r"[A-Z][0-9]+")
_RESOLVERS: Dict[RegionKind, Callable[[Region, int], List[CellId]]] = {}


def cell_id(row: int, col: int) -> CellId:
    """Convert 0-based (row, col) to an id such as 'A1'."""
    return f"{chr(ord('A') + col)}{row + 1}"


def parse_cell(cid: CellId, n: int) -> Tuple[int, int]:
    """Convert a cell id to 0-based (row, col)."""
    if not isinstance(cid, str) or not _CELL_RE.fullmatch(cid):
        raise ClueError(f"Malformed cell id: {cid!r}")

    col = ord(cid[0]) - ord("A")
    row = int(cid[1:]) - 1

    if not (0 <= row < n and 0 <= col < n):
        raise ClueError(f"Cell {cid} is outside the {n}x{n} grid")

    return row, col


def all_cells(n: int) -> List[CellId]:
    """Return every cell id in row-major order."""
    return [cell_id(r, c) for r in range(n) for c in range(n)]


def region_kind(kind: RegionKind):
    """Register a resolver function for a region kind."""
    def deco(fn):
        _RESOLVERS[kind] = fn
        return fn
    return deco


@region_kind(RegionKind.ROW)
def _row(region: Region, n: int) -> List[CellId]:
    if region.of_cell is not None or region.cells:
        raise ClueError("ROW: only index is allowed")

    idx = region.index

    if isinstance(idx, bool) or not isinstance(idx, int) or not (1 <= idx <= n):
        raise ClueError(f"Row index must be in 1..{n}, got {idx!r}")

    return [cell_id(idx - 1, c) for c in range(n)]


@region_kind(RegionKind.COL)
def _column(region: Region, n: int) -> List[CellId]:
    if region.of_cell is not None or region.cells:
        raise ClueError("COL: only index is allowed")

    letter = region.index
    last = chr(ord("A") + n - 1)

    if not isinstance(letter, str) or len(letter) != 1 or not ("A" <= letter <= last):
        raise ClueError(f"Column must be a letter in A..{last}, got {letter!r}")

    col = ord(letter) - ord("A")
    return [cell_id(r, col) for r in range(n)]


@region_kind(RegionKind.NEIGHBORS)
def _neighbors(region: Region, n: int) -> List[CellId]:
    if region.index is not None or region.cells:
        raise ClueError("NEIGHBORS: only of_cell is allowed")

    r0, c0 = parse_cell(region.of_cell, n)

    return [
        cell_id(r, c)
        for r in range(n)
        for c in range(n)
        if max(abs(r - r0), abs(c - c0)) == 1
    ]


@region_kind(RegionKind.CELLS)
def _cells(region: Region, n: int) -> List[CellId]:
    if region.index is not None or region.of_cell is not None:
        raise ClueError("CELLS: only cells is allowed")

    if not isinstance(region.cells, tuple):
        raise ClueError("cells: expected a tuple")

    return list(region.cells)


def resolve_region(region: Region, n: int) -> List[CellId]:
    """Return valid, distinct, non-empty region cells in row-major order."""

    if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= MAX_GRID:
        raise ClueError(f"Invalid grid size: {n!r}")

    if not isinstance(region, Region):
        raise ClueError(f"Region object expected, got {region!r}")

    resolver = _RESOLVERS.get(region.kind)

    if resolver is None:
        raise ClueError(f"Unsupported region kind: {region.kind!r}")

    cells = resolver(region, n)

    for cell in cells:
        parse_cell(cell, n)

    if len(set(cells)) != len(cells):
        raise ClueError(f"Region has duplicate cells: {cells}")

    if not cells:
        raise ClueError("Region is empty")

    return sorted(cells, key=lambda c: parse_cell(c, n))