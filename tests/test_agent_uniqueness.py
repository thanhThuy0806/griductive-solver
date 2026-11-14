"""Tests: uniqueness check (count solutions, capped)."""
import random

import pytest
from fakes import PUZZLE_3X3, PUZZLE_4X4, MiniEncoder, all_models

from griductive.agent import Uniqueness, check_puzzle_uniqueness, count_solutions


def test_unique_example_from_statement():
    # (A or B) and (not A or B): B must be true, A free -> 2 solutions over {A, B}
    r = count_solutions([[1, 2], [-1, 2]], [1, 2])
    assert r.status == Uniqueness.MULTIPLE and r.count == 2
    # projected onto B only the solution is unique
    assert count_solutions([[1, 2], [-1, 2]], [2]).status == Uniqueness.UNIQUE


def test_unsatisfiable():
    r = count_solutions([[1], [-1]], [1])
    assert r.status == Uniqueness.UNSATISFIABLE and r.count == 0 and r.solutions == []


def test_variables_missing_from_clauses_are_free():
    r = count_solutions([], [1, 2], limit=10)
    assert r.count == 4 and r.status == Uniqueness.MULTIPLE


def test_limit_caps_count_and_sat_calls():
    r = count_solutions([], [1, 2, 3], limit=2)
    assert r.count == 2 and r.sat_calls == 2
    assert count_solutions([[1]], [1]).sat_calls == 2        # find 1, then prove no other


def test_limit_must_be_at_least_two():
    with pytest.raises(ValueError):
        count_solutions([[1]], [1], limit=1)


def test_input_not_modified():
    clauses = [[1, 2], [-1, 2]]
    count_solutions(clauses, [1, 2])
    assert clauses == [[1, 2], [-1, 2]]


def test_counts_projection_not_aux_models():
    # var 3 is auxiliary and free: models differ in var 3 only -> still one solution over {1}
    assert count_solutions([[1], [3, -3]], [1]).status == Uniqueness.UNIQUE


@pytest.mark.parametrize("limit", [2, 3, 5])
def test_random_cross_check_with_brute_force(limit):
    rng = random.Random(99)
    for _ in range(200):
        nvars = rng.randint(1, 5)
        clauses = [[rng.choice([-1, 1]) * rng.randint(1, nvars) for _ in range(rng.randint(1, 3))]
                   for _ in range(rng.randint(0, 8))]
        primary = rng.sample(range(1, nvars + 1), rng.randint(1, nvars))
        projections = {tuple(m[v - 1] for v in sorted(primary)) for m in all_models(clauses, nvars)}
        r = count_solutions(clauses, primary, limit=limit)
        assert r.count == min(len(projections), limit), (clauses, primary)
        want = (Uniqueness.UNSATISFIABLE if not projections else
                Uniqueness.UNIQUE if len(projections) == 1 else Uniqueness.MULTIPLE)
        assert r.status == want
        for sol in r.solutions:
            assert tuple(sol[v] for v in sorted(primary)) in projections


@pytest.mark.parametrize("puzzle", [PUZZLE_3X3, PUZZLE_4X4])
def test_puzzles_have_unique_solution_equal_to_hidden_one(puzzle):
    enc = MiniEncoder(puzzle["size"])
    known = {c: puzzle["solution"][c] for c in puzzle["initial"]}
    r = check_puzzle_uniqueness(puzzle["clues"].values(), enc, puzzle["size"], known)
    assert r.status == Uniqueness.UNIQUE
    got = {c: ("CRIMINAL" if r.solutions[0][enc.var_of(c)] else "INNOCENT") for c in enc.cells}
    assert got == puzzle["solution"]


def test_dropping_clues_makes_puzzle_ambiguous():
    enc = MiniEncoder(3)
    some = list(PUZZLE_3X3["clues"].values())[:2]
    r = check_puzzle_uniqueness(some, enc, 3)
    assert r.status == Uniqueness.MULTIPLE and r.count == 2


def test_contradictory_clues_are_unsatisfiable():
    enc = MiniEncoder(3)
    clues = [{"id": "a", "type": "FACT", "cell": "A1", "status": "CRIMINAL"},
             {"id": "b", "type": "FACT", "cell": "A1", "status": "INNOCENT"}]
    assert check_puzzle_uniqueness(clues, enc, 3).status == Uniqueness.UNSATISFIABLE
