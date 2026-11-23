"""Check puzzle truth, primary uniqueness and play using public evidence only."""

import json
from pathlib import Path
from time import perf_counter

import pytest

from griductive.agent.entailment import Classification
from griductive.core.constants import Status, VerdictResult
from griductive.core.types import Clue, Puzzle
from griductive.engine.game_engine import GameEngine
from griductive.engine.puzzle_loader import load_puzzle, parse_puzzle
from griductive.engine.puzzle_uniqueness import check_uniqueness
from griductive.engine.verdict import classify
from griductive.logic.cnf_encoder import encode_clue
from griductive.logic.evaluator import evaluate
from griductive.logic.variable_map import VarMap
from griductive.sat.dpll import DpllSolver
from griductive.sat.stats import SatStats


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "puzzles/3x3/p3x3_01.json"
PATHS = sorted((ROOT / "puzzles").glob("*x*/p*x*_*.json"))
MANIFEST = json.loads((ROOT / "docs/puzzle_sources/test_set.json").read_text(encoding="utf-8"))
CASES = {ROOT / case["path"]: case for case in MANIFEST["cases"]}


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
    result = solver.solve(residual)
    assert not result.timed_out, "answer check timed out"
    assert result.satisfiable, "answer violates CNF"
    result = solver.solve(clauses)
    assert not result.timed_out, "consistency check timed out"
    assert result.satisfiable, "complete clue set is inconsistent"
    blocking = [-v if value else v for v, value in answer.items()]
    result = solver.solve([*clauses, blocking])
    assert not result.timed_out, "uniqueness check timed out"
    assert not result.satisfiable, "multiple primary answers"
    return vm, len(clauses)


def play_publicly(puzzle: Puzzle, trace: list | None = None) -> int:
    """Open one proved card at a time, selecting moves only from public snapshots."""
    engine = GameEngine(puzzle)
    steps = 0
    while not engine.is_solved:
        state = engine.get_public_state()
        for character in state.characters:
            if character.revealed:
                continue
            knowledge = engine.get_agent_knowledge()
            verdict = classify(knowledge, character.cell)
            assert verdict is not Classification.INCONSISTENT, f"step {steps}: inconsistent KB"
            if not verdict.is_forced:
                continue
            response = engine.submit_verdict(character.cell, Status(verdict.value))
            assert response.result is VerdictResult.ACCEPTED, f"step {steps}: {character.cell}"
            if trace is not None:
                trace.append((knowledge, character.cell, Status(verdict.value)))
            steps += 1
            break  # Rebuild public evidence after each reveal.
        else:
            hidden = [c.cell for c in state.characters if not c.revealed]
            pytest.fail(f"step {steps}: stuck with hidden cards {hidden}")
    return steps


def needs_multiple_clues(knowledge, cell: str, status: Status) -> bool:
    """No single revealed clue proves this move, even with all known statuses."""
    vm = VarMap(knowledge.size)
    units = [[vm.var(c) if s is Status.CRIMINAL else -vm.var(c)]
             for c, s in knowledge.proven_verdicts]
    opposite = -vm.var(cell) if status is Status.CRIMINAL else vm.var(cell)
    for clue in knowledge.revealed_clues:
        result = DpllSolver().solve([*units, *encode_clue(clue, vm), [opposite]])
        assert not result.timed_out, "difficulty check timed out"
        if not result.satisfiable:
            return False
    return True


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.name)
def test_dataset_structure(path):
    puzzle = load_puzzle(path)
    assert path.parent.name == f"{puzzle.size}x{puzzle.size}"
    assert len(puzzle.characters) == puzzle.size ** 2
    names = [c.name for c in puzzle.characters]
    assert names == sorted(names), "display names must follow board order"


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.name)
def test_dataset_clue_truth(path):
    assert_true_clues(load_puzzle(path))


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.name)
def test_dataset_primary_uniqueness(path):
    assert_unique_answer(load_puzzle(path))


@pytest.mark.parametrize("path", [p for p in PATHS if p.parent.name != "5x5"],
                         ids=lambda p: p.name)
def test_dataset_bruteforce_uniqueness(path):
    puzzle = load_puzzle(path)
    result = check_uniqueness(puzzle)
    assert result.status == "UNIQUE"
    assert result.solutions[0] == {c.cell: c.status is Status.CRIMINAL
                                   for c in puzzle.characters}


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.name)
def test_dataset_public_play(path, record_property, monkeypatch):
    puzzle = load_puzzle(path)
    trace = []
    totals = SatStats()
    original_solve = DpllSolver.solve

    def measured_solve(solver, *args, **kwargs):
        result = original_solve(solver, *args, **kwargs)
        assert not result.timed_out, "public play timed out"
        totals.add(result.stats)
        return result

    with monkeypatch.context() as patch:
        patch.setattr(DpllSolver, "solve", measured_solve)
        started = perf_counter()
        steps = play_publicly(puzzle, trace)
        runtime_ms = (perf_counter() - started) * 1000
    assert steps == sum(not c.revealed for c in puzzle.characters)
    joint_steps = sum(needs_multiple_clues(*step) for step in trace)
    if path in CASES:
        assert joint_steps >= CASES[path]["min_joint_steps"], "deductions became too shallow"
    else:
        assert joint_steps == 0, "the FACT regression should need only one clue per move"
    vm, clauses = assert_unique_answer(puzzle)
    record_property("reveal_steps", steps)
    record_property("primary_vars", vm.num_primary)
    record_property("aux_vars", vm.num_aux)
    record_property("clauses", clauses)
    record_property("joint_steps", joint_steps)
    record_property("reveal_order", ",".join(step[1] for step in trace))
    record_property("runtime_ms", round(runtime_ms, 3))
    for key, value in totals.to_dict().items():
        record_property("sat_" + key if key == "runtime_ms" else key, value)


def test_dataset_readiness():
    # The old FACT chain stays a regression fixture, outside the seven-case set.
    assert len(CASES) == len(MANIFEST["cases"]) == 7
    assert set(CASES) == set(PATHS) - {SAMPLE}
    assert all(case["origin"] in ("adapted", "authored") and case["sources"]
               for case in CASES.values())
    counts = {size: sum(p.parent.name == f"{size}x{size}" for p in CASES)
              for size in (3, 4, 5)}
    target = {3: 3, 4: 3, 5: 1}
    assert counts == target, counts


def test_dataset_covers_clue_language_and_regions():
    clues = [c.clue for path in PATHS for c in load_puzzle(path).characters]
    assert {c.type.value for c in clues} == {
        "FACT", "SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST", "PARITY", "COMPARE"}
    regions = [r for c in clues for r in (c.region, c.region_a, c.region_b) if r is not None]
    assert {r.kind.value for r in regions} == {"ROW", "COL", "NEIGHBORS", "CELLS"}


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
