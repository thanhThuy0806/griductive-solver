"""Ánh xạ ô <-> biến SAT. Biến dương theo quy ước DIMACS (1, 2, 3...)."""
from griductive.core.constants import MAX_GRID
from griductive.core.regions import cell_id, parse_cell
from griductive.core.types import CellId, ClueError


class VarMap:
    def __init__(self, n: int):
        if not (1 <= n <= MAX_GRID):
            raise ClueError(f"Kích thước lưới không hợp lệ: {n}")
        self.n = n
        self.num_primary = n * n
        self._next_aux = self.num_primary + 1    # biến phụ nằm SAU biến chính

    def var(self, cid: CellId) -> int:
        """A1 -> 1, B1 -> 2, ... (row-major)."""
        r, c = parse_cell(cid, self.n)
        return r * self.n + c + 1

    def cell(self, v: int) -> CellId:
        """Ngược lại của var(). Chỉ dùng cho biến chính."""
        if not (1 <= v <= self.num_primary):
            raise ClueError(f"Biến {v} không phải biến chính")
        return cell_id((v - 1) // self.n, (v - 1) % self.n)

    def new_aux(self) -> int:
        v = self._next_aux
        self._next_aux += 1
        return v

    @property
    def num_aux(self) -> int:
        return self._next_aux - 1 - self.num_primary

    @property
    def num_vars(self) -> int:
        return self._next_aux - 1