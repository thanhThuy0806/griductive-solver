"""Classify characters as CRIMINAL / INNOCENT / UNKNOWN / INCONSISTENT (Agent v1).

Owner: A.

Variable i is the primary variable C_i (True = Criminal). For a knowledge base KB
given as CNF clauses:

    KB itself UNSAT          -> INCONSISTENT
    KB and NOT C_i is UNSAT  -> CRIMINAL     (KB |= C_i)
    KB and C_i is UNSAT      -> INNOCENT     (KB |= NOT C_i)
    both SAT                 -> UNKNOWN

This module never sees the hidden solution or unrevealed clues: it only receives
the clauses that make up KB_t. It depends on the SAT solver only through
`griductive.sat.interface.SatSolver`, so the stub can be replaced by DPLL later.

Every SAT call is recorded in `EntailmentChecker.queries`, to be used by the
deduction trace.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Sequence

from griductive.agent.stub_solver import StubSolver
from griductive.sat.interface import SatSolver, SolveResult

Clauses = Sequence[Sequence[int]]

class Classification(str, Enum):
    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"
    UNKNOWN = "UNKNOWN"
    INCONSISTENT = "INCONSISTENT"

    @property
    def is_forced(self) -> bool:
        """True when the verdict is provable (the Agent may act on it)."""
        return self in (Classification.CRIMINAL, Classification.INNOCENT)

@dataclass(frozen=True)
class SatQuery:
    """One SAT call, for the deduction trace."""

    query_id: int
    formula: str            # e.g. "KB", "KB ∧ ¬C3"
    literal: int | None     # temporary unit clause added to KB, None for plain KB
    satisfiable: bool
    stats: dict = field(default_factory=dict)

class EntailmentChecker:
    """Entailment queries on top of any `SatSolver`.
    use_witnesses: every SAT model proves that each of its variable values is
    possible, so later queries whose answer is already witnessed are skipped.
    This only saves SAT calls; results are identical with it on or off.
    """

    def __init__(self, solver: SatSolver | None = None, use_witnesses: bool = True) -> None:
        self.solver: SatSolver = solver if solver is not None else StubSolver()
        self.use_witnesses = use_witnesses
        self.queries: list[SatQuery] = []
        self.total_sat_calls = 0
        self._next_id = 1

    # logging
    def drain_log(self) -> list[SatQuery]:
        """Return the queries recorded since the last drain and clear the log."""
        log, self.queries = self.queries, []
        return log

    def _query(self, clauses: Clauses, literal: int | None) -> SolveResult:
        extra = [] if literal is None else [[literal]]
        result = self.solver.solve([*clauses, *extra])
        if literal is None:
            formula = "KB"
        else:
            formula = f"KB ∧ C{literal}" if literal > 0 else f"KB ∧ ¬C{-literal}"
        self.queries.append(SatQuery(self._next_id, formula, literal,
                                     result.satisfiable, dict(result.stats or {})))
        self._next_id += 1
        self.total_sat_calls += 1
        return result

    # public API
    def is_consistent(self, clauses: Clauses) -> bool:
        """True iff KB is satisfiable."""
        _validate_clauses(clauses)
        return self._query(clauses, None).satisfiable

    def classify(self, clauses: Clauses, var: int) -> Classification:
        """Classify one variable."""
        return self.classify_all(clauses, [var])[var]

    def classify_all(self, clauses: Clauses, variables: Iterable[int]) -> dict[int, Classification]:
        """Classify every variable in `variables` against the same KB."""
        _validate_clauses(clauses)
        variables = list(variables)
        for v in variables:
            if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                raise ValueError(f"variable must be a positive int, got {v!r}")

        base = self._query(clauses, None)
        if not base.satisfiable:
            return {v: Classification.INCONSISTENT for v in variables}

        seen_true: set[int] = set()
        seen_false: set[int] = set()
        self._note(base.model, seen_true, seen_false)

        return {v: self._classify_one(clauses, v, seen_true, seen_false) for v in variables}

    # internals
    def _note(self, model: dict[int, bool] | None, seen_true: set[int], seen_false: set[int]) -> None:
        if not self.use_witnesses or not model:
            return
        for v, value in model.items():
            (seen_true if value else seen_false).add(v)

    def _can_be(self, clauses: Clauses, v: int, value: bool,
                seen_true: set[int], seen_false: set[int]) -> bool:
        """Is there a model of KB with C_v == value?"""
        if v in (seen_true if value else seen_false):
            return True
        result = self._query(clauses, v if value else -v)
        if result.satisfiable:
            self._note(result.model, seen_true, seen_false)
        return result.satisfiable

    def _classify_one(self, clauses: Clauses, v: int,
                      seen_true: set[int], seen_false: set[int]) -> Classification:
        # KB is known to be SAT here, so at least one polarity is always possible.
        if not self._can_be(clauses, v, False, seen_true, seen_false):
            return Classification.CRIMINAL      # KB ∧ ¬C_v is UNSAT
        if not self._can_be(clauses, v, True, seen_true, seen_false):
            return Classification.INNOCENT      # KB ∧ C_v is UNSAT
        return Classification.UNKNOWN

def _validate_clauses(clauses: Clauses) -> None:
    for clause in clauses:
        for lit in clause:
            if not isinstance(lit, int) or isinstance(lit, bool) or lit == 0:
                raise ValueError(f"invalid literal {lit!r} in clause {list(clause)!r}")