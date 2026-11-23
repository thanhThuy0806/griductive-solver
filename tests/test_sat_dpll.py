"""Comprehensive unit tests for the DPLL solver, optional pure literal
elimination, MOM branching optimization, timeout handling, and 5x5 puzzles.
"""

from __future__ import annotations

import itertools
import time
import unittest
from typing import List, Sequence

try:
    from griductive.sat.dpll import (
        DpllSolver,
        _apply_assumptions,
        _normalize_clauses,
        _pick_branch_literal,
        dpll_solve,
        pure_literal_eliminate,
        unit_propagate,
    )
    from griductive.sat.stats import SatResult, SatStats
except ImportError:
    from dpll import (
        DpllSolver,
        _apply_assumptions,
        _normalize_clauses,
        _pick_branch_literal,
        dpll_solve,
        pure_literal_eliminate,
        unit_propagate,
    )
    from stats import SatResult, SatStats


def brute_force_solve(clauses: list[list[int]], num_vars: int) -> bool:
    """Brute-force iterate through 2^N cases to check with DPLL."""
    if not clauses:
        return True

    variables = list(range(1, num_vars + 1))

    for values in itertools.product([True, False], repeat=num_vars):
        assignment = dict(zip(variables, values))

        formula_satisfied = True

        for clause in clauses:
            clause_satisfied = False

            for lit in clause:
                var = abs(lit)
                val = assignment[var]

                if (lit > 0 and val) or (lit < 0 and not val):
                    clause_satisfied = True
                    break

            if not clause_satisfied:
                formula_satisfied = False
                break

        if formula_satisfied:
            return True

    return False


def _verify_model(clauses: Sequence[Sequence[int]], model: dict[int, bool]) -> bool:
    """Verify that every clause in `clauses` is satisfied by `model`."""
    for clause in clauses:
        if not any(
            (lit > 0 and model[abs(lit)]) or (lit < 0 and not model[abs(lit)])
            for lit in clause
        ):
            return False
    return True


def _at_most_clauses(vars_list: Sequence[int], k: int) -> List[List[int]]:
    """CNF encoding for 'at most k of vars_list are True' (mirrors cnf_encoder)."""
    return [[-v for v in comb] for comb in itertools.combinations(vars_list, k + 1)]


def _at_least_clauses(vars_list: Sequence[int], k: int) -> List[List[int]]:
    """CNF encoding for 'at least k of vars_list are True' (mirrors cnf_encoder)."""
    n = len(vars_list)
    return [list(comb) for comb in itertools.combinations(vars_list, n - k + 1)]


def _exactly_clauses(vars_list: Sequence[int], k: int) -> List[List[int]]:
    """CNF encoding for 'exactly k of vars_list are True'."""
    return _at_most_clauses(vars_list, k) + _at_least_clauses(vars_list, k)


def _pigeonhole_cnf(pigeons: int, holes: int) -> List[List[int]]:
    """Generate UNSAT Pigeonhole Principle CNF: `pigeons` into `holes` (pigeons > holes)."""
    def var(p: int, h: int) -> int:
        return p * holes + h + 1

    clauses: List[List[int]] = []
    # Each pigeon must be in at least one hole
    for p in range(pigeons):
        clauses.append([var(p, h) for h in range(holes)])
    # No two pigeons share the same hole
    for h in range(holes):
        for p1 in range(pigeons):
            for p2 in range(p1 + 1, pigeons):
                clauses.append([-var(p1, h), -var(p2, h)])
    return clauses


