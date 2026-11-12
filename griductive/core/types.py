"""Shared data types: Region, Clue, Cell, Puzzle and CNF aliases."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from griductive.core.constants import ClueType, RegionKind, Status, VerdictResult

CellId = str
Assignment = Dict[CellId, bool]   # True = Criminal
Clause = List[int]                # DIMACS style: [1, -2] means C1 or not C2
CNF = List[Clause]

_CLUE_FIELDS = ("id", "type", "cell", "status", "a", "b", "k", "region")


class ClueError(ValueError):
    """Raised when a clue or region is malformed."""


@dataclass(frozen=True)
class Region:
    """A region of the grid; which fields are used depends on `kind`."""
    kind: RegionKind
    index: Optional[Union[int, str]] = None   # ROW: 1-based int, COL: column letter
    of: Optional[CellId] = None               # NEIGHBORS: centre cell
    cells: Tuple[CellId, ...] = ()            # CELLS: explicit list

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Region":
        """Build a Region from its JSON object."""
        if not isinstance(d, dict):
            raise ClueError(f"Region must be an object, got {d!r}")
        try:
            kind = RegionKind(d.get("kind"))
        except ValueError:
            raise ClueError(f"Unknown region kind in {d!r}") from None
        cells = d.get("cells", ())
        if not isinstance(cells, (list, tuple)):
            raise ClueError(f"'cells' must be a list in {d!r}")
        return cls(kind, d.get("index"), d.get("of"), tuple(cells))


@dataclass(frozen=True)
class Clue:
    """A structured clue; unused fields stay None."""
    id: str
    type: ClueType
    cell: Optional[CellId] = None             # FACT
    status: Optional[Status] = None           # FACT
    a: Optional[CellId] = None                # SAME / DIFFERENT
    b: Optional[CellId] = None                # SAME / DIFFERENT
    k: Optional[int] = None                   # EXACTLY / AT_LEAST / AT_MOST
    region: Optional[Region] = None           # counting clues
    params: Dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Clue":
        """Build a Clue from its JSON object; unknown keys go to `params`."""
        if not isinstance(d, dict):
            raise ClueError(f"Clue must be an object, got {d!r}")
        cid = d.get("id")
        if not isinstance(cid, str) or not cid:
            raise ClueError(f"Clue is missing a string 'id': {d!r}")
        try:
            ctype = ClueType(d.get("type"))
        except ValueError:
            raise ClueError(f"[{cid}] unknown clue type {d.get('type')!r}") from None
        status = d.get("status")
        if status is not None:
            try:
                status = Status(status)
            except ValueError:
                raise ClueError(f"[{cid}] bad status {status!r}") from None
        region = d.get("region")
        if region is not None:
            region = Region.from_dict(region)
        extra = {key: val for key, val in d.items() if key not in _CLUE_FIELDS}
        return cls(cid, ctype, d.get("cell"), status, d.get("a"), d.get("b"),
                   d.get("k"), region, extra)


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


@dataclass(frozen=True)
class AgentKnowledge:
    """Detached evidence: initial givens plus accepted verdicts and revealed clues."""

    size: int
    revealed_clues: Tuple[Clue, ...]
    proven_verdicts: Tuple[Tuple[CellId, Status], ...]


@dataclass(frozen=True)
class PublicCell:
    """One public card; status and clue are absent until it is revealed."""

    cell: CellId
    name: str
    job: str
    revealed: bool
    status: Optional[Status] = None
    clue: Optional[Clue] = None


@dataclass(frozen=True)
class PublicState:
    """Detached public snapshot in row-major order, without hidden answers."""

    size: int
    characters: Tuple[PublicCell, ...]


@dataclass(frozen=True)
class VerdictResponse:
    """Result of submitting a status; new_clue exists only on acceptance."""

    cell: CellId
    status: Status
    result: VerdictResult
    new_clue: Optional[Clue] = None
