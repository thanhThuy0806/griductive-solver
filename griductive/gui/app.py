"""Main window. Task 14: show the board with mock data (Engine/Agent come later)."""
import tkinter as tk

from griductive.gui.board_view import BoardView

# Mock 3x3 puzzle in the README format. Real data will come from the Game Engine.
MOCK_PUZZLE = {
    "size": 3,
    "characters": [
        {"cell": "A1", "name": "Abel", "job": "Astronaut", "status": "INNOCENT", "revealed": True},
        {"cell": "A2", "name": "Bea", "job": "Cook", "status": "CRIMINAL", "revealed": False},
        {"cell": "A3", "name": "Clara", "job": "Guard", "status": "INNOCENT", "revealed": False},
        {"cell": "B1", "name": "Derek", "job": "Cook", "status": "INNOCENT", "revealed": False},
        {"cell": "B2", "name": "Eliza", "job": "Detective", "status": "CRIMINAL", "revealed": True},
        {"cell": "B3", "name": "Franz", "job": "Farmer", "status": "INNOCENT", "revealed": False},
        {"cell": "C1", "name": "Grant", "job": "Clerk", "status": "CRIMINAL", "revealed": False},
        {"cell": "C2", "name": "Hannah", "job": "Guard", "status": "INNOCENT", "revealed": True},
        {"cell": "C3", "name": "Ivy", "job": "Painter", "status": "INNOCENT", "revealed": False},
    ],
}


def run() -> None:
    """Open the main window (called from main.py)."""
    root = tk.Tk()
    root.title("Griductive Solver")
    board = BoardView(root)
    board.pack(padx=20, pady=20)
    board.load_puzzle(MOCK_PUZZLE)
    root.mainloop()