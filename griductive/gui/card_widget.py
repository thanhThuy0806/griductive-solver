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


class CardWidget(tk.Frame):
    """A single card in the grid."""

    def __init__(self, master, cell: str, name: str, job: str) -> None:
        super().__init__(master, width=130, height=92, highlightthickness=3)
        self.pack_propagate(False)  # keep the fixed size
        self.cell_label = tk.Label(self, text=cell, font=("Arial", 8), anchor="w")
        self.name_label = tk.Label(self, text=name, font=("Arial", 11, "bold"))
        self.job_label = tk.Label(self, text=job, font=("Arial", 9))
        self.status_label = tk.Label(self, font=("Arial", 9, "bold"))
        self.cell_label.pack(fill="x", padx=4)
        self.name_label.pack()
        self.job_label.pack()
        self.status_label.pack()
        self.set_state(FACE_DOWN)

    def set_state(self, state: str) -> None:
        """Show the card as FACE_DOWN, CRIMINAL or INNOCENT."""
        bg, fg, border = COLORS[state]
        self.configure(bg=bg, highlightbackground=border, highlightcolor=border)
        for label in (self.cell_label, self.name_label, self.job_label, self.status_label):
            label.configure(bg=bg, fg=fg)
        self.status_label.configure(text=LABELS[state])