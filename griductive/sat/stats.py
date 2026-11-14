"""Data structures for tracking DPLL solver statistics and results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional


@dataclass
class SatStats:
    """Tracks performance metrics across one or more DPLL solver runs."""

    sat_calls: int = 0
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime_ms: float = 0.0

    @property
    def runtime(self) -> float:
        """Alias for runtime_ms in milliseconds."""
        return self.runtime_ms

    @runtime.setter
    def runtime(self, value: float) -> None:
        """Set runtime_ms via the runtime alias."""
        self.runtime_ms = float(value)

    def reset(self) -> None:
        """Reset all counters and runtime to zero."""
        self.sat_calls = 0
        self.decisions = 0
        self.propagations = 0
        self.backtracks = 0
        self.runtime_ms = 0.0

    def add(self, other: "SatStats" | Dict[str, Any]) -> None:
        """Accumulate metrics from another SatStats instance or stats dict."""
        if isinstance(other, dict):
            self.sat_calls += int(other.get("sat_calls", 0))
            self.decisions += int(other.get("decisions", 0))
            self.propagations += int(other.get("propagations", 0))
            self.backtracks += int(other.get("backtracks", 0))
            rt = other.get("runtime_ms", other.get("runtime", 0.0))
            self.runtime_ms += float(rt)
        else:
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

    # Mapping / dict compatibility so `result.stats["decisions"]` or `result.stats["runtime"]` works seamlessly
    def __getitem__(self, key: str) -> float | int:
        """Support dictionary-style key lookup (including 'runtime' alias)."""
        if key == "runtime":
            return self.runtime_ms
        data = self.to_dict()
        if key not in data:
            raise KeyError(key)
        return data[key]

    def __contains__(self, key: object) -> bool:
        """Check whether a metric key exists in the exported dictionary."""
        return key == "runtime" or key in self.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for key if key is in the stats dictionary, else default."""
        if key == "runtime":
            return self.runtime_ms
        return self.to_dict().get(key, default)

    def keys(self):
        """Return a view of the stats dictionary's keys."""
        return self.to_dict().keys()

    def values(self):
        """Return a view of the stats dictionary's values."""
        return self.to_dict().values()

    def items(self):
        """Return a view of the stats dictionary's (key, value) pairs."""
        return self.to_dict().items()


@dataclass(frozen=True)
class SatResult:
    """Encapsulates the outcome of a single DPLL solve call."""

    satisfiable: bool
    model: Optional[Dict[int, bool]] = None
    stats: SatStats = field(default_factory=SatStats)

    @property
    def stats_dict(self) -> Dict[str, float | int]:
        """Return the per-call statistics as a plain Python dictionary."""
        return self.stats.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        """Export the full solve outcome including the statistics dictionary."""
        return {
            "satisfiable": self.satisfiable,
            "model": self.model,
            "stats": self.stats.to_dict(),
        }

    def __iter__(self) -> Iterator[Any]:
        """Allow tuple unpacking: `sat, model = solver.solve(...)`."""
        yield self.satisfiable
        yield self.model

    def as_triple(self) -> tuple[bool, Optional[Dict[int, bool]], Dict[str, float | int]]:
        """Return `(satisfiable, model, stats_dict)` for callers expecting a 3-tuple."""
        return self.satisfiable, self.model, self.stats.to_dict()
