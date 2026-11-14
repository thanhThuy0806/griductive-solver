"""Tests for logic_evaluator."""
import pytest
from griductive.core.types import Clue, ClueError
from griductive.logic.evaluator import evaluate

ASSIGN = {"A1": True, "B1": False, "C1": True,
          "A2": False, "B2": True, "C2": False,
          "A3": False, "B3": False, "C3": True}


def ev(**kw):
    return evaluate(Clue.from_dict({"id": "c", **kw}), ASSIGN, 3)


ROW1 = {"kind": "ROW", "index": 1}     # A1, B1, C1 -> 2 criminals


def test_fact():
    assert ev(type="FACT", cell="A1", status="CRIMINAL")
    assert not ev(type="FACT", cell="A1", status="INNOCENT")
    assert ev(type="FACT", cell="B1", status="INNOCENT")


def test_same_and_different():
    assert ev(type="SAME", a="A1", b="C1")              # both criminals
    assert not ev(type="SAME", a="A1", b="B1")
    assert ev(type="DIFFERENT", a="A1", b="B1")
    assert not ev(type="DIFFERENT", a="A1", b="C1")


def test_counting_on_row1():                            # row 1 has exactly 2 criminals
    assert ev(type="EXACTLY", k=2, region=ROW1)
    assert not ev(type="EXACTLY", k=1, region=ROW1)
    assert ev(type="AT_LEAST", k=2, region=ROW1)
    assert not ev(type="AT_LEAST", k=3, region=ROW1)
    assert ev(type="AT_MOST", k=2, region=ROW1)
    assert not ev(type="AT_MOST", k=1, region=ROW1)


def test_other_region_kinds():
    assert ev(type="EXACTLY", k=1, region={"kind": "COL", "index": "B"})
    assert ev(type="EXACTLY", k=3, region={"kind": "NEIGHBORS", "of": "B2"})
    assert ev(type="EXACTLY", k=1, region={"kind": "NEIGHBORS", "of": "A1"})
    assert ev(type="EXACTLY", k=2, region={"kind": "CELLS", "cells": ["A1", "C3"]})
    assert not ev(type="EXACTLY", k=0, region={"kind": "CELLS", "cells": ["A1", "C3"]})


def test_missing_cell_in_assignment_is_an_error():
    clue = Clue.from_dict({"id": "c", "type": "FACT", "cell": "A1", "status": "CRIMINAL"})
    with pytest.raises(ClueError):
        evaluate(clue, {"B1": True}, 3)