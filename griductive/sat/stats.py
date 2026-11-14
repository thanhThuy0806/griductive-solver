from __future__ import annotations
"""SolverStats: decisions, propagations, backtracks, runtime.

Owner: B
"""
"""Data structures for tracking DPLL solver statistics and results."""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SatStats:
    """Tracks performance metrics across one or more DPLL solver runs."""

    sat_calls: int = 0
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime_ms: float = 0.0

    def reset(self) -> None:
        """Reset all counters and runtime to zero."""
        self.sat_calls = 0
        self.decisions = 0
        self.propagations = 0
        self.backtracks = 0
        self.runtime_ms = 0.0

    def add(self, other: "SatStats") -> None:
        """Accumulate metrics from another SatStats instance into this one."""
        self.sat_calls += other.sat_calls
        self.decisions += other.decisions
        self.propagations += other.propagations
        self.backtracks += other.backtracks
        self.runtime_ms += other.runtime_ms

    def to_dict(self) -> Dict[str, float | int]:
        """Export statistics as a dictionary matching experiment CSV keys."""
        return {
            "sat_calls": self.sat_calls,
            "decisions": self.decisions,
            "propagations": self.propagations,
            "backtracks": self.backtracks,
            "runtime_ms": self.runtime_ms,
        }


@dataclass(frozen=True)
class SatResult:
    """Encapsulates the outcome of a single DPLL solve call."""

    satisfiable: bool
    model: Optional[Dict[int, bool]] = None
    stats: SatStats = field(default_factory=SatStats)

    def __iter__(self):
        """Allow tuple unpacking: `sat, model = solver.solve(...)`."""
        yield self.satisfiable
        yield self.model