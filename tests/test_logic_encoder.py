"""Tests for logic_encoder."""
from itertools import product

import pytest
from griductive.core.types import Clue, ClueError
from griductive.logic.cnf_encoder import encode_clue
from griductive.logic.variable_map import VarMap


def clue(d):
    return Clue.from_dict(d)


def satisfied(cnf, model):
    """True if every clause has at least one true literal under `model` {var: bool}."""
    return all(any(model[abs(lit)] == (lit > 0) for lit in clause) for clause in cnf)


def test_fact_innocent_and_criminal():
    vm = VarMap(3)
    assert encode_clue(clue({"id": "c", "type": "FACT", "cell": "A1",
                             "status": "INNOCENT"}), vm) == [[-1]]
    assert encode_clue(clue({"id": "c", "type": "FACT", "cell": "C3",
                             "status": "CRIMINAL"}), vm) == [[9]]


def test_same_and_different_exact_clauses():
    vm = VarMap(3)   # A1 = 1, B2 = 5
    same = clue({"id": "c", "type": "SAME", "a": "A1", "b": "B2"})
    diff = clue({"id": "c", "type": "DIFFERENT", "a": "A1", "b": "B2"})
    assert encode_clue(same, vm) == [[-1, 5], [1, -5]]
    assert encode_clue(diff, vm) == [[1, 5], [-1, -5]]


@pytest.mark.parametrize("ctype,truth", [
    ("SAME", lambda x, y: x == y),
    ("DIFFERENT", lambda x, y: x != y),
])
def test_binary_matches_truth_table(ctype, truth):
    vm = VarMap(3)
    cnf = encode_clue(clue({"id": "c", "type": ctype, "a": "A1", "b": "B1"}), vm)
    for x, y in product([False, True], repeat=2):
        assert satisfied(cnf, {1: x, 2: y}) == truth(x, y)


def test_invalid_clue_is_rejected_before_encoding():
    with pytest.raises(ClueError):
        encode_clue(clue({"id": "c", "type": "SAME", "a": "A1", "b": "A1"}), VarMap(3))