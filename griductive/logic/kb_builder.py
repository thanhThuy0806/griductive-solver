"""Build KB_t = CNF(revealed clues) + unit clauses; report var/clause counts.

Owner: C (Duy)
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from griductive.core.constants import Status
from griductive.core.types import AgentKnowledge, CNF, CellId, Clue, ClueError, Puzzle
from griductive.logic.cnf_encoder import encode_clue
from griductive.logic.variable_map import VarMap

KnownStatuses = Union[Mapping[CellId, Status], Iterable[Tuple[CellId, Status]]]


@dataclass(frozen=True)
class KBStats:
    """Variable and clause counts for a constructed knowledge base KB_t."""

    size: int
    primary_vars: int
    aux_vars: int
    total_vars: int
    clue_count: int
    clue_clauses: int
    unit_clauses: int
    clauses: int

    def to_dict(self) -> Dict[str, int]:
        """Return statistics as a plain dictionary for logging or CSV export."""
        return {
            "size": self.size,
            "primary_vars": self.primary_vars,
            "aux_vars": self.aux_vars,
            "total_vars": self.total_vars,
            "clue_count": self.clue_count,
            "clue_clauses": self.clue_clauses,
            "unit_clauses": self.unit_clauses,
            "clauses": self.clauses,
        }


@dataclass(frozen=True)
class KnowledgeBase:
    """Constructed CNF knowledge base KB_t together with its variable map and stats."""

    size: int
    var_map: VarMap
    clauses: CNF
    stats: KBStats


def _iter_status_pairs(known_statuses: KnownStatuses) -> List[Tuple[CellId, Status]]:
    """Normalize known statuses from a mapping or iterable into (cell, Status) pairs."""
    if isinstance(known_statuses, Mapping):
        pairs = list(known_statuses.items())
    else:
        pairs = list(known_statuses)

    normalized: List[Tuple[CellId, Status]] = []
    seen: Dict[CellId, Status] = {}
    for item in pairs:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ClueError(f"Expected (cell, Status) pair, got {item!r}")
        cell, status = item
        if not isinstance(status, Status):
            raise ClueError(f"Status for cell {cell!r} must be a Status enum, got {status!r}")
        if cell in seen:
            if seen[cell] is not status:
                raise ClueError(f"Conflicting known statuses for cell {cell!r}")
            continue
        seen[cell] = status
        normalized.append((cell, status))
    return normalized


def build_kb(
    size: int,
    revealed_clues: Iterable[Clue],
    known_statuses: KnownStatuses = (),
    var_map: Optional[VarMap] = None,
) -> KnowledgeBase:
    """Build KB_t = CNF(revealed_clues) AND unit_clauses(known_statuses) with stats."""
    if var_map is None:
        vm = VarMap(size)
    else:
        if var_map.n != size:
            raise ClueError(f"VarMap size {var_map.n} does not match grid size {size}")
        vm = var_map

    clues_list = list(revealed_clues)
    clue_cnf: CNF = []
    for clue in clues_list:
        clue_cnf.extend(encode_clue(clue, vm))

    unit_cnf: CNF = []
    for cell, status in _iter_status_pairs(known_statuses):
        var = vm.var(cell)
        unit_cnf.append([var if status is Status.CRIMINAL else -var])

    all_clauses: CNF = clue_cnf + unit_cnf
    stats = KBStats(
        size=size,
        primary_vars=vm.num_primary,
        aux_vars=vm.num_aux,
        total_vars=vm.num_vars,
        clue_count=len(clues_list),
        clue_clauses=len(clue_cnf),
        unit_clauses=len(unit_cnf),
        clauses=len(all_clauses),
    )
    return KnowledgeBase(size=size, var_map=vm, clauses=all_clauses, stats=stats)


def build_kb_from_knowledge(knowledge: AgentKnowledge) -> KnowledgeBase:
    """Build KB_t directly from an AgentKnowledge public snapshot."""
    return build_kb(
        size=knowledge.size,
        revealed_clues=knowledge.revealed_clues,
        known_statuses=knowledge.proven_verdicts,
    )


def build_kb_from_puzzle(
    puzzle: Puzzle,
    revealed_only: bool = True,
    include_statuses: bool = True,
) -> KnowledgeBase:
    """Build KB_0 (revealed_only=True) or full KB (revealed_only=False) from a Puzzle."""
    cards = [c for c in puzzle.characters if (c.revealed or not revealed_only)]
    clues = [c.clue for c in cards]
    statuses = [(c.cell, c.status) for c in cards] if include_statuses else []
    return build_kb(size=puzzle.size, revealed_clues=clues, known_statuses=statuses)


def summarize_puzzle_file(path: Union[str, Path]) -> Dict[str, Any]:
    """Load one puzzle JSON file and return initial (KB_0) and full-clue KB stats."""
    puzzle_path = Path(path)
    raw = json.loads(puzzle_path.read_text(encoding="utf-8-sig"))
    size = raw["size"]
    chars = raw["characters"]

    init_clues = [Clue.from_dict(ch["clue"]) for ch in chars if ch["revealed"]]
    init_statuses = [(ch["cell"], Status(ch["status"])) for ch in chars if ch["revealed"]]
    all_clues = [Clue.from_dict(ch["clue"]) for ch in chars]

    kb_init = build_kb(size, init_clues, init_statuses)
    kb_all_clues = build_kb(size, all_clues, ())

    return {
        "puzzle": puzzle_path.stem,
        "size": size,
        "primary_vars": kb_all_clues.stats.primary_vars,
        "aux_vars": kb_all_clues.stats.aux_vars,
        "init_clues": kb_init.stats.clue_count,
        "init_units": kb_init.stats.unit_clauses,
        "init_clauses": kb_init.stats.clauses,
        "full_clues": kb_all_clues.stats.clue_count,
        "full_clauses": kb_all_clues.stats.clauses,
    }


def format_puzzle_report(paths: Sequence[Union[str, Path]]) -> str:
    """Format a Markdown table of variable and clause counts across puzzle JSON files."""
    rows = [summarize_puzzle_file(p) for p in paths]
    header = (
        "| Puzzle | Size | Primary Vars | Aux Vars | "
        "KB_0 Clues | KB_0 Units | KB_0 Clauses | Full Clues | Full Clauses |"
    )
    sep = "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    lines = [header, sep]
    for r in rows:
        lines.append(
            f"| {r['puzzle']} | {r['size']}x{r['size']} | {r['primary_vars']} | {r['aux_vars']} | "
            f"{r['init_clues']} | {r['init_units']} | {r['init_clauses']} | "
            f"{r['full_clues']} | {r['full_clauses']} |"
        )
    return "\n".join(lines)


def _discover_puzzles(root: Path) -> List[Path]:
    """Return all puzzle JSON files under puzzles/ sorted by grid size and filename."""
    return sorted((root / "puzzles").glob("*/*.json"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point to print variable and clause statistics for puzzle JSON files."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        paths = [Path(arg) for arg in args]
    else:
        repo_root = Path(__file__).resolve().parents[2]
        paths = _discover_puzzles(repo_root)
    print(format_puzzle_report(paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
