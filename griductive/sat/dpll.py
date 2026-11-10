from __future__ import annotations
"""DPLL solver with assumptions and statistics.

Owner: B
"""
"""DPLL SAT solver with unit propagation, conflict detection, and assumptions."""

import time
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    from .stats import SatResult, SatStats
except ImportError:
    from stats import SatResult, SatStats

Literal = int
Clause = Sequence[Literal]
CNF = Sequence[Clause]
Assignment = Dict[int, bool]


def _lit_value(lit: Literal, assignment: Assignment) -> Optional[bool]:
    """Return the truth value of a DIMACS literal under the current assignment."""
    val = assignment.get(abs(lit))
    if val is None:
        return None
    return val if lit > 0 else not val


def unit_propagate(
    clauses: CNF,
    assignment: Assignment,
    stats: Optional[SatStats] = None,
) -> Tuple[bool, Assignment]:
    """Perform iterative unit propagation and conflict detection on a CNF formula.

    Returns (True, updated_assignment) if no conflict is detected, or
    (False, updated_assignment) immediately upon encountering a falsified clause.
    """
    working = dict(assignment)

    changed = True
    while changed:
        changed = False
        for clause in clauses:
            if not clause:
                return False, working

            satisfied = False
            unassigned_lit: Optional[Literal] = None
            unassigned_count = 0

            for lit in clause:
                val = _lit_value(lit, working)
                if val is True:
                    satisfied = True
                    break
                if val is None:
                    unassigned_lit = lit
                    unassigned_count += 1
                    if unassigned_count > 1:
                        break

            if satisfied:
                continue

            # All literals in the clause evaluated to False -> Conflict!
            if unassigned_count == 0:
                return False, working

            # Exactly one unassigned literal remains -> Unit clause!
            if unassigned_count == 1 and unassigned_lit is not None:
                var = abs(unassigned_lit)
                val = unassigned_lit > 0
                working[var] = val
                if stats is not None:
                    stats.propagations += 1
                changed = True

    return True, working


def _apply_assumptions(
    assumptions: Optional[Iterable[Literal]],
    base_assignment: Optional[Assignment] = None,
) -> Tuple[bool, Assignment]:
    """Convert a list of assumption literals into an initial variable assignment."""
    assignment: Assignment = dict(base_assignment) if base_assignment else {}
    if not assumptions:
        return True, assignment

    for lit in assumptions:
        if lit == 0:
            raise ValueError("DIMACS literal cannot be 0.")
        var = abs(lit)
        val = lit > 0
        if var in assignment:
            if assignment[var] != val:
                return False, assignment
        else:
            assignment[var] = val

    return True, assignment


def _collect_variables(
    clauses: CNF,
    assumptions: Optional[Iterable[Literal]] = None,
    num_vars: Optional[int] = None,
) -> List[int]:
    """Collect and deterministically sort all propositional variables."""
    vars_set: Set[int] = set()
    if num_vars is not None and num_vars > 0:
        vars_set.update(range(1, num_vars + 1))

    for clause in clauses:
        for lit in clause:
            if lit == 0:
                raise ValueError("DIMACS literal cannot be 0.")
            vars_set.add(abs(lit))

    if assumptions:
        for lit in assumptions:
            if lit == 0:
                raise ValueError("DIMACS literal cannot be 0.")
            vars_set.add(abs(lit))

    return sorted(vars_set)


def _pick_variable(variables: Sequence[int], assignment: Assignment) -> Optional[int]:
    """Deterministically select the smallest unassigned variable index."""
    for var in variables:
        if var not in assignment:
            return var
    return None


def _all_clauses_satisfied(clauses: CNF, assignment: Assignment) -> bool:
    """Verify whether every clause in the CNF formula is satisfied."""
    for clause in clauses:
        if not any(_lit_value(lit, assignment) is True for lit in clause):
            return False
    return True


def _complete_assignment(variables: Sequence[int], assignment: Assignment) -> Assignment:
    """Fill any remaining don't-care variables deterministically with False."""
    complete = dict(assignment)
    for var in variables:
        if var not in complete:
            complete[var] = False
    return dict(sorted(complete.items()))


