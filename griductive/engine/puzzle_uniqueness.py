"""Offline brute-force verification of all clues and initially revealed statuses."""

import argparse
from dataclasses import dataclass
from itertools import product
import json
from pathlib import Path
from time import perf_counter
from typing import Literal

from griductive.core.constants import Status
from griductive.core.regions import all_cells
from griductive.core.types import Assignment, Puzzle
from griductive.engine.puzzle_loader import load_puzzle
from griductive.logic.evaluator import evaluate


@dataclass(frozen=True)
class UniquenessResult:
    """Up to two detached witnesses; MULTIPLE does not count all solutions."""

    status: Literal["UNSAT", "UNIQUE", "MULTIPLE"]
    solutions: tuple[Assignment, ...]
    assignments_checked: int
    runtime_ms: float


def check_uniqueness(puzzle: Puzzle) -> UniquenessResult:
    """Enumerate a loader-validated puzzle without consulting hidden statuses."""
    started = perf_counter()
    cells = all_cells(puzzle.size)
    fixed = {c.cell: c.status is Status.CRIMINAL
             for c in puzzle.characters if c.revealed}
    unknown = [cell for cell in cells if cell not in fixed]
    clues = [c.clue for c in puzzle.characters]
    assignment = {cell: fixed.get(cell, False) for cell in cells}
    # Visit every evaluator before enumeration, even if an earlier clue is false.
    for clue in clues:
        evaluate(clue, assignment, puzzle.size)
    solutions = []
    checked = 0
    for values in product((False, True), repeat=len(unknown)):
        assignment.update(zip(unknown, values))
        checked += 1
        if all(evaluate(clue, assignment, puzzle.size) for clue in clues):
            solutions.append(assignment.copy())
            if len(solutions) == 2:
                break
    status = ("UNSAT", "UNIQUE", "MULTIPLE")[len(solutions)]
    return UniquenessResult(status, tuple(solutions), checked,
                            (perf_counter() - started) * 1000)


def main(argv: list[str] | None = None) -> int:
    """Check selected files, or all repository puzzles, and report per-file errors."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="puzzle JSON files")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2] / "puzzles"
    paths = args.paths or sorted(path for size in (3, 4, 5)
                                for path in (root / f"{size}x{size}").glob("*.json"))
    if not paths:
        print("ERROR: no puzzle files found")
        return 1
    failed = False
    for path in paths:
        try:
            puzzle = load_puzzle(path)
            result = check_uniqueness(puzzle)
            print(f"{path} | {puzzle.size}x{puzzle.size} | {result.status} | "
                  f"assignments_checked={result.assignments_checked} | "
                  f"runtime_ms={result.runtime_ms:.3f}", flush=True)
            if result.status == "UNIQUE":
                answer = {c.cell: c.status is Status.CRIMINAL for c in puzzle.characters}
                if result.solutions[0] != answer:
                    print(f"{path} | ERROR: unique solution does not match stored answer")
                    failed = True
            else:
                failed = True
                for index, solution in enumerate(result.solutions, start=1):
                    print(f"  solution {index}: {json.dumps(solution)}")
        except Exception as error:
            # A broken file must not prevent verification of the remaining files.
            print(f"{path} | ERROR: {type(error).__name__}: {error}", flush=True)
            failed = True
    return int(failed)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("INTERRUPTED: verification incomplete")
        raise SystemExit(130)
