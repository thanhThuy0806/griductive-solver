"""Tests for agent_entailment."""
"""Tests for Agent v1 entailment classification (uses the stub solver)."""
import random
from itertools import product

import pytest

from griductive.agent.entailment import Classification as C
from griductive.agent.entailment import EntailmentChecker
from griductive.agent.stub_solver import StubSolver
from griductive.sat.interface import SatSolver, SolveResult

# independent oracle: enumerate every assignment
def brute_force(clauses, nvars, var):
    def holds(m, lit):
        return m[abs(lit) - 1] if lit > 0 else not m[abs(lit) - 1]

    models = [m for m in product([False, True], repeat=nvars)
              if all(any(holds(m, l) for l in c) for c in clauses)]
    if not models:
        return C.INCONSISTENT
    values = {m[var - 1] for m in models}
    if values == {True}:
        return C.CRIMINAL
    if values == {False}:
        return C.INNOCENT
    return C.UNKNOWN

# example from the project statement
def test_statement_example():
    kb = [[1, 2], [-1, 2]]  # (C_A or C_B) and (not C_A or C_B); A=1, B=2
    chk = EntailmentChecker()
    assert chk.classify(kb, 2) == C.CRIMINAL
    assert chk.classify(kb, 1) == C.UNKNOWN

def test_innocent():
    assert EntailmentChecker().classify([[-1], [1, 2]], 1) == C.INNOCENT
    assert EntailmentChecker().classify([[-1], [1, 2]], 2) == C.CRIMINAL

def test_exactly_one_of_three_with_two_innocents():
    kb = [[1, 2, 3], [-1, -2], [-1, -3], [-2, -3], [-1], [-2]]
    res = EntailmentChecker().classify_all(kb, [1, 2, 3])
    assert res == {1: C.INNOCENT, 2: C.INNOCENT, 3: C.CRIMINAL}

def test_variable_not_in_kb_is_unknown():
    assert EntailmentChecker().classify([[1]], 5) == C.UNKNOWN
    assert EntailmentChecker().classify([], 1) == C.UNKNOWN

@pytest.mark.parametrize("kb", [[[1], [-1]], [[]], [[1, 2], [-1], [-2]]])
def test_inconsistent_kb(kb):
    chk = EntailmentChecker()
    assert not chk.is_consistent(kb)
    res = chk.classify_all(kb, [1, 2])
    assert set(res.values()) == {C.INCONSISTENT}

def test_all_four_states_reachable():
    kb = [[1], [-2]]
    res = EntailmentChecker().classify_all(kb, [1, 2, 3])
    assert res == {1: C.CRIMINAL, 2: C.INNOCENT, 3: C.UNKNOWN}
    assert EntailmentChecker().classify([[1], [-1]], 1) == C.INCONSISTENT

def test_is_forced():
    assert C.CRIMINAL.is_forced and C.INNOCENT.is_forced
    assert not C.UNKNOWN.is_forced and not C.INCONSISTENT.is_forced

# cross-check against brute force
def random_kb(rng):
    nvars = rng.randint(1, 6)
    clauses = []
    for _ in range(rng.randint(0, 10)):
        width = rng.randint(1, 3)
        clauses.append([rng.choice([-1, 1]) * rng.randint(1, nvars) for _ in range(width)])
    return nvars, clauses

@pytest.mark.parametrize("use_witnesses", [True, False])
def test_random_cross_check(use_witnesses):
    rng = random.Random(2026)
    for _ in range(300):
        nvars, kb = random_kb(rng)
        chk = EntailmentChecker(use_witnesses=use_witnesses)
        res = chk.classify_all(kb, range(1, nvars + 1))
        for v in range(1, nvars + 1):
            assert res[v] == brute_force(kb, nvars, v), (kb, v)

def test_witnesses_only_save_calls():
    rng = random.Random(7)
    with_w = without_w = 0
    for _ in range(100):
        nvars, kb = random_kb(rng)
        a = EntailmentChecker(use_witnesses=True)
        b = EntailmentChecker(use_witnesses=False)
        assert a.classify_all(kb, range(1, nvars + 1)) == b.classify_all(kb, range(1, nvars + 1))
        with_w += a.total_sat_calls
        without_w += b.total_sat_calls
    assert with_w <= without_w

# query log / solver injection
def test_query_log_records_every_call():
    chk = EntailmentChecker(use_witnesses=False)
    chk.classify([[1, 2], [-1, 2]], 2)
    log = chk.drain_log()
    assert [q.formula for q in log] == ["KB", "KB ∧ ¬C2"]
    assert [q.satisfiable for q in log] == [True, False]
    assert chk.queries == [] and chk.total_sat_calls == 2

def test_accepts_any_solver_with_the_interface():
    class AlwaysUnsat:
        def solve(self, clauses):
            return SolveResult(False)

    assert isinstance(StubSolver(), SatSolver)
    assert EntailmentChecker(AlwaysUnsat()).classify([[1]], 1) == C.INCONSISTENT

@pytest.mark.parametrize("bad", [[[0]], [["a"]], [[1.5]]])
def test_invalid_clauses_rejected(bad):
    with pytest.raises(ValueError):
        EntailmentChecker().classify(bad, 1)

@pytest.mark.parametrize("var", [0, -1])
def test_invalid_variable_rejected(var):
    with pytest.raises(ValueError):
        EntailmentChecker().classify([[1]], var)