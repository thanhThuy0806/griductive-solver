"""Tạo bảng tổng hợp, biểu đồ tiếng Việt, nhận xét, failure cases và limitations từ CSV thực nghiệm.

Owner: B

Toàn bộ kết quả chạy — bao gồm cả TIMEOUT, ERROR, STUCK và INCONSISTENT — đều được
giữ nguyên trong mọi bảng, biểu đồ và báo cáo (không xóa bất kỳ ca lỗi/timeout nào).

Usage:
    python -m experiments.plot_results
    python -m experiments.plot_results --input results/raw/dpll_ablation.csv
    python -m experiments.plot_results --input results/raw/dpll_experiments.csv --steps-csv results/raw/dpll_steps.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_INPUT_CSV = REPO_ROOT / "results" / "raw" / "dpll_experiments.csv"
DEFAULT_RAW_DIR = REPO_ROOT / "results" / "raw"
DEFAULT_FIGURES_DIR = REPO_ROOT / "results" / "figures"

STATUS_ORDER = ("SOLVED", "TIMEOUT", "STUCK", "INCONSISTENT", "ERROR")
STATUS_LABELS_VI = {
    "SOLVED": "SOLVED (Giải được)",
    "TIMEOUT": "TIMEOUT (Quá thời gian)",
    "STUCK": "STUCK (Bế tắc)",
    "INCONSISTENT": "INCONSISTENT (Mâu thuẫn)",
    "ERROR": "ERROR (Lỗi)",
}
STATUS_COLORS = {
    "SOLVED": "#2563EB",
    "TIMEOUT": "#EA580C",
    "STUCK": "#D97706",
    "INCONSISTENT": "#7C3AED",
    "ERROR": "#DC2626",
}
STATUS_HATCHES = {
    "SOLVED": "",
    "TIMEOUT": "//",
    "STUCK": "..",
    "INCONSISTENT": "xx",
    "ERROR": "\\\\",
}

REQUIRED_COLUMNS = {
    "puzzle",
    "size",
    "status",
    "primary_vars",
    "aux_vars",
    "clauses",
    "sat_calls",
    "decisions",
    "propagations",
    "backtracks",
    "steps",
    "runtime_ms",
}

NUMERIC_COLUMNS = (
    "size",
    "trial",
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
)


def _apply_plot_style() -> None:
    """Apply clean matplotlib defaults with full Vietnamese UTF-8 glyph support."""
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "white",
            "axes.facecolor": "#F8FAFC",
            "axes.edgecolor": "#CBD5E1",
            "axes.linewidth": 0.8,
            "axes.grid": True,
            "grid.color": "#E2E8F0",
            "grid.linestyle": "--",
            "grid.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 10,
            "axes.titlesize": 11.5,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.frameon": True,
            "legend.facecolor": "white",
            "legend.edgecolor": "#CBD5E1",
        }
    )


def resolve_input_csvs(input_paths: Sequence[Path] | None) -> list[Path]:
    """Resolve CLI input CSV paths or fall back to default/latest raw experiment CSV."""
    if input_paths:
        missing = [p for p in input_paths if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"Input CSV file(s) not found: {', '.join(str(p) for p in missing)}"
            )
        return list(input_paths)

    if DEFAULT_INPUT_CSV.exists():
        return [DEFAULT_INPUT_CSV]

    candidates = sorted(DEFAULT_RAW_DIR.glob("*dpll_experiments*.csv"))
    if candidates:
        return [candidates[-1]]

    raise FileNotFoundError(
        f"No experiment CSV found at {DEFAULT_INPUT_CSV}. "
        "Run `python -m experiments.run_experiments` first or pass `--input <csv>`."
    )


def _normalize_text_column(series: pd.Series, default: str) -> pd.Series:
    """Safely cast any column (including all-NaN float64) to str without Pandas4Warning."""
    return series.astype("string").fillna(default).astype(str)


def load_experiment_csvs(paths: Sequence[Path]) -> pd.DataFrame:
    """Load and normalize one or more experiment CSV files without dropping any rows."""
    frames = [pd.read_csv(p, encoding="utf-8") for p in paths]
    df = pd.concat(frames, ignore_index=True)

    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"CSV missing required columns: {', '.join(sorted(missing_cols))}"
        )

    # Preserve every row (including TIMEOUT/ERROR); fill optional metadata safely.
    if "puzzle_id" not in df.columns:
        df["puzzle_id"] = _normalize_text_column(df["puzzle"], "").map(
            lambda s: Path(s).stem
        )
    else:
        df["puzzle_id"] = _normalize_text_column(df["puzzle_id"], "")

    if "config" not in df.columns:
        df["config"] = "dpll_full"
    if "trial" not in df.columns:
        df["trial"] = 1
    if "total_vars" not in df.columns:
        df["total_vars"] = df["primary_vars"].fillna(0) + df["aux_vars"].fillna(0)
    if "initial_clauses" not in df.columns:
        df["initial_clauses"] = np.nan
    if "trace_steps" not in df.columns:
        df["trace_steps"] = df["steps"]
    if "sat_runtime_ms" not in df.columns:
        df["sat_runtime_ms"] = np.nan
    if "error" not in df.columns:
        df["error"] = ""

    df["puzzle"] = _normalize_text_column(df["puzzle"], "")
    df["status"] = _normalize_text_column(df["status"], "ERROR").str.upper()
    df["error"] = _normalize_text_column(df["error"], "")
    df["config"] = _normalize_text_column(df["config"], "dpll_full")

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    int_cols = (
        "size",
        "trial",
        "primary_vars",
        "aux_vars",
        "total_vars",
        "clauses",
        "sat_calls",
        "decisions",
        "propagations",
        "backtracks",
        "steps",
        "trace_steps",
    )
    for col in int_cols:
        df[col] = df[col].astype(int)

    df = df.sort_values(
        by=["config", "size", "puzzle_id", "trial"],
        kind="mergesort",
    ).reset_index(drop=True)
    return df


def build_summary_by_size(df: pd.DataFrame) -> pd.DataFrame:
    """Build grouped summary table by `(config, size)` retaining all statuses."""
    rows: list[dict[str, object]] = []
    for (config, size), grp in df.groupby(["config", "size"], sort=True):
        total = len(grp)
        solved = int((grp["status"] == "SOLVED").sum())
        timeout = int((grp["status"] == "TIMEOUT").sum())
        stuck = int((grp["status"] == "STUCK").sum())
        inconsistent = int((grp["status"] == "INCONSISTENT").sum())
        error = int((grp["status"] == "ERROR").sum())
        other = total - (solved + timeout + stuck + inconsistent + error)

        rows.append(
            {
                "config": config,
                "size": int(size),
                "grid": f"{int(size)}x{int(size)}",
                "total_runs": total,
                "solved": solved,
                "timeout": timeout,
                "stuck": stuck,
                "inconsistent": inconsistent,
                "error": error + other,
                "solve_rate_pct": round(100.0 * solved / total, 1) if total else 0.0,
                "avg_primary_vars": round(float(grp["primary_vars"].mean()), 1),
                "avg_aux_vars": round(float(grp["aux_vars"].mean()), 1),
                "avg_clauses": round(float(grp["clauses"].mean()), 1),
                "avg_sat_calls": round(float(grp["sat_calls"].mean()), 1),
                "avg_decisions": round(float(grp["decisions"].mean()), 1),
                "avg_propagations": round(float(grp["propagations"].mean()), 1),
                "avg_backtracks": round(float(grp["backtracks"].mean()), 1),
                "avg_steps": round(float(grp["steps"].mean()), 1),
                "avg_runtime_ms": round(float(grp["runtime_ms"].mean()), 2),
                "max_runtime_ms": round(float(grp["runtime_ms"].max()), 2),
                "avg_sat_runtime_ms": round(float(grp["sat_runtime_ms"].mean()), 2),
            }
        )
    return pd.DataFrame(rows)


def extract_failure_cases(df: pd.DataFrame) -> pd.DataFrame:
    """Return all non-SOLVED rows (TIMEOUT, STUCK, INCONSISTENT, ERROR) intact."""
    cols = [
        "puzzle",
        "puzzle_id",
        "size",
        "config",
        "trial",
        "status",
        "primary_vars",
        "aux_vars",
        "clauses",
        "sat_calls",
        "decisions",
        "propagations",
        "backtracks",
        "steps",
        "runtime_ms",
        "error",
    ]
    return df.loc[df["status"] != "SOLVED", cols].reset_index(drop=True)


def _select_primary_config(df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """Select the default/primary config slice for single-config per-puzzle charts."""
    configs = list(df["config"].unique())
    primary = "dpll_full" if "dpll_full" in configs else configs[0]
    sub = df[df["config"] == primary].copy()
    if sub["trial"].nunique() > 1:
        status_priority = {s: i for i, s in enumerate(STATUS_ORDER)}
        agg_rows = []
        for (size, puzzle_id, puzzle), grp in sub.groupby(
            ["size", "puzzle_id", "puzzle"], sort=True
        ):
            worst_status = max(
                grp["status"].tolist(),
                key=lambda s: status_priority.get(s, len(STATUS_ORDER)),
            )
            agg_rows.append(
                {
                    "puzzle": puzzle,
                    "puzzle_id": puzzle_id,
                    "size": size,
                    "config": primary,
                    "status": worst_status,
                    "primary_vars": int(round(grp["primary_vars"].mean())),
                    "aux_vars": int(round(grp["aux_vars"].mean())),
                    "total_vars": int(round(grp["total_vars"].mean())),
                    "clauses": int(round(grp["clauses"].mean())),
                    "sat_calls": float(grp["sat_calls"].mean()),
                    "decisions": float(grp["decisions"].mean()),
                    "propagations": float(grp["propagations"].mean()),
                    "backtracks": float(grp["backtracks"].mean()),
                    "steps": float(grp["steps"].mean()),
                    "runtime_ms": float(grp["runtime_ms"].mean()),
                    "sat_runtime_ms": float(grp["sat_runtime_ms"].mean()),
                    "error": "; ".join(e for e in grp["error"].unique() if e),
                }
            )
        sub = pd.DataFrame(agg_rows)
    return primary, sub.sort_values(["size", "puzzle_id"]).reset_index(drop=True)


def _status_legend_handles(statuses: Sequence[str]) -> list[mpatches.Patch]:
    """Create Vietnamese legend patches for all statuses present in a plot."""
    seen = [s for s in STATUS_ORDER if s in statuses]
    extras = [s for s in statuses if s not in STATUS_ORDER]
    handles = []
    for st in (*seen, *extras):
        handles.append(
            mpatches.Patch(
                facecolor=STATUS_COLORS.get(st, "#64748B"),
                edgecolor="#1E293B",
                hatch=STATUS_HATCHES.get(st, ""),
                label=STATUS_LABELS_VI.get(st, st),
            )
        )
    return handles


def plot_runtime_by_puzzle(df: pd.DataFrame, out_dir: Path, dpi: int) -> Path:
    """Plot runtime per puzzle in Vietnamese, preserving and annotating failure/timeout cases."""
    primary_cfg, sub = _select_primary_config(df)
    n = len(sub)
    fig_h = max(4.2, 0.48 * n + 1.8)
    fig, ax = plt.subplots(figsize=(10.8, fig_h))

    y = np.arange(n)
    labels = [f"{r.puzzle_id} ({r.size}x{r.size})" for r in sub.itertuples()]
    runtimes = sub["runtime_ms"].to_numpy(dtype=float)
    statuses = sub["status"].tolist()

    bars = ax.barh(
        y,
        runtimes,
        height=0.65,
        color=[STATUS_COLORS.get(s, "#64748B") for s in statuses],
        edgecolor="#1E293B",
        linewidth=0.7,
    )
    for bar, st in zip(bars, statuses):
        hatch = STATUS_HATCHES.get(st, "")
        if hatch:
            bar.set_hatch(hatch)

    max_rt = float(np.max(runtimes)) if len(runtimes) else 1.0
    pad = max(max_rt * 0.015, 0.2)
    for idx, (rt, st) in enumerate(zip(runtimes, statuses)):
        tag = f"  [{st}]" if st != "SOLVED" else ""
        ax.text(
            rt + pad,
            idx,
            f"{rt:.2f} ms{tag}",
            va="center",
            ha="left",
            fontsize=8.5,
            fontweight="bold" if st != "SOLVED" else "normal",
            color="#991B1B" if st in ("TIMEOUT", "ERROR") else "#0F172A",
        )

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Thời gian chạy (ms)")
    ax.set_xlim(0, max_rt * 1.38 + 1.0)
    ax.set_title(
        f"Thời gian chạy theo từng màn chơi ({primary_cfg} — Giữ toàn bộ các trường hợp)",
        pad=14,
    )
    ax.legend(
        handles=_status_legend_handles(statuses),
        title="Trạng thái",
        loc="upper right",
        fontsize=8.5,
    )
    fig.tight_layout()

    out_path = out_dir / "01_runtime_by_puzzle.png"
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return out_path


def plot_scaling_by_size(summary_df: pd.DataFrame, df: pd.DataFrame, out_dir: Path, dpi: int) -> Path:
    """Plot 2x2 scaling overview across board sizes (3x3, 4x4, 5x5) in Vietnamese."""
    primary_cfg, _ = _select_primary_config(df)
    sub = summary_df[summary_df["config"] == primary_cfg].sort_values("size")

    fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.6))
    grids = sub["grid"].tolist()
    x = np.arange(len(grids))
    width = 0.34

    # Panel A: Variables (Primary + Aux) & Clauses
    ax = axes[0, 0]
    p_vars = sub["avg_primary_vars"].to_numpy()
    a_vars = sub["avg_aux_vars"].to_numpy()
    clauses = sub["avg_clauses"].to_numpy()
    ax.bar(x - width / 2, p_vars, width, label="Biến chính", color="#2563EB", edgecolor="#1E293B", linewidth=0.6)
    ax.bar(x - width / 2, a_vars, width, bottom=p_vars, label="Biến phụ", color="#38BDF8", edgecolor="#1E293B", linewidth=0.6)
    ax.bar(x + width / 2, clauses, width, label="Mệnh đề cuối (Clauses)", color="#0F766E", edgecolor="#1E293B", linewidth=0.6)
    for i in range(len(x)):
        ax.text(x[i] - width / 2, p_vars[i] + a_vars[i], f"{p_vars[i] + a_vars[i]:.0f}", ha="center", va="bottom", fontsize=8.5)
        ax.text(x[i] + width / 2, clauses[i], f"{clauses[i]:.0f}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(grids)
    ax.set_ylabel("Số lượng trung bình")
    ax.set_ylim(0, max(float(np.max(clauses)), float(np.max(p_vars + a_vars)), 1.0) * 1.18)
    ax.set_title("A. Kích thước công thức: Số biến & Số mệnh đề")
    ax.legend(fontsize=8.5)

    # Panel B: SAT Calls & Deduction Steps
    ax = axes[0, 1]
    sat_calls = sub["avg_sat_calls"].to_numpy()
    steps = sub["avg_steps"].to_numpy()
    ax.bar(x - width / 2, sat_calls, width, label="Số lần gọi SAT TB", color="#4F46E5", edgecolor="#1E293B", linewidth=0.6)
    ax.bar(x + width / 2, steps, width, label="Số bước giải TB", color="#10B981", edgecolor="#1E293B", linewidth=0.6)
    for i in range(len(x)):
        ax.text(x[i] - width / 2, sat_calls[i], f"{sat_calls[i]:.1f}", ha="center", va="bottom", fontsize=8.5)
        ax.text(x[i] + width / 2, steps[i], f"{steps[i]:.1f}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(grids)
    ax.set_ylabel("Số lượng trung bình")
    ax.set_ylim(0, max(float(np.max(sat_calls)), float(np.max(steps)), 1.0) * 1.18)
    ax.set_title("B. Vòng lặp suy luận: SAT calls và Số bước")
    ax.legend(fontsize=8.5)

    # Panel C: DPLL Search Effort (Decisions, Propagations, Backtracks)
    ax = axes[1, 0]
    w3 = 0.25
    dec = sub["avg_decisions"].to_numpy()
    prop = sub["avg_propagations"].to_numpy()
    bt = sub["avg_backtracks"].to_numpy()
    ax.bar(x - w3, dec, w3, label="Decisions (Chọn nhánh)", color="#F59E0B", edgecolor="#1E293B", linewidth=0.6)
    ax.bar(x, prop, w3, label="Propagations (Lan truyền)", color="#0EA5E9", edgecolor="#1E293B", linewidth=0.6)
    ax.bar(x + w3, bt, w3, label="Backtracks (Quay lui)", color="#EF4444", edgecolor="#1E293B", linewidth=0.6)
    for i in range(len(x)):
        ax.text(x[i] - w3, dec[i], f"{dec[i]:.0f}", ha="center", va="bottom", fontsize=8)
        ax.text(x[i], prop[i], f"{prop[i]:.0f}", ha="center", va="bottom", fontsize=8)
        ax.text(x[i] + w3, bt[i], f"{bt[i]:.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(grids)
    ax.set_ylabel("Số lượng trung bình")
    ax.set_ylim(0, max(float(np.max(dec)), float(np.max(prop)), float(np.max(bt)), 1.0) * 1.18)
    ax.set_title("C. Chỉ số tìm kiếm của DPLL")
    ax.legend(fontsize=8.5)

    # Panel D: Runtime (Mean & Max) + Solve Rate Annotation
    ax = axes[1, 1]
    avg_rt = sub["avg_runtime_ms"].to_numpy()
    max_rt = sub["max_runtime_ms"].to_numpy()
    ax.bar(x - width / 2, avg_rt, width, label="Thời gian TB (ms)", color="#2563EB", edgecolor="#1E293B", linewidth=0.6)
    ax.bar(x + width / 2, max_rt, width, label="Thời gian tối đa (ms)", color="#EA580C", edgecolor="#1E293B", linewidth=0.6)
    for i, row in enumerate(sub.itertuples()):
        ax.text(x[i] - width / 2, avg_rt[i], f"{avg_rt[i]:.1f}", ha="center", va="bottom", fontsize=8)
        ax.text(
            x[i] + width / 2,
            max_rt[i],
            f"{max_rt[i]:.1f}\n({row.solved}/{row.total_runs} đạt)",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(grids)
    ax.set_ylabel("Thời gian chạy (ms)")
    ax.set_ylim(0, max(float(np.max(max_rt)) * 1.25, 1.0))
    ax.set_title("D. Thời gian chạy & Tỉ lệ giải (Giữ cả lỗi/timeout)")
    ax.legend(fontsize=8.5)

    fig.suptitle(
        f"Khả năng mở rộng của DPLL theo kích thước lưới ({primary_cfg})",
        fontsize=13.5,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    out_path = out_dir / "02_scaling_by_size.png"
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return out_path


def plot_search_effort_per_puzzle(df: pd.DataFrame, out_dir: Path, dpi: int) -> Path:
    """Plot per-puzzle decisions, propagations, and backtracks in Vietnamese."""
    primary_cfg, sub = _select_primary_config(df)
    n = len(sub)
    fig, ax = plt.subplots(figsize=(max(10.8, 0.95 * n + 2.5), 5.3))

    x = np.arange(n)
    w = 0.26
    labels = [
        f"{r.puzzle_id}\n({r.size}x{r.size})" + (f"\n[{r.status}]" if r.status != "SOLVED" else "")
        for r in sub.itertuples()
    ]

    ax.bar(x - w, sub["decisions"], w, label="Decisions (Chọn nhánh)", color="#F59E0B", edgecolor="#1E293B", linewidth=0.6)
    ax.bar(x, sub["propagations"], w, label="Propagations (Lan truyền đơn vị)", color="#0EA5E9", edgecolor="#1E293B", linewidth=0.6)
    ax.bar(x + w, sub["backtracks"], w, label="Backtracks (Quay lui)", color="#EF4444", edgecolor="#1E293B", linewidth=0.6)

    for idx, st in enumerate(sub["status"].tolist()):
        if st != "SOLVED":
            ax.axvspan(idx - 0.45, idx + 0.45, color="#FEE2E2", alpha=0.45, zorder=0)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Số lượng")
    ax.set_title(
        f"Nỗ lực tìm kiếm DPLL theo từng màn chơi ({primary_cfg} — Tô nền đỏ cho ca lỗi/timeout)"
    )
    ax.legend(loc="upper left")
    fig.tight_layout()

    out_path = out_dir / "03_search_effort_per_puzzle.png"
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return out_path


def plot_ablation_comparison(df: pd.DataFrame, out_dir: Path, dpi: int) -> Path | None:
    """Plot ablation comparison across solver configurations in Vietnamese when >1 config exists."""
    configs = list(df["config"].unique())
    if len(configs) <= 1:
        return None

    agg = (
        df.groupby("config", sort=False)
        .agg(
            total_runs=("status", "size"),
            solved=("status", lambda s: int((s == "SOLVED").sum())),
            avg_runtime_ms=("runtime_ms", "mean"),
            avg_sat_calls=("sat_calls", "mean"),
            avg_decisions=("decisions", "mean"),
            avg_backtracks=("backtracks", "mean"),
        )
        .reset_index()
    )

    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.8))
    x = np.arange(len(agg))
    cfg_labels = agg["config"].tolist()
    palette = ["#2563EB", "#0EA5E9", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]
    colors = [palette[i % len(palette)] for i in range(len(agg))]

    # Panel 1: Mean Runtime
    ax = axes[0]
    vals = agg["avg_runtime_ms"].to_numpy()
    ax.bar(x, vals, color=colors, edgecolor="#1E293B", linewidth=0.7)
    for i, (v, row) in enumerate(zip(vals, agg.itertuples())):
        ax.text(i, v, f"{v:.1f} ms\n({row.solved}/{row.total_runs} đạt)", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(cfg_labels, rotation=20, ha="right", fontsize=8.5)
    ax.set_ylabel("Thời gian chạy TB (ms)")
    ax.set_ylim(0, max(float(np.max(vals)) * 1.25, 1.0))
    ax.set_title("Thời gian chạy TB & Số ca giải được")

    # Panel 2: Mean SAT Calls
    ax = axes[1]
    vals = agg["avg_sat_calls"].to_numpy()
    ax.bar(x, vals, color=colors, edgecolor="#1E293B", linewidth=0.7)
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(x)
    ax.set_xticklabels(cfg_labels, rotation=20, ha="right", fontsize=8.5)
    ax.set_ylabel("Số SAT calls TB")
    ax.set_ylim(0, max(float(np.max(vals)) * 1.18, 1.0))
    ax.set_title("Số SAT calls trung bình mỗi màn")

    # Panel 3: Decisions vs. Backtracks
    ax = axes[2]
    w = 0.36
    dec = agg["avg_decisions"].to_numpy()
    bt = agg["avg_backtracks"].to_numpy()
    ax.bar(x - w / 2, dec, w, label="Decisions", color="#F59E0B", edgecolor="#1E293B", linewidth=0.6)
    ax.bar(x + w / 2, bt, w, label="Backtracks", color="#EF4444", edgecolor="#1E293B", linewidth=0.6)
    for i in range(len(x)):
        ax.text(x[i] - w / 2, dec[i], f"{dec[i]:.0f}", ha="center", va="bottom", fontsize=8)
        ax.text(x[i] + w / 2, bt[i], f"{bt[i]:.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(cfg_labels, rotation=20, ha="right", fontsize=8.5)
    ax.set_ylabel("Số lượng trung bình")
    ax.set_ylim(0, max(float(np.max(dec)), float(np.max(bt)), 1.0) * 1.2)
    ax.set_title("Nỗ lực tìm kiếm: Decisions và Backtracks")
    ax.legend(fontsize=8.5)

    fig.suptitle(
        "So sánh Ablation giữa các cấu hình DPLL (Giữ toàn bộ các trường hợp)",
        fontsize=13,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    out_path = out_dir / "04_ablation_comparison.png"
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return out_path


def plot_step_trajectory(steps_csv: Path, out_dir: Path, dpi: int) -> Path:
    """Plot KB clause growth and SAT calls per deduction step in Vietnamese."""
    sdf = pd.read_csv(steps_csv, encoding="utf-8")
    if sdf.empty:
        raise ValueError(f"Steps CSV is empty: {steps_csv}")

    configs = list(sdf["config"].unique()) if "config" in sdf.columns else ["dpll_full"]
    primary_cfg = "dpll_full" if "dpll_full" in configs else configs[0]
    if "config" in sdf.columns:
        sdf = sdf[sdf["config"] == primary_cfg]
    if "trial" in sdf.columns:
        sdf = sdf[sdf["trial"] == sdf["trial"].min()]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 4.9))
    for (size, pid), grp in sdf.groupby(["size", "puzzle_id"], sort=True):
        grp = grp.sort_values("step")
        label = f"{pid} ({size}x{size})"
        ax1.plot(grp["step"], grp["kb_clauses"], marker="o", markersize=3.5, linewidth=1.6, label=label)
        ax2.plot(grp["step"], grp["sat_calls"], marker="s", markersize=3.5, linewidth=1.6, label=label)

    ax1.set_xlabel("Bước suy luận")
    ax1.set_ylabel("Số mệnh đề KB (Clauses)")
    ax1.set_title("Tăng trưởng cơ sở tri thức (KB) theo bước")
    ax2.set_xlabel("Bước suy luận")
    ax2.set_ylabel("Số SAT calls trong bước")
    ax2.set_title("Số SAT calls theo từng bước suy luận")

    handles, labels = ax1.get_legend_handles_labels()
    if len(labels) <= 12:
        ax2.legend(handles, labels, fontsize=8, loc="upper right", ncol=1)

    fig.suptitle(
        f"Diễn biến suy luận theo từng bước ({primary_cfg})",
        fontsize=13,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    out_path = out_dir / "05_step_trajectory.png"
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return out_path


def _df_to_markdown(df: pd.DataFrame) -> str:
    """Render a DataFrame as a standard Markdown pipe table without external dependencies."""
    if df.empty:
        return "_Không có dữ liệu._"
    headers = [str(c) for c in df.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in df.itertuples(index=False):
        cells = [str(v).replace("|", "\\|") for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def generate_markdown_report(
    df: pd.DataFrame,
    summary_df: pd.DataFrame,
    failures_df: pd.DataFrame,
    generated_charts: Sequence[Path],
    source_csvs: Sequence[Path],
    report_path: Path,
) -> Path:
    """Write a complete Vietnamese Markdown report with tables, observations, failures, and limitations."""
    total_runs = len(df)
    solved_runs = int((df["status"] == "SOLVED").sum())
    failure_runs = len(failures_df)
    status_counts = df["status"].value_counts().to_dict()

    primary_cfg, primary_df = _select_primary_config(df)
    primary_summary = summary_df[summary_df["config"] == primary_cfg].sort_values("size")

    observations: list[str] = []
    status_str = ", ".join(f"{k}: {v}" for k, v in status_counts.items())
    observations.append(
        f"**Tỉ lệ hoàn thành tổng thể (giữ toàn bộ dòng kết quả):** {solved_runs}/{total_runs} "
        f"lượt chạy giải thành công ({100.0 * solved_runs / total_runs:.1f}%). "
        f"Phân bố trạng thái: {status_str}."
    )

    if len(primary_summary) >= 2:
        smallest = primary_summary.iloc[0]
        largest = primary_summary.iloc[-1]
        rt_ratio = (
            largest["avg_runtime_ms"] / smallest["avg_runtime_ms"]
            if smallest["avg_runtime_ms"] > 0
            else float("nan")
        )
        sat_ratio = (
            largest["avg_sat_calls"] / smallest["avg_sat_calls"]
            if smallest["avg_sat_calls"] > 0
            else float("nan")
        )
        observations.append(
            f"**Độ mở rộng từ lưới {smallest['grid']} lên {largest['grid']} ({primary_cfg}):** "
            f"số mệnh đề trung bình tăng từ {smallest['avg_clauses']:.1f} lên {largest['avg_clauses']:.1f}, "
            f"số SAT calls trung bình tăng từ {smallest['avg_sat_calls']:.1f} lên {largest['avg_sat_calls']:.1f} "
            f"({sat_ratio:.2f}x), và thời gian chạy trung bình tăng từ {smallest['avg_runtime_ms']:.2f} ms "
            f"lên {largest['avg_runtime_ms']:.2f} ms ({rt_ratio:.2f}x)."
        )

    total_dec = int(primary_df["decisions"].sum())
    total_prop = int(primary_df["propagations"].sum())
    total_bt = int(primary_df["backtracks"].sum())
    if total_dec > 0:
        observations.append(
            f"**Hiệu quả lan truyền đơn vị ({primary_cfg}):** {total_prop:,} propagations so với "
            f"{total_dec:,} decisions ({total_prop / total_dec:.2f} propagations/decision) và "
            f"{total_bt:,} backtracks ({total_bt / total_dec:.2f} backtracks/decision)."
        )
    else:
        observations.append(
            f"**Hiệu quả lan truyền đơn vị ({primary_cfg}):** {total_prop:,} propagations với "
            "0 lần phân nhánh (giải hoàn toàn nhờ unit propagation / pure literal elimination)."
        )

    total_wall = float(primary_df["runtime_ms"].sum())
    total_sat_rt = float(primary_df["sat_runtime_ms"].sum())
    if total_wall > 0 and total_sat_rt > 0:
        sat_share = min(100.0, 100.0 * total_sat_rt / total_wall)
        observations.append(
            f"**Phân bổ thời gian chạy ({primary_cfg}):** các lời gọi DPLL `solve()` chiếm "
            f"{sat_share:.1f}% tổng thời gian ({total_sat_rt:.2f} ms / {total_wall:.2f} ms); "
            "phần còn lại là chi phí mã hóa manh mối (CNF encoding), dựng KB và kiểm chứng của engine."
        )

    max_aux = int(primary_df["aux_vars"].max()) if not primary_df.empty else 0
    if max_aux == 0:
        observations.append(
            "**Biến phụ (`aux_vars`):** bằng 0 trên tất cả màn chơi do bộ mã hóa CNF hiện tại "
            "mã hóa trực tiếp `EXACTLY`, `AT_MOST`, `AT_LEAST`, `PARITY` và `COMPARE` trên tập biến "
            "chính của các ô mà chưa tạo biến phụ (Tseitin / sequential counter)."
        )
    else:
        observations.append(
            f"**Biến phụ (`aux_vars`):** phát sinh tối đa {max_aux} biến phụ bên cạnh các biến chính."
        )

    if df["config"].nunique() > 1:
        cfg_means = df.groupby("config")["runtime_ms"].mean().sort_values()
        fastest_cfg = cfg_means.index[0]
        slowest_cfg = cfg_means.index[-1]
        speedup = (
            cfg_means.iloc[-1] / cfg_means.iloc[0]
            if cfg_means.iloc[0] > 0
            else float("nan")
        )
        observations.append(
            f"**Ảnh hưởng qua thử nghiệm Ablation:** cấu hình `{fastest_cfg}` đạt thời gian chạy "
            f"trung bình thấp nhất ({cfg_means.iloc[0]:.2f} ms) so với `{slowest_cfg}` "
            f"({cfg_means.iloc[-1]:.2f} ms, chậm hơn {speedup:.2f}x)."
        )

    per_puzzle_cols = [
        "puzzle_id",
        "size",
        "config",
        "status",
        "primary_vars",
        "aux_vars",
        "clauses",
        "sat_calls",
        "decisions",
        "propagations",
        "backtracks",
        "steps",
        "runtime_ms",
        "error",
    ]
    per_puzzle_md = _df_to_markdown(df[per_puzzle_cols])
    summary_md = _df_to_markdown(summary_df)

    if failure_runs > 0:
        failures_section = _df_to_markdown(
            failures_df[
                [
                    "puzzle",
                    "size",
                    "config",
                    "status",
                    "clauses",
                    "sat_calls",
                    "decisions",
                    "backtracks",
                    "steps",
                    "runtime_ms",
                    "error",
                ]
            ]
        )
    else:
        failures_section = (
            f"Không ghi nhận trường hợp lỗi hoặc quá thời gian trong bộ dữ liệu này "
            f"({solved_runs}/{total_runs} lượt chạy đều đạt trạng thái `SOLVED`). "
            "Mọi trạng thái không thành công (`TIMEOUT`, `STUCK`, `INCONSISTENT`, `ERROR`) "
            "đều được giữ nguyên tự động trong cả `failure_cases.csv` lẫn toàn bộ biểu đồ khi phát sinh."
        )

    chart_bullets = "\n".join(f"- `{p.name}`" for p in generated_charts)
    source_list = ", ".join(f"`{p.name}`" for p in source_csvs)

    report_text = f"""# Phân tích Thực nghiệm Bộ giải DPLL — Griductive