def _build_5x5_griductive_puzzle() -> tuple[List[List[int]], dict[int, bool]]:
    """Construct a realistic 5x5 Griductive puzzle (25 vars) with a known solution.

    Uses the same clause patterns as `griductive/logic/cnf_encoder.py`:
    FACT, SAME, DIFFERENT, AT_MOST, AT_LEAST, and EXACTLY over rows, columns,
    and 3x3 neighborhoods.
    """
    # Known 5x5 ground-truth criminal layout (1 = Criminal/True, 0 = Innocent/False)
    grid = [
        [1, 0, 1, 0, 0],
        [0, 1, 0, 1, 0],
        [1, 0, 0, 0, 1],
        [0, 0, 1, 1, 0],
        [0, 1, 0, 0, 1],
    ]
    solution = {r * 5 + c + 1: bool(grid[r][c]) for r in range(5) for c in range(5)}

    clauses: List[List[int]] = []
    # Row EXACTLY constraints (each row has 2 criminals)
    for r in range(5):
        row_vars = [r * 5 + c + 1 for c in range(5)]
        clauses.extend(_exactly_clauses(row_vars, sum(grid[r])))

    # Column EXACTLY constraints (each column has 2 criminals)
    for c in range(5):
        col_vars = [r * 5 + c + 1 for r in range(5)]
        col_sum = sum(grid[r][c] for r in range(5))
        clauses.extend(_exactly_clauses(col_vars, col_sum))

    # Diagonal AT_MOST / AT_LEAST constraints
    main_diag = [i * 5 + i + 1 for i in range(5)]
    clauses.extend(_exactly_clauses(main_diag, sum(grid[i][i] for i in range(5))))

    anti_diag = [i * 5 + (4 - i) + 1 for i in range(5)]
    clauses.extend(_at_most_clauses(anti_diag, 2))
    clauses.extend(_at_least_clauses(anti_diag, 1))

    # SAME / DIFFERENT clues between cells
    # (0,0)=1 and (0,2)=1 -> SAME
    clauses.extend([[-1, 3], [1, -3]])
    # (0,0)=1 and (0,1)=0 -> DIFFERENT
    clauses.extend([[1, 2], [-1, -2]])
    # (2,4)=1 and (4,4)=1 -> SAME
    clauses.extend([[-15, 25], [15, -25]])
    # (1,1)=1 and (2,2)=0 -> DIFFERENT
    clauses.extend([[7, 13], [-7, -13]])

    # A couple of revealed FACT clues
    clauses.append([1])    # (0,0) is Criminal
    clauses.append([-13])  # (2,2) is Innocent

    return clauses, solution


class TestSatStatsUpdated(unittest.TestCase):
    """Test the newly added dictionary-like behaviors of SatStats."""

    def test_stats_getitem_and_alias(self):
        stats = SatStats(sat_calls=2, decisions=10, runtime_ms=15.5)
        self.assertEqual(stats["sat_calls"], 2)
        self.assertEqual(stats["decisions"], 10)
        self.assertEqual(stats["runtime"], 15.5)
        self.assertEqual(stats["runtime_ms"], 15.5)

    def test_stats_getitem_invalid(self):
        stats = SatStats()
        with self.assertRaises(KeyError):
            _ = stats["invalid_key"]

    def test_stats_contains_and_get(self):
        stats = SatStats(backtracks=5, runtime_ms=2.0)
        self.assertIn("backtracks", stats)
        self.assertIn("runtime", stats)
        self.assertNotIn("unknown", stats)

        self.assertEqual(stats.get("backtracks"), 5)
        self.assertEqual(stats.get("runtime"), 2.0)
        self.assertEqual(stats.get("unknown", "default"), "default")

    def test_stats_dict_views(self):
        stats = SatStats(
            sat_calls=1,
            decisions=2,
            propagations=3,
            backtracks=4,
            runtime_ms=5.0,
        )

        keys = list(stats.keys())
        self.assertCountEqual(
            keys,
            ["sat_calls", "decisions", "propagations", "backtracks", "runtime_ms"],
        )

        values = list(stats.values())
        self.assertCountEqual(values, [1, 2, 3, 4, 5.0])

        items = dict(stats.items())
        self.assertEqual(items["propagations"], 3)

    def test_stats_add_dict(self):
        stats = SatStats(sat_calls=1)
        raw_dict = {"sat_calls": 2, "decisions": 10, "runtime": 100.0}

        stats.add(raw_dict)

        self.assertEqual(stats.sat_calls, 3)
        self.assertEqual(stats.decisions, 10)
        self.assertEqual(stats.runtime_ms, 100.0)


