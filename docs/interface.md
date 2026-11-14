# Hợp đồng puzzle JSON, loader và Game Engine

Hợp đồng v2 ngày 12/11/2026, đồng bộ core của Duy và tích hợp Engine với Agent,
encoder và DPLL của nhóm. Giữ tên trường JSON theo README; không thêm trường
version vào JSON. Loader kiểm tra cấu trúc; Engine kiểm tra verdict bằng suy luận.
Kiểm tra toàn bộ clue đúng với đáp án và nghiệm duy nhất vẫn là bước riêng.
Mọi thay đổi hợp đồng cần cập nhật tài liệu này và báo nhóm qua PR.

## 1. File puzzle

File dùng UTF-8 (chấp nhận BOM), đối tượng gốc có đúng hai trường:

| Trường | Kiểu | Quy định |
| --- | --- | --- |
| `size` | integer | Một trong `3`, `4`, `5`; không nhận Boolean hoặc số thực |
| `characters` | array | Đúng `size * size` nhân vật, mỗi tọa độ xuất hiện một lần |

Mỗi nhân vật có đúng các trường sau, tất cả đều bắt buộc:

| Trường | Kiểu | Quy định |
| --- | --- | --- |
| `cell` | string | Cột chữ HOA + hàng số, ví dụ `A1`, trong phạm vi bàn |
| `name` | string | Không rỗng hoặc chỉ có khoảng trắng |
| `job` | string | Không rỗng hoặc chỉ có khoảng trắng |
| `status` | string | `CRIMINAL` hoặc `INNOCENT`, kể cả khi thẻ còn úp |
| `revealed` | boolean | `true` là thẻ mở lúc bắt đầu; không nhận `0`, `1`, chuỗi |
| `clue` | object | Một clue theo mục 2, kể cả khi thẻ còn úp |

Phải có ít nhất một thẻ mở ban đầu; cho phép tất cả thẻ đã mở. Tên và nghề được
giữ nguyên, không tự cắt khoảng trắng. Không bắt tên/nghề duy nhất và không tự
đổi tọa độ theo tên. Người soạn puzzle sắp tên theo alphabet theo đề bài.

Thứ tự đầu vào tùy ý. Đầu ra luôn theo hàng trước, cột sau:
`A1, B1, C1, A2, B2, C2, ...`. File mẫu đầy đủ:
`puzzles/3x3/p3x3_01.json` (9 nhân vật, A1 mở ban đầu, chuỗi clue FACT).
Ví dụ một nhân vật trong danh sách:

```json
{
  "cell": "A1",
  "name": "Abel",
  "job": "Astronaut",
  "status": "INNOCENT",
  "revealed": true,
  "clue": {"id": "c01", "type": "FACT", "cell": "B1", "status": "CRIMINAL"}
}
```

## 2. Clue và region

Mọi clue có `id` (chuỗi không rỗng, duy nhất trong puzzle) và `type`.
Quy ước đặt ID là `c01`, `c02`, ...; loader không ép định dạng số này.
Ngoài hai trường chung, chỉ nhận đúng trường tương ứng với loại clue:

| `type` | Trường thêm | Ý nghĩa |
| --- | --- | --- |
| `FACT` | `cell`, `status` | Trạng thái của một ô |
| `SAME` | `a`, `b` | Hai ô cùng trạng thái |
| `DIFFERENT` | `a`, `b` | Hai ô khác trạng thái |
| `EXACTLY` | `k`, `region` | Chính xác k tội phạm trong vùng |
| `AT_LEAST` | `k`, `region` | Ít nhất k tội phạm trong vùng |
| `AT_MOST` | `k`, `region` | Nhiều nhất k tội phạm trong vùng |

`cell`, `a`, `b` phải là tọa độ có trên bàn; `status` dùng hai giá trị như trên.
`a` và `b` phải khác nhau, theo validator dùng chung của Duy.
`k` là integer (không nhận Boolean), `0 <= k <= số ô trong region`.

Region chỉ nhận đúng các trường theo loại:

| `kind` | Trường thêm | Quy định |
| --- | --- | --- |
| `ROW` | `index` | Integer từ 1 đến size |
| `COL` | `index` | Một chữ cột HOA trong bàn, ví dụ `B` |
| `NEIGHBORS` | `of` | Tọa độ ô trung tâm trong bàn |
| `CELLS` | `cells` | Danh sách tọa độ trong bàn, không trùng |

