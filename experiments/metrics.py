"""Metric collection helpers for batch Griductive DPLL experiments.

Owner: B
"""
from __future__ import annotations

import csv
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from griductive.agent.logic_agent import LogicAgent, RunStatus
from griductive.agent.trace import DeductionTrace
from griductive.engine.agent_api import AgentAPI
from griductive.engine.game_engine import GameEngine
from griductive.engine.puzzle_loader import load_puzzle
from griductive.sat.dpll import DpllSolver


CSV_FIELDNAMES: tuple[str, ...] = (
    "puzzle",
    "puzzle_id",
    "size",
    "config",
    "trial",
    "status",
    "primary_vars",
    "aux_vars",
    "total_vars",
    "initial_clauses",
    "clauses",
    "sat_calls",
    "decisions",
    "propagations",
    "backtracks",
    "steps",
    "trace_steps",
    "runtime_ms",
    "sat_runtime_ms",
    "error",
)

STEP_CSV_FIELDNAMES: tuple[str, ...] = (
    "puzzle",
    "puzzle_id",
    "size",
    "config",
    "trial",
    "step",
    "cell",
    "verdict",
    "result",
    "forced_count",
    "kb_clauses",
    "sat_calls",
    "decisions",
    "propagations",
    "backtracks",
    "sat_runtime_ms",
    "new_clue_id",
)


@dataclass(frozen=True)
class ExperimentConfig:
    """Solver and agent configuration for an experiment run."""

    name: str = "dpll_full"
    use_pure_literal: bool = True
    use_heuristic: bool = True
    use_witnesses: bool = True
    solver_timeout_s: float | None = None


DEFAULT_CONFIG = ExperimentConfig()

ABLATION_CONFIGS: tuple[ExperimentConfig, ...] = (
    ExperimentConfig(
        name="dpll_full",
        use_pure_literal=True,
        use_heuristic=True,
        use_witnesses=True,
    ),
    ExperimentConfig(
        name="dpll_no_pure",
        use_pure_literal=False,
        use_heuristic=True,
        use_witnesses=True,
    ),
    ExperimentConfig(
        name="dpll_no_heuristic",
        use_pure_literal=True,
        use_heuristic=False,
        use_witnesses=True,
    ),
    ExperimentConfig(
        name="dpll_basic",
        use_pure_literal=False,
        use_heuristic=False,
        use_witnesses=True,
    ),
    ExperimentConfig(
        name="dpll_no_witnesses",
        use_pure_literal=True,
        use_heuristic=True,
        use_witnesses=False,
    ),
)

CONFIG_REGISTRY: dict[str, ExperimentConfig] = {
    cfg.name: cfg for cfg in ABLATION_CONFIGS
}


@dataclass(frozen=True)
class PuzzleMetrics:
    """Aggregated experiment metrics for a single puzzle run."""

    puzzle: str
    puzzle_id: str
    size: int
    config: str
    trial: int
    status: str
    primary_vars: int
    aux_vars: int
    total_vars: int
    initial_clauses: int
    clauses: int
    sat_calls: int
    decisions: int
    propagations: int
    backtracks: int
    steps: int
    trace_steps: int
    runtime_ms: float
    sat_runtime_ms: float
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to a CSV-ready dictionary with rounded floats."""
        data = asdict(self)
        data["runtime_ms"] = round(self.runtime_ms, 4)
        data["sat_runtime_ms"] = round(self.sat_runtime_ms, 4)
        return data


@dataclass(frozen=True)
class StepMetrics:
    """Per-step deduction metrics for detailed trace analysis."""

    puzzle: str
    puzzle_id: str
    size: int
    config: str
    trial: int
    step: int
    cell: str
    verdict: str
    result: str
    forced_count: int
    kb_clauses: int
    sat_calls: int
    decisions: int
    propagations: int
    backtracks: int
    sat_runtime_ms: float
    new_clue_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to a CSV-ready dictionary with rounded floats."""
        data = asdict(self)
        data["sat_runtime_ms"] = round(self.sat_runtime_ms, 4)
        return data