class TestDpllSolverStats(unittest.TestCase):
    """Test DPLL solver's per-call and cumulative statistics tracking."""

    def test_solver_last_stats_sat(self):
        solver = DpllSolver([[1, 2], [-1, 3]], num_vars=3)
        res = solver.solve()

        self.assertTrue(res.satisfiable)
        self.assertFalse(res.timed_out)

        last = solver.last_stats
        self.assertEqual(last["sat_calls"], 1)
        self.assertIn("runtime_ms", last)

    def test_solver_last_stats_unsat(self):
        solver = DpllSolver([[1], [-1]], num_vars=1)
        res = solver.solve()

        self.assertFalse(res.satisfiable)
        self.assertFalse(res.timed_out)

        last = solver.last_stats
        self.assertEqual(last["sat_calls"], 1)
        self.assertIn("runtime_ms", last)

    def test_solver_cumulative_stats(self):
        solver = DpllSolver(num_vars=2)
        solver.solve([[1, 2]])
        solver.solve([[-1, -2]])

        cum_stats = solver.get_stats_dict()

        self.assertEqual(cum_stats["sat_calls"], 2)
        self.assertEqual(solver.last_stats["sat_calls"], 1)

    def test_solver_reset_stats(self):
        solver = DpllSolver([[1]], num_vars=1)
        solver.solve()
        solver.reset_stats()

        self.assertEqual(solver.get_stats_dict()["sat_calls"], 0)
        self.assertEqual(solver.last_stats["sat_calls"], 0)

    def test_solver_assumption_conflict_stats(self):
        solver = DpllSolver([[1, 2]], num_vars=2)
        res = solver.solve(assumptions=[1, -1])

        self.assertFalse(res.satisfiable)
        self.assertFalse(res.timed_out)
        self.assertEqual(res.stats.sat_calls, 1)
        self.assertEqual(res.stats.decisions, 0)
        self.assertGreaterEqual(res.stats.runtime_ms, 0.0)


class TestUnitPropagate(unittest.TestCase):
    """Test core inference function: unit propagation."""

    def test_up_empty(self):
        ok, assign = unit_propagate([], {})
        self.assertTrue(ok)
        self.assertEqual(assign, {})

    def test_up_no_propagation(self):
        ok, assign = unit_propagate([[1, 2], [3, 4]], {})
        self.assertTrue(ok)
        self.assertEqual(assign, {})

    def test_up_single_propagation(self):
        stats = SatStats()
        ok, assign = unit_propagate([[1, 2]], {1: False}, stats)

        self.assertTrue(ok)
        self.assertEqual(assign, {1: False, 2: True})
        self.assertEqual(stats.propagations, 1)

    def test_up_cascade(self):
        stats = SatStats()
        ok, assign = unit_propagate(
            [[-1, 2], [-2, 3], [-3, -4]],
            {1: True},
            stats,
        )

        self.assertTrue(ok)
        self.assertEqual(assign, {1: True, 2: True, 3: True, 4: False})
        self.assertEqual(stats.propagations, 3)

    def test_up_conflict(self):
        ok, _ = unit_propagate([[1, 2], [-2]], {1: False})
        self.assertFalse(ok)


class TestApplyAssumptions(unittest.TestCase):
    """Test assumption handling."""

    def test_aa_none(self):
        ok, assign = _apply_assumptions(None)
        self.assertTrue(ok)
        self.assertEqual(assign, {})

    def test_aa_normal(self):
        ok, assign = _apply_assumptions([1, -2, 3])
        self.assertTrue(ok)
        self.assertEqual(assign, {1: True, 2: False, 3: True})

    def test_aa_contradictory_assumptions(self):
        ok, _ = _apply_assumptions([1, 2, -1])
        self.assertFalse(ok)

    def test_aa_conflict_with_base(self):
        ok, _ = _apply_assumptions(
            [2],
            base_assignment={1: True, 2: False},
        )
        self.assertFalse(ok)

    def test_aa_zero_literal(self):
        with self.assertRaises(ValueError):
            _apply_assumptions([0])


