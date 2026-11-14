"""Private game state and the no-guess reveal protocol."""

from copy import deepcopy
from typing import Callable

from griductive.agent.entailment import Classification
from griductive.core.constants import Status, VerdictResult
from griductive.core.regions import all_cells
from griductive.core.types import AgentKnowledge, PublicCell, PublicState, Puzzle, VerdictResponse
from griductive.engine.agent_knowledge import project_clue
from griductive.engine.verdict import EngineConsistencyError, classify as classify_agent


class GameEngine:
    """Own a validated private puzzle and expose only detached public snapshots."""

    def __init__(self, puzzle: Puzzle,
                 classify: Callable[[AgentKnowledge, str], Classification] | None = None) -> None:
        """Copy a loader-validated puzzle; use the real Agent bridge by default."""
        if classify is not None and not callable(classify):
            raise TypeError("classify must be callable")
        self._puzzle = deepcopy(puzzle)
        self._cells = {character.cell: character for character in self._puzzle.characters}
        self._classify = classify_agent if classify is None else classify
        self._revealed = {cell.cell for cell in self._puzzle.characters if cell.revealed}

    def get_public_state(self) -> PublicState:
        """Return public card data without references to private mutable objects."""
        characters = []
        for cell in all_cells(self._puzzle.size):
            character = self._cells[cell]
            revealed = cell in self._revealed
            characters.append(PublicCell(
                cell=cell, name=character.name, job=character.job, revealed=revealed,
                status=character.status if revealed else None,
                clue=deepcopy(character.clue) if revealed else None,
            ))
        return PublicState(size=self._puzzle.size, characters=tuple(characters))

    def get_agent_knowledge(self) -> AgentKnowledge:
        """Return only revealed clue semantics and initial/accepted public statuses."""
        opened = [self._cells[cell] for cell in all_cells(self._puzzle.size)
                  if cell in self._revealed]
        return AgentKnowledge(
            size=self._puzzle.size,
            revealed_clues=tuple(project_clue(c.clue, self._puzzle.size) for c in opened),
            proven_verdicts=tuple((c.cell, c.status) for c in opened),
        )

    def submit_verdict(self, cell: str, status: Status) -> VerdictResponse:
        """Reveal one card only when the public Agent proves the submitted status."""
        if not isinstance(cell, str) or cell not in self._cells:
            raise ValueError("cell must identify a card on the board")
        if not isinstance(status, Status):
            raise ValueError("status must be a Status enum member")
        if cell in self._revealed:
            raise ValueError("The card is already revealed")

        classification = self._classify(self.get_agent_knowledge(), cell)
        if not isinstance(classification, Classification):
            raise TypeError("Agent must return Classification")
        if classification is Classification.INCONSISTENT:
            raise EngineConsistencyError("Public knowledge is inconsistent")
        if classification is Classification.UNKNOWN:
            return VerdictResponse(cell, status, VerdictResult.NOT_PROVABLE)
        if classification.value != status.value:
            return VerdictResponse(cell, status, VerdictResult.CONTRADICTED)
        if self._cells[cell].status is not status:
            raise EngineConsistencyError("Proved verdict conflicts with puzzle data")

        clue = deepcopy(self._cells[cell].clue)
        self._revealed.add(cell)
        return VerdictResponse(cell, status, VerdictResult.ACCEPTED, clue)

    def restart(self) -> PublicState:
        """Restore the original face-up cards and return a fresh public snapshot."""
        self._revealed = {cell.cell for cell in self._puzzle.characters if cell.revealed}
        return self.get_public_state()

    @property
    def is_solved(self) -> bool:
        """Return whether every card has been revealed."""
        return len(self._revealed) == len(self._cells)
