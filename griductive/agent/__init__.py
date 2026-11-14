"""Logic Agent package (Owner: A)."""
from griductive.agent.entailment import Classification, EntailmentChecker, SatQuery
from griductive.agent.logic_agent import Hint, LogicAgent, RunResult, RunStatus
from griductive.agent.protocols import PublicCard, VerdictResponse
from griductive.agent.trace import DeductionTrace, TraceStep
from griductive.agent.uniqueness import (Uniqueness, UniquenessResult, check_puzzle_uniqueness,
                                         count_solutions)

__all__ = [
    "Classification", "EntailmentChecker", "SatQuery",
    "Hint", "LogicAgent", "RunResult", "RunStatus",
    "PublicCard", "VerdictResponse",
    "DeductionTrace", "TraceStep",
    "Uniqueness", "UniquenessResult", "check_puzzle_uniqueness", "count_solutions",
]
