"""Logic Agent: deduction loop, Hint and Auto Solve (Owner: A).

The Agent only knows PUBLIC information: revealed clues and proved verdicts
(KB_t = CNF(revealed clues) + unit clauses for proved verdicts). It never reads
the hidden solution or unrevealed clues, and it never imports `griductive.engine`.

Deduction step:
  1. classify every unresolved cell with SAT (CRIMINAL / INNOCENT / UNKNOWN);
  2. pick the first forced cell in row-major order (deterministic, never a guess);
  3. submit that verdict to the game; on ACCEPTED, add the status and the newly
     revealed clue to the knowledge base;
  4. record everything in the deduction trace.

Public methods that run SAT queries (`step`, `hint`) leave the checker's query log
empty when they return, so every query belongs to exactly one trace step or Hint.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import perf_counter
from typing import Iterable

from griductive.agent.entailment import Classification, EntailmentChecker, SatQuery
from griductive.agent.grid import row_major_cells
from griductive.agent.protocols import Clause, ClueEncoder, Clue, GameInterface, PublicCard
from griductive.agent.trace import DeductionTrace, TraceStep
from griductive.sat.interface import SatSolver

CRIMINAL = "CRIMINAL"
INNOCENT = "INNOCENT"


class RunStatus(str, Enum):
    SOLVED = "SOLVED"
    STUCK = "STUCK"                  # nothing is provable, but cards remain face-down
    INCONSISTENT = "INCONSISTENT"    # KB_t is unsatisfiable
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass
class RunResult:
    status: RunStatus
    trace: DeductionTrace
    accepted_steps: int
    sat_calls: int
    runtime_ms: float
    error: str | None = None


@dataclass(frozen=True)
class Hint:
    """A provable next verdict plus the public facts that prove it."""

    cell: str
    verdict: str                                   # "CRIMINAL" | "INNOCENT"
    support_clue_ids: list[str]                    # revealed clues needed for the proof
    support_cells: list[str]                       # already-proved cells needed for the proof
    sat_queries: list[SatQuery] = field(default_factory=list)
    message: str = ""


class LogicAgent:
    def __init__(self, size: int, encoder: ClueEncoder, solver: SatSolver | None = None,
                 use_witnesses: bool = True) -> None:
        self.size = size
        self.encoder = encoder
        self._solver = solver
        self._use_witnesses = use_witnesses
        self.cells = row_major_cells(size)
        self._cell_set = set(self.cells)
        self.reset()

    # ------------------------------------------------------------ state
    def reset(self) -> None:
        """Forget everything (used by Restart / Load)."""
        self.checker = EntailmentChecker(self._solver, self._use_witnesses)
        self.trace = DeductionTrace()
        self.last_error: str | None = None
        self._clues: dict[str, Clue] = {}
        self._clue_clauses: dict[str, list[Clause]] = {}
        self._proved: dict[str, str] = {}

    @property
    def proved(self) -> dict[str, str]:
        """Copy of {cell: status} for every cell whose verdict is known."""
        return dict(self._proved)

    def unresolved_cells(self) -> list[str]:
        return [c for c in self.cells if c not in self._proved]

    def observe(self, cell: str, status: str, clue: Clue | None = None) -> None:
        """Add one piece of public knowledge: a known status and (optionally) its clue."""
        if cell not in self._cell_set:
            raise ValueError(f"unknown cell {cell!r}")
        if status not in (CRIMINAL, INNOCENT):
            raise ValueError(f"status must be CRIMINAL or INNOCENT, got {status!r}")
        if self._proved.get(cell, status) != status:
            raise ValueError(f"conflicting status for {cell}")
        clauses = None
        if clue is not None:
            cid = clue.get("id")
            if cid is None:
                raise ValueError("clue has no 'id'")
            if cid in self._clues:
                raise ValueError(f"duplicate clue id {cid!r}")
            clauses = [list(c) for c in self.encoder.encode_clue(clue)]
        # Only mutate state after everything validated and encoded.
        self._proved[cell] = status
        if clue is not None:
            self._clues[cid] = clue
            self._clue_clauses[cid] = clauses

    def observe_cards(self, cards: Iterable[PublicCard]) -> None:
        """Load the initial face-up cards."""
        for card in cards:
            self.observe(card.cell, card.status, card.clue)
        self.trace.initial_clue_ids = list(self._clue_clauses)

    # ------------------------------------------------------------ knowledge base
    def _premises(self) -> dict[str, list[Clause]]:
        """Named groups of clauses: one per revealed clue, one unit per proved cell."""
        premises: dict[str, list[Clause]] = {}
        for cid, clauses in self._clue_clauses.items():
            premises[f"clue:{cid}"] = clauses
        for cell, status in self._proved.items():
            lit = self.encoder.var_of(cell)
            premises[f"cell:{cell}"] = [[lit if status == CRIMINAL else -lit]]
        return premises

    def knowledge_base(self) -> list[Clause]:
        """KB_t as CNF: revealed clues + unit clauses of proved verdicts."""
        return [list(c) for group in self._premises().values() for c in group]

    # ------------------------------------------------------------ reasoning
    def classify_unresolved(self) -> dict[str, Classification]:
        """{cell: classification} for every unresolved cell, in row-major order."""
        cells = self.unresolved_cells()
        if not cells:
            return {}
        variables = {c: self.encoder.var_of(c) for c in cells}
        result = self.checker.classify_all(self.knowledge_base(), variables.values())
        return {c: result[v] for c, v in variables.items()}

    @staticmethod
    def _forced_cells(classes: dict[str, Classification]) -> list[str]:
        return [c for c, k in classes.items() if k.is_forced]   # dict keeps row-major order

    # ------------------------------------------------------------ deduction loop
    def step(self, game: GameInterface) -> RunStatus | None:
        """One deduction step.

        Returns None after an accepted verdict (keep going), otherwise the terminal
        status: SOLVED, STUCK, INCONSISTENT or ERROR.
        """
        if not self.unresolved_cells():
            return RunStatus.SOLVED

        self.checker.drain_log()                       # drop queries of earlier hints
        active = list(self._clue_clauses)
        kb_size = len(self.knowledge_base())
        classes = self.classify_unresolved()
        queries = self.checker.drain_log()
        forced = self._forced_cells(classes)
        number = len(self.trace.steps) + 1

        if not forced:
            inconsistent = any(k == Classification.INCONSISTENT for k in classes.values())
            status = RunStatus.INCONSISTENT if inconsistent else RunStatus.STUCK
            self.trace.steps.append(TraceStep(
                step=number, active_clue_ids=active, sat_queries=queries, forced_count=0,
                cell=None, verdict=None, result=status.value, kb_clauses=kb_size))
            return status

        cell = forced[0]                               # row-major, deterministic
        verdict = classes[cell].value
        response = game.submit_verdict(cell, verdict)
        step = TraceStep(
            step=number, active_clue_ids=active, sat_queries=queries,
            forced_count=len(forced), cell=cell, verdict=verdict,
            result=response.result, kb_clauses=kb_size)
        self.trace.steps.append(step)

        if response.result != "ACCEPTED":
            self.last_error = (f"engine answered {response.result} to a forced verdict "
                               f"({cell} = {verdict})")
            return RunStatus.ERROR

        clue = response.clue
        self.observe(cell, verdict, clue)
        if clue is not None:
            step.new_clue_id = clue["id"]
            step.new_clue = clue
        return None

    def run(self, game: GameInterface, timeout_s: float | None = None) -> RunResult:
        """Auto Solve: repeat `step` until a terminal state."""
        start = perf_counter()
        error: str | None = None
        try:
            while True:
                if timeout_s is not None and perf_counter() - start > timeout_s:
                    status = RunStatus.TIMEOUT
                    break
                outcome = self.step(game)
                if outcome is not None:
                    status = outcome
                    error = self.last_error
                    break
        except Exception as exc:                       # report failures, do not crash the GUI
            status = RunStatus.ERROR
            error = f"{type(exc).__name__}: {exc}"
        self.trace.final_status = status.value
        accepted = sum(1 for s in self.trace.steps if s.result == "ACCEPTED")
        return RunResult(status, self.trace, accepted, self.trace.total_sat_calls,
                         (perf_counter() - start) * 1000.0, error)

    # ------------------------------------------------------------ hint
    def hint(self) -> Hint | None:
        """A forced cell and a minimal set of public facts proving it, or None.

        Uses only the public KB. Does not change the knowledge base or the trace.
        """
        self.checker.drain_log()
        classes = self.classify_unresolved()
        queries = self.checker.drain_log()
        forced = self._forced_cells(classes)
        if not forced:
            return None

        cell = forced[0]
        verdict = classes[cell].value
        var = self.encoder.var_of(cell)
        refutation = -var if verdict == CRIMINAL else var     # KB ∧ refutation is UNSAT
        negated = "¬" if verdict == CRIMINAL else ""

        # Deletion-based minimisation: drop every premise that is not needed.
        premises = self._premises()
        keep = list(premises)
        for key in list(keep):
            trial = [k for k in keep if k != key]
            clauses = [c for k in trial for c in premises[k]] + [[refutation]]
            result = self._solve(clauses)
            queries.append(SatQuery(len(queries) + 1, f"KB \\ {{{key}}} ∧ {negated}C{var}",
                                    refutation, result.satisfiable, dict(result.stats or {})))
            if not result.satisfiable:
                keep = trial

        clue_ids = [k[len("clue:"):] for k in keep if k.startswith("clue:")]
        cell_ids = [k[len("cell:"):] for k in keep if k.startswith("cell:")]
        parts = []
        if clue_ids:
            parts.append("clue(s) " + ", ".join(clue_ids))
        if cell_ids:
            parts.append("known cell(s) " + ", ".join(cell_ids))
        because = " and ".join(parts) if parts else "the rules alone"
        return Hint(cell, verdict, clue_ids, cell_ids, queries,
                    f"{cell} must be {verdict}: it follows from {because}.")

    def _solve(self, clauses: list[Clause]):
        return self.checker.solver.solve(clauses)
