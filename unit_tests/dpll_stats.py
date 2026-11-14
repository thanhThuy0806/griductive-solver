"""Unit tests for the exact cardinality and logic extensions in griductive.logic."""
from __future__ import annotations

import unittest

try:
    from griductive.sat.stats import SatStats, SatResult
except ImportError:
    from griductive.sat.stats import SatStats, SatResult


class TestSatStats(unittest.TestCase):

    def test_sat_stats_initialization(self):
        stats = SatStats()
        self.assertEqual(stats.sat_calls, 0)
        self.assertEqual(stats.decisions, 0)
        self.assertEqual(stats.propagations, 0)
        self.assertEqual(stats.backtracks, 0)
        self.assertEqual(stats.runtime_ms, 0.0)

    def test_sat_stats_reset(self):
        stats = SatStats(sat_calls=5, decisions=10, propagations=20, backtracks=3, runtime_ms=15.5)
        stats.reset()
        self.assertEqual(stats.sat_calls, 0)
        self.assertEqual(stats.decisions, 0)
        self.assertEqual(stats.propagations, 0)
        self.assertEqual(stats.backtracks, 0)
        self.assertEqual(stats.runtime_ms, 0.0)

    def test_sat_stats_add(self):
        stats1 = SatStats(sat_calls=1, decisions=5, propagations=10, backtracks=2, runtime_ms=10.0)
        stats2 = SatStats(sat_calls=2, decisions=10, propagations=20, backtracks=4, runtime_ms=20.0)
        stats1.add(stats2)
        
        self.assertEqual(stats1.sat_calls, 3)
        self.assertEqual(stats1.decisions, 15)
        self.assertEqual(stats1.propagations, 30)
        self.assertEqual(stats1.backtracks, 6)
        self.assertEqual(stats1.runtime_ms, 30.0)
        
        # stats2 should remain unchanged
        self.assertEqual(stats2.sat_calls, 2)

    def test_sat_stats_to_dict(self):
        stats = SatStats(sat_calls=1, decisions=5, propagations=10, backtracks=2, runtime_ms=10.5)
        stats_dict = stats.to_dict()
        
        expected = {
            "sat_calls": 1,
            "decisions": 5,
            "propagations": 10,
            "backtracks": 2,
            "runtime_ms": 10.5,
        }
        self.assertEqual(stats_dict, expected)

    def test_sat_stats_default_add(self):
        stats1 = SatStats()
        stats2 = SatStats(sat_calls=1, decisions=1)
        stats1.add(stats2)
        self.assertEqual(stats1.sat_calls, 1)
        self.assertEqual(stats1.decisions, 1)


class TestSatResult(unittest.TestCase):

    def test_sat_result_sat_initialization(self):
        stats = SatStats(runtime_ms=5.0)
        result = SatResult(satisfiable=True, model={1: True, 2: False}, stats=stats)
        
        self.assertTrue(result.satisfiable)
        self.assertEqual(result.model, {1: True, 2: False})
        self.assertIs(result.stats, stats)

    def test_sat_result_unsat_initialization(self):
        result = SatResult(satisfiable=False, model=None)
        
        self.assertFalse(result.satisfiable)
        self.assertIsNone(result.model)
        self.assertIsInstance(result.stats, SatStats)
        self.assertEqual(result.stats.runtime_ms, 0.0)

    def test_sat_result_unpacking_sat(self):
        result = SatResult(satisfiable=True, model={1: True})
        sat, model = result
        
        self.assertTrue(sat)
        self.assertEqual(model, {1: True})

    def test_sat_result_unpacking_unsat(self):
        result = SatResult(satisfiable=False, model=None)
        sat, model = result
        
        self.assertFalse(sat)
        self.assertIsNone(model)
        
    def test_sat_result_immutable(self):
        result = SatResult(satisfiable=True, model={})
        with self.assertRaises(Exception):
            # dataclass(frozen=True) prevents modification
            result.satisfiable = False

if __name__ == "__main__":
    unittest.main()