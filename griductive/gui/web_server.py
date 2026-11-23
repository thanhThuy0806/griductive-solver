"""FastAPI web backend for Griductive GUI."""
from __future__ import annotations

import glob
import inspect
import os
import re
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from griductive.agent.logic_agent import RunStatus
from griductive.engine.agent_api import AgentAPI
from griductive.engine.game_engine import GameEngine
from griductive.engine.puzzle_loader import load_puzzle

# ---------------------------------------------------------------------------
# Paths & App setup
# ---------------------------------------------------------------------------
PUZZLES_DIR = Path("puzzles")
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Griductive Solver Web UI")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _enum_val(v: Any) -> Any:
    return v.value if hasattr(v, "value") else v


def _infer_difficulty(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("difficulty"):
            return str(data["difficulty"]).lower()
        size = data.get("size", 3)
        types = {ch.get("clue", {}).get("type", "") for ch in data.get("characters", [])}
        if size <= 3 and types <= {"FACT"}:
            return "easy"
        if size <= 3:
            return "medium" if (types & {"PARITY", "COMPARE"}) else "easy"
        if size == 4:
            return "hard"
        return "expert"
    except Exception:
        return "medium"

def _discover_puzzles() -> list[dict[str, str]]:
    """Quét toàn bộ file .json trong thư mục puzzles/ và gom nhóm theo thư mục con."""
    if not PUZZLES_DIR.is_dir():
        return []
    files = sorted(glob.glob(str(PUZZLES_DIR / "**" / "*.json"), recursive=True))
    result = []
    for idx, f in enumerate(files, start=1):
        rel = os.path.relpath(f, PUZZLES_DIR).replace("\\", "/")
        parts = rel.split("/")
        group = parts[0] if len(parts) > 1 else "default"
        result.append({
            "id": rel,
            "name": f"Màn {idx:02d}",
            "group": group,
            "path": os.path.normpath(f),
            "difficulty": _infer_difficulty(f),
        })
    return result


def _cell_to_rc(cell: str) -> tuple[int, int]:
    return int(cell[1:]) - 1, ord(cell[0].upper()) - ord("A")


def _rc_to_cell(r: int, c: int) -> str:
    return f"{chr(ord('A') + c)}{r + 1}"


def _fmt_region_label(region: Any) -> str:
    if region is None:
        return ""
    if isinstance(region, str):
        return region.replace("_", " ")
    if isinstance(region, dict):
        return str(region.get("label") or region.get("name") or region.get("type") or region)
    for attr in ("label", "name", "description"):
        val = getattr(region, attr, None)
        if isinstance(val, str) and val.strip():
            return val

    kind = _enum_val(getattr(region, "kind", None) or getattr(region, "type", None))
    index = _enum_val(getattr(region, "index", None))
    of = _enum_val(getattr(region, "of", None))
    cells = getattr(region, "cells", None)
    val = _enum_val(getattr(region, "value", None) or getattr(region, "target", None))

    if kind is not None:
        k_str = str(kind).upper()
        if k_str == "ROW" and index is not None:
            return f"Row {index}"
        if k_str in ("COL", "COLUMN") and index is not None:
            return f"Column {index}"
        if "NEIGHBOR" in k_str or "ADJACENT" in k_str:
            target = of or index or val
            return f"neighbors of {target}" if target else "neighbors"
        if k_str in ("JOB", "PROFESSION", "ROLE"):
            target = of or index or val
            return f"all {target}s" if target else "profession"
        if k_str in ("ALL", "BOARD", "GRID"):
            return "the board"
        if k_str in ("CORNER", "CORNERS"):
            return "the corners"
        if k_str in ("EDGE", "EDGES", "BORDER"):
            return "the edges"
        if cells:
            return ", ".join(str(c) for c in cells)
        extra = index if index is not None else (of if of is not None else val)
        if extra is not None:
            return f"{k_str.replace('_', ' ').title()} {extra}"
        return k_str.replace("_", " ").title()

    if cells:
        return ", ".join(str(c) for c in cells)
    return str(region)


def _format_clue_text(clue: Any, char_map: dict[str, dict[str, Any]] | None = None) -> str | None:
    """Chuyển đối tượng Clue (str hoặc dataclass) thành câu manh mối ngắn gọn, dễ đọc."""
    if clue is None:
        return None
    if isinstance(clue, str):
        return clue.strip()

    # 1. Nếu object đã có sẵn thuộc tính text/description
    for attr in ("text", "description", "statement", "message"):
        val = getattr(clue, attr, None)
        if isinstance(val, str) and val.strip():
            return val.strip()

    # 2. Format từ các field của dataclass Clue
    ctype = str(_enum_val(getattr(clue, "type", "")) or "").upper()
    cell = getattr(clue, "cell", None)
    status = _enum_val(getattr(clue, "status", None))
    a = getattr(clue, "a", None)
    b = getattr(clue, "b", None)
    k = getattr(clue, "k", None)
    region = getattr(clue, "region", None)
    parity = _enum_val(getattr(clue, "parity", None))
    region_a = getattr(clue, "region_a", None)
    region_b = getattr(clue, "region_b", None)
    op = _enum_val(getattr(clue, "op", None))
    params = getattr(clue, "params", None) or {}

    def fmt_cell(cid: str | None) -> str:
        return str(cid) if cid else ""

    status_str = str(status).upper() if status else ""
    reg_str = _fmt_region_label(region)
    reg_a_str = _fmt_region_label(region_a)
    reg_b_str = _fmt_region_label(region_b)

    op_map = {
        "==": "exactly", "EQ": "exactly", "EQUAL": "exactly",
        ">=": "at least", "GE": "at least", "GTE": "at least",
        "<=": "at most", "LE": "at most", "LTE": "at most",
        ">": "more than", "GT": "more than",
        "<": "fewer than", "LT": "fewer than",
        "!=": "not equal to", "NE": "not equal to",
    }
    op_word = op_map.get(str(op).upper(), str(op)) if op else ""

    target = status_str.lower() if status_str else "criminal"

    # 8 loại ClueType chuẩn trong core/types.py
    if ctype == "FACT" and cell and status_str:
        return f"{fmt_cell(cell)} is {status_str}."

    if ctype == "SAME" and a and b:
        return f"{fmt_cell(a)} and {fmt_cell(b)} have the SAME status."

    if ctype == "DIFFERENT" and a and b:
        return f"{fmt_cell(a)} and {fmt_cell(b)} have DIFFERENT statuses."

    if ctype == "EXACTLY" and k is not None and reg_str:
        return f"Exactly {k} {target}(s) in {reg_str}."

    if ctype == "AT_LEAST" and k is not None and reg_str:
        return f"At least {k} {target}(s) in {reg_str}."

    if ctype == "AT_MOST" and k is not None and reg_str:
        return f"At most {k} {target}(s) in {reg_str}."

    if ctype == "PARITY" and parity is not None and reg_str:
        return f"{reg_str} has an {str(parity).lower()} number of {target}s."

    if ctype == "COMPARE" and reg_a_str and reg_b_str:
        cmp_str = op_word or str(op or "vs")
        return f"{reg_a_str} has {cmp_str} {target}s than {reg_b_str}."

    # 3. Fallback gọn gàng: chỉ hiển thị các field khác None
    parts = []
    if ctype:
        parts.append(ctype)
    for key, val in [
        ("cell", fmt_cell(cell) if cell else None),
        ("status", status_str or None),
        ("a", fmt_cell(a) if a else None),
        ("b", fmt_cell(b) if b else None),
        ("op", op),
        ("k", k),
        ("region", reg_str or None),
        ("parity", parity),
        ("region_a", reg_a_str or None),
        ("region_b", reg_b_str or None),
    ]:
        if val is not None and val != "":
            parts.append(f"{key}: {val}")
    if params:
        parts.append(", ".join(f"{pk}={pv}" for pk, pv in params.items()))
    return " · ".join(parts) if parts else str(clue)


def _cells_from_region(
    region: Any,
    owner_cell: str,
    characters: list[dict[str, Any]],
    size: int,
) -> set[str]:
    """Trích xuất tập ô từ một đối tượng hoặc chuỗi region."""
    valid_cells = {ch["cell"].upper() for ch in characters}
    found: set[str] = set()
    if region is None:
        return found

    # Nếu region là list/set ô
    if isinstance(region, (list, tuple, set)):
        for item in region:
            cid = str(item).upper()
            if cid in valid_cells:
                found.add(cid)
        return found

    # 1. Đọc trực tiếp từ các trường cấu trúc của Region dataclass (kind, index, of, cells)
    if hasattr(region, "cells") and getattr(region, "cells"):
        for item in getattr(region, "cells"):
            cid = str(item).upper()
            if cid in valid_cells:
                found.add(cid)
        if found:
            return found

    kind = _enum_val(getattr(region, "kind", None) or getattr(region, "type", None))
    index = _enum_val(getattr(region, "index", None))
    of = _enum_val(getattr(region, "of", None))
    if kind is not None:
        k_str = str(kind).upper()
        if k_str == "ROW" and index is not None:
            r_idx = int(index) - 1
            if 0 <= r_idx < size:
                return {_rc_to_cell(r_idx, c_idx) for c_idx in range(size)}
        if k_str in ("COL", "COLUMN") and index is not None:
            c_idx = (ord(str(index).upper()) - ord("A")) if isinstance(index, str) and index.isalpha() else int(index) - 1
            if 0 <= c_idx < size:
                return {_rc_to_cell(r_idx, c_idx) for r_idx in range(size)}
        if "NEIGHBOR" in k_str or "ADJACENT" in k_str:
            center = str(of or index or owner_cell).upper()
            if center in valid_cells:
                orow, ocol = _cell_to_rc(center)
                is_ortho = "ORTHO" in k_str or "DIRECT" in k_str
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        if is_ortho and abs(dr) + abs(dc) != 1:
                            continue
                        nr, nc = orow + dr, ocol + dc
                        if 0 <= nr < size and 0 <= nc < size:
                            found.add(_rc_to_cell(nr, nc))
                return found
        if k_str in ("JOB", "PROFESSION", "ROLE"):
            target_job = str(of or index or "").lower()
            return {ch["cell"] for ch in characters if ch["job"].lower() == target_job}
        if k_str in ("ALL", "BOARD", "GRID"):
            return set(valid_cells)
        if k_str in ("CORNER", "CORNERS"):
            return {_rc_to_cell(r, c) for r in (0, size - 1) for c in (0, size - 1)}
        if k_str in ("EDGE", "EDGES", "BORDER"):
            return {
                _rc_to_cell(r, c)
                for r in range(size) for c in range(size)
                if r in (0, size - 1) or c in (0, size - 1)
            }

    text = _fmt_region_label(region).lower()

    # Tọa độ ô cụ thể
    for m in re.findall(r"\b([a-z][1-9])\b", text):
        cid = m.upper()
        if cid in valid_cells:
            found.add(cid)

    # Hàng
    for m in re.findall(r"\brow\s*[_-]?\s*(\d+)\b", text):
        r_idx = int(m) - 1
        if 0 <= r_idx < size:
            for c_idx in range(size):
                found.add(_rc_to_cell(r_idx, c_idx))

    # Cột
    for m in re.findall(r"\bcol(?:umn)?\s*[_-]?\s*([a-z])\b", text):
        c_idx = ord(m.upper()) - ord("A")
        if 0 <= c_idx < size:
            for r_idx in range(size):
                found.add(_rc_to_cell(r_idx, c_idx))

    # Hàng xóm
    if any(k in text for k in ("neighbor", "neighbour", "adjacent")):
        orow, ocol = _cell_to_rc(owner_cell)
        is_ortho = "ortho" in text or "direct" in text
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                if is_ortho and abs(dr) + abs(dc) != 1:
                    continue
                nr, nc = orow + dr, ocol + dc
                if 0 <= nr < size and 0 <= nc < size:
                    found.add(_rc_to_cell(nr, nc))

    # Toàn bộ bàn cờ / góc / viền
    if text.strip() in ("all", "board", "grid"):
        found.update(valid_cells)
    elif "corner" in text:
        for r_idx in (0, size - 1):
            for c_idx in (0, size - 1):
                found.add(_rc_to_cell(r_idx, c_idx))
    elif "edge" in text or "border" in text:
        for r_idx in range(size):
            for c_idx in range(size):
                if r_idx in (0, size - 1) or c_idx in (0, size - 1):
                    found.add(_rc_to_cell(r_idx, c_idx))

    # Nghề nghiệp hoặc tên
    for ch in characters:
        job = ch["job"].lower()
        name = ch["name"].lower()
        if job and re.search(rf"\b{re.escape(job)}s?\b", text):
            found.add(ch["cell"])
        if name and re.search(rf"\b{re.escape(name)}\b", text):
            found.add(ch["cell"])

    return found


def _resolve_referenced_cells(
    owner_cell: str,
    clue_obj: Any,
    clue_text: str | None,
    characters: list[dict[str, Any]],
    size: int,
) -> list[str]:
    """Xác định các ô được tham chiếu/đếm bởi một clue để highlight trên bàn cờ."""
    valid_cells = {ch["cell"].upper() for ch in characters}
    found: set[str] = set()

    if clue_obj is not None and not isinstance(clue_obj, str):
        for attr in ("referenced_cells", "target_cells", "scope_cells", "cells"):
            vals = getattr(clue_obj, attr, None)
            if vals:
                for x in vals:
                    cid = str(x).upper()
                    if cid in valid_cells:
                        found.add(cid)

        for attr in ("cell", "a", "b"):
            val = getattr(clue_obj, attr, None)
            if isinstance(val, str) and val.upper() in valid_cells:
                found.add(val.upper())

        for attr in ("region", "region_a", "region_b"):
            reg = getattr(clue_obj, attr, None)
            if reg is not None:
                found.update(_cells_from_region(reg, owner_cell, characters, size))

        params = getattr(clue_obj, "params", None)
        if isinstance(params, dict):
            for pv in params.values():
                if isinstance(pv, str) and pv.upper() in valid_cells:
                    found.add(pv.upper())
                else:
                    found.update(_cells_from_region(pv, owner_cell, characters, size))

    if not found and clue_text:
        found.update(_cells_from_region(clue_text, owner_cell, characters, size))

    return sorted(found)


# ---------------------------------------------------------------------------
# Game Session Manager
# ---------------------------------------------------------------------------
class GameSession:
    def __init__(self) -> None:
        self.puzzle_id: str | None = None
        self.puzzle_path: str | None = None
        self.engine: GameEngine | None = None
        self.api: AgentAPI | None = None
        self.agent: Any = None
        self.clue_cache: dict[str, Any] = {}
        self.status_enum: Any = None

    def load(self, puzzle_id: str) -> dict[str, Any]:
        puzzles = {p["id"]: p for p in _discover_puzzles()}
        if puzzle_id not in puzzles:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy màn chơi: {puzzle_id}")
        path = puzzles[puzzle_id]["path"]

        puzzle = load_puzzle(path)
        self.puzzle_id = puzzle_id
        self.puzzle_path = path
        self.engine = GameEngine(puzzle)
        self.api = AgentAPI(self.engine)
        self.agent = self.api.create_agent()
        self.clue_cache = {}
        self._detect_status_enum()
        return self.get_state()

    def restart(self) -> dict[str, Any]:
        self._ensure_loaded()
        self.engine.restart()
        self.api = AgentAPI(self.engine)
        self.agent = self.api.create_agent()
        self.clue_cache = {}
        return self.get_state()

    def _ensure_loaded(self) -> None:
        if self.engine is None or self.api is None or self.agent is None:
            raise HTTPException(status_code=400, detail="Chưa có màn chơi nào được tải.")

    def _detect_status_enum(self) -> None:
        pub = self.engine.get_public_state()
        for c in pub.characters:
            if c.status is not None and hasattr(c.status, "value"):
                self.status_enum = type(c.status)
                return
        sig = inspect.signature(self.api.submit_verdict)
        verdict_param = list(sig.parameters.values())[1]
        if hasattr(verdict_param.annotation, "__members__"):
            self.status_enum = verdict_param.annotation

    def _coerce_verdict(self, verdict_str: str) -> Any:
        v = verdict_str.upper()
        if self.status_enum is not None:
            try:
                return self.status_enum(v)
            except ValueError:
                return self.status_enum[v]
        return v

    def submit_verdict(self, cell: str, verdict_str: str) -> dict[str, Any]:
        self._ensure_loaded()
        verdict = self._coerce_verdict(verdict_str)
        response = self.api.submit_verdict(cell, verdict)
        result = str(_enum_val(response.result)).upper()

        clue_obj = getattr(response, "clue", None)
        if result == "ACCEPTED":
            self.agent.observe(cell, verdict, clue_obj)
            if clue_obj is not None:
                self.clue_cache[cell] = clue_obj

        state = self.get_state()
        char_map = {ch["cell"]: ch for ch in state["characters"]}
        return {
            "cell": cell,
            "verdict": verdict_str.upper(),
            "result": result,
            "message": getattr(response, "message", "") or "",
            "clue": _format_clue_text(clue_obj, char_map) if result == "ACCEPTED" else None,
            "state": state,
        }

    def get_hint(self) -> dict[str, Any]:
        self._ensure_loaded()
        hint = self.agent.hint()
        if hint is None:
            return {"available": False, "message": "Không còn gợi ý (đã giải xong hoặc bị kẹt)."}

        verdict = _enum_val(getattr(hint, "verdict", None))
        return {
            "available": True,
            "cell": hint.cell,
            "verdict": str(verdict).upper() if verdict else None,
            "message": getattr(hint, "message", f"Có thể suy luận ô {hint.cell}."),
        }

    def step_auto(self) -> dict[str, Any]:
        self._ensure_loaded()
        outcome = self.agent.step(self.api)

        trace = getattr(self.agent, "trace", None)
        if trace and getattr(trace, "steps", None):
            last = trace.steps[-1]
            if getattr(last, "clue", None) and getattr(last, "cell", None):
                self.clue_cache[last.cell] = last.clue

        status = "RUNNING"
        if outcome is RunStatus.SOLVED:
            status = "SOLVED"
        elif outcome is RunStatus.STUCK:
            status = "STUCK"
        elif outcome is RunStatus.INCONSISTENT:
            status = "INCONSISTENT"
        elif outcome is not None:
            status = str(_enum_val(outcome))

        return {"outcome": status, "state": self.get_state()}

    def get_state(self) -> dict[str, Any]:
        self._ensure_loaded()
        pub = self.engine.get_public_state()

        pub_clues: dict[str, Any] = {}
        raw_clues = getattr(pub, "clues", None) or getattr(pub, "revealed_clues", None)
        if isinstance(raw_clues, dict):
            pub_clues.update(raw_clues)
        elif isinstance(raw_clues, list):
            for cl in raw_clues:
                owner = getattr(cl, "cell", None) or getattr(cl, "speaker", None)
                if owner:
                    pub_clues[owner] = cl

        raw_chars = [
            {
                "cell": c.cell,
                "name": c.name,
                "job": c.job,
                "status": str(_enum_val(c.status)).upper() if (c.revealed and c.status) else None,
                "revealed": bool(c.revealed),
            }
            for c in pub.characters
        ]
        char_map = {ch["cell"]: ch for ch in raw_chars}

        clues_list = []
        for ch, c_obj in zip(raw_chars, pub.characters):
            if ch["revealed"]:
                clue_obj = (
                    getattr(c_obj, "clue", None)
                    or pub_clues.get(ch["cell"])
                    or self.clue_cache.get(ch["cell"])
                )
                clue_text = _format_clue_text(clue_obj, char_map)
                ref_cells = _resolve_referenced_cells(
                    ch["cell"], clue_obj, clue_text, raw_chars, pub.size
                )
                ch["clue"] = clue_text
                ch["referenced_cells"] = ref_cells
                if clue_text:
                    clues_list.append({
                        "cell": ch["cell"],
                        "name": ch["name"],
                        "text": clue_text,
                        "referenced_cells": ref_cells,
                    })
            else:
                ch["clue"] = None
                ch["referenced_cells"] = []

        trace_steps = []
        trace = getattr(self.agent, "trace", None)
        if trace and getattr(trace, "steps", None):
            for idx, s in enumerate(trace.steps, start=1):
                trace_steps.append({
                    "step": getattr(s, "step", idx),
                    "cell": getattr(s, "cell", ""),
                    "verdict": str(_enum_val(getattr(s, "verdict", ""))),
                    "result": str(_enum_val(getattr(s, "result", ""))),
                    "clue": _format_clue_text(getattr(s, "clue", None), char_map),
                })

        return {
            "puzzle_id": self.puzzle_id,
            "size": pub.size,
            "is_solved": bool(self.engine.is_solved),
            "characters": raw_chars,
            "clues": clues_list,
            "trace": trace_steps,
        }


session = GameSession()


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
class LoadRequest(BaseModel):
    puzzle_id: str


class VerdictRequest(BaseModel):
    cell: str
    verdict: str


@app.get("/")
def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/puzzles")
def list_puzzles():
    return {"puzzles": _discover_puzzles()}


@app.post("/api/load")
def api_load(req: LoadRequest):
    return session.load(req.puzzle_id)


@app.post("/api/restart")
def api_restart():
    return session.restart()


@app.post("/api/verdict")
def api_verdict(req: VerdictRequest):
    return session.submit_verdict(req.cell, req.verdict)


@app.post("/api/hint")
def api_hint():
    return session.get_hint()


@app.post("/api/step")
def api_step():
    return session.step_auto()


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    import threading
    import webbrowser
    import uvicorn

    threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
