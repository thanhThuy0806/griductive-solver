"""Extension 2: Compare region counts (MORE, EQUAL, LESS criminals between two regions).

Owner: C (Duy)
"""
from itertools import product
from typing import Callable, List, Tuple

from griductive.core.constants import ClueType, CompareOp
from griductive.core.regions import resolve_region
from griductive.core.types import CNF, Assignment, CellId, Clue, ClueError
from griductive.logic.clue_validator import _need, validator
from griductive.logic.cnf_encoder import encoder
from griductive.logic.evaluator import _is_criminal, evaluator
from griductive.logic.variable_map import VarMap

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


@validator(ClueType.COMPARE)
def validate_compare(clue: Clue, n: int) -> None:
    """Validate COMPARE clue fields and both regions."""
    _need(clue, "region_a")
    _need(clue, "region_b")
    _need(clue, "op")
    _normalize_op(clue)
    resolve_region(clue.region_a, n)
    resolve_region(clue.region_b, n)


def compare_clauses(
    cells_a: List[CellId],
    cells_b: List[CellId],
    op_name: str,
    vm: VarMap,
) -> CNF:
    """CNF encoding: forbid truth assignments on union(A, B) that violate op."""
    predicate = _OP_PREDICATES[op_name]
    # Union of distinct cells in row-major sorted order
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
def encode_compare(clue: Clue, vm: VarMap) -> CNF:
    """Encode COMPARE clue to CNF clauses."""
    cells_a = resolve_region(clue.region_a, vm.n)
    cells_b = resolve_region(clue.region_b, vm.n)
    op_name = _normalize_op(clue)
    return compare_clauses(cells_a, cells_b, op_name, vm)


@evaluator(ClueType.COMPARE)
def evaluate_compare(clue: Clue, assign: Assignment, n: int) -> bool:
    """Evaluate COMPARE clue under a complete assignment."""
    cells_a = resolve_region(clue.region_a, n)
    cells_b = resolve_region(clue.region_b, n)
    op_name = _normalize_op(clue)
    predicate = _OP_PREDICATES[op_name]

    cnt_a = sum(1 for c in cells_a if _is_criminal(assign, c))
    cnt_b = sum(1 for c in cells_b if _is_criminal(assign, c))
    return predicate(cnt_a, cnt_b)
