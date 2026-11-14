"""Tests: deduction loop, trace, row-major choice, Hint (Agent, using fakes)."""
import ast
import json
from pathlib import Path

import pytest
from fakes import PUZZLE_3X3, PUZZLE_4X4, MiniEncoder, MiniGame, all_models

from griductive.agent import LogicAgent, PublicCard, RunStatus
from griductive.agent.grid import row_major_cells


def make(puzzle, observe=True):
    enc = MiniEncoder(puzzle["size"])
    game = MiniGame(puzzle)
    agent = LogicAgent(puzzle["size"], enc)
    if observe:
        agent.observe_cards(game.public_cards())
    return agent, game, enc


def oracle_forced(agent, enc, size):
    """First forced unresolved cell in row-major order, by brute force over all models."""
    models = all_models(agent.knowledge_base(), size * size)
    for cell in agent.unresolved_cells():
        values = {m[enc.var_of(cell) - 1] for m in models}
        if len(values) == 1:
            return cell, "CRIMINAL" if values == {True} else "INNOCENT"
    return None


def test_row_major_cells():
    assert row_major_cells(3) == ["A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"]


@pytest.mark.parametrize("puzzle", [PUZZLE_3X3, PUZZLE_4X4])
def test_auto_solve_matches_hidden_solution(puzzle):
    agent, game, _ = make(puzzle)
    result = agent.run(game)
    assert result.status == RunStatus.SOLVED
    assert agent.proved == puzzle["solution"]
    assert result.accepted_steps == len(puzzle["solution"]) - len(puzzle["initial"])
    assert len(game.submissions) == result.accepted_steps


@pytest.mark.parametrize("puzzle", [PUZZLE_3X3, PUZZLE_4X4])
def test_every_step_is_row_major_first_forced_cell(puzzle):
    """Never a guess: each chosen cell is the first provably forced one (brute-force oracle)."""
    agent, game, enc = make(puzzle)
    size = puzzle["size"]
    while True:
        expected = oracle_forced(agent, enc, size)
        outcome = agent.step(game)
        if outcome is not None:
            assert outcome == RunStatus.SOLVED and expected is None
            break
        step = agent.trace.steps[-1]
        assert (step.cell, step.verdict) == expected


def test_trace_contents():
    agent, game, _ = make(PUZZLE_3X3)
    result = agent.run(game)
    trace = result.trace
    assert trace.final_status == "SOLVED"
    assert len(trace.initial_clue_ids) == len(PUZZLE_3X3["initial"])
    assert [s.step for s in trace.steps] == list(range(1, len(trace.steps) + 1))
    known_ids = set(trace.initial_clue_ids)
    for s in trace.steps:
        assert set(s.active_clue_ids) == known_ids          # KB_t when the queries were made
        assert s.result == "ACCEPTED" and s.cell and s.verdict
        assert s.sat_queries and s.sat_calls == len(s.sat_queries)
        assert s.sat_queries[0].formula == "KB"
        assert s.forced_count >= 1
        assert s.new_clue_id == s.new_clue["id"]
        known_ids.add(s.new_clue_id)
    assert result.sat_calls == trace.total_sat_calls
    # serialisable and printable
    assert json.loads(trace.to_json())["steps"][0]["cell"] == trace.steps[0].cell
    assert "Final status: SOLVED" in trace.format_table()


def test_stuck_when_nothing_is_provable():
    agent, game, _ = make(PUZZLE_3X3, observe=False)
    result = agent.run(game)
    assert result.status == RunStatus.STUCK
    assert game.submissions == []                            # no guessing
    assert result.trace.steps[-1].result == "STUCK" and result.trace.steps[-1].sat_queries


def test_inconsistent_state_is_reported_and_nothing_is_submitted():
    agent, game, _ = make(PUZZLE_3X3, observe=False)
    agent.observe("B1", "INNOCENT", {"id": "x1", "type": "FACT", "cell": "A1", "status": "CRIMINAL"})
    agent.observe("C1", "INNOCENT", {"id": "x2", "type": "FACT", "cell": "A1", "status": "INNOCENT"})
    result = agent.run(game)
    assert result.status == RunStatus.INCONSISTENT
    assert game.submissions == []


def test_engine_rejection_becomes_error_not_crash():
    class RejectingGame(MiniGame):
        def submit_verdict(self, cell, status):
            self.submissions.append((cell, status))
            from griductive.agent import VerdictResponse
            return VerdictResponse("NOT_PROVABLE")

    agent, _, _ = make(PUZZLE_3X3, observe=False)
    game = RejectingGame(PUZZLE_3X3)
    agent.observe_cards(game.public_cards())
    result = agent.run(game)
    assert result.status == RunStatus.ERROR and "NOT_PROVABLE" in result.error


