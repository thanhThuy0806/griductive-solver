import pytest
from griductive.core.regions import all_cells
from griductive.core.types import ClueError
from griductive.logic.variable_map import VarMap


def test_var_map_roundtrip():
    vm = VarMap(4)
    assert vm.var("A1") == 1 and vm.var("D4") == 16
    for cid in all_cells(4):
        assert vm.cell(vm.var(cid)) == cid
    assert vm.num_primary == 16 and vm.num_aux == 0
    a = vm.new_aux()
    assert a == 17 and vm.num_aux == 1 and vm.num_vars == 17
    with pytest.raises(ClueError):
        vm.cell(a)                      # biến phụ không phải ô


def test_var_map_rejects_bad_cell():
    with pytest.raises(ClueError):
        VarMap(3).var("D4")