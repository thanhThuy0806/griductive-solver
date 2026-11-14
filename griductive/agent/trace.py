"""Deduction trace (Owner: A).

One TraceStep per deduction step: step number, active clue ids, SAT queries,
verdict, newly revealed clue. A terminal step (cell=None) is appended when the
run ends STUCK or INCONSISTENT, so the SAT calls spent on that last
classification are not lost.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from griductive.agent.entailment import SatQuery


@dataclass
class TraceStep:
    step: int
    active_clue_ids: list[str]            # clues in KB_t when the queries were made
    sat_queries: list[SatQuery]
    forced_count: int                     # how many unresolved cells were forced at this step
    cell: str | None                      # chosen cell (None for a terminal step)
    verdict: str | None                   # "CRIMINAL" | "INNOCENT" | None
    result: str                           # ACCEPTED / NOT_PROVABLE / CONTRADICTED / STUCK / INCONSISTENT
    new_clue_id: str | None = None
    new_clue: dict[str, Any] | None = None
    kb_clauses: int = 0                   # number of clauses in KB_t

    @property
    def sat_calls(self) -> int:
        return len(self.sat_queries)


@dataclass
class DeductionTrace:
    initial_clue_ids: list[str] = field(default_factory=list)
    steps: list[TraceStep] = field(default_factory=list)
    final_status: str | None = None

    @property
    def total_sat_calls(self) -> int:
        return sum(s.sat_calls for s in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_clue_ids": list(self.initial_clue_ids),
            "final_status": self.final_status,
            "steps": [asdict(s) for s in self.steps],
        }

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def format_table(self) -> str:
        """Plain-text table, handy for the terminal and the report."""
        header = ["Step", "Cell", "Verdict", "Result", "New clue", "Forced", "SAT", "Active clues"]
        rows = [header]
        for s in self.steps:
            rows.append([
                str(s.step), s.cell or "-", s.verdict or "-", s.result,
                s.new_clue_id or "-", str(s.forced_count), str(s.sat_calls),
                ",".join(s.active_clue_ids) or "-",
            ])
        widths = [max(len(r[i]) for r in rows) for i in range(len(header))]
        lines = ["  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows]
        lines.insert(1, "  ".join("-" * w for w in widths))
        lines.append(f"Final status: {self.final_status}")
        return "\n".join(lines)
