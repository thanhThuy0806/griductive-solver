"""Entry point.

Usage:
    python main.py                                   # open Web GUI
    python main.py --solve puzzles/3x3/p3x3_01.json  # run agent in terminal
"""
import argparse


def _solve(path: str) -> None:
    """Load a puzzle, create Engine → AgentAPI → LogicAgent, solve and print."""
    from griductive.engine.puzzle_loader import load_puzzle
    from griductive.engine.game_engine import GameEngine
    from griductive.engine.agent_api import AgentAPI

    puzzle = load_puzzle(path)
    engine = GameEngine(puzzle)
    api = AgentAPI(engine)
    agent = api.create_agent()
    result = agent.run(api)

    print(result.trace.format_table())
    print(f"\nStatus     : {result.status.value}")
    print(f"Steps      : {result.accepted_steps}")
    print(f"SAT calls  : {result.sat_calls}")
    print(f"Runtime    : {result.runtime_ms:.1f} ms")
    if result.error:
        print(f"Error      : {result.error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Griductive Solver")
    parser.add_argument("--solve", metavar="PUZZLE_JSON", help="solve a puzzle without GUI")
    args = parser.parse_args()

    if args.solve:
        _solve(args.solve)
        return

    from griductive.gui.web_server import run
    run()


if __name__ == "__main__":
    main()