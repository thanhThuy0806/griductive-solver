"""Project only supported clue semantics and validate the Agent input contract."""

from dataclasses import fields

from griductive.core.constants import ClueType, RegionKind, Status
from griductive.core.regions import parse_cell
from griductive.core.types import AgentKnowledge, Clue, Region
from griductive.logic.clue_validator import validate_clue


def project_clue(clue: Clue, size: int) -> Clue:
    """Rebuild a supported clue without metadata, unused fields or shared payloads."""
    if type(clue) is not Clue:
        raise TypeError("Expected Clue")
    if type(clue.id) is not str or not clue.id.strip():
        raise ValueError("Clue id must be a nonempty string")
    if not isinstance(clue.type, ClueType):
        raise ValueError("Unsupported clue type")
    if clue.type is ClueType.FACT:
        clean = Clue(clue.id, clue.type, cell=clue.cell, status=clue.status)
    elif clue.type in (ClueType.SAME, ClueType.DIFFERENT):
        clean = Clue(clue.id, clue.type, a=clue.a, b=clue.b)
    elif clue.type in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST):
        region = clue.region
        if type(region) is not Region or not isinstance(region.kind, RegionKind):
            raise ValueError("Unsupported region")
        if region.kind in (RegionKind.ROW, RegionKind.COL):
            clean_region = Region(region.kind, index=region.index)
        elif region.kind is RegionKind.NEIGHBORS:
            clean_region = Region(region.kind, of=region.of)
        elif region.kind is RegionKind.CELLS:
            clean_region = Region(region.kind, cells=tuple(c for c in region.cells))
        else:
            raise ValueError("Unsupported region kind")
        clean = Clue(clue.id, clue.type, k=clue.k, region=clean_region)
    else:
        raise ValueError("Unsupported clue type")
    validate_clue(clean, size)
    return clean


def validate_knowledge(knowledge: AgentKnowledge) -> None:
    """Reject malformed or noncanonical evidence before any solver is called."""
    if type(knowledge) is not AgentKnowledge:
        raise TypeError("Expected AgentKnowledge")
    if set(vars(knowledge)) != {f.name for f in fields(AgentKnowledge)}:
        raise ValueError("Unexpected AgentKnowledge fields")
    if type(knowledge.size) is not int or knowledge.size not in (3, 4, 5):
        raise ValueError("AgentKnowledge size must be 3, 4 or 5")
    if type(knowledge.revealed_clues) is not tuple or type(knowledge.proven_verdicts) is not tuple:
        raise TypeError("AgentKnowledge collections must be tuples")
    seen_cells = set()
    for verdict in knowledge.proven_verdicts:
        if type(verdict) is not tuple or len(verdict) != 2:
            raise TypeError("Verdicts must be (cell, Status) tuples")
        cell, status = verdict
        parse_cell(cell, knowledge.size)
        if not isinstance(status, Status):
            raise TypeError("Verdict status must be a Status enum")
        if cell in seen_cells:
            raise ValueError("Duplicate verdict cell")
        seen_cells.add(cell)
    seen_ids = set()
    for clue in knowledge.revealed_clues:
        clean = project_clue(clue, knowledge.size)
        if type(clue.params) is not dict or vars(clue) != vars(clean):
            raise ValueError("Clue contains metadata or unused fields")
        if clue.region is not None:
            if vars(clue.region) != vars(clean.region) or type(clue.region.cells) is not tuple:
                raise ValueError("Region contains metadata or unused fields")
        if clue.id in seen_ids:
            raise ValueError("Duplicate clue id")
        seen_ids.add(clue.id)
