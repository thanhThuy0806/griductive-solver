"""Tests for logic_encoder."""
from itertools import product

import pytest
from griductive.core.types import Clue, ClueError
from griductive.logic.cnf_encoder import encode_clue
from griductive.logic.variable_map import VarMap

from griductive.core.regions import resolve_region
from griductive.core.types import Region

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

def counting(ctype, k, region):
    return clue({"id": "c", "type": ctype, "k": k, "region": region})


ROW1 = {"kind": "ROW", "index": 1}   # A1, B1, C1 -> vars 1, 2, 3


def test_exactly_2_on_row1_gives_the_four_clauses():
    cnf = encode_clue(counting("EXACTLY", 2, ROW1), VarMap(3))
    assert cnf == [[-1, -2, -3], [1, 2], [1, 3], [2, 3]]


def test_boundary_values():
    vm = VarMap(3)
    assert encode_clue(counting("AT_MOST", 0, ROW1), vm) == [[-1], [-2], [-3]]
    assert encode_clue(counting("AT_LEAST", 3, ROW1), vm) == [[1], [2], [3]]
    assert encode_clue(counting("AT_MOST", 3, ROW1), vm) == []
    assert encode_clue(counting("AT_LEAST", 0, ROW1), vm) == []


@pytest.mark.parametrize("ctype", ["EXACTLY", "AT_LEAST", "AT_MOST"])
@pytest.mark.parametrize("region", [
    ROW1,
    {"kind": "COL", "index": "B"},
    {"kind": "NEIGHBORS", "of": "A1"},       # corner: 3 cells
    {"kind": "NEIGHBORS", "of": "B2"},       # centre: 8 cells
    {"kind": "CELLS", "cells": ["A1", "C2", "B3", "C3"]},
])
def test_counting_matches_direct_count(ctype, region):
    """For every k and every assignment, CNF is satisfied iff the direct count says so."""
    vm = VarMap(3)
    cells = resolve_region(Region.from_dict(region), 3)
    vs = [vm.var(c) for c in cells]
    rules = {
        "EXACTLY": lambda count, k: count == k,
        "AT_LEAST": lambda count, k: count >= k,
        "AT_MOST": lambda count, k: count <= k,
    }
    for k in range(len(cells) + 1):
        cnf = encode_clue(counting(ctype, k, region), vm)
        for bits in product([False, True], repeat=len(vs)):
            model = dict(zip(vs, bits))
            assert satisfied(cnf, model) == rules[ctype](sum(bits), k)