def _extract_query_stats(queries: Iterable[Any]) -> dict[str, int | float]:
    """Sum DPLL metrics across an iterable of SatQuery objects."""
    sat_calls = 0
    decisions = 0
    propagations = 0
    backtracks = 0
    sat_runtime_ms = 0.0

    for query in queries:
        stats = getattr(query, "stats", None) or {}
        sat_calls += int(stats.get("sat_calls", 1))
        decisions += int(stats.get("decisions", 0))
        propagations += int(stats.get("propagations", 0))
        backtracks += int(stats.get("backtracks", 0))
        rt = stats.get("runtime_ms", stats.get("runtime", 0.0))
        sat_runtime_ms += float(rt)

    return {
        "sat_calls": sat_calls,
        "decisions": decisions,
        "propagations": propagations,
        "backtracks": backtracks,
        "sat_runtime_ms": sat_runtime_ms,
    }


def collect_solver_stats(
    trace: DeductionTrace,
    extra_queries: Sequence[Any] = (),
) -> dict[str, int | float]:
    """Aggregate solver statistics across all trace steps and any undrained queries."""
    all_queries: list[Any] = []
    for step in trace.steps:
        all_queries.extend(step.sat_queries)
    if extra_queries:
        all_queries.extend(extra_queries)
    return _extract_query_stats(all_queries)


def extract_var_counts(
    api: AgentAPI,
    kb_clauses: Sequence[Sequence[int]],
    size: int,
) -> tuple[int, int, int]:
    """Return `(primary_vars, aux_vars, total_vars)` from AgentAPI's VarMap.

    Falls back to inspecting the CNF literals if `_vm` is unavailable.
    """
    vm = getattr(api, "_vm", None)
    if vm is not None:
        primary_vars = int(vm.num_primary)
        aux_vars = int(vm.num_aux)
        total_vars = int(vm.num_vars)
        return primary_vars, aux_vars, total_vars

    primary_vars = size * size
    max_var = max((abs(lit) for clause in kb_clauses for lit in clause), default=primary_vars)
    aux_vars = max(0, max_var - primary_vars)
    return primary_vars, aux_vars, primary_vars + aux_vars


def _relative_puzzle_label(puzzle_path: Path, repo_root: Path | None) -> str:
    """Format puzzle path as a POSIX path relative to repo_root when possible."""
    resolved = puzzle_path.resolve()
    if repo_root is not None:
        try:
            return resolved.relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    return puzzle_path.as_posix()


