"""Direct semantic evaluator: is a clue true under a complete assignment?

It must NOT use the CNF encoder: it is the independent answer key that the
encoder is checked against (Task 23).
"""
from typing import Callable, Dict

from griductive.core.constants import ClueType, Status
from griductive.core.regions import resolve_region
from griductive.core.types import Assignment, CellId, Clue, ClueError

_EVALUATORS: Dict[ClueType, Callable[[Clue, Assignment, int], bool]] = {}


def evaluator(*types: ClueType):
    """Register an evaluator function for one or more clue types."""
    def deco(fn):
        for t in types:
            _EVALUATORS[t] = fn
        return fn
    return deco


def evaluate(clue: Clue, assign: Assignment, n: int) -> bool:
    """Return True if the clue holds under `assign` ({cell_id: True if CRIMINAL})."""
    fn = _EVALUATORS.get(clue.type)
    if fn is None:
        raise ClueError(f"[{clue.id}] no evaluator for clue type {clue.type.value}")
    return fn(clue, assign, n)


def _is_criminal(assign: Assignment, cell: CellId) -> bool:
    """Look up one cell in the assignment, with a clear error if it is missing."""
    try:
        return assign[cell]
    except KeyError:
        raise ClueError(f"Assignment has no value for cell {cell}") from None


def _count_criminals(clue: Clue, assign: Assignment, n: int) -> int:
    """Count the criminals inside the clue's region."""
    return sum(_is_criminal(assign, c) for c in resolve_region(clue.region, n))


@evaluator(ClueType.FACT)
def _fact(clue: Clue, assign: Assignment, n: int) -> bool:
    return _is_criminal(assign, clue.cell) == (clue.status is Status.CRIMINAL)


@evaluator(ClueType.SAME)
def _same(clue: Clue, assign: Assignment, n: int) -> bool:
    return _is_criminal(assign, clue.a) == _is_criminal(assign, clue.b)


@evaluator(ClueType.DIFFERENT)
def _different(clue: Clue, assign: Assignment, n: int) -> bool:
    return _is_criminal(assign, clue.a) != _is_criminal(assign, clue.b)


@evaluator(ClueType.EXACTLY)
def _exactly(clue: Clue, assign: Assignment, n: int) -> bool:
    return _count_criminals(clue, assign, n) == clue.k


@evaluator(ClueType.AT_LEAST)
def _at_least(clue: Clue, assign: Assignment, n: int) -> bool:
    return _count_criminals(clue, assign, n) >= clue.k


@evaluator(ClueType.AT_MOST)
def _at_most(clue: Clue, assign: Assignment, n: int) -> bool:
    return _count_criminals(clue, assign, n) <= clue.k