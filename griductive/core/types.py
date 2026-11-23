"""Shared data types: Region, Clue, Cell, Puzzle and CNF aliases."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from griductive.core.constants import (
    ClueType,
    CompareOp,
    Parity,
    RegionKind,
    Status,
    VerdictResult,
)


CellId = str
Assignment = Dict[CellId, bool]   # True = Criminal
Clause = List[int]                # DIMACS style: [1, -2] means C1 or not C2
CNF = List[Clause]

_CLUE_FIELDS = (
    "id", "type", "cell", "status",
    "a", "b", "k", "region",
    "parity", "region_a", "region_b", "op", "comparator",
)


class ClueError(ValueError):
    """Raised when a clue or region is malformed."""


@dataclass(frozen=True)
class Region:
    """A region of the grid; fields depend on its kind."""

    kind: RegionKind
    index: Optional[Union[int, str]] = None
    of: Optional[CellId] = None
    cells: Tuple[CellId, ...] = ()

    def __init__(
        self,
        kind: RegionKind,
        index: Optional[Union[int, str]] = None,
        of: Optional[CellId] = None,
        cells: Tuple[CellId, ...] = (),
        of_cell: Optional[CellId] = None,
    ):
        if of is None and of_cell is not None:
            of = of_cell
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "index", index)
        object.__setattr__(self, "of", of)
        object.__setattr__(
            self,
            "cells",
            tuple(cells) if isinstance(cells, (list, tuple)) else cells,
        )

    @property
    def of_cell(self) -> Optional[CellId]:
        return self.of

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
            of=d.get("of", d.get("of_cell")),
            cells=tuple(cells),
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
    parity: Optional[Union[str, Parity]] = None
    region_a: Optional[Region] = None
    region_b: Optional[Region] = None
    op: Optional[Union[str, CompareOp]] = None
    params: Dict[str, Any] = field(
        default_factory=dict,
        compare=False,
        hash=False,
    )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Clue":
        """Build a Clue from its JSON object; unknown keys go to params."""

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
                raise ClueError(f"[{cid}] bad status {status!r}") from None

        region = d.get("region")
        if region is not None:
            region = Region.from_dict(region)

        parity = d.get("parity")
        if parity is not None:
            try:
                parity = Parity(parity)
            except (ValueError, TypeError):
                pass

        region_a = d.get("region_a")
        if region_a is not None:
            region_a = Region.from_dict(region_a)
        elif ctype == ClueType.COMPARE and region is not None:
            region_a = region

        region_b = d.get("region_b")
        if region_b is not None:
            region_b = Region.from_dict(region_b)

        op = d.get("op", d.get("comparator"))
        if op is not None:
            try:
                op = CompareOp(op)
            except (ValueError, TypeError):
                pass

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
            parity=parity,
            region_a=region_a,
            region_b=region_b,
            op=op,
            params=extra,
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