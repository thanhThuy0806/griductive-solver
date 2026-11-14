"""Validate a Clue before encoding; extensions register their own validators."""
from typing import Any, Callable, Dict

from griductive.core.constants import COUNT_CLUE_TYPES, ClueType, Status
from griductive.core.regions import parse_cell, resolve_region
from griductive.core.types import Clue, ClueError

_VALIDATORS: Dict[ClueType, Callable[[Clue, int], None]] = {}


def validator(*types: ClueType):
    """Register a validator function for one or more clue types."""
    def deco(fn):
        for t in types:
            _VALIDATORS[t] = fn
        return fn
    return deco


def validate_clue(clue: Clue, n: int) -> None:
    """Raise ClueError if the clue is malformed for an n x n grid."""
    fn = _VALIDATORS.get(clue.type)
    if fn is None:
        raise ClueError(f"[{clue.id}] no validator for clue type {clue.type!r}")
    fn(clue, n)


def _need(clue: Clue, name: str) -> Any:
    value = getattr(clue, name)
    if value is None:
        raise ClueError(f"[{clue.id}] {clue.type.value} is missing field '{name}'")
    return value


@validator(ClueType.FACT)
def _fact(clue: Clue, n: int) -> None:
    parse_cell(_need(clue, "cell"), n)
    if not isinstance(_need(clue, "status"), Status):
        raise ClueError(f"[{clue.id}] 'status' must be CRIMINAL or INNOCENT")


@validator(ClueType.SAME, ClueType.DIFFERENT)
def _binary(clue: Clue, n: int) -> None:
    a, b = _need(clue, "a"), _need(clue, "b")
    parse_cell(a, n)
    parse_cell(b, n)
    if a == b:
        raise ClueError(f"[{clue.id}] {clue.type.value} needs two different cells, got {a}")


@validator(*COUNT_CLUE_TYPES)
def _counting(clue: Clue, n: int) -> None:
    cells = resolve_region(_need(clue, "region"), n)
    k = _need(clue, "k")
    if isinstance(k, bool) or not isinstance(k, int):
        raise ClueError(f"[{clue.id}] k must be an integer, got {k!r}")
    if not (0 <= k <= len(cells)):
        raise ClueError(f"[{clue.id}] k={k} is outside [0, {len(cells)}]")