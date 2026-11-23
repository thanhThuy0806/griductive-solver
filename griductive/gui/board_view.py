"""The N x N board: column letters on top, row numbers on the left, one card per cell."""
import tkinter as tk

from griductive.gui.card_widget import CardWidget


def _cell_to_rc(cell: str) -> tuple[int, int]:
    """Convert a cell id like 'B3' to (row_index, col_index) = (2, 1)."""
    return int(cell[1:]) - 1, ord(cell[0].upper()) - ord("A")


class BoardView(tk.Frame):
    """Draws the grid of cards from a puzzle dict (format: README section 4)."""

    def __init__(self, master) -> None:
        super().__init__(master)
        self.cards: dict[str, CardWidget] = {}

    def load_puzzle(self, puzzle: dict) -> None:
        """Rebuild the board. Only characters with revealed=True are shown face-up."""
        for child in self.winfo_children():
            child.destroy()
        self.cards = {}
        size = puzzle["size"]
        for c in range(size):
            letter = tk.Label(self, text=chr(ord("A") + c), font=("Arial", 12, "bold"))
            letter.grid(row=0, column=c + 1, pady=(0, 4))
        for r in range(size):
            number = tk.Label(self, text=str(r + 1), font=("Arial", 12, "bold"))
            number.grid(row=r + 1, column=0, padx=(0, 6))
        for ch in puzzle["characters"]:
            row, col = _cell_to_rc(ch["cell"])
            card = CardWidget(self, ch["cell"], ch["name"], ch["job"])
            card.grid(row=row + 1, column=col + 1, padx=4, pady=4)
            if ch.get("revealed"):
                card.set_state(ch["status"])  # hidden statuses are never read
            self.cards[ch["cell"]] = card