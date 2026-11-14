import pytest
from griductive.core.types import Clue, ClueError
from griductive.logic.clue_validator import validate_clue

README_CLUES = [   # the examples in README section 4
    {"id": "c01", "type": "FACT", "cell": "A1", "status": "INNOCENT"},
    {"id": "c02", "type": "SAME", "a": "A1", "b": "B2"},
    {"id": "c03", "type": "DIFFERENT", "a": "A1", "b": "B2"},
    {"id": "c04", "type": "EXACTLY", "k": 2, "region": {"kind": "ROW", "index": 2}},
    {"id": "c05", "type": "AT_LEAST", "k": 1, "region": {"kind": "COL", "index": "B"}},
    {"id": "c06", "type": "AT_MOST", "k": 1, "region": {"kind": "NEIGHBORS", "of": "B2"}},
    {"id": "c07", "type": "EXACTLY", "k": 0,
     "region": {"kind": "CELLS", "cells": ["A1", "C3"]}},
]


def clue(d):
    return Clue.from_dict(d)


def count(k):
    return clue({"id": "c", "type": "EXACTLY", "k": k,
                 "region": {"kind": "ROW", "index": 1}})


def test_readme_examples_are_valid():
    for d in README_CLUES:
        validate_clue(clue(d), 3)


def test_k_bounds():
    for k in (0, 3):
        validate_clue(count(k), 3)              # valid boundaries
    for k in (-1, 4, True, 1.5):
        with pytest.raises(ClueError):
            validate_clue(count(k), 3)


@pytest.mark.parametrize("d", [
    {"id": "c", "type": "SAME", "a": "A1", "b": "A1"},               # same cell twice
    {"id": "c", "type": "EXACTLY", "region": {"kind": "ROW", "index": 1}},   # missing k
    {"id": "c", "type": "FACT", "cell": "A1"},                       # missing status
    {"id": "c", "type": "FACT", "cell": "D4", "status": "CRIMINAL"}, # outside grid
])
def test_other_errors(d):
    with pytest.raises(ClueError):
        validate_clue(clue(d), 3)