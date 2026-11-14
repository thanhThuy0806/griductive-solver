"""Bridge public game knowledge to the team's encoder, Agent and DPLL solver."""

from griductive.agent.entailment import Classification, EntailmentChecker
from griductive.core.constants import Status
from griductive.core.regions import parse_cell
from griductive.core.types import AgentKnowledge
from griductive.engine.agent_knowledge import validate_knowledge
from griductive.logic.cnf_encoder import encode_clue
from griductive.logic.variable_map import VarMap
from griductive.sat.dpll import DpllSolver


class EngineConsistencyError(RuntimeError):
    """Public knowledge is inconsistent or a proved verdict conflicts with the puzzle."""


def classify(knowledge: AgentKnowledge, cell: str) -> Classification:
    """Classify a cell using only revealed clues and publicly known statuses."""
    validate_knowledge(knowledge)
    parse_cell(cell, knowledge.size)
    vm = VarMap(knowledge.size)
    clauses = []
    for clue in knowledge.revealed_clues:
        clauses.extend(encode_clue(clue, vm))
    for known_cell, status in knowledge.proven_verdicts:
        variable = vm.var(known_cell)
        clauses.append([variable if status is Status.CRIMINAL else -variable])
    checker = EntailmentChecker(solver=DpllSolver())
    return checker.classify(clauses, vm.var(cell))