Hàng xóm gồm ngang, dọc và chéo, không gồm ô trung tâm. Góc/biên/giữa lần lượt
có 3/5/8 hàng xóm. `CELLS` không được rỗng, theo core dùng chung của Duy.
Tất cả kết quả resolve region được sắp theo thứ tự hàng trước, cột sau.

```json
{"id": "c02", "type": "SAME", "a": "A1", "b": "B2"}
{"id": "c03", "type": "DIFFERENT", "a": "A1", "b": "B2"}
{"id": "c04", "type": "EXACTLY", "k": 2, "region": {"kind": "ROW", "index": 2}}
{"id": "c05", "type": "AT_LEAST", "k": 1, "region": {"kind": "COL", "index": "B"}}
{"id": "c06", "type": "AT_MOST", "k": 1, "region": {"kind": "NEIGHBORS", "of": "B2"}}
{"id": "c07", "type": "EXACTLY", "k": 0, "region": {"kind": "CELLS", "cells": ["A1", "C3"]}}
```

Mỗi dòng trên là một ví dụ riêng, không phải một file JSON hoàn chỉnh.
Thiếu trường, trường thừa và loại extension chưa hỗ trợ đều bị từ chối.
Khi bổ sung extension cần mở rộng đồng thời enum, kiểu dữ liệu, parser, test
và hợp đồng này; không tự bỏ qua clue lạ.

## 3. API và kiểu dữ liệu dùng chung

```python
from griductive.engine.puzzle_loader import load_puzzle, parse_puzzle
from griductive.core.regions import resolve_region

puzzle = load_puzzle("puzzles/3x3/p3x3_01.json")  # str hoặc pathlib.Path
# parse_puzzle(data: object) -> Puzzle: dùng với dữ liệu đã json.loads()
first = puzzle.characters[0]  # Cell ở A1
if first.clue.region is not None:
    cells = resolve_region(first.clue.region, puzzle.size)
```

`resolve_region` dùng với clue đếm; clue đầu tiên của file mẫu là FACT nên
không có region.

Enum dạng chuỗi trong `core.constants`: `Status`, `ClueType`, `RegionKind`.
Các kiểu trong `core.types` được đồng bộ với nhánh core của Duy:

- `Puzzle(size: int, characters: list[Cell])`, có thể thay đổi.
- `Cell(cell, name, job, status: Status, revealed: bool, clue: Clue)`;
  cell/name/job là string; Cell có thể thay đổi.
- `Clue(id: str, type: ClueType, cell?, status?, a?, b?, k?, region?, params={})`.
  Các trường không thuộc loại clue có giá trị `None`; status dùng `Status`,
  k dùng int, region dùng `Region`, cell/a/b dùng string.
- `Region(kind: RegionKind, index?, of?, cells=())`.
  index dùng int cho ROW, string cho COL; JSON `of` ánh xạ trực tiếp thành `of`;
  cells dùng tuple string. index/of không dùng là `None`.
- Clue và Region dùng `frozen=True`, nhưng dictionary `Clue.params` có thể sửa.
  `from_dict()` của core giữ trường clue lạ trong params; loader vẫn kiểm tra
  chặt và từ chối trường JSON lạ như hợp đồng đầu vào, không nới lỏng theo helper.
- Có thêm các alias `CellId`, `Assignment`, `Clause`, `CNF` và `ClueError`.

`resolve_region(region: Region, n: int) -> list[str]` kiểm tra tọa độ, trùng ô,
vùng rỗng và trả kết quả tất định. Loader kiểm tra riêng các trường thừa/thiếu.
Core chỉ phụ thuộc thư viện chuẩn và
chính core; không import engine, encoder hoặc SAT.

Dataclass không tự validate khi khởi tạo trực tiếp. Dữ liệu đầu vào bên ngoài
phải đi qua `load_puzzle(path)` hoặc `parse_puzzle(data)`. Loader gọi thêm
`validate_clue` của Duy, không sửa dữ liệu nguồn và không giữ tham chiếu tới
các list/dictionary của dữ liệu đầu vào.

**Ranh giới thông tin:** Puzzle và Cell chứa status cùng clue ẩn, chỉ dành cho
Game Engine. `revealed` ở đây là cấu hình khởi đầu; Engine quản lý trạng thái
chơi riêng. Agent không nhận Puzzle/Cell đầy đủ; Engine chỉ cung cấp clue đã
mở và trạng thái công khai qua API ở mục 5.

