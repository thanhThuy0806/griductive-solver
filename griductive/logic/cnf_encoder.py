"""Clue -> CNF (list of int clauses, DIMACS style)."""
from itertools import combinations, product
from typing import Callable, Dict, List

from griductive.core.constants import ClueType, CompareOp, Parity, Status
from griductive.core.regions import resolve_region
from griductive.core.types import CNF, CellId, Clue, ClueError
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


def _region_vars(clue: Clue, vm: VarMap) -> list[int]:
    """Return the variable numbers of the clue's region, in row-major order."""
    return [vm.var(c) for c in resolve_region(clue.region, vm.n)]


def at_most_clauses(vs: list[int], k: int) -> CNF:
    """At most k true: forbid every group of k+1 variables being true together."""
    return [[-v for v in group] for group in combinations(vs, k + 1)]


def at_least_clauses(vs: list[int], k: int) -> CNF:
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


# ---------------------------------------------------------------------------
# Extension 1: Parity Clue (PARITY)
# ---------------------------------------------------------------------------
def _is_even(clue: Clue) -> bool:
    """Normalize clue parity to boolean: True for EVEN, False for ODD."""
    p = clue.parity
    if p in (Parity.EVEN, "EVEN"):
        return True
    if p in (Parity.ODD, "ODD"):
        return False
    raise ClueError(f"[{clue.id}] 'parity' must be EVEN or ODD, got {p!r}")


def parity_clauses(vs: list[int], is_even: bool) -> CNF:
    """CNF encoding: forbid every assignment whose sum mod 2 contradicts parity."""
    clauses: CNF = []
    for bits in product([False, True], repeat=len(vs)):
        if (sum(bits) % 2 == 0) != is_even:
            clauses.append([-v if bit else v for v, bit in zip(vs, bits)])
    return clauses


@encoder(ClueType.PARITY)
def _parity(clue: Clue, vm: VarMap) -> CNF:
    """Encode PARITY clue to CNF clauses."""
    cells = resolve_region(clue.region, vm.n)
    vs = [vm.var(c) for c in cells]
    return parity_clauses(vs, _is_even(clue))


# ---------------------------------------------------------------------------
# Extension 2: Compare Region Counts (COMPARE)
# ---------------------------------------------------------------------------
_OP_PREDICATES: dict[str, Callable[[int, int], bool]] = {
    "MORE": lambda a, b: a > b,
    ">": lambda a, b: a > b,
    "EQUAL": lambda a, b: a == b,
    "==": lambda a, b: a == b,
    "=": lambda a, b: a == b,
    "LESS": lambda a, b: a < b,
    "<": lambda a, b: a < b,
}


def _normalize_op(clue: Clue) -> str:
    """Normalize and validate comparison operator."""
    op = clue.op
    if isinstance(op, CompareOp):
        op = op.value
    if not isinstance(op, str) or op not in _OP_PREDICATES:
        raise ClueError(
            f"[{clue.id}] 'op' must be MORE, EQUAL, or LESS, got {op!r}"
        )
    return op


def compare_clauses(
    cells_a: list[CellId],
    cells_b: list[CellId],
    op_name: str,
    vm: VarMap,
) -> CNF:
    """CNF encoding: forbid truth assignments on union(A, B) that violate op."""
    predicate = _OP_PREDICATES[op_name]
    union_cells = sorted(set(cells_a) | set(cells_b))
    vs = [vm.var(c) for c in union_cells]
    cell_idx = {c: i for i, c in enumerate(union_cells)}

    idx_a = [cell_idx[c] for c in cells_a]
    idx_b = [cell_idx[c] for c in cells_b]

    clauses: CNF = []
    for bits in product([False, True], repeat=len(union_cells)):
        cnt_a = sum(1 for i in idx_a if bits[i])
        cnt_b = sum(1 for i in idx_b if bits[i])
        if not predicate(cnt_a, cnt_b):
            clauses.append([-v if bit else v for v, bit in zip(vs, bits)])
    return clauses


@encoder(ClueType.COMPARE)
def _compare(clue: Clue, vm: VarMap) -> CNF:
    """Encode COMPARE clue to CNF clauses."""
    cells_a = resolve_region(clue.region_a, vm.n)
    cells_b = resolve_region(clue.region_b, vm.n)
    op_name = _normalize_op(clue)
    return compare_clauses(cells_a, cells_b, op_name, vm)