class TestDpllSolver(unittest.TestCase):
    """Test unit propagation, conflict detection, branching, and assumptions."""

    def test_brute_force_crosscheck_spec_example(self) -> None:
        kb = [[1, 2], [-1, 2]]

        is_sat_brute = brute_force_solve(kb, num_vars=2)
        res_dpll = dpll_solve(kb, num_vars=2)

        self.assertEqual(is_sat_brute, res_dpll.satisfiable)
        self.assertTrue(res_dpll.satisfiable)
        self.assertTrue(res_dpll.model[2])

    def test_entailment_example_from_spec(self) -> None:
        kb = [[1, 2], [-1, 2]]
        solver = DpllSolver(kb, num_vars=2)

        res_b_innocent = solver.solve(assumptions=[-2])
        self.assertFalse(res_b_innocent.satisfiable)

        self.assertTrue(solver.solve(assumptions=[1]).satisfiable)
        self.assertTrue(solver.solve(assumptions=[-1]).satisfiable)

    def test_branching_and_backtracking_unsat_3sat(self) -> None:
        clauses = [
            [1, 2, 3], [1, 2, -3], [1, -2, 3], [1, -2, -3],
            [-1, 2, 3], [-1, 2, -3], [-1, -2, 3], [-1, -2, -3],
        ]

        is_sat_brute = brute_force_solve(clauses, num_vars=3)
        res_dpll = dpll_solve(clauses, num_vars=3)

        self.assertEqual(is_sat_brute, res_dpll.satisfiable)
        self.assertFalse(res_dpll.satisfiable)
        self.assertGreater(res_dpll.stats.decisions, 0)
        self.assertGreater(res_dpll.stats.backtracks, 0)

    def test_contradictory_assumptions(self) -> None:
        res = dpll_solve([[1, 2]], assumptions=[1, -1])

        self.assertFalse(res.satisfiable)
        self.assertIsNone(res.model)


class TestPureLiteralEliminate(unittest.TestCase):
    """Test optional pure literal elimination (direct helper + solver toggle)."""

    def test_pure_literal_empty_and_no_pure(self) -> None:
        self.assertEqual(pure_literal_eliminate([], {}), {})
        # Both 1 and 2 appear positively and negatively -> no pure literals
        assign = pure_literal_eliminate([[1, 2], [-1, -2]], {})
        self.assertEqual(assign, {})

    def test_pure_literal_positive_and_negative(self) -> None:
        stats = SatStats()
        # Var 1 appears only positively, var 3 only negatively, var 2 mixed
        clauses = [[1, 2], [-2, -3]]
        assign = pure_literal_eliminate(clauses, {}, stats=stats)

        self.assertEqual(assign, {1: True, 3: False})
        self.assertEqual(stats.propagations, 2)

    def test_pure_literal_cascade(self) -> None:
        # Initially only var 1 is pure positive; var 2 appears as +2 and -2.
        # Satisfying [1, -2] via 1=True leaves only [2, 3] and [2, -3],
        # making var 2 pure positive in the next pass!
        clauses = [[1, -2], [2, 3], [2, -3]]
        assign = pure_literal_eliminate(clauses, {})

        self.assertEqual(assign.get(1), True)
        self.assertEqual(assign.get(2), True)
        self.assertTrue(_verify_model(clauses, {1: True, 2: True, 3: False}))

    def test_pure_literal_ignores_satisfied_clauses_and_preserves_assumptions(self) -> None:
        # Clause [1, -2] is already satisfied by {1: True}; in remaining [2, 3],
        # var 2 is pure positive and var 3 is pure positive.
        clauses = [[1, -2], [2, 3]]
        assign = pure_literal_eliminate(clauses, {1: True})

        self.assertEqual(assign, {1: True, 2: True, 3: True})

    def test_optional_pure_literal_toggle_and_crosscheck(self) -> None:
        # Formula solvable entirely by pure literal elimination with 0 decisions
        clauses = [[1, 2], [2, 3], [3, -4], [-4, 5]]

        res_with_pure = dpll_solve(clauses, num_vars=5, use_pure_literal=True)
        res_without_pure = dpll_solve(clauses, num_vars=5, use_pure_literal=False)

        self.assertTrue(res_with_pure.satisfiable)
        self.assertTrue(res_without_pure.satisfiable)
        self.assertTrue(_verify_model(clauses, res_with_pure.model))
        self.assertTrue(_verify_model(clauses, res_without_pure.model))
        self.assertEqual(res_with_pure.stats.decisions, 0)
        self.assertGreater(res_without_pure.stats.decisions, 0)

        # Per-call override on DpllSolver
        solver = DpllSolver(clauses, num_vars=5, use_pure_literal=False)
        res_override = solver.solve(use_pure_literal=True)
        self.assertTrue(res_override.satisfiable)
        self.assertEqual(res_override.stats.decisions, 0)

        # Brute-force agreement on mixed formula with assumptions
        mixed = [[1, 2, -3], [-1, 3, 4], [-2, -4], [2, 3, 4], [-1, -2, 4]]
        bf = brute_force_solve(mixed, num_vars=4)
        self.assertEqual(dpll_solve(mixed, num_vars=4, use_pure_literal=True).satisfiable, bf)
        self.assertEqual(dpll_solve(mixed, num_vars=4, use_pure_literal=False).satisfiable, bf)


