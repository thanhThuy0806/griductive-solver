"""Uniqueness check: count solutions (capped) with a SAT solver (Owner: A).

A valid puzzle has exactly one complete assignment of Criminal/Innocent. This
check is a SEPARATE tool for puzzle authors and experiments: it takes the
COMPLETE clue set, so it must never be called from inside the Agent's solving
loop (the Agent only knows revealed clues).

Counting is projected onto the primary variables C_i: two models that differ
only in auxiliary variables count as the same solution. Method: find a model,
add a blocking clause over the primary variables, repeat. With limit=2 this
needs at most 3 SAT calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Sequence

from griductive.agent.grid import row_major_cells
from griductive.agent.protocols import ClueEncoder
from griductive.agent.stub_solver import StubSolver
from griductive.sat.interface import SatSolver


class Uniqueness(str, Enum):
    UNIQUE = "UNIQUE"
    MULTIPLE = "MULTIPLE"
    UNSATISFIABLE = "UNSATISFIABLE"


@dataclass
class UniquenessResult:
    status: Uniqueness
    count: int                                   # solutions found, never more than `limit`
    solutions: list[dict[int, bool]] = field(default_factory=list)   # primary vars only
    sat_calls: int = 0


def count_solutions(clauses: Sequence[Sequence[int]], primary_vars: Iterable[int],
                    limit: int = 2, solver: SatSolver | None = None) -> UniquenessResult:
    """Count distinct assignments of `primary_vars` satisfying `clauses`, up to `limit`."""
    if limit < 2:
        raise ValueError("limit must be at least 2 to tell UNIQUE from MULTIPLE")
    primary = sorted(set(primary_vars))
    solver = solver if solver is not None else StubSolver()

    base = [list(c) for c in clauses]
    # Tautologies make sure every primary variable appears in the formula, so the
    # solver returns a value for it even when no clue mentions it.
    base += [[v, -v] for v in primary]

    blocking: list[list[int]] = []
    solutions: list[dict[int, bool]] = []
    calls = 0
    while len(solutions) < limit:
        result = solver.solve(base + blocking)
        calls += 1
        if not result.satisfiable:
            break
        model = {v: bool(result.model[v]) for v in primary}
        solutions.append(model)
        blocking.append([-v if value else v for v, value in model.items()])

    count = len(solutions)
    if count == 0:
        status = Uniqueness.UNSATISFIABLE
    elif count == 1:
        status = Uniqueness.UNIQUE
    else:
        status = Uniqueness.MULTIPLE
    return UniquenessResult(status, count, solutions, calls)


def check_puzzle_uniqueness(clues: Iterable[dict], encoder: ClueEncoder, size: int,
                            known: Mapping[str, str] | None = None, limit: int = 2,
                            solver: SatSolver | None = None) -> UniquenessResult:
    """Uniqueness of a whole puzzle.

    clues: every clue of the puzzle (revealed or not).
    known: optional {cell: "CRIMINAL"/"INNOCENT"} statuses that are given for free
           (face-up cards at the start).
    """
    clauses: list[list[int]] = []
    for clue in clues:
        clauses.extend(list(c) for c in encoder.encode_clue(clue))
    for cell, status in (known or {}).items():
        lit = encoder.var_of(cell)
        clauses.append([lit if status == "CRIMINAL" else -lit])
    primary = [encoder.var_of(c) for c in row_major_cells(size)]
    return count_solutions(clauses, primary, limit, solver)
