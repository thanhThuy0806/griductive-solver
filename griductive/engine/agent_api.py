"""Public-only adapter for the existing LogicAgent encoder and game protocols."""

from enum import Enum

from griductive.agent.logic_agent import LogicAgent
from griductive.agent.protocols import PublicCard, VerdictResponse
from griductive.core.constants import ClueType, RegionKind, Status, VerdictResult
from griductive.core.types import Clue, Region
from griductive.engine.agent_knowledge import project_clue, validate_knowledge
from griductive.engine.game_engine import GameEngine
from griductive.logic.cnf_encoder import encode_clue as encode_structured_clue
from griductive.logic.variable_map import VarMap
from griductive.sat.dpll import DpllSolver


_FIELDS = {
    ClueType.FACT: ("cell", "status"),
    ClueType.SAME: ("a", "b"),
    ClueType.DIFFERENT: ("a", "b"),
    ClueType.EXACTLY: ("k", "region"),
    ClueType.AT_LEAST: ("k", "region"),
    ClueType.AT_MOST: ("k", "region"),
    ClueType.PARITY: ("parity", "region"),
    ClueType.COMPARE: ("region_a", "region_b", "op"),
}


def _region_dict(region: Region) -> dict:
    data = {"kind": region.kind.value}
    if region.kind in (RegionKind.ROW, RegionKind.COL):
        data["index"] = region.index
    elif region.kind is RegionKind.NEIGHBORS:
        data["of"] = region.of
    else:
        data["cells"] = list(region.cells)
    return data


def _clue_dict(clue: Clue, size: int) -> dict:
    # Project first: a revealed Clue can still carry private metadata in params.
    clean = project_clue(clue, size)
    data = {"id": clean.id, "type": clean.type.value}
    for field in _FIELDS[clean.type]:
        value = getattr(clean, field)
        if isinstance(value, Region):
            value = _region_dict(value)
        elif isinstance(value, Enum):
            value = value.value
        data[field] = value
    return data


class AgentAPI:
    """Expose public evidence and verdict submission without handing Agent a Puzzle."""

    def __init__(self, engine: GameEngine) -> None:
        """Bind public Engine operations; keep no puzzle or GUI snapshot."""
        knowledge = engine.get_agent_knowledge()
        validate_knowledge(knowledge)
        self._vm = VarMap(knowledge.size)
        self._get_knowledge = engine.get_agent_knowledge
        self._submit = engine.submit_verdict

    @property
    def size(self) -> int:
        """Return the public board size."""
        return self._vm.n

    def public_cards(self) -> tuple[PublicCard, ...]:
        """Return detached face-up cards using only canonical AgentKnowledge."""
        knowledge = self._get_knowledge()
        validate_knowledge(knowledge)
        # Engine emits one clue and one status per opened card, both row-major.
        if len(knowledge.revealed_clues) != len(knowledge.proven_verdicts):
            raise ValueError("Engine evidence must contain one clue per opened card")
        return tuple(PublicCard(cell, status.value, _clue_dict(clue, self.size))
                     for (cell, status), clue in zip(knowledge.proven_verdicts,
                                                    knowledge.revealed_clues))

    def create_agent(self) -> LogicAgent:
        """Initialize the real LogicAgent from the current public evidence and DPLL."""
        agent = LogicAgent(self.size, encoder=self, solver=DpllSolver())
        agent.observe_cards(self.public_cards())
        return agent

    def var_of(self, cell: str) -> int:
        """Map a cell to the shared deterministic SAT variable."""
        return self._vm.var(cell)

    def encode_clue(self, data: dict) -> list[list[int]]:
        """Validate a canonical public clue dict and use the team's CNF encoder."""
        clue = Clue.from_dict(data)
        if data != _clue_dict(clue, self.size):
            raise ValueError("Agent clue contains metadata or unused fields")
        return encode_structured_clue(clue, self._vm)

    def submit_verdict(self, cell: str, status: str) -> VerdictResponse:
        """Translate the Agent protocol and project every newly revealed clue."""
        response = self._submit(cell, Status(status))
        clue = (_clue_dict(response.new_clue, self.size)
                if response.result is VerdictResult.ACCEPTED else None)
        return VerdictResponse(response.result.value, clue)
