"""Contract between the SAT solver and its users (Agent, experiments).

Owner: B (implements DpllSolver against this) / A (consumes it).

Any solver used by the Agent must provide `solve(clauses) -> SolveResult`.
`clauses` is a list of clauses in DIMACS style: each clause is a list of non-zero
ints, `3` means C3 and `-3` means NOT C3.

Rules for implementers:
  * satisfiable=True  -> `model` is a complete assignment {var: bool} for every
    variable that appears in `clauses`.
  * satisfiable=False -> `model` is None.
  * An empty clause list is SAT. A list containing an empty clause is UNSAT.
  * `stats` may hold decisions / propagations / backtracks / runtime_ms.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence, runtime_checkable

@dataclass
class SolveResult:
    satisfiable: bool
    model: dict[int, bool] | None = None
    stats: dict = field(default_factory=dict)

@runtime_checkable
class SatSolver(Protocol):
    def solve(self, clauses: Sequence[Sequence[int]]) -> SolveResult:
        """Solve the given CNF clauses and return a SolveResult."""
        ...
