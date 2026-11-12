"""Immutable puzzle definitions; construct validated data through the loader."""

from dataclasses import dataclass

from griductive.core.constants import ClueType, RegionKind, Status


@dataclass(frozen=True)
class Region:
    """A structured region; only fields belonging to its kind are populated."""

    kind: RegionKind
    index: int | str | None = None
    of_cell: str | None = None
    cells: tuple[str, ...] | None = None


@dataclass(frozen=True)
class Clue:
    """A structured clue; only fields belonging to its type are populated."""

    id: str
    type: ClueType
    cell: str | None = None
    status: Status | None = None
    a: str | None = None
    b: str | None = None
    k: int | None = None
    region: Region | None = None


@dataclass(frozen=True)
class Cell:
    """Full character definition, including private status and clue."""

    cell: str
    name: str
    job: str
    status: Status
    revealed: bool
    clue: Clue


@dataclass(frozen=True)
class Puzzle:
    """Complete private puzzle definition for the Game Engine, not the Agent."""

    size: int
    characters: tuple[Cell, ...]
