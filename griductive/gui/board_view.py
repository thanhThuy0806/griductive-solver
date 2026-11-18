"""The N x N board: column letters on top, row numbers on the left, one card per cell."""
import tkinter as tk

from griductive.gui.card_widget import CardWidget


def _cell_to_rc(cell: str) -> tuple[int, int]:
    """Convert a cell id like 'B3' to (row_index, col_index) = (2, 1)."""
    return int(cell[1:]) - 1, ord(cell[0].upper()) - ord("A")


class BoardView(tk.Frame):
    """Draws the grid of cards from a PublicState and tracks selection / highlight."""

    def __init__(self, master, on_click=None) -> None:
        super().__init__(master)
        self.on_click = on_click
        self.cards: dict[str, CardWidget] = {}
        self.selected_cell = None

    def load_state(self, state) -> None:
        """Rebuild the board. Only revealed cards show a status; the rest stay face-down."""
        for child in self.winfo_children():
            child.destroy()
        self.cards = {}
        self.selected_cell = None
        for c in range(state.size):
            letter = tk.Label(self, text=chr(ord("A") + c), font=("Arial", 12, "bold"))
            letter.grid(row=0, column=c + 1, pady=(0, 4))
        for r in range(state.size):
            number = tk.Label(self, text=str(r + 1), font=("Arial", 12, "bold"))
            number.grid(row=r + 1, column=0, padx=(0, 6))
        for pc in state.characters:
            row, col = _cell_to_rc(pc.cell)
            card = CardWidget(self, pc.cell, pc.name, pc.job, on_click=self._card_clicked)
            card.grid(row=row + 1, column=col + 1, padx=4, pady=4)
            if pc.revealed:
                card.set_state(pc.status)  # a face-down card's status is never read
            self.cards[pc.cell] = card

    def reveal_card(self, cell: str, status) -> None:
        """Flip a card face-up after the Engine accepted the verdict."""
        self.cards[cell].set_state(status)

    def select_cell(self, cell) -> None:
        """Mark one card as selected (orange border); None clears the selection."""
        if self.selected_cell in self.cards:
            self.cards[self.selected_cell].set_selected(False)
        self.selected_cell = cell
        if cell in self.cards:
            self.cards[cell].set_selected(True)

    def highlight_cells(self, cells) -> None:
        """Highlight exactly these cells (purple border, yellow background)."""
        wanted = set(cells)
        for cell, card in self.cards.items():
            card.set_highlighted(cell in wanted)

    def _card_clicked(self, cell: str) -> None:
        if self.on_click:
            self.on_click(cell)