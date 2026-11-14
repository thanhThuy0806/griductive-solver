"""TEMPORARY SAT solver so Agent v1 can be developed before B finishes DPLL.

Owner: A. Delete (or keep only for tests) once `griductive/sat/dpll.py` is ready:
the Agent only depends on `griductive.sat.interface.SatSolver`.

Naive DPLL: unit propagation + branch on the first literal of the first clause.
No heuristics, no statistics except a call counter. Correct but not fast.
"""
from __future__ import annotations

from typing import Sequence

from griductive.sat.interface import SolveResult

Clause = list[int]

def _assign(clauses: list[Clause], lit: int) -> list[Clause]:
    """Make `lit` true: drop satisfied clauses, remove the falsified literal elsewhere."""
    out: list[Clause] = []
    for clause in clauses:
        if lit in clause:
            continue
        out.append([x for x in clause if x != -lit])
    return out

def _dpll(clauses: list[Clause], assignment: dict[int, bool]) -> bool:
    while True:
        if not clauses:
            return True
        if any(len(c) == 0 for c in clauses):
            return False
        unit = next((c[0] for c in clauses if len(c) == 1), None)
        if unit is None:
            break
        assignment[abs(unit)] = unit > 0
        clauses = _assign(clauses, unit)

    lit = clauses[0][0]
    for choice in (lit, -lit):
        trial = dict(assignment)
        trial[abs(choice)] = choice > 0
        if _dpll(_assign(clauses, choice), trial):
            assignment.clear()
            assignment.update(trial)
            return True
    return False

class StubSolver:
    """Implements `griductive.sat.interface.SatSolver`."""

    def __init__(self) -> None:
        self.calls = 0

    def solve(self, clauses: Sequence[Sequence[int]]) -> SolveResult:
        self.calls += 1
        work = [list(c) for c in clauses]
        variables = sorted({abs(lit) for c in work for lit in c})
        assignment: dict[int, bool] = {}
        if not _dpll(work, assignment):
            return SolveResult(satisfiable=False, model=None, stats={"stub": True})
        for v in variables:  # variables left free by the search: any value works
            assignment.setdefault(v, False)
        return SolveResult(satisfiable=True, model=assignment, stats={"stub": True})
