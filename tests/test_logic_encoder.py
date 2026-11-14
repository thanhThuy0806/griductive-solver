"""Tests for logic_encoder."""
from itertools import product

import pytest
from griductive.core.types import Clue, ClueError
from griductive.logic.cnf_encoder import encode_clue
from griductive.logic.variable_map import VarMap

from griductive.core.regions import resolve_region
from griductive.core.types import Region
from griductive.logic.evaluator import evaluate

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

# ---- Task 23: evaluator vs CNF on every complete assignment ----

REGIONS = [
    ("row1", ROW1), ("row3", {"kind": "ROW", "index": 3}),
    ("colA", {"kind": "COL", "index": "A"}), ("colC", {"kind": "COL", "index": "C"}),
    ("nbA1", {"kind": "NEIGHBORS", "of": "A1"}),    # corner: 3 cells
    ("nbB1", {"kind": "NEIGHBORS", "of": "B1"}),    # edge: 5 cells
    ("nbB2", {"kind": "NEIGHBORS", "of": "B2"}),    # centre: 8 cells
    ("nbC3", {"kind": "NEIGHBORS", "of": "C3"}),
    ("cells4", {"kind": "CELLS", "cells": ["A1", "C2", "B3", "C3"]}),
]


def all_core_clues(n=3):
    """Build many clues of the six core types, including every k from 0 to |R|."""
    out = []
    for cell in ("A1", "B2", "C3"):
        for status in ("CRIMINAL", "INNOCENT"):
            out.append({"id": f"FACT_{cell}_{status}", "type": "FACT",
                        "cell": cell, "status": status})
    for ctype in ("SAME", "DIFFERENT"):
        for a, b in (("A1", "B2"), ("A1", "C3"), ("B1", "B3")):
            out.append({"id": f"{ctype}_{a}_{b}", "type": ctype, "a": a, "b": b})
    for ctype in ("EXACTLY", "AT_LEAST", "AT_MOST"):
        for name, region in REGIONS:
            size = len(resolve_region(Region.from_dict(region), n))
            for k in range(size + 1):
                out.append({"id": f"{ctype}_{name}_k{k}", "type": ctype,
                            "k": k, "region": region})
    return out


def involved_cells(c, n=3):
    """Cells whose status the clue depends on."""
    if c.cell is not None:
        return [c.cell]
    if c.a is not None:
        return [c.a, c.b]
    return resolve_region(c.region, n)


@pytest.mark.parametrize("d", all_core_clues(), ids=lambda d: d["id"])
def test_evaluator_matches_cnf(d):
    c, n = clue(d), 3
    vm = VarMap(n)
    cnf = encode_clue(c, vm)
    cells = involved_cells(c, n)
    for bits in product([False, True], repeat=len(cells)):
        assign = dict(zip(cells, bits))                       # {"A1": True, ...}
        model = {vm.var(cell): val for cell, val in assign.items()}   # {1: True, ...}
        assert satisfied(cnf, model) == evaluate(c, assign, n), \
            f"{d['id']}: evaluator and CNF disagree on {assign}"