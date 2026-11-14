"""Unit tests for the exact cardinality and logic extensions in griductive.logic."""
from __future__ import annotations

import unittest

# Assuming cnf_encoder and evaluator functions are available or mocked
# Since the user requested tests for DPLL and other files (excluding entailment),
# and the previous context built dpll.py, we will focus on exhaustive tests for dpll.py.

# The prompt asks for 5 test cases *each function* in dpll.py.
# Functions in dpll.py:
# 1. _lit_value
# 2. unit_propagate
# 3. _apply_assumptions
# 4. _collect_variables
# 5. _pick_variable
# 6. _all_clauses_satisfied
# 7. _complete_assignment
# 8. DpllSolver.add_clause / add_clauses / reset_stats (can be grouped)
# 9. DpllSolver.solve / _dpll_recursive (integration)

import unittest

try:
    from griductive.sat.dpll import (
        _lit_value,
        unit_propagate,
        _apply_assumptions,
        _collect_variables,
        _pick_variable,
        _all_clauses_satisfied,
        _complete_assignment,
        DpllSolver,
        dpll_solve
    )
    from griductive.sat.stats import SatStats
except ImportError:
    from unit_tests.dpll import (
        _lit_value,
        unit_propagate,
        _apply_assumptions,
        _collect_variables,
        _pick_variable,
        _all_clauses_satisfied,
        _complete_assignment,
        DpllSolver,
        dpll_solve
    )
    from griductive.sat.dpll import SatStats

