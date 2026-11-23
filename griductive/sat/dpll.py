"""DPLL SAT solver with unit propagation, optional pure literal elimination,
MOM branching heuristic, conflict detection, assumptions, and timeout handling.
"""
from __future__ import annotations

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

_TIMEOUT_CHECK_INTERVAL = 256


class _DpllTimeout(Exception):
    """Internal exception raised when a DPLL solve call exceeds its time limit."""


def _check_timeout(deadline: Optional[float]) -> None:
    """Raise _DpllTimeout if the monotonic deadline has been reached."""
    if deadline is not None and time.perf_counter() >= deadline:
        raise _DpllTimeout()


def _validate_timeout(timeout: Optional[float]) -> None:
    """Validate that an optional timeout (in seconds) is non-negative."""
    if timeout is not None and timeout < 0:
        raise ValueError("timeout must be non-negative.")


def _lit_value(lit: Literal, assignment: Assignment) -> Optional[bool]:
    """Return the truth value of a DIMACS literal under the current assignment."""
    val = assignment.get(abs(lit))
    if val is None:
        return None
    return val if lit > 0 else not val


def _normalize_clauses(clauses: CNF) -> List[Tuple[Literal, ...]]:
    """Deduplicate literals in each clause and drop tautological clauses.

    Preserves empty clauses so UNSAT formulas are detected immediately.
    """
    normalized: List[Tuple[Literal, ...]] = []
    for clause in clauses:
        if not clause:
            normalized.append(())
            continue

        seen: Set[Literal] = set()
        deduped: List[Literal] = []
        is_tautology = False
        for lit in clause:
            if lit == 0:
                raise ValueError("DIMACS literal cannot be 0.")
            if -lit in seen:
                is_tautology = True
                break
            if lit not in seen:
                seen.add(lit)
                deduped.append(lit)

        if not is_tautology:
            normalized.append(tuple(deduped))

    return normalized


def unit_propagate(
    clauses: CNF,
    assignment: Assignment,
    stats: Optional[SatStats] = None,
    deadline: Optional[float] = None,
) -> Tuple[bool, Assignment]:
    """Perform iterative unit propagation and conflict detection on a CNF formula.

    Returns (True, updated_assignment) if no conflict is detected, or
    (False, updated_assignment) immediately upon encountering a falsified clause.
    Raises _DpllTimeout if `deadline` is exceeded.
    """
    working = dict(assignment)

    changed = True
    while changed:
        _check_timeout(deadline)
        changed = False
        for idx, clause in enumerate(clauses):
            if idx % _TIMEOUT_CHECK_INTERVAL == 0:
                _check_timeout(deadline)

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
                    if unassigned_lit is None:
                        unassigned_lit = lit
                        unassigned_count = 1
                    elif lit != unassigned_lit:
                        unassigned_count += 1
                        break

            if satisfied:
                continue

            # All literals in the clause evaluated to False -> Conflict!
            if unassigned_count == 0:
                return False, working

            # Exactly one unique unassigned literal remains -> Unit clause!
            if unassigned_count == 1 and unassigned_lit is not None:
                var = abs(unassigned_lit)
                val = unassigned_lit > 0
                working[var] = val
                if stats is not None:
                    stats.propagations += 1
                changed = True

    return True, working


def pure_literal_eliminate(
    clauses: CNF,
    assignment: Assignment,
    stats: Optional[SatStats] = None,
    deadline: Optional[float] = None,
) -> Assignment:
    """Assign all pure literals in currently unsatisfied clauses to satisfy them.

    A literal is pure if its variable is currently unassigned and appears with
    only one polarity (either only positive or only negative) across all
    unsatisfied clauses. Iterates until a fixed point is reached.
    """
    working = dict(assignment)

    while True:
        _check_timeout(deadline)
        pos_vars: Set[int] = set()
        neg_vars: Set[int] = set()

        for idx, clause in enumerate(clauses):
            if idx % _TIMEOUT_CHECK_INTERVAL == 0:
                _check_timeout(deadline)

            satisfied = False
            clause_pos: List[int] = []
            clause_neg: List[int] = []

            for lit in clause:
                val = _lit_value(lit, working)
                if val is True:
                    satisfied = True
                    break
                if val is None:
                    if lit > 0:
                        clause_pos.append(lit)
                    else:
                        clause_neg.append(-lit)

            if not satisfied:
                pos_vars.update(clause_pos)
                neg_vars.update(clause_neg)

        pure_pos = pos_vars - neg_vars
        pure_neg = neg_vars - pos_vars

        if not pure_pos and not pure_neg:
            break

        for var in sorted(pure_pos):
            working[var] = True
            if stats is not None:
                stats.propagations += 1
        for var in sorted(pure_neg):
            working[var] = False
            if stats is not None:
                stats.propagations += 1

    return working


