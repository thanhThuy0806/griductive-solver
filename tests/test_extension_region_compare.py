"""Unit tests for Extension 2: Compare Region Counts (Task 25).

Owner: C (Duy)
"""
from itertools import product
import pytest

from griductive.core.constants import ClueType, CompareOp, RegionKind
from griductive.core.regions import resolve_region
from griductive.core.types import Clue, ClueError, Region
from griductive.engine.puzzle_loader import parse_puzzle
from griductive.logic.clue_validator import validate_clue
from griductive.logic.cnf_encoder import encode_clue
from griductive.logic.evaluator import evaluate
from griductive.logic.variable_map import VarMap
from griductive.sat.dpll import dpll_solve


def satisfied(cnf, model):
    """True if every clause has at least one true literal under model {var: bool}."""
    return all(any(model[abs(lit)] == (lit > 0) for lit in clause) for clause in cnf)


def test_validate_compare_success():
    clue = Clue(
        id="c_cmp",
        type=ClueType.COMPARE,
        region_a=Region(RegionKind.ROW, index=1),
        region_b=Region(RegionKind.COL, index="B"),
        op=CompareOp.MORE,
    )
    validate_clue(clue, 3)

    # string op alias
    clue2 = Clue(
        id="c_cmp2",
        type=ClueType.COMPARE,
        region_a=Region(RegionKind.ROW, index=2),
        region_b=Region(RegionKind.NEIGHBORS, of="B2"),
        op="EQUAL",
    )
    validate_clue(clue2, 3)


def test_validate_compare_failures():
    # Missing region_a
    with pytest.raises(ClueError, match="missing field 'region_a'"):
        validate_clue(
            Clue(
                id="c1",
                type=ClueType.COMPARE,
                region_b=Region(RegionKind.COL, index="A"),
                op=CompareOp.EQUAL,
            ),
            3,
        )

    # Missing region_b
    with pytest.raises(ClueError, match="missing field 'region_b'"):
        validate_clue(
            Clue(
                id="c2",
                type=ClueType.COMPARE,
                region_a=Region(RegionKind.ROW, index=1),
                op=CompareOp.EQUAL,
            ),
            3,
        )

    # Missing op
    with pytest.raises(ClueError, match="missing field 'op'"):
        validate_clue(
            Clue(
                id="c3",
                type=ClueType.COMPARE,
                region_a=Region(RegionKind.ROW, index=1),
                region_b=Region(RegionKind.COL, index="A"),
            ),
            3,
        )

    # Invalid op
    with pytest.raises(ClueError, match="'op' must be MORE, EQUAL, or LESS"):
        validate_clue(
            Clue(
                id="c4",
                type=ClueType.COMPARE,
                region_a=Region(RegionKind.ROW, index=1),
                region_b=Region(RegionKind.COL, index="A"),
                op="INVALID",
            ),
            3,
        )


def test_evaluator_compare_truth():
    ra = Region(RegionKind.CELLS, cells=("A1", "B1"))
    rb = Region(RegionKind.CELLS, cells=("A2", "B2"))

    clue_more = Clue(id="c_more", type=ClueType.COMPARE, region_a=ra, region_b=rb, op=CompareOp.MORE)
    clue_eq = Clue(id="c_eq", type=ClueType.COMPARE, region_a=ra, region_b=rb, op=CompareOp.EQUAL)
    clue_less = Clue(id="c_less", type=ClueType.COMPARE, region_a=ra, region_b=rb, op=CompareOp.LESS)

    # ra=2, rb=1 -> More=True, Eq=False, Less=False
    assign1 = {"A1": True, "B1": True, "A2": True, "B2": False}
    assert evaluate(clue_more, assign1, 3) is True
    assert evaluate(clue_eq, assign1, 3) is False
    assert evaluate(clue_less, assign1, 3) is False

    # ra=1, rb=1 -> More=False, Eq=True, Less=False
    assign2 = {"A1": True, "B1": False, "A2": False, "B2": True}
    assert evaluate(clue_more, assign2, 3) is False
    assert evaluate(clue_eq, assign2, 3) is True
    assert evaluate(clue_less, assign2, 3) is False

    # ra=0, rb=1 -> More=False, Eq=False, Less=True
    assign3 = {"A1": False, "B1": False, "A2": True, "B2": False}
    assert evaluate(clue_more, assign3, 3) is False
    assert evaluate(clue_eq, assign3, 3) is False
    assert evaluate(clue_less, assign3, 3) is True


