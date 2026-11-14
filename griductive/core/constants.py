"""Shared enums and constants (imports nothing from the project)."""

from enum import Enum

MAX_GRID = 26  # columns are letters A-Z


class Status(str, Enum):
    """Hidden or proved status of a character."""

    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"


class VerdictResult(str, Enum):
    """Result of a player's verdict."""

    ACCEPTED = "ACCEPTED"
    NOT_PROVABLE = "NOT_PROVABLE"
    CONTRADICTED = "CONTRADICTED"


class ClueType(str, Enum):
    """Clue templates (extension types are added here in Tasks 24-25)."""

    FACT = "FACT"
    SAME = "SAME"
    DIFFERENT = "DIFFERENT"
    EXACTLY = "EXACTLY"
    AT_LEAST = "AT_LEAST"
    AT_MOST = "AT_MOST"


class RegionKind(str, Enum):
    """Region kinds usable inside a clue."""

    ROW = "ROW"
    COL = "COL"
    NEIGHBORS = "NEIGHBORS"
    CELLS = "CELLS"


BINARY_CLUE_TYPES = (ClueType.SAME, ClueType.DIFFERENT)

COUNT_CLUE_TYPES = (
    ClueType.EXACTLY,
    ClueType.AT_LEAST,
    ClueType.AT_MOST,
)