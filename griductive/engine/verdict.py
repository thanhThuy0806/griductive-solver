"""Bridge public game knowledge to the team's encoder, Agent and DPLL solver."""

from griductive.agent.entailment import Classification, EntailmentChecker
from griductive.core.constants import Status
from griductive.core.regions import parse_cell
from griductive.core.types import PublicState
from griductive.logic.cnf_encoder import encode_clue
from griductive.logic.variable_map import VarMap
from griductive.sat.dpll import DpllSolver


class EngineConsistencyError(RuntimeError):
    """Public knowledge is inconsistent or a proved verdict conflicts with the puzzle."""


def classify(public_state: PublicState, cell: str) -> Classification:
    """Classify a cell using only revealed clues and publicly known statuses."""
    parse_cell(cell, public_state.size)
    vm = VarMap(public_state.size)
    clauses = []
    for character in public_state.characters:
        if not character.revealed:
            continue
        if character.status is None or character.clue is None:
            raise ValueError("Revealed cards must have a public status and clue")
        clauses.extend(encode_clue(character.clue, vm))
        variable = vm.var(character.cell)
        clauses.append([variable if character.status is Status.CRIMINAL else -variable])
    checker = EntailmentChecker(solver=DpllSolver())
    return checker.classify(clauses, vm.var(cell))