## 4. Lỗi và cách kiểm tra

- Cú pháp JSON sai: `ValueError` kèm file, dòng và cột.
- Không phải UTF-8: `ValueError` kèm file.
- Sai dữ liệu: `ValueError` kèm vị trí, ví dụ
  `characters[2].clue.k: expected an integer in 0..3`.
- File thiếu hoặc không đọc được: giữ `FileNotFoundError`/`PermissionError`
  và các lỗi hệ thống tương ứng.
- Không trả puzzle đọc dở khi có lỗi. Phát hiện và báo lỗi đầu tiên.

Chạy từ thư mục gốc repo:

```bash
python -m pytest tests/ unit_tests/dpll.py unit_tests/dpll_stats.py
python -c "from griductive.engine.puzzle_loader import load_puzzle; print(load_puzzle('puzzles/3x3/p3x3_01.json'))"
```

Loader không kiểm tra clue đúng với đáp án, KB nhất quán, nghiệm duy nhất hay
khả năng giải tuần tự. Engine kiểm tra KB công khai khi nhận verdict; việc xác
minh toàn bộ puzzle, nghiệm duy nhất và khả năng giải là luồng riêng về sau.
`main.py` hiện vẫn là skeleton; đọc được puzzle chưa đồng nghĩa GUI/solver đã chạy.

## 5. Game Engine và API công khai

```python
from griductive.core.constants import Status
from griductive.engine.game_engine import GameEngine
from griductive.engine.puzzle_loader import load_puzzle

engine = GameEngine(load_puzzle("puzzles/3x3/p3x3_01.json"))
initial = engine.get_public_state()
response = engine.submit_verdict("B1", Status.CRIMINAL)
assert response.result.value == "ACCEPTED"
assert response.new_clue.id == "c02"
assert not initial.characters[1].revealed  # snapshot cũ không thay đổi
restored = engine.restart()
assert restored == initial
assert not engine.is_solved
```

### Kiểu trả về

- `PublicCell(cell, name, job, revealed, status=None, clue=None)`:
  thẻ úp có status/clue bằng None, vẫn hiển thị được tọa độ/tên/nghề.
- `PublicState(size, characters: tuple[PublicCell, ...])`: thứ tự row-major.
- `VerdictResponse(cell, status, result: VerdictResult, new_clue=None)`:
  status là lựa chọn đã gửi; chỉ ACCEPTED có new_clue.

Ba DTO này dùng frozen dataclass. Clue chứa params có thể sửa nên không hứa
bất biến sâu: mọi clue được sao chép sâu, sửa snapshot/response không sửa
đáp án Engine hoặc các snapshot đã trả trước đó.

### Interface Engine

- `GameEngine(puzzle, classify=None)`: nhận Puzzle đã được loader kiểm tra,
  sao chép sâu dữ liệu và giữ đáp án nội bộ. classify phải callable nếu được truyền.
- `get_public_state() -> PublicState`: snapshot mới, không chứa dữ liệu ẩn.
- `submit_verdict(cell: str, status: Status) -> VerdictResponse`:
  chỉ nhận Status enum, không nhận chuỗi. Tọa độ sai, status sai, thẻ đã mở
  gây ValueError trước khi gọi Agent.
- `restart() -> PublicState`: khôi phục đúng thẻ mở trong cấu hình ban đầu.
- `is_solved: bool`: True khi mọi thẻ đã mở, kể cả puzzle mở hết từ đầu.

Không có public API mở thẻ tùy ý. Để tải puzzle khác, tạo Engine mới.
Phiên bản này dùng tuần tự trong một luồng; callback không được gọi ngược
Engine để restart/submit trong khi một submit khác đang chạy.

### Phân loại qua code thật

`engine.verdict.classify(public_state, cell) -> Classification` tạo VarMap,
encode clue của thẻ đã mở và thêm unit clauses của status công khai. Thẻ úp
bị bỏ qua kể cả khi một PublicState tự tạo chứa status/clue ở thẻ đó.
Hàm gọi `EntailmentChecker(solver=DpllSolver()).classify(clauses, vm.var(cell))`.
Classification dùng nguyên enum của `griductive.agent.entailment`, không có
enum thứ hai trong core. Mỗi lượt dựng KB/checker/solver mới, không giữ KB cũ
hoặc log truy vấn tích lũy giữa các lượt. Trace tích lũy thuộc task Agent sau.

