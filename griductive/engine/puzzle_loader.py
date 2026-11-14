"""Load the complete private puzzle; validate structure, not logical solvability."""

import json
from enum import Enum
from pathlib import Path

from griductive.core.constants import ClueType, RegionKind, Status
from griductive.core.regions import resolve_region
from griductive.core.types import Cell, Clue, Puzzle, Region


def _object(data: object, fields: set[str], path: str) -> dict:
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object")
    missing, extra = fields - data.keys(), data.keys() - fields
    if missing:
        raise ValueError(f"{path}: missing fields {sorted(missing)}")
    if extra:
        raise ValueError(f"{path}: unexpected fields {sorted(extra, key=str)}")
    return data


def _text(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: expected a non-empty string")
    return value


def _enum(enum_type: type[Enum], value: object, path: str) -> Enum:
    if not isinstance(value, str):
        raise ValueError(f"{path}: expected one of {[e.value for e in enum_type]}")
    try:
        return enum_type(value)
    except ValueError:
        raise ValueError(f"{path}: expected one of {[e.value for e in enum_type]}") from None


def _reference(value: object, board: tuple[str, ...], path: str) -> str:
    if not isinstance(value, str) or value not in board:
        raise ValueError(f"{path}: expected a cell on the board")
    return value


def _region(data: object, size: int, path: str) -> Region:
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object")
    kind = _enum(RegionKind, data.get("kind"), f"{path}.kind")
    field = {RegionKind.ROW: "index", RegionKind.COL: "index",
             RegionKind.NEIGHBORS: "of", RegionKind.CELLS: "cells"}[kind]
    _object(data, {"kind", field}, path)
    if kind == RegionKind.CELLS:
        if not isinstance(data["cells"], list):
            raise ValueError(f"{path}.cells: expected a list")
        region = Region(kind=kind, cells=tuple(data["cells"]))
    elif kind == RegionKind.NEIGHBORS:
        region = Region(kind=kind, of_cell=data["of"])
    else:
        region = Region(kind=kind, index=data["index"])
    try:
        resolve_region(region, size)
    except ValueError as error:
        raise ValueError(f"{path}.{error}") from error
    return region


def _clue(data: object, board: tuple[str, ...], size: int, path: str) -> Clue:
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object")
    kind = _enum(ClueType, data.get("type"), f"{path}.type")
    fields = {ClueType.FACT: {"cell", "status"}, ClueType.SAME: {"a", "b"},
              ClueType.DIFFERENT: {"a", "b"}, ClueType.EXACTLY: {"k", "region"},
              ClueType.AT_LEAST: {"k", "region"}, ClueType.AT_MOST: {"k", "region"}}
    _object(data, {"id", "type"} | fields[kind], path)
    clue_id = _text(data["id"], f"{path}.id")
    if kind == ClueType.FACT:
        return Clue(id=clue_id, type=kind,
                    cell=_reference(data["cell"], board, f"{path}.cell"),
                    status=_enum(Status, data["status"], f"{path}.status"))
    if kind in (ClueType.SAME, ClueType.DIFFERENT):
        return Clue(id=clue_id, type=kind,
                    a=_reference(data["a"], board, f"{path}.a"),
                    b=_reference(data["b"], board, f"{path}.b"))
    region = _region(data["region"], size, f"{path}.region")
    count = len(resolve_region(region, size))
    if type(data["k"]) is not int or not 0 <= data["k"] <= count:
        raise ValueError(f"{path}.k: expected an integer in 0..{count}")
    return Clue(id=clue_id, type=kind, k=data["k"], region=region)


def parse_puzzle(data: object) -> Puzzle:
    """Validate decoded JSON and return an immutable, row-major private puzzle."""
    data = _object(data, {"size", "characters"}, "puzzle")
    size = data["size"]
    if type(size) is not int or size not in (3, 4, 5):
        raise ValueError("puzzle.size: expected an integer in {3, 4, 5}")
    characters = data["characters"]
    if not isinstance(characters, list) or len(characters) != size * size:
        raise ValueError(f"puzzle.characters: expected a list of {size * size} characters")
    board = tuple(f"{chr(65 + col)}{row}" for row in range(1, size + 1)
                  for col in range(size))
    cells, clue_ids = {}, set()
    for index, character in enumerate(characters):
        path = f"characters[{index}]"
        character = _object(character, {"cell", "name", "job", "status", "revealed", "clue"},
                            path)
        cell = _reference(character["cell"], board, f"{path}.cell")
        if cell in cells:
            raise ValueError(f"{path}.cell: duplicate cell {cell}")
        name = _text(character["name"], f"{path}.name")
        job = _text(character["job"], f"{path}.job")
        status = _enum(Status, character["status"], f"{path}.status")
        if type(character["revealed"]) is not bool:
            raise ValueError(f"{path}.revealed: expected a boolean")
        clue = _clue(character["clue"], board, size, f"{path}.clue")
        if clue.id in clue_ids:
            raise ValueError(f"{path}.clue.id: duplicate clue id {clue.id}")
        clue_ids.add(clue.id)
        cells[cell] = Cell(cell, name, job, status, character["revealed"], clue)
    if not any(cell.revealed for cell in cells.values()):
        raise ValueError("puzzle.characters: at least one character must be revealed")
    return Puzzle(size=size, characters=tuple(cells[cell] for cell in board))


def load_puzzle(path: str | Path) -> Puzzle:
    """Read UTF-8 JSON (optional BOM); preserve filesystem errors and reject bad data."""
    try:
        with Path(path).open(encoding="utf-8-sig") as stream:
            data = json.load(stream)
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}: invalid JSON at line {error.lineno}, "
                         f"column {error.colno}: {error.msg}") from error
    except UnicodeDecodeError as error:
        raise ValueError(f"{path}: expected UTF-8 JSON") from error
    return parse_puzzle(data)
