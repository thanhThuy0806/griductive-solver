"""Comprehensive unit tests for the updated DPLL solver and SatStats data structures."""
from __future__ import annotations

import unittest

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


class TestSatStatsUpdated(unittest.TestCase):
    """Test the newly added dictionary-like behaviors of SatStats."""

    def test_stats_getitem_and_alias(self):
        """Case 1: Test __getitem__ normal access and 'runtime' alias."""
        stats = SatStats(sat_calls=2, decisions=10, runtime_ms=15.5)
        self.assertEqual(stats["sat_calls"], 2)
        self.assertEqual(stats["decisions"], 10)
        self.assertEqual(stats["runtime"], 15.5)  # alias
        self.assertEqual(stats["runtime_ms"], 15.5)

    def test_stats_getitem_invalid(self):
        """Case 2: Test __getitem__ raises KeyError for invalid keys."""
        stats = SatStats()
        with self.assertRaises(KeyError):
            _ = stats["invalid_key"]

    def test_stats_contains_and_get(self):
        """Case 3: Test __contains__ (in operator) and .get() with defaults."""
        stats = SatStats(backtracks=5, runtime_ms=2.0)
        self.assertIn("backtracks", stats)
        self.assertIn("runtime", stats)
        self.assertNotIn("unknown", stats)
        
        self.assertEqual(stats.get("backtracks"), 5)
        self.assertEqual(stats.get("runtime"), 2.0)
        self.assertEqual(stats.get("unknown", "default"), "default")

    def test_stats_dict_views(self):
        """Case 4: Test keys(), values(), and items()."""
        stats = SatStats(sat_calls=1, decisions=2, propagations=3, backtracks=4, runtime_ms=5.0)
        keys = list(stats.keys())
        self.assertCountEqual(keys, ["sat_calls", "decisions", "propagations", "backtracks", "runtime_ms"])
        
        values = list(stats.values())
        self.assertCountEqual(values, [1, 2, 3, 4, 5.0])
        
        items = dict(stats.items())
        self.assertEqual(items["propagations"], 3)

    def test_stats_add_dict(self):
        """Case 5: Test adding a raw dictionary to SatStats."""
        stats = SatStats(sat_calls=1)
        raw_dict = {"sat_calls": 2, "decisions": 10, "runtime": 100.0}
        stats.add(raw_dict)
        self.assertEqual(stats.sat_calls, 3)
        self.assertEqual(stats.decisions, 10)
        self.assertEqual(stats.runtime_ms, 100.0)


class TestDpllSolverStats(unittest.TestCase):
    """Test DPLL solver's per-call and cumulative statistics tracking."""

    def test_solver_last_stats_sat(self):
        """Case 1: last_stats after a successful SAT call."""
        solver = DpllSolver([[1, 2], [-1, 3]], num_vars=3)
        res = solver.solve()
        self.assertTrue(res.satisfiable)
        last = solver.last_stats
        self.assertEqual(last["sat_calls"], 1)
        self.assertIn("runtime_ms", last)

    def test_solver_last_stats_unsat(self):
        """Case 2: last_stats after an UNSAT call."""
        solver = DpllSolver([[1], [-1]], num_vars=1)
        res = solver.solve()
        self.assertFalse(res.satisfiable)
        last = solver.last_stats
        self.assertEqual(last["sat_calls"], 1)
        self.assertIn("runtime_ms", last)

    def test_solver_cumulative_stats(self):
        """Case 3: Cumulative stats across multiple calls."""
        solver = DpllSolver(num_vars=2)
        solver.solve([[1, 2]])
        solver.solve([[-1, -2]])
        
        cum_stats = solver.get_stats_dict()
        self.assertEqual(cum_stats["sat_calls"], 2)
        # last_stats should only reflect the most recent call
        self.assertEqual(solver.last_stats["sat_calls"], 1)

    def test_solver_reset_stats(self):
        """Case 4: reset_stats clears both cumulative and last call stats."""
        solver = DpllSolver([[1]], num_vars=1)
        solver.solve()
        solver.reset_stats()
        self.assertEqual(solver.get_stats_dict()["sat_calls"], 0)
        self.assertEqual(solver.last_stats["sat_calls"], 0)

    def test_solver_assumption_conflict_stats(self):
        """Case 5: Stats tracked correctly when assumptions immediately conflict."""
        solver = DpllSolver([[1, 2]], num_vars=2)
        res = solver.solve(assumptions=[1, -1])  # Immediate conflict
        self.assertFalse(res.satisfiable)
        self.assertEqual(res.stats.sat_calls, 1)
        self.assertEqual(res.stats.decisions, 0)
        self.assertGreaterEqual(res.stats.runtime_ms, 0.0)


class TestUnitPropagate(unittest.TestCase):
    """Test core inference function: unit propagation (5 cases)."""

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
        ok, assign = unit_propagate([[-1, 2], [-2, 3], [-3, -4]], {1: True}, stats)
        self.assertTrue(ok)
        self.assertEqual(assign, {1: True, 2: True, 3: True, 4: False})
        self.assertEqual(stats.propagations, 3)

    def test_up_conflict(self):
        ok, _ = unit_propagate([[1, 2], [-2]], {1: False})
        self.assertFalse(ok)


class TestApplyAssumptions(unittest.TestCase):
    """Test assumption handling (5 cases)."""

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
        ok, _ = _apply_assumptions([2], base_assignment={1: True, 2: False})
        self.assertFalse(ok)

    def test_aa_zero_literal(self):
        with self.assertRaises(ValueError):
            _apply_assumptions([0])

if __name__ == "__main__":
    unittest.main()