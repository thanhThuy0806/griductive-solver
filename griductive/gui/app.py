"""Main window: connects the board, the clue panel and the buttons to the Game Engine."""
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from griductive.core.constants import Status
from griductive.engine.game_engine import GameEngine
from griductive.engine.puzzle_loader import load_puzzle
from griductive.gui.board_view import BoardView
from griductive.gui.clue_panel import CluePanel, clue_cells, clue_to_text

PUZZLE_DIR = Path(__file__).resolve().parents[2] / "puzzles"
GREEN, ORANGE, RED, BLUE = "#1E7B34", "#B35900", "#B00020", "#1B4F7C"


def list_puzzle_files() -> list[Path]:
    """All puzzle files in puzzles/<size>/ (the Load list)."""
    return sorted(PUZZLE_DIR.glob("*/*.json"))


class App:
    """Builds the window. The hidden puzzle lives only inside the GameEngine."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Griductive Solver")
        self.engine = None
        self.size = 0
        self.puzzle_files = list_puzzle_files()

        # ---- top bar: Load list + Restart / Hint / Auto Solve ----
        top = tk.Frame(root)
        top.pack(fill="x", padx=10, pady=8)
        tk.Label(top, text="Puzzle:").pack(side="left")
        self.combo = ttk.Combobox(top, state="readonly", width=24,
                                  values=[p.stem for p in self.puzzle_files])
        self.combo.pack(side="left", padx=6)
        self.combo.bind("<<ComboboxSelected>>", self._on_load)
        tk.Button(top, text="Restart", command=self._on_restart).pack(side="left", padx=4)
        tk.Button(top, text="Hint", command=lambda: self._todo("Hint")).pack(side="left", padx=4)
        tk.Button(top, text="Auto Solve", command=lambda: self._todo("Auto Solve")).pack(
            side="left", padx=4)

        # ---- middle: board (left) + clue list (right) ----
        middle = tk.Frame(root)
        middle.pack(padx=10, pady=4)
        self.board = BoardView(middle, on_click=self._on_card_click)
        self.board.pack(side="left", padx=(0, 16))
        self.clue_panel = CluePanel(middle, on_pick=self._show_clue)
        self.clue_panel.pack(side="left", fill="y")

        # ---- bottom: verdict buttons + message line ----
        bottom = tk.Frame(root)
        bottom.pack(fill="x", padx=10, pady=8)
        self.selected_label = tk.Label(bottom, text="Selected: -", width=14, anchor="w")
        self.selected_label.pack(side="left")
        self.criminal_btn = tk.Button(bottom, text="CRIMINAL",
                                      command=lambda: self._on_verdict(Status.CRIMINAL))
        self.innocent_btn = tk.Button(bottom, text="INNOCENT",
                                      command=lambda: self._on_verdict(Status.INNOCENT))
        self.criminal_btn.pack(side="left", padx=4)
        self.innocent_btn.pack(side="left", padx=4)
        self.message = tk.Label(root, text="", anchor="w", relief="sunken")
        self.message.pack(fill="x", padx=10, pady=(0, 10))

        if self.puzzle_files:
            self.combo.current(0)
            self._load(self.puzzle_files[0])
        else:
            self._say("No puzzle file found in puzzles/.", RED)

    # ---------------- loading ----------------
    def _load(self, path: Path) -> None:
        try:
            engine = GameEngine(load_puzzle(path))  # the hidden puzzle stays inside the engine
        except Exception as exc:  # show the problem instead of crashing the app
            messagebox.showerror("Cannot load puzzle", f"{path.name}\n\n{exc}")
            return
        self.engine = engine
        self._show_state(engine.get_public_state())
        self._say(f"Loaded {path.name}. Select a face-down card, then call a verdict.", BLUE)

    def _show_state(self, state) -> None:
        """Redraw everything from a public snapshot (load and restart)."""
        self.size = state.size
        self.board.load_state(state)
        self.clue_panel.set_clues(
            [(pc.cell, pc.clue) for pc in state.characters if pc.revealed and pc.clue is not None])
        self.selected_label.config(text="Selected: -")
        self._set_verdict_buttons(not self.engine.is_solved)

    def _on_load(self, _event=None) -> None:
        self._load(self.puzzle_files[self.combo.current()])

    def _on_restart(self) -> None:
        if self.engine is not None:
            self._show_state(self.engine.restart())
            self._say("Restarted. Only the starting cards are face-up.", BLUE)

    # ---------------- interaction ----------------
    def _on_card_click(self, cell: str) -> None:
        if self.board.cards[cell].is_face_up:  # face-up card: show its clue
            clue = self.clue_panel.select_owner(cell)
            if clue is not None:
                self._show_clue(cell, clue)
            return
        self.board.select_cell(cell)  # face-down card: choose it for a verdict
        self.selected_label.config(text=f"Selected: {cell}")

    def _show_clue(self, owner: str, clue) -> None:
        """Highlight the cells a clue refers to and describe the clue."""
        cells = clue_cells(clue, self.size)
        self.board.highlight_cells(cells)
        shown = ", ".join(cells) if cells else "none"
        self._say(f"{clue.id} (from {owner}): {clue_to_text(clue)}  Highlighted: {shown}", BLUE)

    def _on_verdict(self, status: Status) -> None:
        cell = self.board.selected_cell
        if cell is None:
            self._say("Select a face-down card first.", ORANGE)
            return
        try:
            response = self.engine.submit_verdict(cell, status)
        except Exception as exc:  # e.g. inconsistent knowledge
            self._say(f"Engine error: {exc}", RED)
            return
        result = getattr(response.result, "value", response.result)
        if result == "ACCEPTED":
            self.board.reveal_card(cell, status)
            self.board.select_cell(None)
            self.selected_label.config(text="Selected: -")
            clue = response.new_clue
            if clue is not None:
                self.clue_panel.add_clue(cell, clue)
                self.clue_panel.select_owner(cell)
                self.board.highlight_cells(clue_cells(clue, self.size))
            text = f"ACCEPTED: {cell} is {status.value}."
            if clue is not None:
                text += f" New clue {clue.id}: {clue_to_text(clue)}"
            if self.engine.is_solved:
                text += "  Puzzle solved!"
                self._set_verdict_buttons(False)
            self._say(text, GREEN)
        elif result == "NOT_PROVABLE":
            self._say(f"NOT_PROVABLE: neither status of {cell} follows from the revealed clues.",
                      ORANGE)
        else:
            self._say(f"CONTRADICTED: the opposite verdict for {cell} is forced.", RED)

    def _set_verdict_buttons(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.criminal_btn.configure(state=state)
        self.innocent_btn.configure(state=state)

    def _todo(self, name: str) -> None:
        self._say(f"{name}: will be connected to the Agent in task 31.", ORANGE)

    def _say(self, text: str, color: str = BLUE) -> None:
        self.message.config(text=text, fg=color)


def run() -> None:
    """Open the main window (called from main.py)."""
    root = tk.Tk()
    App(root)
    root.mainloop()