class TestTimeoutHandling(unittest.TestCase):
    """Test timeout configuration, validation, and responsive termination."""

    def test_negative_timeout_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            DpllSolver([[1, 2]], timeout=-0.1)

        solver = DpllSolver([[1, 2]])
        with self.assertRaises(ValueError):
            solver.solve(timeout=-1.0)

    def test_zero_timeout_returns_timed_out_result(self) -> None:
        res = dpll_solve([[1, 2], [-1, 2]], num_vars=2, timeout=0.0)

        self.assertFalse(res.satisfiable)
        self.assertIsNone(res.model)
        self.assertTrue(res.timed_out)
        self.assertTrue(res.to_dict()["timed_out"])
        self.assertEqual(res.stats.sat_calls, 1)

    def test_hard_unsat_formula_respects_timeout_without_hanging(self) -> None:
        # PHP(9, 8) has 72 vars and is notoriously hard for resolution/DPLL
        php_clauses = _pigeonhole_cnf(pigeons=9, holes=8)
        budget_sec = 0.05

        start = time.perf_counter()
        res = dpll_solve(php_clauses, timeout=budget_sec)
        elapsed = time.perf_counter() - start

        self.assertTrue(res.timed_out)
        self.assertFalse(res.satisfiable)
        self.assertIsNone(res.model)
        # Must terminate promptly near the 50ms budget (no hanging)
        self.assertLess(elapsed, 0.5)
        self.assertGreater(res.stats.runtime_ms, 0.0)

    def test_generous_timeout_succeeds_normally(self) -> None:
        clauses = [[1, 2], [-1, 3], [-2, -3, 4], [1, -4]]
        res = dpll_solve(clauses, num_vars=4, timeout=2.0)

        self.assertTrue(res.satisfiable)
        self.assertFalse(res.timed_out)
        self.assertIsNotNone(res.model)
        self.assertTrue(_verify_model(clauses, res.model))

    def test_per_call_timeout_override_and_stats_accumulation(self) -> None:
        php_clauses = _pigeonhole_cnf(pigeons=9, holes=8)
        solver = DpllSolver(timeout=5.0)

        # Override with tight timeout on hard UNSAT formula -> times out
        res_timeout = solver.solve(clauses=php_clauses, timeout=0.03)
        self.assertTrue(res_timeout.timed_out)
        self.assertFalse(res_timeout.satisfiable)

        # Subsequent easy call with default 5.0s timeout succeeds cleanly
        res_ok = solver.solve(clauses=[[1, 2], [-1, 2]], num_vars=2)
        self.assertTrue(res_ok.satisfiable)
        self.assertFalse(res_ok.timed_out)
        self.assertEqual(solver.get_stats_dict()["sat_calls"], 2)


