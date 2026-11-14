"""Shared data types: Region, Clue, Cell, Puzzle and CNF aliases."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from griductive.core.constants import ClueType, RegionKind, Status


CellId = str
Assignment = Dict[CellId, bool]  # True = Criminal
Clause = List[int]
CNF = List[Clause]

_CLUE_FIELDS = (
    "id", "type", "cell", "status",
    "a", "b", "k", "region"
)


class ClueError(ValueError):
    """Raised when a clue or region is malformed."""


@dataclass(frozen=True)
class Region:
    """A region of the grid; fields depend on its kind."""

    kind: RegionKind
    index: Optional[Union[int, str]] = None
    of_cell: Optional[CellId] = None
    cells: Tuple[CellId, ...] = ()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Region":
        """Build a Region from its JSON object."""

        if not isinstance(d, dict):
            raise ClueError(f"Region must be an object, got {d!r}")

        try:
            kind = RegionKind(d.get("kind"))
        except (ValueError, TypeError):
            raise ClueError(f"Unknown region kind in {d!r}") from None

        cells = d.get("cells", ())

        if not isinstance(cells, (list, tuple)):
            raise ClueError(f"'cells' must be a list in {d!r}")

        return cls(
            kind=kind,
            index=d.get("index"),
            of_cell=d.get("of_cell", d.get("of")),
            cells=tuple(cells)
        )


@dataclass(frozen=True)
class Clue:
    """A structured clue; unused fields stay None."""

    id: str
    type: ClueType
    cell: Optional[CellId] = None
    status: Optional[Status] = None
    a: Optional[CellId] = None
    b: Optional[CellId] = None
    k: Optional[int] = None
    region: Optional[Region] = None
    params: Dict[str, Any] = field(
        default_factory=dict,
        compare=False,
        hash=False
    )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Clue":
        """Build a Clue from its JSON object."""

        if not isinstance(d, dict):
            raise ClueError(f"Clue must be an object, got {d!r}")

        cid = d.get("id")

        if not isinstance(cid, str) or not cid:
            raise ClueError(f"Clue is missing a string 'id': {d!r}")

        try:
            ctype = ClueType(d.get("type"))
        except (ValueError, TypeError):
            raise ClueError(
                f"[{cid}] unknown clue type {d.get('type')!r}"
            ) from None

        status = d.get("status")

        if status is not None:
            try:
                status = Status(status)
            except (ValueError, TypeError):
                raise ClueError(
                    f"[{cid}] bad status {status!r}"
                ) from None

        region = d.get("region")

        if region is not None:
            region = Region.from_dict(region)

        extra = {
            key: val
            for key, val in d.items()
            if key not in _CLUE_FIELDS
        }

        return cls(
            id=cid,
            type=ctype,
            cell=d.get("cell"),
            status=status,
            a=d.get("a"),
            b=d.get("b"),
            k=d.get("k"),
            region=region,
            params=extra
        )


@dataclass
class Cell:
    """One character card on the board."""

    cell: CellId
    name: str
    job: str
    status: Status
    revealed: bool
    clue: Clue


@dataclass
class Puzzle:
    """A full puzzle: grid size and all characters."""

    size: int
    characters: List[Cell]