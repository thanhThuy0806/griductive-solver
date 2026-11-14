"""Engine behavior and integration with the real encoder, Agent and DPLL."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from griductive.agent.entailment import Classification, EntailmentChecker
from griductive.core.constants import Status, VerdictResult
from griductive.engine.game_engine import GameEngine
from griductive.engine.puzzle_loader import parse_puzzle
from griductive.engine.verdict import EngineConsistencyError, classify


@pytest.fixture
def data():
    path = Path(__file__).resolve().parents[1] / "puzzles/3x3/p3x3_01.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_initial_snapshot_hides_all_private_data(data):
    puzzle = parse_puzzle(data)
    state = GameEngine(puzzle).get_public_state()
    assert state.size == 3
    assert tuple(c.cell for c in state.characters) == (
        "A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3")
    assert state.characters[0].status is Status.INNOCENT
    assert state.characters[0].clue == puzzle.characters[0].clue
    assert state.characters[0].clue is not puzzle.characters[0].clue
    for cell in state.characters[1:]:
        assert not cell.revealed
        assert cell.status is None and cell.clue is None
        assert cell.name and cell.job
    with pytest.raises(FrozenInstanceError):
        state.characters[0].revealed = False


def test_real_agent_solves_sample_one_card_at_a_time(data):
    puzzle = parse_puzzle(data)
    engine = GameEngine(puzzle)
    assert not engine.is_solved
    for index, cell in enumerate(puzzle.characters[1:], start=2):
        before = engine.get_public_state()
        response = engine.submit_verdict(cell.cell, cell.status)
        assert response.result is VerdictResult.ACCEPTED
        assert response.cell == cell.cell and response.status is cell.status
        assert response.new_clue == cell.clue
        assert sum(c.revealed for c in engine.get_public_state().characters) == index
        assert not next(c for c in before.characters if c.cell == cell.cell).revealed
    assert engine.is_solved
    assert not puzzle.characters[1].revealed


@pytest.mark.parametrize("kind,expected", [
    ("SAME", Status.INNOCENT), ("DIFFERENT", Status.CRIMINAL)])
def test_real_binary_clues(data, kind, expected):
    data["characters"][0]["clue"] = {
        "id": "c01", "type": kind, "a": "A1", "b": "B1"}
    data["characters"][1]["status"] = expected.value
    response = GameEngine(parse_puzzle(data)).submit_verdict("B1", expected)
    assert response.result is VerdictResult.ACCEPTED


@pytest.mark.parametrize("kind,k,status", [
    ("EXACTLY", 1, Status.CRIMINAL),
    ("AT_LEAST", 1, Status.CRIMINAL),
    ("AT_MOST", 0, Status.INNOCENT)])
def test_real_row_counting_clues(data, kind, k, status):
    data["characters"][0]["clue"] = {
        "id": "c01", "type": kind, "k": k, "region": {"kind": "ROW", "index": 1}}
    data["characters"][2]["revealed"] = True
    data["characters"][1]["status"] = status.value
    response = GameEngine(parse_puzzle(data)).submit_verdict("B1", status)
    assert response.result is VerdictResult.ACCEPTED


@pytest.mark.parametrize("region,cells", [
    ({"kind": "NEIGHBORS", "of": "A1"}, ("B1", "A2", "B2")),
    ({"kind": "COL", "index": "B"}, ("B1", "B2", "B3")),
    ({"kind": "CELLS", "cells": ["B1", "C3"]}, ("B1", "C3"))])
def test_real_other_counting_regions(data, region, cells):
    data["characters"][0]["clue"] = {
        "id": "c01", "type": "EXACTLY", "k": 0, "region": region}
    for cell in data["characters"]:
        if cell["cell"] in cells:
            cell["status"] = "INNOCENT"
    engine = GameEngine(parse_puzzle(data))
    assert engine.submit_verdict(cells[0], Status.INNOCENT).result is VerdictResult.ACCEPTED


@pytest.mark.parametrize("status", list(Status))
def test_unknown_is_not_provable_even_if_answer_matches(data, status):
    data["characters"][-1]["status"] = status.value
    engine = GameEngine(parse_puzzle(data))
    before = engine.get_public_state()
    result = engine.submit_verdict("C3", status)
    assert result.result is VerdictResult.NOT_PROVABLE
    assert result.new_clue is None
    assert engine.get_public_state() == before


def test_opposite_forced_verdict_is_contradicted(data):
    engine = GameEngine(parse_puzzle(data))
    before = engine.get_public_state()
    response = engine.submit_verdict("B1", Status.INNOCENT)
    assert response.result is VerdictResult.CONTRADICTED
    assert response.new_clue is None
    assert engine.get_public_state() == before


def test_inconsistent_public_kb_does_not_reveal(data):
    data["characters"][0]["clue"]["cell"] = "A1"
    engine = GameEngine(parse_puzzle(data))
    before = engine.get_public_state()
    with pytest.raises(EngineConsistencyError, match="Public knowledge is inconsistent"):
        engine.submit_verdict("B1", Status.CRIMINAL)
    assert engine.get_public_state() == before


def test_proved_verdict_conflicting_with_hidden_answer_does_not_reveal(data):
    data["characters"][1]["status"] = "INNOCENT"
    engine = GameEngine(parse_puzzle(data))
    before = engine.get_public_state()
    with pytest.raises(EngineConsistencyError) as error:
        engine.submit_verdict("B1", Status.CRIMINAL)
    assert "INNOCENT" not in str(error.value) and "CRIMINAL" not in str(error.value)
    assert engine.get_public_state() == before


def test_private_changes_do_not_affect_public_classification(data):
    other = deepcopy(data)
    for cell in other["characters"][1:]:
        cell["status"] = "CRIMINAL"
        cell["clue"] = {"id": cell["clue"]["id"], "type": "FACT",
                        "cell": "C3", "status": "CRIMINAL"}
    first = GameEngine(parse_puzzle(data))
    second = GameEngine(parse_puzzle(other))
    assert first.get_public_state() == second.get_public_state()
    for engine in (first, second):
        assert engine.submit_verdict("C3", Status.CRIMINAL).result is VerdictResult.NOT_PROVABLE


def test_agent_receives_only_public_cnf_and_solver_stats_work(data, monkeypatch):
    seen = []
    original = EntailmentChecker.classify

    def record(checker, clauses, var):
        seen.append((deepcopy(clauses), var))
        result = original(checker, clauses, var)
        assert checker.queries and "runtime_ms" in checker.queries[-1].stats
        return result

    monkeypatch.setattr(EntailmentChecker, "classify", record)
    engine = GameEngine(parse_puzzle(data))
    engine.submit_verdict("C3", Status.INNOCENT)
    assert seen == [([[2], [-1]], 9)]


def test_bridge_ignores_unrevealed_fields_even_in_handmade_snapshot(data):
    puzzle = parse_puzzle(data)
    state = GameEngine(puzzle).get_public_state()
    hidden = replace(state.characters[-1], status=Status.CRIMINAL,
                     clue=puzzle.characters[-1].clue)
    state = replace(state, characters=(*state.characters[:-1], hidden))
    assert classify(state, "C3") is Classification.UNKNOWN


def test_restart_discards_revealed_clues_and_restores_initial_state(data):
    engine = GameEngine(parse_puzzle(data))
    initial = engine.get_public_state()
    engine.submit_verdict("B1", Status.CRIMINAL)
    assert classify(engine.get_public_state(), "C1") is Classification.INNOCENT
    assert engine.restart() == initial
    assert classify(engine.get_public_state(), "C1") is Classification.UNKNOWN
    assert not engine.is_solved


def test_engines_input_and_mutable_clue_payloads_are_independent(data):
    puzzle = parse_puzzle(data)
    puzzle.characters[0].clue.params["note"] = {"items": ["original"]}
    puzzle.characters[1].clue.params["note"] = ["private"]
    engine, other = GameEngine(puzzle), GameEngine(puzzle)
    initial = engine.get_public_state()
    puzzle.characters[0].clue.params["note"]["items"].append("input change")
    puzzle.characters[1].status = Status.INNOCENT
    snapshot = engine.get_public_state()
    snapshot.characters[0].clue.params["note"]["items"].append("snapshot change")
    assert engine.get_public_state() == initial
    assert other.get_public_state() == initial
    response = engine.submit_verdict("B1", Status.CRIMINAL)
    response.new_clue.params["note"].append("response change")
    assert engine.get_public_state().characters[1].clue.params["note"] == ["private"]
    assert other.get_public_state() == initial


def test_all_cards_initially_revealed_is_solved(data):
    for cell in data["characters"]:
        cell["revealed"] = True
    engine = GameEngine(parse_puzzle(data))
    assert engine.is_solved
    engine.restart()
    assert engine.is_solved


@pytest.mark.parametrize("cell,status", [
    ("Z9", Status.INNOCENT), (None, Status.CRIMINAL), ([], Status.CRIMINAL),
    ("A1", Status.INNOCENT), ("B1", "CRIMINAL"), ("B1", None)])
def test_invalid_submissions_do_not_call_agent(data, cell, status):
    callback = Mock(return_value=Classification.CRIMINAL)
    engine = GameEngine(parse_puzzle(data), classify=callback)
    before = engine.get_public_state()
    with pytest.raises(ValueError):
        engine.submit_verdict(cell, status)
    callback.assert_not_called()
    assert engine.get_public_state() == before


def test_cannot_submit_same_card_twice(data):
    engine = GameEngine(parse_puzzle(data))
    engine.submit_verdict("B1", Status.CRIMINAL)
    before = engine.get_public_state()
    with pytest.raises(ValueError, match="already revealed"):
        engine.submit_verdict("B1", Status.CRIMINAL)
    assert engine.get_public_state() == before


@pytest.mark.parametrize("invalid", ["CRIMINAL", None, Status.CRIMINAL])
def test_invalid_agent_return_does_not_reveal(data, invalid):
    engine = GameEngine(parse_puzzle(data), classify=lambda state, cell: invalid)
    before = engine.get_public_state()
    with pytest.raises(TypeError, match="Classification"):
        engine.submit_verdict("B1", Status.CRIMINAL)
    assert engine.get_public_state() == before


def test_callback_error_and_mutation_do_not_change_engine(data):
    def failing(state, cell):
        state.characters[0].clue.params["changed"] = True
        assert all(c.status is None and c.clue is None for c in state.characters[1:])
        raise RuntimeError("Agent failed")

    engine = GameEngine(parse_puzzle(data), classify=failing)
    before = engine.get_public_state()
    with pytest.raises(RuntimeError, match="Agent failed"):
        engine.submit_verdict("B1", Status.CRIMINAL)
    assert engine.get_public_state() == before


def test_non_callable_classifier_is_rejected(data):
    with pytest.raises(TypeError, match="callable"):
        GameEngine(parse_puzzle(data), classify=False)
