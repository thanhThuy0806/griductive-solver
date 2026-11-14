"""What the Agent needs from the rest of the system (Owner: A).

The Agent never imports `griductive.engine`. Instead it is handed objects that
satisfy these protocols (duck typing), so it can only see public information.

  * ClueEncoder  - provided by C's encoder. Must allocate UNIQUE auxiliary
                   variables across calls (aux ids > number of cells).
  * GameInterface - provided by D's GameEngine. `submit_verdict` must return an
                   object with `.result` and `.clue` (VerdictResponse below).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

Clause = list[int]
Clue = dict[str, Any]          # JSON clue, see README section 4; must contain "id"


@dataclass(frozen=True)
class PublicCard:
    """A face-up card: its status and clue are public knowledge."""

    cell: str
    status: str                # "CRIMINAL" | "INNOCENT"
    clue: Clue | None


@dataclass(frozen=True)
class VerdictResponse:
    """Engine's answer to a submitted verdict."""

    result: str                # "ACCEPTED" | "NOT_PROVABLE" | "CONTRADICTED"
    clue: Clue | None = None   # the clue revealed by an ACCEPTED verdict


@runtime_checkable
class ClueEncoder(Protocol):
    def var_of(self, cell: str) -> int:
        """Primary variable C_i of a cell (positive int, deterministic)."""
        ...

    def encode_clue(self, clue: Clue) -> list[Clause]:
        """CNF clauses of one clue (may use auxiliary variables)."""
        ...


@runtime_checkable
class GameInterface(Protocol):
    def submit_verdict(self, cell: str, status: str) -> VerdictResponse:
        ...
