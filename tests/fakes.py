"""Test doubles for the Agent tests, standing in for C's encoder and D's engine.

MiniEncoder  : minimal CNF encoder for the 6 core clue types (no auxiliary variables).
MiniGame     : tiny game engine that knows the hidden solution.
These live in tests/ only; the real ones are C's `logic/` and D's `engine/`.
"""
from itertools import combinations
from string import ascii_uppercase

from griductive.agent.grid import row_major_cells
from griductive.agent.protocols import PublicCard, VerdictResponse


class MiniEncoder:
    def __init__(self, size):
        self.size = size
        self.cells = row_major_cells(size)
        self._var = {c: i + 1 for i, c in enumerate(self.cells)}

    def var_of(self, cell):
        return self._var[cell]

    def region_cells(self, region):
        kind = region["kind"]
        if kind == "ROW":
            return [c for c in self.cells if int(c[1:]) == region["index"]]
        if kind == "COL":
            return [c for c in self.cells if c[0] == region["index"]]
        if kind == "NEIGHBORS":
            col, row = ascii_uppercase.index(region["of"][0]), int(region["of"][1:])
            out = []
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    c, r = col + dc, row + dr
                    if (dc, dr) != (0, 0) and 0 <= c < self.size and 1 <= r <= self.size:
                        out.append(f"{ascii_uppercase[c]}{r}")
            return sorted(out, key=self.cells.index)
        if kind == "CELLS":
            return list(region["cells"])
        raise ValueError(f"unknown region kind {kind!r}")

    def encode_clue(self, clue):
        t, v = clue["type"], self.var_of
        if t == "FACT":
            return [[v(clue["cell"]) if clue["status"] == "CRIMINAL" else -v(clue["cell"])]]
        if t == "SAME":
            a, b = v(clue["a"]), v(clue["b"])
            return [[-a, b], [a, -b]]
        if t == "DIFFERENT":
            a, b = v(clue["a"]), v(clue["b"])
            return [[a, b], [-a, -b]]
        if t in ("EXACTLY", "AT_LEAST", "AT_MOST"):
            vs = [v(c) for c in self.region_cells(clue["region"])]
            k, m = clue["k"], len(vs)
            if not 0 <= k <= m:
                raise ValueError("k out of range")
            clauses = []
            if t in ("EXACTLY", "AT_MOST"):      # no k+1 criminals
                clauses += [[-x for x in s] for s in combinations(vs, k + 1)]
            if t in ("EXACTLY", "AT_LEAST"):     # no m-k+1 innocents
                clauses += [[x for x in s] for s in combinations(vs, m - k + 1)]
            return clauses
        raise ValueError(f"unknown clue type {t!r}")

    def evaluate(self, clue, status_of):
        """Direct semantic evaluator. status_of: {cell: 'CRIMINAL'|'INNOCENT'}."""
        t = clue["type"]
        crim = lambda c: status_of[c] == "CRIMINAL"
        if t == "FACT":
            return status_of[clue["cell"]] == clue["status"]
        if t == "SAME":
            return crim(clue["a"]) == crim(clue["b"])
        if t == "DIFFERENT":
            return crim(clue["a"]) != crim(clue["b"])
        n = sum(crim(c) for c in self.region_cells(clue["region"]))
        return {"EXACTLY": n == clue["k"], "AT_LEAST": n >= clue["k"], "AT_MOST": n <= clue["k"]}[t]


class MiniGame:
    """puzzle = {"size", "solution": {cell: status}, "clues": {cell: clue}, "initial": [cells]}"""

    def __init__(self, puzzle):
        self.size = puzzle["size"]
        self._solution = dict(puzzle["solution"])
        self._clues = dict(puzzle["clues"])
        self._initial = list(puzzle["initial"])
        self.revealed = set(self._initial)
        self.submissions = []

    def public_cards(self):
        return [PublicCard(c, self._solution[c], self._clues[c]) for c in self._initial]

    def submit_verdict(self, cell, status):
        self.submissions.append((cell, status))
        if cell in self.revealed:
            return VerdictResponse("ALREADY_REVEALED")
        if status != self._solution[cell]:
            return VerdictResponse("CONTRADICTED")
        self.revealed.add(cell)
        return VerdictResponse("ACCEPTED", self._clues[cell])


