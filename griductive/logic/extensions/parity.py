"""Extension 1: Parity clue (even/odd criminal count in a region).

Owner: C (Duy)
"""
from itertools import product
from typing import List

from griductive.core.constants import ClueType, Parity
from griductive.core.regions import resolve_region
from griductive.core.types import CNF, Assignment, Clue, ClueError
from griductive.logic.clue_validator import _need, validator
from griductive.logic.cnf_encoder import encoder
from griductive.logic.evaluator import _is_criminal, evaluator
from griductive.logic.variable_map import VarMap


def _is_even(clue: Clue) -> bool:
    """Normalize clue parity to boolean: True for EVEN, False for ODD."""
    p = clue.parity
    if p in (Parity.EVEN, "EVEN"):
        return True
    if p in (Parity.ODD, "ODD"):
        return False
    raise ClueError(f"[{clue.id}] 'parity' must be EVEN or ODD, got {p!r}")


@validator(ClueType.PARITY)
def validate_parity(clue: Clue, n: int) -> None:
    """Validate PARITY clue fields and region geometry."""
    _need(clue, "parity")
    _is_even(clue)
    resolve_region(_need(clue, "region"), n)


def parity_clauses(vs: List[int], is_even: bool) -> CNF:
    """CNF encoding: forbid every assignment whose sum mod 2 contradicts parity."""
    clauses: CNF = []
    for bits in product([False, True], repeat=len(vs)):
        if (sum(bits) % 2 == 0) != is_even:
            clauses.append([-v if bit else v for v, bit in zip(vs, bits)])
    return clauses


@encoder(ClueType.PARITY)
def encode_parity(clue: Clue, vm: VarMap) -> CNF:
    """Encode PARITY clue to CNF clauses."""
    cells = resolve_region(clue.region, vm.n)
    vs = [vm.var(c) for c in cells]
    return parity_clauses(vs, _is_even(clue))


@evaluator(ClueType.PARITY)
def evaluate_parity(clue: Clue, assign: Assignment, n: int) -> bool:
    """Evaluate PARITY clue under a complete assignment."""
    cells = resolve_region(clue.region, n)
    count = sum(1 for c in cells if _is_criminal(assign, c))
    return (count % 2 == 0) == _is_even(clue)
