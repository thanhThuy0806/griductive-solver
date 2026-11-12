"""Check puzzle truth, primary uniqueness and play using public evidence only."""

import json
from pathlib import Path

import pytest

from griductive.agent.entailment import Classification
from griductive.core.constants import Status, VerdictResult
from griductive.core.types import Clue, Puzzle
from griductive.engine.game_engine import GameEngine
from griductive.engine.puzzle_loader import load_puzzle, parse_puzzle
from griductive.engine.verdict import classify
from griductive.logic.cnf_encoder import encode_clue
from griductive.logic.evaluator import evaluate
from griductive.logic.variable_map import VarMap
from griductive.sat.dpll import DpllSolver


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "puzzles/3x3/p3x3_01.json"
PATHS = sorted((ROOT / "puzzles").glob("*x*/p*x*_*.json"))


def assert_true_clues(puzzle: Puzzle) -> None:
    """Check every clue independently against the private answer key."""
    answer = {c.cell: c.status is Status.CRIMINAL for c in puzzle.characters}
    for character in puzzle.characters:
        assert evaluate(character.clue, answer, puzzle.size), character.clue.id


def assert_unique_answer(puzzle: Puzzle) -> tuple[VarMap, int]:
    """Exclude the answer on primary variables, leaving auxiliary variables free."""
    vm = VarMap(puzzle.size)
    clauses = []
    for character in puzzle.characters:
        clauses.extend(encode_clue(character.clue, vm))
        if character.revealed:
            v = vm.var(character.cell)
            clauses.append([v if character.status is Status.CRIMINAL else -v])
    answer = {vm.var(c.cell): c.status is Status.CRIMINAL for c in puzzle.characters}
    # Substitute the answer instead of supplying hidden unit clauses to the KB.
    residual = []
    for clause in clauses:
        if any(abs(lit) in answer and answer[abs(lit)] == (lit > 0) for lit in clause):
            continue
        residual.append([lit for lit in clause if abs(lit) not in answer])
    solver = DpllSolver()
    assert solver.solve(residual).satisfiable, "answer violates CNF"
    assert solver.solve(clauses).satisfiable, "complete clue set is inconsistent"
    blocking = [-v if value else v for v, value in answer.items()]
    assert not solver.solve([*clauses, blocking]).satisfiable, "multiple primary answers"
    return vm, len(clauses)


def play_publicly(puzzle: Puzzle) -> int:
    """Open one proved card at a time, selecting moves only from public snapshots."""
    engine = GameEngine(puzzle)
    steps = 0
    while not engine.is_solved:
        state = engine.get_public_state()
        for character in state.characters:
            if character.revealed:
                continue
            verdict = classify(state, character.cell)
            assert verdict is not Classification.INCONSISTENT, f"step {steps}: inconsistent KB"
            if not verdict.is_forced:
                continue
            response = engine.submit_verdict(character.cell, Status(verdict.value))
            assert response.result is VerdictResult.ACCEPTED, f"step {steps}: {character.cell}"
            steps += 1
            break  # Rebuild public evidence after each reveal.
        else:
            hidden = [c.cell for c in state.characters if not c.revealed]
            pytest.fail(f"step {steps}: stuck with hidden cards {hidden}")
    return steps


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.name)
def test_dataset_structure(path):
    puzzle = load_puzzle(path)
    assert path.parent.name == f"{puzzle.size}x{puzzle.size}"
    assert len(puzzle.characters) == puzzle.size ** 2


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.name)
def test_dataset_clue_truth(path):
    assert_true_clues(load_puzzle(path))


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.name)
def test_dataset_primary_uniqueness(path):
    assert_unique_answer(load_puzzle(path))


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.name)
def test_dataset_public_play(path, record_property):
    puzzle = load_puzzle(path)
    steps = play_publicly(puzzle)
    assert steps == sum(not c.revealed for c in puzzle.characters)
    vm, clauses = assert_unique_answer(puzzle)
    record_property("reveal_steps", steps)
    record_property("primary_vars", vm.num_primary)
    record_property("aux_vars", vm.num_aux)
    record_property("clauses", clauses)


def test_official_dataset_readiness():
    # The existing FACT sample is a regression fixture, not an official import.
    counts = {size: sum(p.parent.name == f"{size}x{size}" and p != SAMPLE for p in PATHS)
              for size in (3, 4, 5)}
    target = {3: 3, 4: 3, 5: 1}
    assert all(counts[n] <= target[n] for n in target), counts
    if counts != target:
        pytest.skip(f"official source imports pending: {counts}; target {target}; "
                    "see docs/puzzle_dataset.md")


def test_checks_reject_a_false_hidden_clue():
    puzzle = load_puzzle(SAMPLE)
    puzzle.characters[-1].clue = Clue(
        id="false-hidden", type=puzzle.characters[0].clue.type,
        cell="A1", status=Status.CRIMINAL)
    with pytest.raises(AssertionError, match="false-hidden"):
        assert_true_clues(puzzle)
    with pytest.raises(AssertionError, match="answer violates CNF"):
        assert_unique_answer(puzzle)


def ambiguous_puzzle() -> Puzzle:
    """Build an in-memory negative case; never publish it as an official puzzle."""
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    for character in data["characters"]:
        character["clue"] = {"id": character["clue"]["id"], "type": "FACT",
                             "cell": "A1", "status": "INNOCENT"}
    return parse_puzzle(data)


def test_uniqueness_does_not_assume_hidden_statuses():
    with pytest.raises(AssertionError, match="multiple primary answers"):
        assert_unique_answer(ambiguous_puzzle())


def test_public_play_reports_stuck_without_guessing():
    with pytest.raises(pytest.fail.Exception, match="step 0: stuck"):
        play_publicly(ambiguous_puzzle())