def run_single_puzzle(
    puzzle_path: str | Path,
    config: ExperimentConfig = DEFAULT_CONFIG,
    timeout_s: float | None = None,
    trial: int = 1,
    repo_root: Path | None = None,
) -> tuple[PuzzleMetrics, list[StepMetrics]]:
    """Run one puzzle with the specified DPLL configuration and collect all metrics."""
    path = Path(puzzle_path)
    puzzle_label = _relative_puzzle_label(path, repo_root)
    puzzle_id = path.stem

    puzzle = load_puzzle(path)
    engine = GameEngine(puzzle)
    api = AgentAPI(engine)

    solver = DpllSolver(
        use_pure_literal=config.use_pure_literal,
        use_heuristic=config.use_heuristic,
        timeout=config.solver_timeout_s,
    )
    agent = LogicAgent(
        api.size,
        encoder=api,
        solver=solver,
        use_witnesses=config.use_witnesses,
    )
    agent.observe_cards(api.public_cards())
    initial_clauses = len(agent.knowledge_base())

    wall_start = time.perf_counter()
    result = agent.run(api, timeout_s=timeout_s)
    wall_ms = (time.perf_counter() - wall_start) * 1000.0

    # Include any undrained queries (e.g., if a run timed out or errored mid-step).
    undrained = list(getattr(agent.checker, "queries", ()))
    agg = collect_solver_stats(result.trace, extra_queries=undrained)

    # Prefer solver-accumulated totals if present and consistent, otherwise trace sums.
    final_kb = agent.knowledge_base()
    primary_vars, aux_vars, total_vars = extract_var_counts(api, final_kb, puzzle.size)

    sat_calls = int(
        getattr(result, "sat_calls", getattr(result, "total_sat_calls", agg["sat_calls"]))
    )
    if undrained and sat_calls < int(agg["sat_calls"]):
        sat_calls = int(agg["sat_calls"])

    runtime_ms = float(
        getattr(result, "runtime_ms", getattr(result, "elapsed_ms", wall_ms))
    )
    status_str = (
        result.status.value if isinstance(result.status, RunStatus) else str(result.status)
    )

    puzzle_metrics = PuzzleMetrics(
        puzzle=puzzle_label,
        puzzle_id=puzzle_id,
        size=puzzle.size,
        config=config.name,
        trial=trial,
        status=status_str,
        primary_vars=primary_vars,
        aux_vars=aux_vars,
        total_vars=total_vars,
        initial_clauses=initial_clauses,
        clauses=len(final_kb),
        sat_calls=sat_calls,
        decisions=int(agg["decisions"]),
        propagations=int(agg["propagations"]),
        backtracks=int(agg["backtracks"]),
        steps=int(result.accepted_steps),
        trace_steps=len(result.trace.steps),
        runtime_ms=runtime_ms,
        sat_runtime_ms=float(agg["sat_runtime_ms"]),
        error=result.error or "",
    )

    step_rows: list[StepMetrics] = []
    for trace_step in result.trace.steps:
        step_stats = _extract_query_stats(trace_step.sat_queries)
        step_rows.append(
            StepMetrics(
                puzzle=puzzle_label,
                puzzle_id=puzzle_id,
                size=puzzle.size,
                config=config.name,
                trial=trial,
                step=trace_step.step,
                cell=trace_step.cell or "",
                verdict=trace_step.verdict or "",
                result=trace_step.result,
                forced_count=trace_step.forced_count,
                kb_clauses=trace_step.kb_clauses,
                sat_calls=trace_step.sat_calls,
                decisions=int(step_stats["decisions"]),
                propagations=int(step_stats["propagations"]),
                backtracks=int(step_stats["backtracks"]),
                sat_runtime_ms=float(step_stats["sat_runtime_ms"]),
                new_clue_id=trace_step.new_clue_id or "",
            )
        )

    return puzzle_metrics, step_rows


def write_metrics_csv(rows: Sequence[PuzzleMetrics], output_path: str | Path) -> Path:
    """Write puzzle-level experiment metrics to a UTF-8 CSV file."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())
    return out


def write_step_metrics_csv(rows: Sequence[StepMetrics], output_path: str | Path) -> Path:
    """Write step-level deduction trace metrics to a UTF-8 CSV file."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STEP_CSV_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())
    return out


def summarize_metrics(rows: Sequence[PuzzleMetrics]) -> list[dict[str, Any]]:
    """Aggregate metrics grouped by `(config, size)` for reporting."""
    groups: dict[tuple[str, int], list[PuzzleMetrics]] = {}
    for row in rows:
        groups.setdefault((row.config, row.size), []).append(row)

    summary: list[dict[str, Any]] = []
    for (config_name, size), group in sorted(groups.items()):
        n = len(group)
        solved = sum(1 for r in group if r.status == RunStatus.SOLVED.value)
        summary.append(
            {
                "config": config_name,
                "size": f"{size}x{size}",
                "runs": n,
                "solved": f"{solved}/{n}",
                "avg_vars": round(sum(r.total_vars for r in group) / n, 1),
                "avg_clauses": round(sum(r.clauses for r in group) / n, 1),
                "avg_sat_calls": round(sum(r.sat_calls for r in group) / n, 1),
                "avg_decisions": round(sum(r.decisions for r in group) / n, 1),
                "avg_propagations": round(sum(r.propagations for r in group) / n, 1),
                "avg_backtracks": round(sum(r.backtracks for r in group) / n, 1),
                "avg_steps": round(sum(r.steps for r in group) / n, 1),
                "avg_runtime_ms": round(sum(r.runtime_ms for r in group) / n, 2),
                "max_runtime_ms": round(max(r.runtime_ms for r in group), 2),
            }
        )
    return summary