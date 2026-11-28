"""Batch-run all Griductive puzzles with DPLL and export metrics to CSV.

Owner: B

Usage:
    python -m experiments.run_experiments
    python -m experiments.run_experiments --ablation --output results/raw/ablation.csv
    python -m experiments.run_experiments --sizes 3 4 --timeout 30 --steps-csv results/raw/steps.csv
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.metrics import (  # noqa: E402
    ABLATION_CONFIGS,
    CONFIG_REGISTRY,
    DEFAULT_CONFIG,
    ExperimentConfig,
    PuzzleMetrics,
    StepMetrics,
    run_single_puzzle,
    summarize_metrics,
    write_metrics_csv,
    write_step_metrics_csv,
)


DEFAULT_PUZZLES_DIR = REPO_ROOT / "puzzles"
DEFAULT_OUTPUT_CSV = REPO_ROOT / "results" / "raw" / "dpll_experiments.csv"


def discover_puzzles(
    puzzles_dir: str | Path,
    sizes: Sequence[int] | None = None,
) -> list[Path]:
    """Find all puzzle JSON files under `puzzles_dir`, sorted by board size and name."""
    root = Path(puzzles_dir)
    if not root.exists():
        raise FileNotFoundError(f"Puzzles directory not found: {root}")

    size_filter = {f"{s}x{s}" for s in sizes} if sizes else None
    found: list[Path] = []
    for path in sorted(root.rglob("*.json")):
        if not path.is_file():
            continue
        if size_filter is not None and path.parent.name not in size_filter:
            continue
        found.append(path)

    return sorted(found, key=lambda p: (p.parent.name, p.name))


def resolve_configs(
    config_names: Sequence[str] | None,
    ablation: bool,
    solver_timeout_s: float | None,
) -> list[ExperimentConfig]:
    """Resolve CLI config flags into a list of ExperimentConfig instances."""
    if ablation:
        base_configs: list[ExperimentConfig] = list(ABLATION_CONFIGS)
    elif config_names:
        base_configs = []
        for name in config_names:
            if name not in CONFIG_REGISTRY:
                valid = ", ".join(sorted(CONFIG_REGISTRY))
                raise ValueError(f"Unknown config {name!r}. Valid configs: {valid}")
            base_configs.append(CONFIG_REGISTRY[name])
    else:
        base_configs = [DEFAULT_CONFIG]

    if solver_timeout_s is None:
        return base_configs

    return [
        ExperimentConfig(
            name=cfg.name,
            use_pure_literal=cfg.use_pure_literal,
            use_heuristic=cfg.use_heuristic,
            use_witnesses=cfg.use_witnesses,
            solver_timeout_s=solver_timeout_s,
        )
        for cfg in base_configs
    ]


def run_batch(
    puzzle_paths: Sequence[Path],
    configs: Sequence[ExperimentConfig] = (DEFAULT_CONFIG,),
    timeout_s: float | None = None,
    repeats: int = 1,
    repo_root: Path = REPO_ROOT,
) -> tuple[list[PuzzleMetrics], list[StepMetrics]]:
    """Execute all `(config, puzzle, trial)` combinations and collect metrics."""
    if repeats < 1:
        raise ValueError(f"repeats must be >= 1, got {repeats}")

    puzzle_rows: list[PuzzleMetrics] = []
    step_rows: list[StepMetrics] = []

    for config in configs:
        for puzzle_path in puzzle_paths:
            for trial in range(1, repeats + 1):
                metrics, steps = run_single_puzzle(
                    puzzle_path=puzzle_path,
                    config=config,
                    timeout_s=timeout_s,
                    trial=trial,
                    repo_root=repo_root,
                )
                puzzle_rows.append(metrics)
                step_rows.extend(steps)

    return puzzle_rows, step_rows


def _format_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """Render an aligned plain-text table without external dependencies."""
    str_rows = [[str(cell) for cell in row] for row in rows]
    widths = [
        max(len(headers[i]), *(len(r[i]) for r in str_rows)) if str_rows else len(headers[i])
        for i in range(len(headers))
    ]
    header_line = " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers)))
    sep_line = "-+-".join("-" * widths[i] for i in range(len(headers)))
    body_lines = [
        " | ".join(r[i].ljust(widths[i]) for i in range(len(headers)))
        for r in str_rows
    ]
    return "\n".join([header_line, sep_line, *body_lines])


def format_results_table(rows: Sequence[PuzzleMetrics]) -> str:
    """Format per-puzzle experiment results for terminal display."""
    headers = [
        "Puzzle",
        "Cfg",
        "Size",
        "Status",
        "Vars(P/A)",
        "Clauses",
        "SAT",
        "Dec",
        "Prop",
        "BT",
        "Steps",
        "Time(ms)",
    ]
    table_rows = [
        [
            r.puzzle_id,
            r.config,
            f"{r.size}x{r.size}",
            r.status,
            f"{r.primary_vars}/{r.aux_vars}",
            r.clauses,
            r.sat_calls,
            r.decisions,
            r.propagations,
            r.backtracks,
            r.steps,
            f"{r.runtime_ms:.2f}",
        ]
        for r in rows
    ]
    return _format_table(headers, table_rows)


def format_summary_table(rows: Sequence[PuzzleMetrics]) -> str:
    """Format aggregated summary metrics grouped by config and board size."""
    summary = summarize_metrics(rows)
    headers = [
        "Config",
        "Size",
        "Solved",
        "AvgVars",
        "AvgClauses",
        "AvgSAT",
        "AvgDec",
        "AvgProp",
        "AvgBT",
        "AvgSteps",
        "AvgTime(ms)",
        "MaxTime(ms)",
    ]
    table_rows = [
        [
            s["config"],
            s["size"],
            s["solved"],
            s["avg_vars"],
            s["avg_clauses"],
            s["avg_sat_calls"],
            s["avg_decisions"],
            s["avg_propagations"],
            s["avg_backtracks"],
            s["avg_steps"],
            f"{s['avg_runtime_ms']:.2f}",
            f"{s['max_runtime_ms']:.2f}",
        ]
        for s in summary
    ]
    return _format_table(headers, table_rows)


def build_arg_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for batch experiments."""
    parser = argparse.ArgumentParser(
        description="Batch-run Griductive puzzles with DPLL and export metrics to CSV.",
    )
    parser.add_argument(
        "--puzzles-dir",
        type=Path,
        default=DEFAULT_PUZZLES_DIR,
        help="Root directory containing puzzle JSON files (default: puzzles/).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Destination CSV path (default: results/raw/dpll_experiments.csv).",
    )
    parser.add_argument(
        "--timestamped",
        action="store_true",
        help="Write to results/raw/YYYYMMDD_dpll_experiments.csv when --output is omitted.",
    )
    parser.add_argument(
        "--steps-csv",
        type=Path,
        default=None,
        help="Optional CSV path to also export step-by-step trace metrics.",
    )
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        choices=(3, 4, 5),
        default=None,
        help="Filter puzzles by board size (e.g. --sizes 3 4).",
    )
    parser.add_argument(
        "--configs",
        nargs="+",
        choices=sorted(CONFIG_REGISTRY.keys()),
        default=None,
        help="Specific solver configurations to run (default: dpll_full).",
    )
    parser.add_argument(
        "--ablation",
        action="store_true",
        help="Run all predefined DPLL ablation configurations.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Per-puzzle agent timeout in seconds.",
    )
    parser.add_argument(
        "--solver-timeout",
        type=float,
        default=None,
        help="Per-SAT-call DPLL solver timeout in seconds.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Number of repeated trials per puzzle and configuration (default: 1).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress terminal result tables.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for batch DPLL experiments."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    puzzle_paths = discover_puzzles(args.puzzles_dir, sizes=args.sizes)
    if not puzzle_paths:
        print(f"No puzzle JSON files found in {args.puzzles_dir}", file=sys.stderr)
        return 1

    configs = resolve_configs(
        config_names=args.configs,
        ablation=args.ablation,
        solver_timeout_s=args.solver_timeout,
    )

    if args.output is not None:
        output_csv = args.output
    elif args.timestamped:
        stamp = datetime.now().strftime("%Y%m%d")
        output_csv = REPO_ROOT / "results" / "raw" / f"{stamp}_dpll_experiments.csv"
    else:
        output_csv = DEFAULT_OUTPUT_CSV

    puzzle_rows, step_rows = run_batch(
        puzzle_paths=puzzle_paths,
        configs=configs,
        timeout_s=args.timeout,
        repeats=args.repeats,
        repo_root=REPO_ROOT,
    )

    written_path = write_metrics_csv(puzzle_rows, output_csv)
    written_steps = (
        write_step_metrics_csv(step_rows, args.steps_csv)
        if args.steps_csv is not None
        else None
    )

    if not args.quiet:
        print(format_results_table(puzzle_rows))
        print()
        print("Summary by config and size:")
        print(format_summary_table(puzzle_rows))
        print()
        print(f"Saved {len(puzzle_rows)} rows to: {written_path}")
        if written_steps is not None:
            print(f"Saved {len(step_rows)} step rows to: {written_steps}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())