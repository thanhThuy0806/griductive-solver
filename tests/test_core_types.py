import pytest
from griductive.core.constants import ClueType, Status
from griductive.core.types import Clue, ClueError, Region


def test_parse_clue_with_status():
    c = Clue.from_dict({"id": "c01", "type": "FACT", "cell": "A1", "status": "INNOCENT"})
    assert c.type is ClueType.FACT and c.status is Status.INNOCENT


def test_parse_counting_clue_with_region():
    c = Clue.from_dict({"id": "c04", "type": "EXACTLY", "k": 2,
                        "region": {"kind": "ROW", "index": 2}})
    assert isinstance(c.region, Region) and c.k == 2


def test_unknown_keys_go_to_params():
    c = Clue.from_dict({"id": "c9", "type": "SAME", "a": "A1", "b": "B1", "note": "x"})
    assert c.params == {"note": "x"}


@pytest.mark.parametrize("bad", [
    {"type": "FACT"},                                     # missing id
    {"id": "c", "type": "FOO"},                           # unknown type
    {"id": "c", "type": "FACT", "status": "MAYBE"},       # bad status
    {"id": "c", "type": "EXACTLY", "region": {"kind": "DIAGONAL"}},
])
def test_bad_clue_dicts(bad):
    with pytest.raises(ClueError):
        Clue.from_dict(bad)