class TestOptimizationsAnd5x5Puzzle(unittest.TestCase):
    """Test clause normalization, MOM heuristic, and 5x5 puzzle performance."""

    def test_clause_normalization_dedup_and_tautology(self) -> None:
        # Duplicate literal [1, 1] becomes unit [1]; tautology [2, -2] is dropped
        norm = _normalize_clauses([[1, 1], [2, -2], [3, -1, 3]])
        self.assertEqual(norm, [(1,), (3, -1)])

        res = dpll_solve([[1, -1], [2, 2]], num_vars=2)
        self.assertTrue(res.satisfiable)
        self.assertTrue(res.model[2])
        self.assertEqual(res.stats.decisions, 0)

    def test_mom_branching_heuristic_prefers_shortest_clause_frequent_var(self) -> None:
        # Shortest clauses have size 2: [-3, 4] and [-3, 5] -> var 3 appears twice negatively
        clauses = [(1, 2, 6), (-3, 4), (-3, 5)]
        var, order = _pick_branch_literal(clauses, [1, 2, 3, 4, 5, 6], {}, use_heuristic=True)

        self.assertEqual(var, 3)
        self.assertEqual(order, (False, True))

        # With heuristic disabled, falls back to smallest variable index (1) and (True, False)
        var_plain, order_plain = _pick_branch_literal(
            clauses, [1, 2, 3, 4, 5, 6], {}, use_heuristic=False
        )
        self.assertEqual(var_plain, 1)
        self.assertEqual(order_plain, (True, False))

    def test_5x5_griductive_puzzle_solves_fast_without_hanging(self) -> None:
        clauses, _ = _build_5x5_griductive_puzzle()
        solver = DpllSolver(clauses, num_vars=25, use_pure_literal=True, timeout=2.0)

        res = solver.solve()

        self.assertFalse(res.timed_out)
        self.assertTrue(res.satisfiable)
        self.assertIsNotNone(res.model)
        self.assertEqual(len(res.model), 25)
        self.assertTrue(_verify_model(clauses, res.model))
        self.assertLess(res.stats.runtime_ms, 1000.0)

    def test_5x5_griductive_entailment_queries_all_25_cells(self) -> None:
        clauses, _ = _build_5x5_griductive_puzzle()
        solver = DpllSolver(clauses, num_vars=25, use_pure_literal=True, timeout=2.0)

        start = time.perf_counter()
        for var in range(1, 26):
            res_pos = solver.solve(assumptions=[var])
            res_neg = solver.solve(assumptions=[-var])
            self.assertFalse(res_pos.timed_out)
            self.assertFalse(res_neg.timed_out)
            # At least one polarity must be satisfiable for a valid SAT puzzle
            self.assertTrue(res_pos.satisfiable or res_neg.satisfiable)
        elapsed = time.perf_counter() - start

        self.assertEqual(solver.get_stats_dict()["sat_calls"], 50)
        self.assertLess(elapsed, 2.0)

    def test_5x5_unsat_cardinality_conflict_no_hang(self) -> None:
        # Impossible 5x5 grid: every row has exactly 2 criminals (total=10),
        # while every column has exactly 3 criminals (total=15) -> UNSAT!
        clauses: List[List[int]] = []
        for r in range(5):
            row_vars = [r * 5 + c + 1 for c in range(5)]
            clauses.extend(_exactly_clauses(row_vars, 2))
        for c in range(5):
            col_vars = [r * 5 + c + 1 for r in range(5)]
            clauses.extend(_exactly_clauses(col_vars, 3))

        start = time.perf_counter()
        res = dpll_solve(clauses, num_vars=25, timeout=1.0)
        elapsed = time.perf_counter() - start

        self.assertFalse(res.satisfiable)
        self.assertIsNone(res.model)
        # Must either prove UNSAT quickly or stop cleanly at the 1.0s timeout (never hang)
        self.assertLess(elapsed, 1.5)


if __name__ == "__main__":
    unittest.main()