class DpllSolver:
    """DPLL SAT solver supporting assumptions, unit propagation, and statistics."""

    def __init__(self, clauses: Optional[CNF] = None, num_vars: Optional[int] = None) -> None:
        """Initialize the solver with an optional base CNF formula and variable count."""
        self._base_clauses: List[Tuple[Literal, ...]] = (
            [tuple(c) for c in clauses] if clauses else []
        )
        self._num_vars = num_vars
        self.stats = SatStats()

    def add_clause(self, clause: Clause) -> None:
        """Append a single DIMACS clause to the solver's base formula."""
        if any(lit == 0 for lit in clause):
            raise ValueError("DIMACS literal cannot be 0.")
        self._base_clauses.append(tuple(clause))

    def add_clauses(self, clauses: CNF) -> None:
        """Append multiple DIMACS clauses to the solver's base formula."""
        for clause in clauses:
            self.add_clause(clause)

    def reset_stats(self) -> None:
        """Reset cumulative solver statistics."""
        self.stats.reset()

    def solve(
        self,
        clauses: Optional[CNF] = None,
        assumptions: Optional[Iterable[Literal]] = None,
        num_vars: Optional[int] = None,
    ) -> SatResult:
        """Solve the CNF formula under optional unit assumptions using DPLL."""
        start_time = time.perf_counter()
        call_stats = SatStats(sat_calls=1)

        active_clauses: List[Tuple[Literal, ...]]
        if clauses is not None:
            active_clauses = self._base_clauses + [tuple(c) for c in clauses]
        else:
            active_clauses = list(self._base_clauses)

        total_vars = num_vars if num_vars is not None else self._num_vars
        variables = _collect_variables(active_clauses, assumptions, total_vars)

        consistent, initial_assign = _apply_assumptions(assumptions)
        if not consistent:
            call_stats.runtime_ms = (time.perf_counter() - start_time) * 1000.0
            self.stats.add(call_stats)
            return SatResult(satisfiable=False, model=None, stats=call_stats)

        sat, final_assign = self._dpll_recursive(
            active_clauses, variables, initial_assign, call_stats
        )

        call_stats.runtime_ms = (time.perf_counter() - start_time) * 1000.0
        self.stats.add(call_stats)

        if sat and final_assign is not None:
            complete_model = _complete_assignment(variables, final_assign)
            return SatResult(satisfiable=True, model=complete_model, stats=call_stats)

        return SatResult(satisfiable=False, model=None, stats=call_stats)

    def _dpll_recursive(
        self,
        clauses: Sequence[Tuple[Literal, ...]],
        variables: Sequence[int],
        assignment: Assignment,
        stats: SatStats,
    ) -> Tuple[bool, Optional[Assignment]]:
        """Execute recursive DPLL search with unit propagation and backtracking."""
        ok, propagated = unit_propagate(clauses, assignment, stats)
        if not ok:
            return False, None

        if _all_clauses_satisfied(clauses, propagated):
            return True, propagated

        var = _pick_variable(variables, propagated)
        if var is None:
            if _all_clauses_satisfied(clauses, propagated):
                return True, propagated
            return False, None

        for branch_val in (True, False):
            stats.decisions += 1
            next_assignment = dict(propagated)
            next_assignment[var] = branch_val

            sat, result_assign = self._dpll_recursive(
                clauses, variables, next_assignment, stats
            )
            if sat:
                return True, result_assign

            stats.backtracks += 1

        return False, None


def dpll_solve(
    clauses: CNF,
    assumptions: Optional[Iterable[Literal]] = None,
    num_vars: Optional[int] = None,
    stats: Optional[SatStats] = None,
) -> SatResult:
    """Functional entry point for solving a CNF formula with optional assumptions."""
    solver = DpllSolver(clauses=clauses, num_vars=num_vars)
    result = solver.solve(assumptions=assumptions)
    if stats is not None:
        stats.add(result.stats)
    return result