"""Unit tests for griductive.logic.kb_builder (Task 41).

Owner: C (Duy)
"""
from pathlib import Path
import pytest

from griductive.core.constants import ClueType, CompareOp, Parity, RegionKind, Status
from griductive.core.types import AgentKnowledge, Clue, ClueError, Region
from griductive.engine.puzzle_loader import load_puzzle
from griductive.logic.kb_builder import (
    KBStats,
    build_kb,
    build_kb_from_knowledge,
    build_kb_from_puzzle,
    format_puzzle_report,
    summarize_puzzle_file,
)
from griductive.logic.variable_map import VarMap
from griductive.sat.dpll import dpll_solve

ROOT = Path(__file__).resolve().parents[1]


def test_build_kb_empty():
    kb = build_kb(3, revealed_clues=[], known_statuses=[])
    assert kb.size == 3
    assert kb.clauses == []
    assert kb.stats == KBStats(
        size=3,
        primary_vars=9,
        aux_vars=0,
        total_vars=9,
        clue_count=0,
        clue_clauses=0,
        unit_clauses=0,
        clauses=0,
    )
    assert kb.stats.to_dict()["clauses"] == 0


def test_build_kb_clues_and_unit_clauses():
    clues = [
        Clue("c01", ClueType.SAME, a="A1", b="B1"),
        Clue("c02", ClueType.EXACTLY, k=1, region=Region(RegionKind.ROW, index=2)),
    ]
    known = {"A1": Status.CRIMINAL, "C1": Status.INNOCENT}

    kb = build_kb(3, revealed_clues=clues, known_statuses=known)

    # SAME(A1, B1) -> 2 clauses; EXACTLY(1, ROW 2) -> C(3,2)+C(3,3) = 3+1 = 4 clauses
    # 2 unit clauses: [1] for A1=CRIMINAL, [-3] for C1=INNOCENT
    assert kb.stats.primary_vars == 9
    assert kb.stats.aux_vars == 0
    assert kb.stats.total_vars == 9
    assert kb.stats.clue_count == 2
    assert kb.stats.clue_clauses == 6
    assert kb.stats.unit_clauses == 2
    assert kb.stats.clauses == 8
    assert kb.clauses[-2:] == [[1], [-3]]

    # DPLL must deduce B1 = CRIMINAL from A1 = CRIMINAL and SAME(A1, B1)
    res = dpll_solve(kb.clauses, num_vars=kb.stats.total_vars)
    assert res.satisfiable is True
    assert res.model[kb.var_map.var("B1")] is True


def test_build_kb_supports_extension_clues():
    clues = [
        Clue("p1", ClueType.PARITY, parity=Parity.EVEN, region=Region(RegionKind.ROW, index=1)),
        Clue(
            "cmp1",
            ClueType.COMPARE,
            region_a=Region(RegionKind.ROW, index=1),
            region_b=Region(RegionKind.ROW, index=2),
            op=CompareOp.EQUAL,
        ),
    ]
    kb = build_kb(3, revealed_clues=clues, known_statuses=[("A1", Status.CRIMINAL)])
    assert kb.stats.clue_count == 2
    assert kb.stats.unit_clauses == 1
    assert kb.stats.clauses == kb.stats.clue_clauses + 1
    assert dpll_solve(kb.clauses, num_vars=kb.stats.total_vars).satisfiable is True


def test_build_kb_deduplicates_identical_and_rejects_conflicting_statuses():
    kb = build_kb(
        3,
        revealed_clues=[],
        known_statuses=[("A1", Status.INNOCENT), ("A1", Status.INNOCENT)],
    )
    assert kb.clauses == [[-1]]
    assert kb.stats.unit_clauses == 1

    with pytest.raises(ClueError, match="Conflicting known statuses"):
        build_kb(
            3,
            revealed_clues=[],
            known_statuses=[("A1", Status.INNOCENT), ("A1", Status.CRIMINAL)],
        )


def test_build_kb_rejects_invalid_inputs():
    with pytest.raises(ClueError, match="does not match grid size"):
        build_kb(3, revealed_clues=[], var_map=VarMap(4))

    with pytest.raises(ClueError, match="Status enum"):
        build_kb(3, revealed_clues=[], known_statuses=[("A1", "CRIMINAL")])  # type: ignore[list-item]

    with pytest.raises(ClueError, match="outside the 3x3 grid"):
        build_kb(3, revealed_clues=[], known_statuses=[("D4", Status.CRIMINAL)])


def test_build_kb_from_knowledge():
    knowledge = AgentKnowledge(
        size=3,
        revealed_clues=(Clue("c01", ClueType.FACT, cell="B1", status=Status.CRIMINAL),),
        proven_verdicts=(("A1", Status.INNOCENT),),
    )
    kb = build_kb_from_knowledge(knowledge)
    assert kb.clauses == [[2], [-1]]
    assert kb.stats.clue_count == 1
    assert kb.stats.clue_clauses == 1
    assert kb.stats.unit_clauses == 1
    assert kb.stats.clauses == 2


def test_build_kb_from_puzzle_initial_and_full():
    puzzle = load_puzzle(ROOT / "puzzles/3x3/p3x3_01.json")
    kb0 = build_kb_from_puzzle(puzzle, revealed_only=True)
    kb_full = build_kb_from_puzzle(puzzle, revealed_only=False, include_statuses=False)

    assert kb0.stats.primary_vars == 9
    assert kb0.stats.clue_count == sum(1 for c in puzzle.characters if c.revealed)
    assert kb0.stats.unit_clauses == kb0.stats.clue_count
    assert kb_full.stats.clue_count == 9
    assert kb_full.stats.unit_clauses == 0
    assert dpll_solve(kb_full.clauses, num_vars=kb_full.stats.total_vars).satisfiable is True


def test_summarize_and_format_report_across_all_puzzles():
    puzzle_paths = sorted((ROOT / "puzzles").glob("*/*.json"))
    assert len(puzzle_paths) >= 7

    for path in puzzle_paths:
        summary = summarize_puzzle_file(path)
        assert summary["primary_vars"] == summary["size"] ** 2
        assert summary["full_clues"] == summary["size"] ** 2
        assert summary["init_clauses"] > 0
        assert summary["full_clauses"] >= summary["init_clauses"]

    report = format_puzzle_report(puzzle_paths)
    assert "| Puzzle | Size | Primary Vars |" in report
    assert "p3x3_01" in report
    assert "p5x5_01" in report
