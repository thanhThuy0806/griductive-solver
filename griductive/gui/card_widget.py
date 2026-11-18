"""One character card: face-down, or face-up as CRIMINAL / INNOCENT."""
import tkinter as tk

FACE_DOWN, CRIMINAL, INNOCENT = "FACE_DOWN", "CRIMINAL", "INNOCENT"

# (background, text color, border color) - colors are free to choose
COLORS = {
    FACE_DOWN: ("#ECE8DD", "#8A8577", "#B8B3A4"),
    CRIMINAL: ("#F9DCDC", "#7B1E1E", "#C0392B"),
    INNOCENT: ("#DCEBFA", "#1B4F7C", "#2E86C1"),
}
LABELS = {FACE_DOWN: "?", CRIMINAL: "CRIMINAL", INNOCENT: "INNOCENT"}
SELECT_BORDER = "#E67E22"     # orange: the card chosen for a verdict
HIGHLIGHT_BORDER = "#8E44AD"  # purple: card mentioned by the chosen clue
HIGHLIGHT_BG = "#FFF2A8"      # light yellow background of highlighted cards


class CardWidget(tk.Frame):
    """A single card in the grid."""

    def __init__(self, master, cell: str, name: str, job: str, on_click=None) -> None:
        super().__init__(master, width=130, height=92, highlightthickness=3)
        self.pack_propagate(False)  # keep the fixed size
        self.cell = cell
        self.on_click = on_click
        self.card_state = FACE_DOWN
        self.selected = False
        self.highlighted = False

        self.cell_label = tk.Label(self, text=cell, font=("Arial", 8), anchor="w")
        self.name_label = tk.Label(self, text=name, font=("Arial", 11, "bold"))
        self.job_label = tk.Label(self, text=job, font=("Arial", 9))
        self.status_label = tk.Label(self, font=("Arial", 9, "bold"))
        self.cell_label.pack(fill="x", padx=4)
        self.name_label.pack()
        self.job_label.pack()
        self.status_label.pack()

        self._parts = (self, self.cell_label, self.name_label, self.job_label, self.status_label)
        for part in self._parts:
            part.bind("<Button-1>", self._clicked)
        self.refresh()

    @property
    def is_face_up(self) -> bool:
        """True once the card shows CRIMINAL or INNOCENT."""
        return self.card_state != FACE_DOWN

    def set_state(self, state) -> None:
        """Show the card as FACE_DOWN, CRIMINAL or INNOCENT (Status enums are accepted)."""
        self.card_state = getattr(state, "value", state)
        self.refresh()

    def set_selected(self, value: bool) -> None:
        self.selected = value
        self.refresh()

    def set_highlighted(self, value: bool) -> None:
        self.highlighted = value
        self.refresh()

    def refresh(self) -> None:
        """Redraw colors and text from the current state and flags."""
        bg, fg, border = COLORS[self.card_state]
        if self.highlighted:
            bg = HIGHLIGHT_BG
        for part in self._parts:
            part.configure(bg=bg)
        for part in self._parts[1:]:
            part.configure(fg=fg)
        self.status_label.configure(text=LABELS[self.card_state])
        if self.selected:
            border = SELECT_BORDER
        elif self.highlighted:
            border = HIGHLIGHT_BORDER
        self.configure(highlightbackground=border, highlightcolor=border)

    def _clicked(self, _event) -> None:
        if self.on_click:
            self.on_click(self.cell)