def _filter_unsatisfied_clauses(
    clauses: Sequence[Tuple[Literal, ...]],
    assignment: Assignment,
) -> List[Tuple[Literal, ...]]:
    """Return only clauses not yet satisfied under `assignment`."""
    remaining: List[Tuple[Literal, ...]] = []
    for clause in clauses:
        if not any(_lit_value(lit, assignment) is True for lit in clause):
            remaining.append(clause)
    return remaining


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


def _pick_branch_literal(
    clauses: Sequence[Tuple[Literal, ...]],
    variables: Sequence[int],
    assignment: Assignment,
    use_heuristic: bool = True,
) -> Tuple[Optional[int], Tuple[bool, bool]]:
    """Select the next branching variable and preferred truth-value order.

    When `use_heuristic=True`, applies the MOM (Maximum Occurrences in clauses
    of Minimum size) heuristic across currently unsatisfied clauses to trigger
    unit propagation aggressively on structured puzzles (e.g., 5x5 Griductive).
    """
    if not use_heuristic:
        return _pick_variable(variables, assignment), (True, False)

    min_len: Optional[int] = None
    pos_counts: Dict[int, int] = {}
    neg_counts: Dict[int, int] = {}

    for clause in clauses:
        unassigned: List[Literal] = []
        satisfied = False
        for lit in clause:
            val = _lit_value(lit, assignment)
            if val is True:
                satisfied = True
                break
            if val is None:
                unassigned.append(lit)

        if satisfied or not unassigned:
            continue

        clen = len(unassigned)
        if min_len is None or clen < min_len:
            min_len = clen
            pos_counts.clear()
            neg_counts.clear()
        if clen == min_len:
            for lit in unassigned:
                var = abs(lit)
                if lit > 0:
                    pos_counts[var] = pos_counts.get(var, 0) + 1
                else:
                    neg_counts[var] = neg_counts.get(var, 0) + 1

    candidates = set(pos_counts) | set(neg_counts)
    if not candidates:
        return _pick_variable(variables, assignment), (True, False)

    best_var = max(
        candidates,
        key=lambda v: (
            pos_counts.get(v, 0) + neg_counts.get(v, 0),
            max(pos_counts.get(v, 0), neg_counts.get(v, 0)),
            -v,
        ),
    )
    branch_order = (
        (True, False)
        if pos_counts.get(best_var, 0) >= neg_counts.get(best_var, 0)
        else (False, True)
    )
    return best_var, branch_order


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
    """DPLL SAT solver supporting assumptions, unit propagation, optional pure
    literal elimination, MOM branching heuristic, timeout handling, and stats.
    """

    def __init__(
        self,
        clauses: Optional[CNF] = None,
        num_vars: Optional[int] = None,
        use_pure_literal: bool = True,
        timeout: Optional[float] = None,
        use_heuristic: bool = True,
    ) -> None:
        """Initialize the solver with an optional base CNF formula and options."""
        _validate_timeout(timeout)
        self._base_clauses: List[Tuple[Literal, ...]] = (
            [tuple(c) for c in clauses] if clauses else []
        )
        self._num_vars = num_vars
        self._use_pure_literal = bool(use_pure_literal)
        self._timeout = timeout
        self._use_heuristic = bool(use_heuristic)
        self.stats = SatStats()
        self._last_call_stats = SatStats()

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
        self._last_call_stats.reset()

    @property
    def last_stats(self) -> Dict[str, float | int]:
        """Return the dictionary of statistics from the most recent solve() call."""
        return getattr(self, "_last_call_stats", SatStats()).to_dict()

    def get_stats_dict(self) -> Dict[str, float | int]:
        """Return cumulative solver statistics as a dictionary."""
        return self.stats.to_dict()

    def solve(
        self,
        clauses: Optional[CNF] = None,
        assumptions: Optional[Iterable[Literal]] = None,
        num_vars: Optional[int] = None,
        timeout: Optional[float] = None,
        use_pure_literal: Optional[bool] = None,
    ) -> SatResult:
        """Solve the CNF formula under optional unit assumptions using DPLL.

        Args:
            clauses: Optional additional clauses merged with base clauses.
            assumptions: Optional iterable of DIMACS unit literals.
            num_vars: Optional total number of variables for model completion.
            timeout: Optional per-call timeout in seconds (overrides solver default).
            use_pure_literal: Optional override to enable/disable pure literal elimination.

        Returns:
            SatResult with `satisfiable`, `model`, `stats`, and `timed_out`.
        """
        effective_timeout = self._timeout if timeout is None else timeout
        _validate_timeout(effective_timeout)
        effective_pure = (
            self._use_pure_literal if use_pure_literal is None else bool(use_pure_literal)
        )

        start_time = time.perf_counter()
        deadline = (
            start_time + effective_timeout if effective_timeout is not None else None
        )
        call_stats = SatStats(sat_calls=1)

        raw_clauses: List[Tuple[Literal, ...]]
        if clauses is not None:
            raw_clauses = self._base_clauses + [tuple(c) for c in clauses]
        else:
            raw_clauses = list(self._base_clauses)

        total_vars = num_vars if num_vars is not None else self._num_vars
        variables = _collect_variables(raw_clauses, assumptions, total_vars)
        active_clauses = _normalize_clauses(raw_clauses)

        # 1. Apply assumptions and check for immediate contradiction among assumptions
        consistent, initial_assign = _apply_assumptions(assumptions)
        if not consistent:
            call_stats.runtime_ms = (time.perf_counter() - start_time) * 1000.0
            self._last_call_stats = call_stats
            self.stats.add(call_stats)
            return SatResult(
                satisfiable=False, model=None, stats=call_stats, timed_out=False
            )

        # 2. Run recursive DPLL with timeout protection
        try:
            sat, final_assign = self._dpll_recursive(
                active_clauses,
                variables,
                initial_assign,
                call_stats,
                deadline=deadline,
                use_pure_literal=effective_pure,
            )
        except _DpllTimeout:
            call_stats.runtime_ms = (time.perf_counter() - start_time) * 1000.0
            self._last_call_stats = call_stats
            self.stats.add(call_stats)
            return SatResult(
                satisfiable=False, model=None, stats=call_stats, timed_out=True
            )

        call_stats.runtime_ms = (time.perf_counter() - start_time) * 1000.0
        self._last_call_stats = call_stats
        self.stats.add(call_stats)

        if sat and final_assign is not None:
            complete_model = _complete_assignment(variables, final_assign)
            return SatResult(
                satisfiable=True, model=complete_model, stats=call_stats, timed_out=False
            )

        return SatResult(
            satisfiable=False, model=None, stats=call_stats, timed_out=False
        )

    def _dpll_recursive(
        self,
        clauses: Sequence[Tuple[Literal, ...]],
        variables: Sequence[int],
        assignment: Assignment,
        stats: SatStats,
        deadline: Optional[float] = None,
        use_pure_literal: bool = True,
    ) -> Tuple[bool, Optional[Assignment]]:
        """Execute recursive DPLL search with propagation, optional pure literal
        elimination, clause filtering, MOM branching, and timeout checks.
        """
        _check_timeout(deadline)

        ok, propagated = unit_propagate(clauses, assignment, stats, deadline=deadline)
        if not ok:
            return False, None

        remaining_clauses = _filter_unsatisfied_clauses(clauses, propagated)
        if not remaining_clauses:
            return True, propagated

        if use_pure_literal:
            propagated = pure_literal_eliminate(
                remaining_clauses, propagated, stats, deadline=deadline
            )
            remaining_clauses = _filter_unsatisfied_clauses(
                remaining_clauses, propagated
            )
            if not remaining_clauses:
                return True, propagated

        var, branch_order = _pick_branch_literal(
            remaining_clauses,
            variables,
            propagated,
            use_heuristic=self._use_heuristic,
        )
        if var is None:
            if _all_clauses_satisfied(remaining_clauses, propagated):
                return True, propagated
            return False, None

        for branch_val in branch_order:
            _check_timeout(deadline)
            stats.decisions += 1
            next_assignment = dict(propagated)
            next_assignment[var] = branch_val

            sat, result_assign = self._dpll_recursive(
                remaining_clauses,
                variables,
                next_assignment,
                stats,
                deadline=deadline,
                use_pure_literal=use_pure_literal,
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
    use_pure_literal: bool = True,
    timeout: Optional[float] = None,
    use_heuristic: bool = True,
) -> SatResult:
    """Functional entry point for solving a CNF formula with optional assumptions,
    pure literal elimination, and timeout handling.
    """
    solver = DpllSolver(
        clauses=clauses,
        num_vars=num_vars,
        use_pure_literal=use_pure_literal,
        timeout=timeout,
        use_heuristic=use_heuristic,
    )
    result = solver.solve(assumptions=assumptions)
    if stats is not None:
        stats.add(result.stats)
    return result