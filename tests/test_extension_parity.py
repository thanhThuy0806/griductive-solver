"""Unit tests for Extension 1: Parity Clue (Task 24).

Owner: C (Duy)
"""
from itertools import product
import pytest

from griductive.core.constants import ClueType, Parity, RegionKind
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


def test_validate_parity_success():
    clue_even = Clue(
        id="c_even",
        type=ClueType.PARITY,
        parity=Parity.EVEN,
        region=Region(RegionKind.ROW, index=1),
    )
    validate_clue(clue_even, 3)

    clue_odd = Clue(
        id="c_odd",
        type=ClueType.PARITY,
        parity="ODD",
        region=Region(RegionKind.NEIGHBORS, of="B2"),
    )
    validate_clue(clue_odd, 3)


def test_validate_parity_failures():
    # Missing parity
    with pytest.raises(ClueError, match="missing field 'parity'"):
        validate_clue(
            Clue(id="c1", type=ClueType.PARITY, region=Region(RegionKind.ROW, index=1)),
            3,
        )

    # Missing region
    with pytest.raises(ClueError, match="missing field 'region'"):
        validate_clue(
            Clue(id="c2", type=ClueType.PARITY, parity=Parity.EVEN),
            3,
        )

    # Invalid parity string
    with pytest.raises(ClueError, match="'parity' must be EVEN or ODD"):
        validate_clue(
            Clue(
                id="c3",
                type=ClueType.PARITY,
                parity="MAYBE",
                region=Region(RegionKind.ROW, index=1),
            ),
            3,
        )

    # Invalid region (out of grid)
    with pytest.raises(ClueError):
        validate_clue(
            Clue(
                id="c4",
                type=ClueType.PARITY,
                parity=Parity.EVEN,
                region=Region(RegionKind.ROW, index=5),
            ),
            3,
        )


def test_evaluator_parity_truth():
    region = Region(RegionKind.ROW, index=1)  # A1, B1, C1
    clue_even = Clue(id="c_even", type=ClueType.PARITY, parity=Parity.EVEN, region=region)
    clue_odd = Clue(id="c_odd", type=ClueType.PARITY, parity=Parity.ODD, region=region)

    # 0 criminals -> Even=True, Odd=False
    assign_0 = {"A1": False, "B1": False, "C1": False}
    assert evaluate(clue_even, assign_0, 3) is True
    assert evaluate(clue_odd, assign_0, 3) is False

    # 1 criminal -> Even=False, Odd=True
    assign_1 = {"A1": True, "B1": False, "C1": False}
    assert evaluate(clue_even, assign_1, 3) is False
    assert evaluate(clue_odd, assign_1, 3) is True

    # 2 criminals -> Even=True, Odd=False
    assign_2 = {"A1": True, "B1": True, "C1": False}
    assert evaluate(clue_even, assign_2, 3) is True
    assert evaluate(clue_odd, assign_2, 3) is False

    # 3 criminals -> Even=False, Odd=True
    assign_3 = {"A1": True, "B1": True, "C1": True}
    assert evaluate(clue_even, assign_3, 3) is False
    assert evaluate(clue_odd, assign_3, 3) is True


@pytest.mark.parametrize("parity", [Parity.EVEN, Parity.ODD])
@pytest.mark.parametrize("region", [
    Region(RegionKind.ROW, index=1),
    Region(RegionKind.COL, index="B"),
    Region(RegionKind.NEIGHBORS, of="A1"),
    Region(RegionKind.CELLS, cells=("A1", "C2", "B3", "C3")),
])
def test_parity_cross_check_cnf_vs_evaluator(parity, region):
    n = 3
    clue = Clue(id="p_test", type=ClueType.PARITY, parity=parity, region=region)
    vm = VarMap(n)
    cnf = encode_clue(clue, vm)
    cells = resolve_region(region, n)

    for bits in product([False, True], repeat=len(cells)):
        assign = dict(zip(cells, bits))
        model = {vm.var(c): val for c, val in assign.items()}
        assert satisfied(cnf, model) == evaluate(clue, assign, n)


def test_parity_with_dpll_solver():
    n = 3
    vm = VarMap(n)
    region = Region(RegionKind.ROW, index=1)  # A1, B1, C1
    clue = Clue(id="p_solve", type=ClueType.PARITY, parity=Parity.ODD, region=region)
    cnf = encode_clue(clue, vm)

    # Add assumptions: A1=False, B1=False -> C1 must be True (CRIMINAL)
    res = dpll_solve(cnf, num_vars=vm.num_primary, assumptions=[-vm.var("A1"), -vm.var("B1")])
    assert res.satisfiable is True
    assert res.model[vm.var("C1")] is True

    # Add assumptions: A1=True, B1=True, C1=True -> Odd sum is 3, valid
    res2 = dpll_solve(cnf, num_vars=vm.num_primary, assumptions=[vm.var("A1"), vm.var("B1"), vm.var("C1")])
    assert res2.satisfiable is True

    # Add assumptions: A1=True, B1=True, C1=False -> Sum is 2 (EVEN) -> UNSAT for ODD
    res3 = dpll_solve(cnf, num_vars=vm.num_primary, assumptions=[vm.var("A1"), vm.var("B1"), -vm.var("C1")])
    assert res3.satisfiable is False


def test_parity_puzzle_loader():
    raw_data = {
        "size": 3,
        "characters": [
            {
                "cell": "A1",
                "name": "Alice",
                "job": "Agent",
                "status": "INNOCENT",
                "revealed": True,
                "clue": {
                    "id": "c01",
                    "type": "PARITY",
                    "parity": "EVEN",
                    "region": {"kind": "ROW", "index": 2},
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
    assert clue.type is ClueType.PARITY
    assert clue.parity is Parity.EVEN
    assert clue.region.kind is RegionKind.ROW
    assert clue.region.index == 2
