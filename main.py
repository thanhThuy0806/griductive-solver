"""Entry point.

Usage:
    python main.py                                   # open GUI
    python main.py --solve puzzles/3x3/p3x3_01.json  # run agent in terminal
"""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Griductive Solver")
    parser.add_argument("--solve", metavar="PUZZLE_JSON", help="solve a puzzle without GUI")
    args = parser.parse_args()
    if args.solve:
        raise NotImplementedError("TODO (A): wire Engine + Agent")
    raise NotImplementedError("TODO (E): launch GUI")


if __name__ == "__main__":
    main()
