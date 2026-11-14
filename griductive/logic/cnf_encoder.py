"""Clue -> CNF (list of int clauses, DIMACS style).
"""
from typing import Callable, Dict

from griductive.core.constants import ClueType, Status
from griductive.core.types import CNF, Clue, ClueError
from griductive.logic.clue_validator import validate_clue
from griductive.logic.variable_map import VarMap
from itertools import combinations

from griductive.core.regions import resolve_region

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

def _region_vars(clue: Clue, vm: VarMap) -> list:
    """Return the variable numbers of the clue's region, in row-major order."""
    return [vm.var(c) for c in resolve_region(clue.region, vm.n)]


def at_most_clauses(vs: list, k: int) -> CNF:
    """At most k true: forbid every group of k+1 variables being true together."""
    return [[-v for v in group] for group in combinations(vs, k + 1)]


def at_least_clauses(vs: list, k: int) -> CNF:
    """At least k true: forbid every group of n-k+1 variables being false together."""
    return [list(group) for group in combinations(vs, len(vs) - k + 1)]


@encoder(ClueType.AT_MOST)
def _at_most(clue: Clue, vm: VarMap) -> CNF:
    """AT_MOST k over the clue's region."""
    return at_most_clauses(_region_vars(clue, vm), clue.k)


@encoder(ClueType.AT_LEAST)
def _at_least(clue: Clue, vm: VarMap) -> CNF:
    """AT_LEAST k over the clue's region."""
    return at_least_clauses(_region_vars(clue, vm), clue.k)


@encoder(ClueType.EXACTLY)
def _exactly(clue: Clue, vm: VarMap) -> CNF:
    """EXACTLY k = AT_MOST k and AT_LEAST k."""
    vs = _region_vars(clue, vm)
    return at_most_clauses(vs, clue.k) + at_least_clauses(vs, clue.k)