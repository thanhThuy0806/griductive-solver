"""Real Agent integration and public-only evidence across the full reveal cycle."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from griductive.agent.logic_agent import RunStatus
from griductive.agent.protocols import ClueEncoder, GameInterface
from griductive.core.constants import ClueType, RegionKind, Status
from griductive.core.types import Clue, Region
from griductive.engine.agent_api import AgentAPI
from griductive.engine.game_engine import GameEngine
from griductive.engine.puzzle_loader import load_puzzle


ROOT = Path(__file__).resolve().parents[1]
PATHS = sorted((ROOT / "puzzles").glob("*x*/p*x*_*.json"))
SAMPLE = ROOT / "puzzles/3x3/p3x3_01.json"


@pytest.fixture
def puzzle():
    return load_puzzle(SAMPLE)


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.name)
def test_real_agent_solves_without_private_metadata_or_gui(path, monkeypatch, record_property):
    puzzle = load_puzzle(path)
    for card in puzzle.characters:
        card.clue.params["answer_key"] = {c.cell: c.status for c in puzzle.characters}

    def forbidden(*args):
        pytest.fail("Agent integration must not read the GUI snapshot")

    monkeypatch.setattr(GameEngine, "get_public_state", forbidden)
    engine = GameEngine(puzzle)
    api = AgentAPI(engine)
    assert isinstance(api, ClueEncoder) and isinstance(api, GameInterface)
    agent = api.create_agent()
    initial = engine.get_agent_knowledge()
    assert set(agent._clues) == {c.id for c in initial.revealed_clues}
    assert agent.proved == {c: s.value for c, s in initial.proven_verdicts}

    result = agent.run(api)
    assert result.status is RunStatus.SOLVED, result.error
    assert engine.is_solved
    assert result.accepted_steps == sum(not c.revealed for c in puzzle.characters)
    assert agent.proved == {c: s.value for c, s in engine.get_agent_knowledge().proven_verdicts}
    active = set(agent.trace.initial_clue_ids)
    for step in agent.trace.steps:
        assert set(step.active_clue_ids) == active
        assert step.result == "ACCEPTED"
        assert step.new_clue_id not in active
        active.add(step.new_clue_id)
    assert "answer_key" not in json.dumps(agent.trace.to_dict())
    assert "answer_key" not in json.dumps(agent._clues)
    record_property("accepted_steps", result.accepted_steps)
    record_property("agent_sat_calls", result.sat_calls)
    record_property("status", result.status.value)


def test_hidden_answers_clues_and_names_cannot_change_agent_or_hint(puzzle):
    other = deepcopy(puzzle)
    for card in other.characters:
        card.name = "changed name"
        card.job = "changed job"
        if not card.revealed:
            card.status = Status.INNOCENT if card.status is Status.CRIMINAL else Status.CRIMINAL
            card.clue = Clue(card.clue.id, ClueType.FACT, cell="C3", status=Status.CRIMINAL)
    first = AgentAPI(GameEngine(puzzle)).create_agent()
    second = AgentAPI(GameEngine(other)).create_agent()
    assert first.knowledge_base() == second.knowledge_base()
    assert first.classify_unresolved() == second.classify_unresolved()
    first_hint, second_hint = first.hint(), second.hint()
    assert first_hint is not None and second_hint is not None
    assert replace(first_hint, sat_queries=[]) == replace(second_hint, sat_queries=[])
    assert [(q.formula, q.literal, q.satisfiable) for q in first_hint.sat_queries] == [
        (q.formula, q.literal, q.satisfiable) for q in second_hint.sat_queries]


def test_initial_and_accepted_payloads_are_detached_and_filtered(puzzle):
    puzzle.characters[0].clue.params["answer_key"] = {"C3": "secret"}
    puzzle.characters[1].clue.params["answer_key"] = {"C3": "secret"}
    puzzle.characters[1].clue = replace(puzzle.characters[1].clue,
                                       region=Region(RegionKind.ROW, index=3), a="C3")
    engine = GameEngine(puzzle)
    api = AgentAPI(engine)
    cards = api.public_cards()
    assert len(cards) == 1
    assert cards[0].clue == {"id": "c01", "type": "FACT", "cell": "B1", "status": "CRIMINAL"}
    cards[0].clue["cell"] = "C3"
    assert api.public_cards()[0].clue["cell"] == "B1"
    response = api.submit_verdict("B1", "CRIMINAL")
    assert response.result == "ACCEPTED"
    assert response.clue == {"id": "c02", "type": "FACT", "cell": "C1", "status": "INNOCENT"}
    response.clue["cell"] = "A1"
    assert engine.get_agent_knowledge().revealed_clues[1].cell == "C1"


@pytest.mark.parametrize("payload", [
    {"id": "extension", "type": "PARITY", "parity": "ODD",
     "region": {"kind": "NEIGHBORS", "of": "B2"}},
    {"id": "extension", "type": "COMPARE", "op": "MORE",
     "region_a": {"kind": "ROW", "index": 1},
     "region_b": {"kind": "CELLS", "cells": ["A2", "B2"]}},
])
def test_extensions_export_only_semantic_fields(puzzle, payload):
    clue = Clue.from_dict(payload)
    clue.params["answer_key"] = {"C3": "secret"}
    for region in (clue.region, clue.region_a, clue.region_b):
        if region is not None:
            object.__setattr__(region, "answer_key", {"C3": "secret"})
    puzzle.characters[0].clue = replace(clue, a="C3")
    api = AgentAPI(GameEngine(puzzle))
    exported = api.public_cards()[0].clue
    assert exported == payload
    assert api.encode_clue(exported)


@pytest.mark.parametrize("cell,status,expected", [
    ("B1", "INNOCENT", "CONTRADICTED"),
    ("C3", "CRIMINAL", "NOT_PROVABLE"),
])
def test_rejected_verdicts_never_return_clues_or_change_evidence(puzzle, cell, status, expected):
    engine = GameEngine(puzzle)
    api = AgentAPI(engine)
    before = engine.get_agent_knowledge()
    response = api.submit_verdict(cell, status)
    assert response.result == expected and response.clue is None
    assert engine.get_agent_knowledge() == before


@pytest.mark.parametrize("cell,status", [("Z9", "CRIMINAL"), ("B1", "UNKNOWN"),
                                       ("A1", "INNOCENT")])
def test_invalid_submissions_do_not_call_classifier(puzzle, cell, status):
    engine = GameEngine(puzzle, classify=lambda *args: pytest.fail("classifier called"))
    api = AgentAPI(engine)
    before = engine.get_agent_knowledge()
    with pytest.raises(ValueError):
        api.submit_verdict(cell, status)
    assert engine.get_agent_knowledge() == before


def test_encoder_rejects_extra_data_before_encoding(puzzle, monkeypatch):
    api = AgentAPI(GameEngine(puzzle))
    data = api.public_cards()[0].clue
    data["answer_key"] = {"C3": "secret"}
    monkeypatch.setattr("griductive.engine.agent_api.encode_structured_clue",
                        lambda *args: pytest.fail("encoder called"))
    with pytest.raises(ValueError, match="metadata"):
        api.encode_clue(data)


def test_bad_new_clue_is_rejected_before_engine_mutates(puzzle):
    puzzle.characters[1].clue = Clue("unsupported", "UNSUPPORTED")
    engine = GameEngine(puzzle)
    api = AgentAPI(engine)
    before = engine.get_agent_knowledge()
    with pytest.raises(ValueError, match="Unsupported clue type"):
        api.submit_verdict("B1", "CRIMINAL")
    assert engine.get_agent_knowledge() == before
    assert not engine.get_public_state().characters[1].revealed


def test_restart_recreates_agent_from_current_evidence(puzzle):
    engine = GameEngine(puzzle)
    api = AgentAPI(engine)
    agent = api.create_agent()
    hint = agent.hint()
    assert hint.cell == "B1" and hint.verdict == "CRIMINAL"
    assert not agent.trace.steps and len(api.public_cards()) == 1
    assert agent.step(api) is None
    current = api.create_agent()
    assert set(current.proved) == {"A1", "B1"}
    engine.restart()
    restarted = api.create_agent()
    assert restarted.proved == {"A1": "INNOCENT"}
    assert not restarted.trace.steps
    assert restarted.run(api).status is RunStatus.SOLVED


def test_inconsistent_public_knowledge_stops_agent_without_reveal(puzzle):
    puzzle.characters[0].clue = Clue("contradiction", ClueType.FACT,
                                    cell="A1", status=Status.CRIMINAL)
    engine = GameEngine(puzzle)
    api = AgentAPI(engine)
    before = engine.get_agent_knowledge()
    result = api.create_agent().run(api)
    assert result.status is RunStatus.INCONSISTENT
    assert engine.get_agent_knowledge() == before
