"""Loader contract tests; runnable with unittest or pytest."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from griductive.core.constants import ClueType, RegionKind, Status
from griductive.core.regions import resolve_region
from griductive.core.types import Region
from griductive.engine.puzzle_loader import load_puzzle, parse_puzzle


SAMPLE = Path(__file__).resolve().parents[1] / "puzzles" / "3x3" / "p3x3_01.json"


class PuzzleLoaderTests(unittest.TestCase):
    """Exercise public loader behavior without an encoder or solver."""

    def setUp(self) -> None:
        """Read a fresh source dictionary for each test."""
        self.data = json.loads(SAMPLE.read_text(encoding="utf-8"))

    def test_sample_and_private_data_are_preserved(self) -> None:
        puzzle = load_puzzle(SAMPLE)
        self.assertEqual(puzzle.size, 3)
        self.assertEqual(len(puzzle.characters), 9)
        for raw, cell in zip(self.data["characters"], puzzle.characters):
            expected = tuple(raw[key] for key in ("cell", "name", "job", "status", "revealed"))
            self.assertEqual((cell.cell, cell.name, cell.job, cell.status.value, cell.revealed),
                             expected)
            self.assertEqual(cell.clue.id, raw["clue"]["id"])
            self.assertEqual(cell.clue.cell, raw["clue"]["cell"])
            self.assertEqual(cell.clue.status.value, raw["clue"]["status"])
        self.assertIs(puzzle.characters[0].status, Status.INNOCENT)
        self.assertIs(puzzle.characters[0].clue.type, ClueType.FACT)
        self.assertIsInstance(puzzle.characters, list)

    def test_input_is_not_mutated_and_output_is_row_major(self) -> None:
        self.data["characters"].reverse()
        before = copy.deepcopy(self.data)
        puzzle = parse_puzzle(self.data)
        self.assertEqual([cell.cell for cell in puzzle.characters],
                         [f"{col}{row}" for row in range(1, 4) for col in "ABC"])
        self.assertEqual(self.data, before)
        self.data["characters"][0]["clue"]["status"] = "CRIMINAL"
        self.assertIs(puzzle.characters[-1].clue.status, Status.INNOCENT)

    def test_larger_boards(self) -> None:
        for size in (4, 5):
            with self.subTest(size=size):
                characters = []
                for row in range(1, size + 1):
                    for col in range(size):
                        cell = copy.deepcopy(self.data["characters"][0])
                        cell["cell"] = f"{chr(65 + col)}{row}"
                        cell["clue"]["id"] = f"c{len(characters) + 1:02}"
                        characters.append(cell)
                puzzle = parse_puzzle({"size": size, "characters": characters})
                self.assertEqual(len(puzzle.characters), size * size)

    def test_all_core_clue_types(self) -> None:
        clues = [
            {"type": "FACT", "cell": "C3", "status": "INNOCENT"},
            {"type": "SAME", "a": "A1", "b": "B2"},
            {"type": "DIFFERENT", "a": "A1", "b": "B2"},
            *({"type": kind, "k": 1, "region": {"kind": "ROW", "index": 2}}
              for kind in ("EXACTLY", "AT_LEAST", "AT_MOST")),
        ]
        for clue in clues:
            with self.subTest(clue=clue):
                self.data["characters"][0]["clue"] = {"id": "c01", **clue}
                parsed = parse_puzzle(self.data).characters[0].clue
                self.assertEqual(parsed.type.value, clue["type"])
                for field in ("cell", "a", "b", "k"):
                    if field in clue:
                        self.assertEqual(getattr(parsed, field), clue[field])

    def test_count_boundaries_and_all_region_forms(self) -> None:
        regions = [({"kind": "ROW", "index": 2}, 3),
                   ({"kind": "COL", "index": "B"}, 3),
                   ({"kind": "NEIGHBORS", "of": "B2"}, 8),
                   ({"kind": "CELLS", "cells": ["C3", "A1"]}, 2)]
        for region, count in regions:
            for kind in ("EXACTLY", "AT_LEAST", "AT_MOST"):
                for k in (0, count):
                    with self.subTest(region=region, kind=kind, k=k):
                        self.data["characters"][0]["clue"] = {
                            "id": "c01", "type": kind, "k": k, "region": region}
                        parsed = parse_puzzle(self.data).characters[0].clue
                        self.assertEqual(len(resolve_region(parsed.region, 3)), count)

    def test_reject_invalid_puzzle_fields(self) -> None:
        cases = [([], "puzzle"), ({}, "missing"),
                 ({**self.data, "extra": 1}, "unexpected")]
        cases += [({**self.data, "size": size}, "size")
                  for size in (True, 3.0, "3", 0, 2, 6, None)]
        cases += [({**self.data, "characters": chars}, "characters")
                  for chars in (None, {}, [], self.data["characters"][:-1])]
        for data, error in cases:
            with self.subTest(data=data):
                with self.assertRaisesRegex(ValueError, error):
                    parse_puzzle(data)

    def test_reject_invalid_character_fields(self) -> None:
        cases = [("cell", "Z9", "cell"), ("cell", "a1", "cell"),
                 ("cell", "B1", "duplicate cell"), ("cell", [], "cell"),
                 ("name", "  ", "name"), ("job", 123, "job"),
                 ("status", "UNKNOWN", "status"), ("status", [], "status"),
                 ("revealed", 1, "revealed"), ("revealed", "false", "revealed"),
                 ("clue", None, "clue")]
        for field, value, error in cases:
            with self.subTest(field=field, value=value):
                data = copy.deepcopy(self.data)
                data["characters"][0][field] = value
                with self.assertRaisesRegex(ValueError, rf"characters\[\d+\].*{error}"):
                    parse_puzzle(data)
        for field in ("name", "revealed", "clue"):
            data = copy.deepcopy(self.data)
            del data["characters"][0][field]
            with self.assertRaisesRegex(ValueError, "missing"):
                parse_puzzle(data)
        self.data["characters"][0]["extra"] = True
        with self.assertRaisesRegex(ValueError, "unexpected"):
            parse_puzzle(self.data)

    def test_reject_invalid_clues(self) -> None:
        cases = [{"id": "c01", "type": "PARITY"},
                 {"id": "", "type": "FACT", "cell": "A1", "status": "INNOCENT"},
                 {"id": "c02", "type": "FACT", "cell": "A1", "status": "INNOCENT"},
                 {"id": "c01", "type": "FACT", "cell": "Z9", "status": "INNOCENT"},
                 {"id": "c01", "type": "FACT", "cell": "A1", "status": "UNKNOWN"},
                 {"id": "c01", "type": "SAME", "a": "A1"},
                 {"id": "c01", "type": "SAME", "a": "A1", "b": "A1"},
                 {"id": "c01", "type": "DIFFERENT", "a": "A1", "b": "A1"},
                 {"id": "c01", "type": "DIFFERENT", "a": "Z9", "b": "B1"},
                 {**self.data["characters"][0]["clue"], "k": 1}]
        for clue in cases:
            with self.subTest(clue=clue):
                self.data["characters"][0]["clue"] = clue
                with self.assertRaisesRegex(ValueError, r"characters\[\d+\].clue"):
                    parse_puzzle(self.data)

    def test_reject_invalid_regions_and_counts(self) -> None:
        regions = [None, {}, {"kind": "OTHER"}, {"kind": "ROW", "index": True},
                   {"kind": "ROW", "index": 0}, {"kind": "ROW", "index": 4},
                   {"kind": "ROW", "index": "1"}, {"kind": "COL", "index": "D"},
                   {"kind": "COL", "index": "b"}, {"kind": "NEIGHBORS", "of": "Z9"},
                   {"kind": "CELLS", "cells": "A1"},
                   {"kind": "CELLS", "cells": []},
                   {"kind": "CELLS", "cells": ["A1", "A1"]},
                   {"kind": "CELLS", "cells": [["A1"]]},
                   {"kind": "CELLS", "cells": ["Z9"]},
                   {"kind": "ROW", "index": 1, "of": "A1"}]
        for region in regions:
            with self.subTest(region=region):
                self.data["characters"][0]["clue"] = {
                    "id": "c01", "type": "EXACTLY", "k": 0, "region": region}
                with self.assertRaisesRegex(ValueError, "clue.region"):
                    parse_puzzle(self.data)
        for k in (-1, 4, True, 1.0, "1", None):
            self.data["characters"][0]["clue"] = {
                "id": "c01", "type": "EXACTLY", "k": k,
                "region": {"kind": "ROW", "index": 1}}
            with self.subTest(k=k), self.assertRaisesRegex(ValueError, "clue.k"):
                parse_puzzle(self.data)

    def test_requires_an_initially_revealed_card(self) -> None:
        for cell in self.data["characters"]:
            cell["revealed"] = False
        with self.assertRaisesRegex(ValueError, "at least one"):
            parse_puzzle(self.data)

    def test_files_utf8_bom_and_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "puzzle.json"
            with self.assertRaises(FileNotFoundError):
                load_puzzle(path)
            with self.assertRaises(OSError):
                load_puzzle(directory)
            self.data["characters"][0]["name"] = "Kiệt"
            path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8-sig")
            self.assertEqual(load_puzzle(path).characters[0].name, "Kiệt")
            path.write_text('{"size":', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid JSON at line"):
                load_puzzle(path)
            path.write_bytes(b"\xff\xfe")
            with self.assertRaisesRegex(ValueError, "UTF-8"):
                load_puzzle(path)


class RegionTests(unittest.TestCase):
    """Check region geometry independently of loader parsing."""

    def test_exact_cells_and_order(self) -> None:
        self.assertEqual(resolve_region(Region(RegionKind.ROW, index=2), 3),
                         ["A2", "B2", "C2"])
        self.assertEqual(resolve_region(Region(RegionKind.COL, index="B"), 3),
                         ["B1", "B2", "B3"])
        self.assertEqual(resolve_region(Region(RegionKind.CELLS, cells=("C3", "A1")), 3),
                         ["A1", "C3"])

    def test_neighbor_geometry(self) -> None:
        expected = {"A1": ("B1", "A2", "B2"),
                    "B1": ("A1", "C1", "A2", "B2", "C2"),
                    "B2": ("A1", "B1", "C1", "A2", "C2", "A3", "B3", "C3")}
        for cell, cells in expected.items():
            with self.subTest(cell=cell):
                self.assertEqual(resolve_region(Region(RegionKind.NEIGHBORS, of=cell), 3),
                                 list(cells))

    def test_invalid_direct_regions(self) -> None:
        for region in (Region(RegionKind.ROW, index=0),
                       Region(RegionKind.COL, index="D"),
                       Region(RegionKind.NEIGHBORS, of="Z9"),
                       Region(RegionKind.CELLS), Region("UNKNOWN")):
            with self.subTest(region=region), self.assertRaises(ValueError):
                resolve_region(region, 3)


if __name__ == "__main__":
    unittest.main()