def test_bad_clue_from_engine_becomes_error():
    class BadClueGame(MiniGame):
        def submit_verdict(self, cell, status):
            from griductive.agent import VerdictResponse
            return VerdictResponse("ACCEPTED", {"id": "bad", "type": "NOPE"})

    agent, _, _ = make(PUZZLE_3X3, observe=False)
    game = BadClueGame(PUZZLE_3X3)
    agent.observe_cards(game.public_cards())
    assert agent.run(game).status == RunStatus.ERROR


def test_timeout():
    agent, game, _ = make(PUZZLE_4X4)
    assert agent.run(game, timeout_s=-1).status == RunStatus.TIMEOUT


def test_reset_forgets_everything():
    agent, game, _ = make(PUZZLE_3X3)
    agent.run(game)
    agent.reset()
    assert agent.proved == {} and agent.knowledge_base() == [] and agent.trace.steps == []


def test_observe_validation():
    agent, _, _ = make(PUZZLE_3X3, observe=False)
    with pytest.raises(ValueError):
        agent.observe("Z9", "CRIMINAL")
    with pytest.raises(ValueError):
        agent.observe("A1", "MAYBE")
    agent.observe("A1", "CRIMINAL", {"id": "k1", "type": "FACT", "cell": "B1", "status": "INNOCENT"})
    with pytest.raises(ValueError):
        agent.observe("A1", "INNOCENT")                      # conflicting status
    with pytest.raises(ValueError):
        agent.observe("B1", "INNOCENT", {"id": "k1", "type": "FACT", "cell": "C1", "status": "INNOCENT"})
    assert agent.proved == {"A1": "CRIMINAL"}                # failed calls changed nothing


# ---------------------------------------------------------------- Hint
@pytest.mark.parametrize("puzzle", [PUZZLE_3X3, PUZZLE_4X4])
def test_hint_is_forced_and_support_is_minimal(puzzle):
    agent, game, enc = make(puzzle)
    size, n = puzzle["size"], puzzle["size"] ** 2
    while agent.unresolved_cells():
        hint = agent.hint()
        expected = oracle_forced(agent, enc, size)
        assert hint is not None and (hint.cell, hint.verdict) == expected

        premises = {f"clue:{cid}": enc.encode_clue(c) for cid, c in agent._clues.items()}
        units = {f"cell:{c}": [[enc.var_of(c) if s == "CRIMINAL" else -enc.var_of(c)]]
                 for c, s in agent.proved.items()}
        premises.update(units)
        used = [f"clue:{c}" for c in hint.support_clue_ids] + [f"cell:{c}" for c in hint.support_cells]
        refute = [[-enc.var_of(hint.cell)]] if hint.verdict == "CRIMINAL" else [[enc.var_of(hint.cell)]]

        def flat(keys):
            return [c for k in keys for c in premises[k]]

        assert all_models(flat(used) + refute, n) == []                    # support proves it
        for k in used:                                                      # and is minimal
            rest = [x for x in used if x != k]
            assert all_models(flat(rest) + refute, n) != []

        # hint changed nothing
        before = (agent.proved, agent.knowledge_base(), len(agent.trace.steps), len(game.submissions))
        agent.hint()
        assert before == (agent.proved, agent.knowledge_base(), len(agent.trace.steps), len(game.submissions))
        assert hint.message and hint.sat_queries
        assert agent.step(game) is None                                     # continue the game


def test_hint_none_when_nothing_provable():
    agent, _, _ = make(PUZZLE_3X3, observe=False)
    assert agent.hint() is None


def test_hint_then_step_agree_on_cell():
    agent, game, _ = make(PUZZLE_4X4)
    hint = agent.hint()
    agent.step(game)
    assert agent.trace.steps[-1].cell == hint.cell and agent.trace.steps[-1].verdict == hint.verdict


def test_query_log_is_empty_after_public_calls():
    agent, game, _ = make(PUZZLE_3X3)
    agent.hint()
    assert agent.checker.queries == []
    agent.step(game)
    assert agent.checker.queries == []


# ---------------------------------------------------------------- architecture rule
def test_agent_package_never_imports_engine():
    agent_dir = Path(__file__).resolve().parent.parent / "griductive" / "agent"
    for path in agent_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                assert not name.startswith("griductive.engine"), f"{path.name} imports {name}"
