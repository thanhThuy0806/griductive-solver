"""Right-hand panel: revealed clues. Click one to highlight the cells it refers to."""
import tkinter as tk

from griductive.core.regions import resolve_region


def _val(x):
    """Return the plain value of an Enum member (or the object itself)."""
    return getattr(x, "value", x)


def _center(region) -> str:
    """Center cell of a NEIGHBORS region (the field is called 'of' or 'of_cell')."""
    for name in ("of", "of_cell"):
        value = getattr(region, name, None)
        if value:
            return value
    return "?"


def region_text(region) -> str:
    """Human-readable name of a region."""
    kind = _val(region.kind)
    if kind == "ROW":
        return f"row {region.index}"
    if kind == "COL":
        return f"column {region.index}"
    if kind == "NEIGHBORS":
        return f"the neighbors of {_center(region)}"
    if kind == "CELLS":
        return "cells " + ", ".join(region.cells)
    return str(kind)


def clue_to_text(clue) -> str:
    """Short English sentence for a structured clue."""
    kind = _val(clue.type)
    if kind == "FACT":
        return f"{clue.cell} is {_val(clue.status).lower()}."
    if kind == "SAME":
        return f"{clue.a} and {clue.b} have the same status."
    if kind == "DIFFERENT":
        return f"{clue.a} and {clue.b} have different statuses."
    if kind in ("EXACTLY", "AT_LEAST", "AT_MOST"):
        word = {"EXACTLY": "Exactly", "AT_LEAST": "At least", "AT_MOST": "At most"}[kind]
        noun = "criminal" if clue.k == 1 else "criminals"
        return f"{word} {clue.k} {noun} in {region_text(clue.region)}."
    return f"[{kind}] extension clue"  # extensions get their own text later


def clue_cells(clue, size: int) -> list[str]:
    """Cells that a clue refers to (used to highlight them on the board)."""
    cells = [c for c in (clue.cell, clue.a, clue.b) if c]
    if clue.region is not None:
        cells.extend(resolve_region(clue.region, size))
    return list(dict.fromkeys(cells))  # remove duplicates, keep order


class CluePanel(tk.Frame):
    """Shows revealed clues as 'c01  [A1]  B1 is criminal.' ([A1] = card that owns the clue)."""

    def __init__(self, master, on_pick=None) -> None:
        super().__init__(master)
        self.on_pick = on_pick
        self.items: list[tuple[str, object]] = []  # (owner cell, clue)
        tk.Label(self, text="Revealed clues", font=("Arial", 12, "bold")).pack(anchor="w")
        box = tk.Frame(self)
        box.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(box, width=58, height=14, exportselection=False,
                                  activestyle="none")
        scroll = tk.Scrollbar(box, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self._picked)

    def set_clues(self, items) -> None:
        """Replace the whole list with (owner, clue) pairs."""
        self.items = []
        self.listbox.delete(0, "end")
        for owner, clue in items:
            self.add_clue(owner, clue)

    def add_clue(self, owner: str, clue) -> None:
        """Append one newly revealed clue."""
        self.items.append((owner, clue))
        self.listbox.insert("end", f"{clue.id}  [{owner}]  {clue_to_text(clue)}")

    def select_owner(self, owner: str):
        """Select the row of the clue owned by this card and return the clue (or None)."""
        for index, (who, clue) in enumerate(self.items):
            if who == owner:
                self.listbox.selection_clear(0, "end")
                self.listbox.selection_set(index)
                self.listbox.see(index)
                return clue
        return None

    def _picked(self, _event) -> None:
        selection = self.listbox.curselection()
        if selection and self.on_pick:
            owner, clue = self.items[selection[0]]
            self.on_pick(owner, clue)