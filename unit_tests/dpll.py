
"""Comprehensive unit tests for the updated DPLL solver and SatStats data structures."""

from __future__ import annotations

import unittest
import itertools

try:
    from griductive.sat.dpll import (
        DpllSolver, dpll_solve, unit_propagate, _apply_assumptions
    )
    from griductive.sat.stats import SatStats, SatResult
except ImportError:
    from dpll import (
        DpllSolver, dpll_solve, unit_propagate, _apply_assumptions
    )
    from stats import SatStats, SatResult


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
            runtime_ms=5.0
        )

        keys = list(stats.keys())
        self.assertCountEqual(
            keys,
            ["sat_calls", "decisions", "propagations", "backtracks", "runtime_ms"]
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

        last = solver.last_stats
        self.assertEqual(last["sat_calls"], 1)
        self.assertIn("runtime_ms", last)

    def test_solver_last_stats_unsat(self):
        solver = DpllSolver([[1], [-1]], num_vars=1)
        res = solver.solve()

        self.assertFalse(res.satisfiable)

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
            stats
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
            base_assignment={1: True, 2: False}
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


if __name__ == "__main__":
    unittest.main()