@pytest.mark.parametrize("op", [CompareOp.MORE, CompareOp.EQUAL, CompareOp.LESS])
@pytest.mark.parametrize("ra,rb", [
    # Disjoint regions
    (Region(RegionKind.ROW, index=1), Region(RegionKind.ROW, index=2)),
    # Overlapping regions (intersect at A1)
    (Region(RegionKind.ROW, index=1), Region(RegionKind.COL, index="A")),
    # Explicit subsets
    (Region(RegionKind.CELLS, cells=("A1", "B2")), Region(RegionKind.CELLS, cells=("B2", "C3"))),
])
def test_compare_cross_check_cnf_vs_evaluator(op, ra, rb):
    n = 3
    clue = Clue(id="cmp_cross", type=ClueType.COMPARE, region_a=ra, region_b=rb, op=op)
    vm = VarMap(n)
    cnf = encode_clue(clue, vm)

    cells_a = resolve_region(ra, n)
    cells_b = resolve_region(rb, n)
    union_cells = sorted(set(cells_a) | set(cells_b))

    for bits in product([False, True], repeat=len(union_cells)):
        assign = dict(zip(union_cells, bits))
        model = {vm.var(c): val for c, val in assign.items()}
        assert satisfied(cnf, model) == evaluate(clue, assign, n)


def test_compare_with_dpll_solver():
    n = 3
    vm = VarMap(n)
    ra = Region(RegionKind.ROW, index=1)  # A1, B1, C1
    rb = Region(RegionKind.ROW, index=2)  # A2, B2, C2
    clue = Clue(id="cmp_solve", type=ClueType.COMPARE, region_a=ra, region_b=rb, op=CompareOp.EQUAL)
    cnf = encode_clue(clue, vm)

    # Assume Row 1 has A1=True, B1=False, C1=False (count=1)
    # And Row 2 has A2=False, B2=False -> C2 must be True to have count=1!
    assumptions = [
        vm.var("A1"), -vm.var("B1"), -vm.var("C1"),
        -vm.var("A2"), -vm.var("B2"),
    ]
    res = dpll_solve(cnf, num_vars=vm.num_primary, assumptions=assumptions)
    assert res.satisfiable is True
    assert res.model[vm.var("C2")] is True

    # If we force C2=False as well (count in rb = 0 != 1) -> must be UNSAT
    res2 = dpll_solve(cnf, num_vars=vm.num_primary, assumptions=[*assumptions, -vm.var("C2")])
    assert res2.satisfiable is False


def test_compare_puzzle_loader():
    raw_data = {
        "size": 3,
        "characters": [
            {
                "cell": "A1",
                "name": "Bob",
                "job": "Investigator",
                "status": "CRIMINAL",
                "revealed": True,
                "clue": {
                    "id": "c01",
                    "type": "COMPARE",
                    "region_a": {"kind": "ROW", "index": 1},
                    "region_b": {"kind": "COL", "index": "A"},
                    "op": "MORE",
                },
            },
            *[
                {
                    "cell": f"{col}{row}",
                    "name": f"Person_{col}{row}",
                    "job": "Staff",
                    "status": "INNOCENT",
                    "revealed": False,
                    "clue": {"id": f"c_{col}{row}", "type": "FACT", "cell": "A1", "status": "INNOCENT"},
                }
                for row in range(1, 4)
                for col in ("A", "B", "C")
                if not (col == "A" and row == 1)
            ],
        ],
    }

    puzzle = parse_puzzle(raw_data)
    clue = puzzle.characters[0].clue
    assert clue.type is ClueType.COMPARE
    assert clue.op is CompareOp.MORE
    assert clue.region_a.kind is RegionKind.ROW
    assert clue.region_b.kind is RegionKind.COL