# Puzzles found by a seeded search (unique solution, fully solvable by the Agent).
PUZZLE_3X3 = {
    "size": 3,
    "initial": ["C1", "C2"],
    "solution": {
        "A1": "INNOCENT",
        "B1": "INNOCENT",
        "C1": "INNOCENT",
        "A2": "CRIMINAL",
        "B2": "INNOCENT",
        "C2": "CRIMINAL",
        "A3": "INNOCENT",
        "B3": "INNOCENT",
        "C3": "INNOCENT",
    },
    "clues": {
        "A1": {"type": "AT_LEAST", "k": 0, "region": {"kind": "CELLS", "cells": ["A1", "A2", "B2", "C2"]}, "id": "c01"},
        "B1": {"type": "EXACTLY", "k": 1, "region": {"kind": "NEIGHBORS", "of": "C1"}, "id": "c02"},
        "C1": {"type": "DIFFERENT", "a": "A2", "b": "A1", "id": "c03"},
        "A2": {"type": "EXACTLY", "k": 0, "region": {"kind": "COL", "index": "B"}, "id": "c04"},
        "B2": {"type": "EXACTLY", "k": 1, "region": {"kind": "NEIGHBORS", "of": "A3"}, "id": "c05"},
        "C2": {"type": "AT_MOST", "k": 0, "region": {"kind": "ROW", "index": 1}, "id": "c06"},
        "A3": {"type": "AT_MOST", "k": 3, "region": {"kind": "COL", "index": "B"}, "id": "c07"},
        "B3": {"type": "EXACTLY", "k": 0, "region": {"kind": "ROW", "index": 3}, "id": "c08"},
        "C3": {"type": "EXACTLY", "k": 1, "region": {"kind": "COL", "index": "C"}, "id": "c09"},
    },
}

PUZZLE_4X4 = {
    "size": 4,
    "initial": ["C2", "D2", "C4"],
    "solution": {
        "A1": "CRIMINAL",
        "B1": "CRIMINAL",
        "C1": "INNOCENT",
        "D1": "INNOCENT",
        "A2": "INNOCENT",
        "B2": "CRIMINAL",
        "C2": "INNOCENT",
        "D2": "INNOCENT",
        "A3": "CRIMINAL",
        "B3": "INNOCENT",
        "C3": "INNOCENT",
        "D3": "CRIMINAL",
        "A4": "INNOCENT",
        "B4": "CRIMINAL",
        "C4": "INNOCENT",
        "D4": "CRIMINAL",
    },
    "clues": {
        "A1": {"type": "EXACTLY", "k": 2, "region": {"kind": "NEIGHBORS", "of": "B1"}, "id": "c01"},
        "B1": {"type": "EXACTLY", "k": 3, "region": {"kind": "COL", "index": "B"}, "id": "c02"},
        "C1": {"type": "DIFFERENT", "a": "D1", "b": "A3", "id": "c03"},
        "D1": {"type": "AT_LEAST", "k": 0, "region": {"kind": "COL", "index": "C"}, "id": "c04"},
        "A2": {"type": "AT_MOST", "k": 3, "region": {"kind": "ROW", "index": 4}, "id": "c05"},
        "B2": {"type": "AT_MOST", "k": 4, "region": {"kind": "ROW", "index": 2}, "id": "c06"},
        "C2": {"type": "EXACTLY", "k": 2, "region": {"kind": "CELLS", "cells": ["B1", "D4"]}, "id": "c07"},
        "D2": {"type": "AT_LEAST", "k": 2, "region": {"kind": "ROW", "index": 4}, "id": "c08"},
        "A3": {"type": "EXACTLY", "k": 1, "region": {"kind": "NEIGHBORS", "of": "D4"}, "id": "c09"},
        "B3": {"type": "EXACTLY", "k": 2, "region": {"kind": "COL", "index": "A"}, "id": "c10"},
        "C3": {"type": "EXACTLY", "k": 2, "region": {"kind": "COL", "index": "D"}, "id": "c11"},
        "D3": {"type": "AT_LEAST", "k": 2, "region": {"kind": "COL", "index": "B"}, "id": "c12"},
        "A4": {"type": "EXACTLY", "k": 2, "region": {"kind": "ROW", "index": 3}, "id": "c13"},
        "B4": {"type": "AT_MOST", "k": 2, "region": {"kind": "COL", "index": "D"}, "id": "c14"},
        "C4": {"type": "EXACTLY", "k": 3, "region": {"kind": "CELLS", "cells": ["A1", "B1", "D3"]}, "id": "c15"},
        "D4": {"type": "EXACTLY", "k": 3, "region": {"kind": "CELLS", "cells": ["B2", "C2", "B4", "D4"]}, "id": "c16"},
    },
}

def all_models(clauses, nvars):
    """Every satisfying assignment over variables 1..nvars (brute force oracle)."""
    def holds(m, lit):
        return m[abs(lit) - 1] if lit > 0 else not m[abs(lit) - 1]
    from itertools import product
    return [m for m in product([False, True], repeat=nvars)
            if all(any(holds(m, l) for l in c) for c in clauses)]
