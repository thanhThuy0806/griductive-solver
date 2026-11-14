"""Brute-force correctness, independent SAT comparison and offline CLI behavior."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from griductive.core.constants import ClueType, Status
from griductive.core.types import Clue, ClueError
from griductive.engine import puzzle_uniqueness as uniqueness
from griductive.engine.puzzle_loader import load_puzzle, parse_puzzle
from griductive.logic import evaluator
from griductive.logic.cnf_encoder import encode_clue
from griductive.logic.variable_map import VarMap
from griductive.sat.dpll import DpllSolver


SAMPLE = Path(__file__).resolve().parents[1] / "puzzles/3x3/p3x3_01.json"


def make_puzzle(size=3):
    cells = [f"{chr(65 + col)}{row}" for row in range(1, size + 1) for col in range(size)]
    return parse_puzzle({"size": size, "characters": [
        {"cell": cell, "name": cell, "job": "tester", "status": "INNOCENT",
         "revealed": index == 0,
         "clue": {"id": f"c{index}", "type": "FACT", "cell": "A1",
                  "status": "INNOCENT"}}
        for index, cell in enumerate(cells)]})


def test_sample_unique_and_input_unchanged():
    puzzle = load_puzzle(SAMPLE)
    before = deepcopy(puzzle)
    result = uniqueness.check_uniqueness(puzzle)
    assert result.status == "UNIQUE"
    assert result.solutions == ({c.cell: c.status is Status.CRIMINAL
                                 for c in puzzle.characters},)
    assert result.assignments_checked == 256
    assert result.runtime_ms >= 0
    assert puzzle == before


def test_multiple_stops_at_second_detached_witness():
    result = uniqueness.check_uniqueness(make_puzzle())
    assert result.status == "MULTIPLE"
    assert result.assignments_checked == 2
    assert len(result.solutions) == 2
    assert result.solutions[0] != result.solutions[1]
    result.solutions[0]["A1"] = True
    assert result.solutions[1]["A1"] is False


def test_unique_at_last_assignment_checks_entire_space():
    puzzle = make_puzzle()
    for character in puzzle.characters[1:]:
        character.clue = Clue(character.clue.id, ClueType.FACT,
                              cell=character.cell, status=Status.CRIMINAL)
    result = uniqueness.check_uniqueness(puzzle)
    assert result.status == "UNIQUE"
    assert result.assignments_checked == 256
    assert all(result.solutions[0][c.cell] for c in puzzle.characters[1:])


def test_hidden_answers_are_not_constraints():
    puzzle = load_puzzle(SAMPLE)
    expected = uniqueness.check_uniqueness(puzzle)
    for character in puzzle.characters[1:]:
        character.status = Status.CRIMINAL
    actual = uniqueness.check_uniqueness(puzzle)
    assert actual.status == expected.status
    assert actual.solutions == expected.solutions
    assert actual.assignments_checked == expected.assignments_checked


@pytest.mark.parametrize("all_revealed", [False, True])
def test_revealed_status_can_make_hidden_clue_unsatisfiable(all_revealed):
    puzzle = make_puzzle()
    for character in puzzle.characters:
        character.revealed = all_revealed or character.cell == "A1"
    puzzle.characters[-1].clue = Clue("contradiction", ClueType.FACT,
                                      cell="A1", status=Status.CRIMINAL)
    result = uniqueness.check_uniqueness(puzzle)
    assert result.status == "UNSAT"
    assert result.solutions == ()
    assert result.assignments_checked == (1 if all_revealed else 256)


@pytest.mark.parametrize("size", [3, 4, 5])
def test_large_shapes_with_few_unknowns_are_fast_fixtures(size):
    puzzle = make_puzzle(size)
    for character in puzzle.characters:
        character.revealed = True
    result = uniqueness.check_uniqueness(puzzle)
    assert result.status == "UNIQUE" and result.assignments_checked == 1
    puzzle.characters[-1].revealed = False
    result = uniqueness.check_uniqueness(puzzle)
    assert result.status == "MULTIPLE" and result.assignments_checked == 2


CLUES = [
    {"type": "FACT", "cell": "B1", "status": "CRIMINAL"},
    {"type": "SAME", "a": "B1", "b": "C1"},
    {"type": "DIFFERENT", "a": "B1", "b": "C1"},
    {"type": "EXACTLY", "k": 1, "region": {"kind": "ROW", "index": 1}},
    {"type": "AT_LEAST", "k": 1, "region": {"kind": "COL", "index": "B"}},
    {"type": "AT_MOST", "k": 0, "region": {"kind": "NEIGHBORS", "of": "A1"}},
    {"type": "EXACTLY", "k": 2,
     "region": {"kind": "CELLS", "cells": ["B1", "C1"]}},
]


@pytest.mark.parametrize("clue_data", CLUES)
def test_semantic_bruteforce_agrees_with_dpll(clue_data):
    puzzle = make_puzzle()
    for character in puzzle.characters:
        character.revealed = character.cell not in ("B1", "C1")
    puzzle.characters[-1].clue = Clue.from_dict({"id": "mixed", **clue_data})
    vm = VarMap(3)
    clauses = [[v, -v] for v in range(1, 10)]  # Include every primary in SAT models.
    for character in puzzle.characters:
        clauses.extend(encode_clue(character.clue, vm))
        if character.revealed:
            clauses.append([-vm.var(character.cell)])
    sat_solutions = []
    while len(sat_solutions) < 2:
        result = DpllSolver().solve(clauses)
        if not result.satisfiable:
            break
        solution = {vm.cell(v): result.model[v] for v in range(1, 10)}
        sat_solutions.append(solution)
        clauses.append([-v if result.model[v] else v for v in range(1, 10)])
    brute = uniqueness.check_uniqueness(puzzle)
    assert len(brute.solutions) == len(sat_solutions)
    assert brute.status == ("UNSAT", "UNIQUE", "MULTIPLE")[len(sat_solutions)]
    if brute.status == "UNIQUE":
        assert brute.solutions[0] == sat_solutions[0]


def test_preflight_surfaces_unsupported_late_clue(monkeypatch):
    puzzle = make_puzzle()
    puzzle.characters[0].clue = Clue("false", ClueType.FACT,
                                     cell="A1", status=Status.CRIMINAL)
    puzzle.characters[-1].clue = Clue.from_dict({
        "id": "unsupported", "type": "AT_MOST", "k": 0,
        "region": {"kind": "ROW", "index": 1}})
    monkeypatch.delitem(evaluator._EVALUATORS, ClueType.AT_MOST)
    with pytest.raises(ClueError, match="unsupported.*no evaluator"):
        uniqueness.check_uniqueness(puzzle)


def write_puzzle(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_cli_continues_after_file_error_and_reports_answer_mismatch(tmp_path, capsys):
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    data["characters"][1]["status"] = "INNOCENT"
    wrong = write_puzzle(tmp_path, "wrong.json", data)
    assert uniqueness.main([str(tmp_path / "missing.json"), str(wrong), str(SAMPLE)]) == 1
    output = capsys.readouterr().out
    assert "FileNotFoundError" in output
    assert "unique solution does not match stored answer" in output
    assert output.count("| UNIQUE |") == 2
    assert str(SAMPLE) in output.splitlines()[-1]


def test_cli_default_checks_repository_sample(monkeypatch, capsys):
    # Keep future full 5x5 datasets out of this fast CLI discovery test.
    monkeypatch.setattr(Path, "glob", lambda path, pattern:
                        iter([SAMPLE]) if path.name == "3x3" else iter(()))
    assert uniqueness.main([]) == 0
    output = capsys.readouterr().out
    assert "p3x3_01.json" in output and "assignments_checked=256" in output


def test_cli_empty_discovery_fails(monkeypatch, capsys):
    monkeypatch.setattr(Path, "glob", lambda *args: iter(()))
    assert uniqueness.main([]) == 1
    assert "no puzzle files found" in capsys.readouterr().out


@pytest.mark.parametrize("contradiction", [False, True])
def test_cli_rejects_nonunique_or_unsat_and_prints_witnesses(tmp_path, capsys, contradiction):
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    for character in data["characters"]:
        character["clue"] = {"id": character["clue"]["id"], "type": "FACT",
                             "cell": "A1", "status": "INNOCENT"}
    if contradiction:
        data["characters"][-1]["clue"]["status"] = "CRIMINAL"
    path = write_puzzle(tmp_path, "negative.json", data)
    assert uniqueness.main([str(path)]) == 1
    output = capsys.readouterr().out
    assert ("| UNSAT |" if contradiction else "| MULTIPLE |") in output
    assert ("solution 2:" in output) is not contradiction
