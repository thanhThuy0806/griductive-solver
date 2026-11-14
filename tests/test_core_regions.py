"""Tests for core_regions."""
import pytest
from griductive.core.regions import resolve_region
from griductive.core.types import ClueError, Region


def nb(cid, n=3):
    return resolve_region({"kind": "neighbors", "of": cid}, n)


def test_neighbor_counts():
    assert len(nb("A1")) == 3          # góc
    assert len(nb("B1")) == 5          # cạnh
    assert len(nb("B2")) == 8          # giữa
    assert "B2" not in nb("B2")        # không tự là hàng xóm của mình


def test_row_column_cells():
    assert resolve_region({"kind": "row", "index": 2}, 3) == ["A2", "B2", "C2"]
    assert resolve_region({"kind": "column", "letter": "B"}, 3) == ["B1", "B2", "B3"]


def test_region_sorted_row_major():
    r = resolve_region({"kind": "cells", "cells": ["C3", "A1", "B2"]}, 3)
    assert r == ["A1", "B2", "C3"]


def test_region_errors():
    for bad in [{"kind": "row", "index": 0}, {"kind": "row", "index": 4},
                {"kind": "column", "letter": "D"},
                {"kind": "cells", "cells": ["A1", "A1"]},
                {"kind": "cells", "cells": []},
                {"kind": "cells", "cells": ["D4"]},
                {"kind": "diagonal"}]:
        with pytest.raises(ClueError):
            resolve_region(bad, 3)

def region(kind, **kw):
    return Region.from_dict({"kind": kind, **kw})


def nb(cid, n=3):
    return resolve_region(region("NEIGHBORS", of=cid), n)


def test_neighbor_counts():
    assert len(nb("A1")) == 3          # corner
    assert len(nb("B1")) == 5          # edge
    assert len(nb("B2")) == 8          # centre
    assert "B2" not in nb("B2")        # a cell is not its own neighbour


def test_row_column_cells():
    assert resolve_region(region("ROW", index=2), 3) == ["A2", "B2", "C2"]
    assert resolve_region(region("COL", index="B"), 3) == ["B1", "B2", "B3"]


def test_region_sorted_row_major():
    r = resolve_region(region("CELLS", cells=["C3", "A1", "B2"]), 3)
    assert r == ["A1", "B2", "C3"]


@pytest.mark.parametrize("kind,kw", [
    ("ROW", {"index": 0}), ("ROW", {"index": 4}), ("COL", {"index": "D"}),
    ("CELLS", {"cells": ["A1", "A1"]}), ("CELLS", {"cells": []}),
    ("CELLS", {"cells": ["D4"]}), ("NEIGHBORS", {"of": "D4"}),
])
def test_region_errors(kind, kw):
    with pytest.raises(ClueError):
        resolve_region(region(kind, **kw), 3)