**Tệp CSV nguồn:** {source_list}  
**Tổng số lượt chạy được giữ lại:** {total_runs} (giữ nguyên toàn bộ `SOLVED`, `TIMEOUT`, `STUCK`, `INCONSISTENT`, `ERROR`)

## 1. Bảng tổng hợp theo Cấu hình và Kích thước lưới

{summary_md}

## 2. Bảng kết quả chi tiết từng màn chơi (Giữ toàn bộ các trường hợp)

{per_puzzle_md}

## 3. Các biểu đồ đã xuất

{chart_bullets}

## 4. Nhận xét chính (Observations)

""" + "\n".join(f"- {obs}" for obs in observations) + f"""

## 5. Các trường hợp lỗi & quá thời gian (Failure Cases)

{failures_section}

## 6. Hạn chế hiện tại (Limitations)

- **Bùng nổ số mệnh đề CNF khi vùng lớn:** `PARITY` và `COMPARE` hiện liệt kê trực tiếp các phép gán vi phạm trên hợp hai vùng (tối đa `2^|region|`), còn `EXACTLY`/`AT_MOST`/`AT_LEAST` dùng tổ hợp trực tiếp thay vì mã hóa có biến phụ (như Sinz sequential counter hoặc chuỗi XOR Tseitin). Số mệnh đề tăng nhanh khi lưới lớn hơn `5x5` hoặc có nhiều ràng buộc chồng lấp.
- **DPLL không lưu trạng thái (stateless) giữa các truy vấn suy luận:** Mỗi kiểm tra kéo theo logic (`KB ^ C_i` và `KB ^ ¬C_i`) gọi `DpllSolver.solve()` lại từ đầu, chưa có học mệnh đề xung đột (CDCL), watched literals hay tái sử dụng trạng thái giữa các bước.
- **Chi phí gọi SAT lặp lại theo từng bước:** Dù đã có cơ chế tận dụng model mẫu (`use_witnesses=True`), việc phân loại tất cả các ô chưa rõ ở mỗi bước vẫn cần nhiều lần gọi SAT khi kích thước bàn cờ tăng.
- **Giới hạn hiệu năng Python thuần và rủi ro timeout:** Vì `DpllSolver` cài đặt bằng Python thuần, các màn `5x5` phức tạp hơn hoặc cấu hình tắt heuristic (`dpll_basic`) có thể gặp `TIMEOUT`; mọi dòng `TIMEOUT`, `STUCK`, `INCONSISTENT` và `ERROR` đều được giữ lại đầy đủ để tránh thiên lệch kết quả.
"""

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


def build_arg_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for results plotting and report generation."""
    parser = argparse.ArgumentParser(
        description="Tạo bảng tổng hợp, biểu đồ tiếng Việt, nhận xét và phân tích lỗi từ CSV thực nghiệm.",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        nargs="+",
        default=None,
        help="Đường dẫn tệp CSV thực nghiệm (mặc định: results/raw/dpll_experiments.csv).",
    )
    parser.add_argument(
        "--steps-csv",
        type=Path,
        default=None,
        help="Tệp CSV theo từng bước tạo bằng `--steps-csv` của run_experiments.py.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=DEFAULT_FIGURES_DIR,
        help="Thư mục lưu biểu đồ, bảng CSV và báo cáo (mặc định: results/figures/).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Đường dẫn tệp báo cáo Markdown (mặc định: <output-dir>/experiment_report.md).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Độ phân giải DPI cho ảnh PNG (mặc định: 200).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Tắt thông báo trên terminal.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for plotting and summarizing Griductive DPLL experiments."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    input_csvs = resolve_input_csvs(args.input)
    df = load_experiment_csvs(input_csvs)

    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.report if args.report is not None else out_dir / "experiment_report.md"

    _apply_plot_style()

    summary_df = build_summary_by_size(df)
    failures_df = extract_failure_cases(df)

    summary_csv = out_dir / "summary_by_size.csv"
    failures_csv = out_dir / "failure_cases.csv"
    summary_df.to_csv(summary_csv, index=False, encoding="utf-8")
    failures_df.to_csv(failures_csv, index=False, encoding="utf-8")

    generated_charts: list[Path] = [
        plot_runtime_by_puzzle(df, out_dir, args.dpi),
        plot_scaling_by_size(summary_df, df, out_dir, args.dpi),
        plot_search_effort_per_puzzle(df, out_dir, args.dpi),
    ]

    ablation_chart = plot_ablation_comparison(df, out_dir, args.dpi)
    if ablation_chart is not None:
        generated_charts.append(ablation_chart)

    if args.steps_csv is not None:
        if not args.steps_csv.exists():
            raise FileNotFoundError(f"Steps CSV not found: {args.steps_csv}")
        generated_charts.append(plot_step_trajectory(args.steps_csv, out_dir, args.dpi))

    generate_markdown_report(
        df=df,
        summary_df=summary_df,
        failures_df=failures_df,
        generated_charts=generated_charts,
        source_csvs=input_csvs,
        report_path=report_path,
    )

    if not args.quiet:
        print(f"Đã đọc {len(df)} dòng kết quả ({len(failures_df)} ca không SOLVED được giữ lại).")
        print(f"Đã lưu bảng tổng hợp: {summary_csv}")
        print(f"Đã lưu bảng failure cases: {failures_csv}")
        print(f"Đã lưu báo cáo Markdown: {report_path}")
        for chart in generated_charts:
            print(f"Đã lưu biểu đồ: {chart}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())