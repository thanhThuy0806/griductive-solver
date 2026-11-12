"""Shared values used by puzzle data and logic modules."""

from enum import Enum


class Status(str, Enum):
    """Hidden or proved status of a character."""

    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"


class ClueType(str, Enum):
    """The six supported core clue templates."""

    FACT = "FACT"
    SAME = "SAME"
    DIFFERENT = "DIFFERENT"
    EXACTLY = "EXACTLY"
    AT_LEAST = "AT_LEAST"
    AT_MOST = "AT_MOST"


class RegionKind(str, Enum):
    """Ways of selecting cells from the board."""

    ROW = "ROW"
    COL = "COL"
    NEIGHBORS = "NEIGHBORS"
    CELLS = "CELLS"