class TestDpllInternals(unittest.TestCase):

    # --- 1. _lit_value ---
    def test_lit_value_unassigned(self):
        self.assertIsNone(_lit_value(1, {}))
        
    def test_lit_value_positive_true(self):
        self.assertTrue(_lit_value(1, {1: True}))
        
    def test_lit_value_positive_false(self):
        self.assertFalse(_lit_value(1, {1: False}))
        
    def test_lit_value_negative_true(self):
        self.assertTrue(_lit_value(-1, {1: False}))
        
    def test_lit_value_negative_false(self):
        self.assertFalse(_lit_value(-1, {1: True}))


    # --- 2. unit_propagate ---
    def test_up_empty_formula(self):
        ok, assign = unit_propagate([], {1: True})
        self.assertTrue(ok)
        self.assertEqual(assign, {1: True})
        
    def test_up_already_satisfied(self):
        ok, assign = unit_propagate([[1, 2]], {1: True})
        self.assertTrue(ok)
        self.assertEqual(assign, {1: True})

    def test_up_single_unit(self):
        ok, assign = unit_propagate([[1]], {})
        self.assertTrue(ok)
        self.assertEqual(assign, {1: True})

    def test_up_chain_reaction(self):
        # 1 -> -2 -> 3
        ok, assign = unit_propagate([[-1, -2], [2, 3]], {1: True})
        self.assertTrue(ok)
        self.assertEqual(assign, {1: True, 2: False, 3: True})

    def test_up_conflict_detected(self):
        ok, _ = unit_propagate([[1], [-1]], {})
        self.assertFalse(ok)


    # --- 3. _apply_assumptions ---
    def test_aa_none(self):
        ok, assign = _apply_assumptions(None)
        self.assertTrue(ok)
        self.assertEqual(assign, {})

    def test_aa_positive_and_negative(self):
        ok, assign = _apply_assumptions([1, -2])
        self.assertTrue(ok)
        self.assertEqual(assign, {1: True, 2: False})

    def test_aa_zero_raises_error(self):
        with self.assertRaises(ValueError):
            _apply_assumptions([0])

    def test_aa_conflict_within_assumptions(self):
        ok, _ = _apply_assumptions([1, -1])
        self.assertFalse(ok)

    def test_aa_conflict_with_base(self):
        ok, _ = _apply_assumptions([1], base_assignment={1: False})
        self.assertFalse(ok)


    # --- 4. _collect_variables ---
    def test_cv_empty(self):
        self.assertEqual(_collect_variables([]), [])

    def test_cv_from_clauses(self):
        self.assertEqual(_collect_variables([[-3, 1], [2]]), [1, 2, 3])

    def test_cv_from_assumptions(self):
        self.assertEqual(_collect_variables([], assumptions=[-4, 1]), [1, 4])

    def test_cv_with_num_vars(self):
        self.assertEqual(_collect_variables([[5]], num_vars=3), [1, 2, 3, 5])

    def test_cv_zero_raises_error(self):
        with self.assertRaises(ValueError):
            _collect_variables([[0]])


    # --- 5. _pick_variable ---
    def test_pv_empty_vars(self):
        self.assertIsNone(_pick_variable([], {}))

    def test_pv_all_assigned(self):
        self.assertIsNone(_pick_variable([1, 2], {1: True, 2: False}))

    def test_pv_picks_smallest_unassigned(self):
        self.assertEqual(_pick_variable([1, 2, 3], {1: True, 3: False}), 2)
        
    def test_pv_picks_first_unassigned(self):
        self.assertEqual(_pick_variable([3, 1, 2], {3: True}), 1)

    def test_pv_no_assigned(self):
        self.assertEqual(_pick_variable([4, 5], {}), 4)


    # --- 6. _all_clauses_satisfied ---
    def test_acs_empty(self):
        self.assertTrue(_all_clauses_satisfied([], {}))

    def test_acs_fully_satisfied(self):
        self.assertTrue(_all_clauses_satisfied([[1, 2], [-3]], {1: True, 3: False}))

    def test_acs_partially_unassigned(self):
        # Clause 1 is satisfied, Clause 2 is unassigned
        self.assertFalse(_all_clauses_satisfied([[1], [2]], {1: True}))

    def test_acs_falsified_clause(self):
        self.assertFalse(_all_clauses_satisfied([[1]], {1: False}))
        
    def test_acs_mixed_falsified_unassigned(self):
        self.assertFalse(_all_clauses_satisfied([[1, 2]], {1: False}))


    # --- 7. _complete_assignment ---
    def test_ca_empty(self):
        self.assertEqual(_complete_assignment([], {}), {})

    def test_ca_all_present(self):
        self.assertEqual(_complete_assignment([1, 2], {1: True, 2: True}), {1: True, 2: True})

    def test_ca_fills_false(self):
        self.assertEqual(_complete_assignment([1, 2, 3], {2: True}), {1: False, 2: True, 3: False})

    def test_ca_sorts_keys(self):
        res = _complete_assignment([3, 1], {3: True})
        self.assertEqual(list(res.keys()), [1, 3])

    def test_ca_ignores_extra(self):
        # Though technically it shouldn't happen, ensure it keeps base
        self.assertEqual(_complete_assignment([1], {1: True, 2: True}), {1: True, 2: True})


class TestDpllSolverClass(unittest.TestCase):
    
    # --- 8. DpllSolver basic methods (5 tests) ---
    def test_init_empty(self):
        solver = DpllSolver()
        self.assertEqual(solver._base_clauses, [])
        self.assertIsNone(solver._num_vars)
        
    def test_add_clause(self):
        solver = DpllSolver()
        solver.add_clause([1, -2])
        self.assertEqual(solver._base_clauses, [(1, -2)])
        
    def test_add_clauses(self):
        solver = DpllSolver()
        solver.add_clauses([[1], [-2, 3]])
        self.assertEqual(solver._base_clauses, [(1,), (-2, 3)])
        
    def test_add_clause_zero_error(self):
        solver = DpllSolver()
        with self.assertRaises(ValueError):
            solver.add_clause([1, 0])
            
    def test_reset_stats(self):
        solver = DpllSolver()
        solver.stats.decisions = 10
        solver.reset_stats()
        self.assertEqual(solver.stats.decisions, 0)

if __name__ == "__main__":
    unittest.main()