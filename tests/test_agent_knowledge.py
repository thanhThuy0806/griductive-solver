"""The Agent boundary exposes only detached, canonical, public evidence."""

import ast
from copy import deepcopy
from dataclasses import fields, replace
from importlib.util import resolve_name
from pathlib import Path

import pytest

from griductive.agent.entailment import Classification
from griductive.core.constants import ClueType, RegionKind, Status, VerdictResult
from griductive.core.types import AgentKnowledge, Clue, Region
from griductive.engine.game_engine import GameEngine
from griductive.engine.puzzle_loader import load_puzzle
from griductive.engine.verdict import EngineConsistencyError, classify
from griductive.sat.dpll import DpllSolver


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def puzzle():
    return load_puzzle(ROOT / "puzzles/3x3/p3x3_01.json")


def test_callback_shape_and_pending_choice_is_not_evidence(puzzle):
    seen = []

    def spy(knowledge, cell):
        seen.append((knowledge, cell))
        return classify(knowledge, cell)

    engine = GameEngine(puzzle, classify=spy)
    initial = engine.get_agent_knowledge()
    assert {f.name for f in fields(initial)} == {"size", "revealed_clues", "proven_verdicts"}
    assert initial.proven_verdicts == (("A1", Status.INNOCENT),)
    assert tuple(c.id for c in initial.revealed_clues) == ("c01",)
    assert engine.submit_verdict("B1", Status.INNOCENT).result is VerdictResult.CONTRADICTED
    assert engine.submit_verdict("C3", Status.CRIMINAL).result is VerdictResult.NOT_PROVABLE
    assert seen == [(initial, "B1"), (initial, "C3")]
    assert engine.get_agent_knowledge() == initial
    assert engine.submit_verdict("B1", Status.CRIMINAL).result is VerdictResult.ACCEPTED
    after = engine.get_agent_knowledge()
    assert after.proven_verdicts == (*initial.proven_verdicts, ("B1", Status.CRIMINAL))
    assert tuple(c.id for c in after.revealed_clues) == ("c01", "c02")
    assert initial.proven_verdicts == (("A1", Status.INNOCENT),)
    engine.restart()
    assert engine.get_agent_knowledge() == initial


def test_hidden_data_and_all_metadata_do_not_affect_agent(puzzle):
    other = deepcopy(puzzle)
    for card in other.characters:
        card.name = "changed"
        card.job = "changed"
        card.clue.params["answer_key"] = {c.cell: c.status for c in other.characters}
        if not card.revealed:
            card.status = Status.CRIMINAL
            card.clue = Clue(card.clue.id, ClueType.FACT, cell="C3", status=Status.CRIMINAL)
    other.characters[0].clue = replace(other.characters[0].clue,
                                       a="C3", region=Region(RegionKind.ROW, index=3))
    first, second = GameEngine(puzzle), GameEngine(other)
    assert first.get_agent_knowledge() == second.get_agent_knowledge()
    for cell in ("B1", "C1", "C3"):
        assert classify(first.get_agent_knowledge(), cell) == classify(
            second.get_agent_knowledge(), cell)


def test_requests_are_detached_from_engine_gui_and_each_other(puzzle):
    engine = GameEngine(puzzle)
    before = engine.get_agent_knowledge()
    request = engine.get_agent_knowledge()
    request.revealed_clues[0].params["private"] = {"items": [1]}
    engine.get_public_state().characters[0].clue.params["gui"] = [2]
    puzzle.characters[0].clue.params["source"] = [3]
    assert before.revealed_clues[0].params == {}
    assert engine.get_agent_knowledge().revealed_clues[0].params == {}
    assert engine.get_agent_knowledge() == before


def test_export_order_and_only_opened_clues_are_projected(puzzle):
    puzzle.characters[-1].revealed = True
    puzzle.characters[1].clue = Clue("hidden-extension", "UNSUPPORTED")
    puzzle.characters.reverse()
    knowledge = GameEngine(puzzle).get_agent_knowledge()
    assert knowledge.proven_verdicts == (("A1", Status.INNOCENT), ("C3", Status.INNOCENT))
    assert tuple(c.id for c in knowledge.revealed_clues) == ("c01", "c09")


def test_unsupported_opened_clue_is_rejected_before_callback(puzzle):
    puzzle.characters[0].clue = Clue("unsupported", "UNSUPPORTED")
    engine = GameEngine(puzzle, classify=lambda *args: pytest.fail("callback called"))
    with pytest.raises(ValueError, match="Unsupported clue type"):
        engine.submit_verdict("B1", Status.CRIMINAL)


def test_callback_exception_and_answer_conflict_preserve_knowledge(puzzle):
    def failing(knowledge, cell):
        knowledge.revealed_clues[0].params["changed"] = [1]
        raise RuntimeError("callback failed")

    engine = GameEngine(puzzle, classify=failing)
    before = engine.get_agent_knowledge()
    with pytest.raises(RuntimeError, match="callback failed"):
        engine.submit_verdict("B1", Status.CRIMINAL)
    assert engine.get_agent_knowledge() == before
    assert engine.get_agent_knowledge().revealed_clues[0].params == {}
    puzzle.characters[1].status = Status.INNOCENT
    engine = GameEngine(puzzle)
    before = engine.get_agent_knowledge()
    with pytest.raises(EngineConsistencyError) as error:
        engine.submit_verdict("B1", Status.CRIMINAL)
    assert "INNOCENT" not in str(error.value) and "CRIMINAL" not in str(error.value)
    assert engine.get_agent_knowledge() == before


