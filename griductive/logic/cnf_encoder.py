"""Clue -> CNF (list of int clauses, DIMACS style).
"""
from typing import Callable, Dict

from griductive.core.constants import ClueType, Status
from griductive.core.types import CNF, Clue, ClueError
from griductive.logic.clue_validator import validate_clue
from griductive.logic.variable_map import VarMap

_ENCODERS: Dict[ClueType, Callable[[Clue, VarMap], CNF]] = {}


def encoder(*types: ClueType):
    """Register an encoder function for one or more clue types."""
    def deco(fn):
        for t in types:
            _ENCODERS[t] = fn
        return fn
    return deco


def encode_clue(clue: Clue, vm: VarMap) -> CNF:
    """Validate a clue, then convert it to a list of clauses."""
    validate_clue(clue, vm.n)
    fn = _ENCODERS.get(clue.type)
    if fn is None:
        raise ClueError(f"[{clue.id}] no encoder for clue type {clue.type.value}")
    return fn(clue, vm)


@encoder(ClueType.FACT)
def _fact(clue: Clue, vm: VarMap) -> CNF:
    """FACT: one unit clause, positive for CRIMINAL and negative for INNOCENT."""
    v = vm.var(clue.cell)
    return [[v]] if clue.status is Status.CRIMINAL else [[-v]]


@encoder(ClueType.SAME)
def _same(clue: Clue, vm: VarMap) -> CNF:
    """SAME: (not a or b) and (a or not b); forbids the mixed cases."""
    a, b = vm.var(clue.a), vm.var(clue.b)
    return [[-a, b], [a, -b]]


@encoder(ClueType.DIFFERENT)
def _different(clue: Clue, vm: VarMap) -> CNF:
    """DIFFERENT: (a or b) and (not a or not b); forbids the equal cases."""
    a, b = vm.var(clue.a), vm.var(clue.b)
    return [[a, b], [-a, -b]]