`GameEngine` mặc định dùng hàm thật này. Có thể truyền callback cùng chữ ký
để tích hợp Agent khác hoặc kiểm thử lỗi; không mặc định dùng StubSolver.
Core không import Agent/Engine. Engine được phép gọi Agent; Agent chỉ nhận CNF,
không import Engine, không nhận tham chiếu tới Puzzle/Cell hoặc đáp án ẩn.

| Agent trả về | Kết quả Engine |
| --- | --- |
| UNKNOWN | NOT_PROVABLE; không đổi trạng thái, không trả clue |
| Ngược lựa chọn | CONTRADICTED; không đổi trạng thái, không trả clue |
| Cùng lựa chọn và khớp đáp án | ACCEPTED; mở đúng một thẻ, trả clue mới |
| INCONSISTENT | EngineConsistencyError; không đổi trạng thái |
| Chứng minh lựa chọn nhưng trái đáp án ẩn | EngineConsistencyError; không đổi trạng thái |

`EngineConsistencyError` ở `engine.verdict`, kế thừa RuntimeError; thông báo
không chứa đáp án ẩn. Callback trả sai kiểu gây TypeError; lỗi callback được
truyền cho bên gọi. Mọi thay đổi thẻ chỉ diễn ra sau khi kiểm tra thành công.

## 6. Nguồn tích hợp và bàn giao

Nhánh task: `feat/d-game-engine-verdict`, dựa trên schema/loader `d78bb7b`.
Chỉ lấy file cần dùng, không merge nhánh khác hoặc đưa README/GUI vào task.

| Nguồn | Commit đã lấy | Nội dung |
| --- | --- | --- |
| feat/logic-agent (Thúy) | d901e28115a1aa3359bd23e8a55f735b0340b0db | entailment, stub phụ thuộc của Agent, SAT interface, exports và test Agent |
| feat/c-core-regions-varmap (Duy) | 21bebdc0e9de379cf55da2ada272eea145df12af | core, validator, VarMap, encoder, evaluator và các test tương ứng |
| feat/b-dpll-counter (Phong) | c87469a12db3a8f9add0c3f22a6b113a5c127bb7 | DPLL, thống kê, unit_tests/dpll.py và dpll_stats.py |

Phần task này bổ sung: DTO công khai vào core.types; đồng bộ loader/test;
Engine, cầu nối CNF và test tích hợp. Các thuật toán của nhóm được giữ nguyên.
Đã kiểm tra nhánh GUI `ecb60cd`: đang dùng mock, chưa có API Engine cần lấy về.

Chuyển đổi từ hợp đồng v1:

- Python `Region.of_cell` -> `Region.of`; JSON không đổi.
- Puzzle/Cell có thể sửa, Puzzle.characters là list; resolve_region trả list.
  Engine tự sao chép sâu và cung cấp DTO công khai riêng.
- CELLS rỗng và SAME/DIFFERENT cùng một ô nay bị từ chối theo validator chung.
- Kiểm thử toàn bộ dùng pytest. Các test DPLL không có tiền tố test_ nên cần
  chỉ định hai file unit_tests trong lệnh chạy, không chỉ chạy tests/.

Bàn giao cho các thành viên (người dùng chuyển giúp):

- **Thúy:** Engine gọi classify(clauses, var) hiện có; cầu nối chỉ dùng thông tin
  công khai. Vòng Agent, Hint, Auto Solve và trace tích lũy chưa thuộc task này.
- **Duy:** core/encoder đồng bộ theo nhánh của anh, chỉ bổ sung ba DTO công khai;
  loader cập nhật theo of, vùng không rỗng và hai ô binary khác nhau.
- **Phong:** Engine truyền DpllSolver vào EntailmentChecker; thống kê SatStats
  hiện đã đọc được qua dict(result.stats) trong log truy vấn Agent.
- **Vy:** dùng snapshot công khai để hiển thị, submit_verdict để gửi lựa chọn,
  restart để chơi lại, is_solved để kiểm tra hoàn thành; không truyền Puzzle
  riêng hoặc dữ liệu mock chứa đáp án vào Agent.