@pytest.mark.parametrize("result", [Classification.UNKNOWN, Classification.INNOCENT,
                                    Classification.INCONSISTENT, "CRIMINAL", None])
def test_rejected_or_invalid_results_preserve_evidence(puzzle, result):
    engine = GameEngine(puzzle, classify=lambda knowledge, cell: result)
    before = engine.get_agent_knowledge()
    if result is Classification.INCONSISTENT:
        with pytest.raises(EngineConsistencyError):
            engine.submit_verdict("B1", Status.CRIMINAL)
    elif not isinstance(result, Classification):
        with pytest.raises(TypeError):
            engine.submit_verdict("B1", Status.CRIMINAL)
    else:
        engine.submit_verdict("B1", Status.CRIMINAL)
    assert engine.get_agent_knowledge() == before


@pytest.mark.parametrize("region", [
    Region(RegionKind.ROW, index=1), Region(RegionKind.COL, index="B"),
    Region(RegionKind.NEIGHBORS, of="B2"),
    Region(RegionKind.CELLS, cells=("A1", "C3")),
])
def test_region_projection_is_detached_and_drops_unused_fields(puzzle, region):
    dirty = replace(region, of="A1") if region.kind is not RegionKind.NEIGHBORS else replace(
        region, index="B")
    puzzle.characters[0].clue = Clue("count", ClueType.EXACTLY, k=0, region=dirty)
    engine = GameEngine(puzzle)
    clean = engine.get_agent_knowledge().revealed_clues[0]
    assert clean.region == region
    assert clean.region is not dirty


@pytest.mark.parametrize("changes", [
    {"size": True}, {"size": 2}, {"size": 3.0},
    {"revealed_clues": []}, {"proven_verdicts": []},
    {"proven_verdicts": (("A1", "INNOCENT"),)},
    {"proven_verdicts": (("Z9", Status.INNOCENT),)},
    {"proven_verdicts": (("A1", Status.INNOCENT), ("A1", Status.CRIMINAL))},
    {"proven_verdicts": (["A1", Status.INNOCENT],)},
    {"proven_verdicts": (("A1",),)},
    {"revealed_clues": (Clue("", ClueType.FACT, cell="B1", status=Status.CRIMINAL),)},
    {"revealed_clues": (Clue("x", "EXTENSION"),)},
    {"revealed_clues": (Clue("x", ClueType.FACT, cell="Z9", status=Status.CRIMINAL),)},
    {"revealed_clues": (Clue("x", ClueType.FACT, cell="B1", status=Status.CRIMINAL,
                              params={"secret": 1}),)},
    {"revealed_clues": (Clue("x", ClueType.FACT, cell="B1", status=Status.CRIMINAL,
                              a="C3"),)},
    {"revealed_clues": (Clue("x", ClueType.EXACTLY, k=0,
                              region=Region(RegionKind.ROW, index=1, of="C3")),)},
    {"revealed_clues": (Clue("x", ClueType.EXACTLY, k=0,
                              region=Region("EXTENSION")),)},
])
def test_invalid_knowledge_fails_before_solver(puzzle, monkeypatch, changes):
    def forbidden(*args, **kwargs):
        pytest.fail("solver called for invalid evidence")

    monkeypatch.setattr(DpllSolver, "solve", forbidden)
    knowledge = replace(GameEngine(puzzle).get_agent_knowledge(), **changes)
    with pytest.raises((TypeError, ValueError)):
        classify(knowledge, "C3")


def test_duplicate_clues_and_invalid_target_fail_before_solver(puzzle, monkeypatch):
    monkeypatch.setattr(DpllSolver, "solve", lambda *args: pytest.fail("solver called"))
    knowledge = GameEngine(puzzle).get_agent_knowledge()
    with pytest.raises(ValueError, match="Duplicate clue"):
        classify(replace(knowledge, revealed_clues=knowledge.revealed_clues * 2), "C3")
    with pytest.raises(ValueError):
        classify(knowledge, "Z9")
    object.__setattr__(knowledge, "answer_key", {"C3": True})
    with pytest.raises(ValueError, match="Unexpected AgentKnowledge fields"):
        classify(knowledge, "C3")


def test_contradictory_valid_evidence_is_inconsistent():
    knowledge = AgentKnowledge(3, (Clue("x", ClueType.FACT, cell="A1",
                                       status=Status.CRIMINAL),),
                               (("A1", Status.INNOCENT),))
    assert classify(knowledge, "B1") is Classification.INCONSISTENT


def imported_modules(source, package):
    """Resolve static absolute and relative imports, including from-package forms."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                module = resolve_name("." * node.level + module, package)
            yield module
            yield from (module + "." + alias.name for alias in node.names)


def test_agent_has_no_imports_of_private_engine_tools():
    for path in (ROOT / "griductive/agent").rglob("*.py"):
        package = ".".join(path.relative_to(ROOT).parent.parts)
        for module in imported_modules(path.read_text(encoding="utf-8"), package):
            assert not (module == "griductive.engine" or module.startswith("griductive.engine.")), (
                path, module)


def test_import_check_covers_relative_imports():
    source = "from ..engine import puzzle_loader\nfrom .. import engine\nimport griductive.engine"
    assert "griductive.engine.puzzle_loader" in set(imported_modules(source, "griductive.agent"))
    assert "griductive.engine" in set(imported_modules(source, "griductive.agent"))
