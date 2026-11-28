# Hợp đồng puzzle JSON, loader và Game Engine

Hợp đồng v4 ngày 23/11/2026: giữ AgentKnowledge của v3 và bổ sung AgentAPI
để nối LogicAgent thật với encoder/Engine, lọc cả clue mới được mở.
Kế thừa core, encoder và DPLL của nhóm, gồm PARITY/COMPARE.
Giữ tên trường JSON theo README; không thêm trường
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
| `PARITY` | `parity`, `region` | Extension 1: Chẵn/lẻ số tội phạm trong vùng (`EVEN` / `ODD`) |
| `COMPARE` | `region_a`, `region_b`, `op` | Extension 2: So sánh số tội phạm 2 vùng (`MORE` / `EQUAL` / `LESS`) |

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
{"id": "c08", "type": "PARITY", "parity": "EVEN", "region": {"kind": "ROW", "index": 1}}
{"id": "c09", "type": "COMPARE", "region_a": {"kind": "ROW", "index": 1}, "region_b": {"kind": "COL", "index": "A"}, "op": "MORE"}
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
- `get_agent_knowledge() -> AgentKnowledge`: chỉ clue đã mở và trạng thái công khai.
- `submit_verdict(cell: str, status: Status) -> VerdictResponse`:
  chỉ nhận Status enum, không nhận chuỗi. Tọa độ sai, status sai, thẻ đã mở
  gây ValueError trước khi gọi Agent.
- `restart() -> PublicState`: khôi phục đúng thẻ mở trong cấu hình ban đầu.
- `is_solved: bool`: True khi mọi thẻ đã mở, kể cả puzzle mở hết từ đầu.

Không có public API mở thẻ tùy ý. Để tải puzzle khác, tạo Engine mới.
Phiên bản này dùng tuần tự trong một luồng; callback không được gọi ngược
Engine để restart/submit trong khi một submit khác đang chạy.

### Phân loại qua code thật

`engine.verdict.classify(knowledge: AgentKnowledge, cell) -> Classification`
tạo VarMap, encode revealed_clues và thêm unit clauses của proven_verdicts.
PublicState không còn được chấp nhận làm đầu vào classifier.
Hàm gọi `EntailmentChecker(solver=DpllSolver()).classify(clauses, vm.var(cell))`.
Classification dùng nguyên enum của `griductive.agent.entailment`, không có
enum thứ hai trong core. Mỗi lượt dựng KB/checker/solver mới, không giữ KB cũ
hoặc log truy vấn tích lũy giữa các lượt. Trace tích lũy thuộc task Agent sau.

`GameEngine` mặc định dùng hàm thật này. Có thể truyền callback cùng chữ ký
để tích hợp Agent khác hoặc kiểm thử lỗi; không mặc định dùng StubSolver.
Core không import Agent/Engine. Callback Agent nhận AgentKnowledge từ core;
EntailmentChecker cấp thấp vẫn chỉ nhận CNF. Agent không import Engine/loader,
không nhận Puzzle/Cell hoặc đáp án ẩn. Không cần đổi thuật toán entailment.

### Hợp đồng AgentKnowledge và chuyển đổi từ v2

```python
from griductive.core.types import AgentKnowledge
from griductive.engine.verdict import classify

knowledge = engine.get_agent_knowledge()
assert isinstance(knowledge, AgentKnowledge)
assert knowledge.proven_verdicts == (("A1", Status.INNOCENT),)
assert classify(knowledge, "B1").value == "CRIMINAL"

# Caller cũ: classify(engine.get_public_state(), "B1")
# Caller mới: classify(engine.get_agent_knowledge(), "B1")
```

`AgentKnowledge(size: int, revealed_clues: tuple[Clue, ...],
proven_verdicts: tuple[tuple[CellId, Status], ...])` là frozen dataclass.
Kích thước là integer 3/4/5 (không nhận Boolean). Engine xuất clue theo thứ tự
thẻ row-major, verdict theo tọa độ row-major; ID clue và tọa độ verdict không trùng.
proven_verdicts gồm dữ kiện mở ban đầu và verdict đã ACCEPTED, không có lựa chọn
người chơi đang thử. Tên trường không có nghĩa Agent đã tự chứng minh ô cho sẵn.

DTO chỉ có ba trường trên: không có tên/nghề, thẻ úp, đường dẫn file hoặc tham
chiếu Engine/Puzzle/Cell. get_agent_knowledge đọc tập thẻ mở nội bộ, không nhận
snapshot bên ngoài. Tên/nghề không cần cho sáu clue hiện tại vì đã dùng tọa độ.

Mỗi clue được dựng mới chỉ với id/type và trường có ý nghĩa: FACT dùng cell/status;
SAME/DIFFERENT dùng a/b; EXACTLY/AT_LEAST/AT_MOST dùng k/region; PARITY dùng parity/region;
COMPARE dùng region_a/region_b/op. Region mới chỉ
giữ index cho ROW/COL, of cho NEIGHBORS hoặc tuple cells cho CELLS. params luôn
là dict rỗng; không chuyển metadata/trường dư. Kiểu clue/region chưa hỗ trợ gây
lỗi; khi thêm extension phải mở rộng rõ projector, validator, encoder và test.

Callback truyền qua GameEngine(classify=...) nay nhận (AgentKnowledge, cell),
trả Classification như cũ. Không hỗ trợ đồng thời chữ ký PublicState cũ.
get_public_state vẫn dành cho GUI, không đổi schema JSON hoặc phản hồi Engine.

Cầu nối kiểm tra đúng DTO/tuple, kích thước, tọa độ, Status enum, clue hợp lệ,
ID/trạng thái trùng và trường dư trước khi gọi solver. Sai kiểu gây TypeError,
sai giá trị gây ValueError (bao gồm ClueError). Clue hợp lệ nhưng mâu thuẫn logic
vẫn trả INCONSISTENT qua solver. Classifier cho phép hỏi mọi ô hợp lệ; Engine
riêng từ chối submit lại ô đã mở. DTO tự dựng không chứng minh nguồn gốc verdict;
caller chịu trách nhiệm, Engine là nguồn dữ kiện xác nhận trong luồng ứng dụng.

Snapshot Agent độc lập với input/Engine/snapshot khác. Clue.params vẫn là dict
có thể sửa nên không hứa bất biến sâu; sửa request không sửa Engine. Dữ kiện mới
chỉ xuất hiện sau ACCEPTED. Từ chối/lỗi không cập nhật dữ kiện; restart khôi phục
đúng dữ kiện ban đầu. Không giữ cache hay trace tích lũy trong cầu nối.

Đây là hợp đồng giữa các module hợp tác trong cùng tiến trình Python, không phải
sandbox chống mã cố ý đọc bộ nhớ. Công cụ kiểm chứng offline của task 26/27 được
phép đọc puzzle đầy đủ, không được dùng làm dữ kiện trong luồng Agent.

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

Nền tích hợp Engine: `feat/d-game-engine-verdict`, dựa trên schema/loader `d78bb7b`.
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

- **Thúy:** callback mới nhận AgentKnowledge, trả Classification; core chứa DTO
  nên Agent không cần import Engine. EntailmentChecker vẫn dùng classify(clauses,
  var) hiện có. LogicAgent/Hint/Auto Solve/trace đã có; AgentAPI ở mục 7 nối
  các protocol hiện tại mà không sửa thuật toán hoặc thêm import Engine vào Agent.
- **Duy:** core/encoder đồng bộ theo nhánh của anh, chỉ bổ sung ba DTO công khai;
  loader cập nhật theo of, vùng không rỗng và hai ô binary khác nhau.
  V3 bổ sung AgentKnowledge; extension phải khai báo trường được xuất sang Agent.
- **Phong:** Engine truyền DpllSolver vào EntailmentChecker; thống kê SatStats
  hiện đã đọc được qua dict(result.stats) trong log truy vấn Agent.
- **Vy:** dùng snapshot công khai để hiển thị, submit_verdict để gửi lựa chọn,
  restart để chơi lại, is_solved để kiểm tra hoàn thành; không truyền Puzzle
  riêng hoặc dữ liệu mock chứa đáp án vào Agent.

Task 28: nhánh feat/d-engine-agent-api dựa trên task 27 tại d14b873. Caller Engine,
callback test và lộ trình dataset đã chuyển sang AgentKnowledge. Kiểm chứng được
bằng entailment/DPLL thật và sample hiện có, không phụ thuộc đủ bảy màn.

Kiểm thử ban đầu task 28 ngày 13/11: 358 passed, 97 subtests passed, 1 skipped
(readiness task 26). Kết quả mới nhất và đường tích hợp đầy đủ ở mục 7.
Lệnh chạy: `python -m pytest tests/ unit_tests/dpll.py unit_tests/dpll_stats.py -q -rs`.
Nếu thư mục tạm pytest mặc định bị lỗi quyền, thêm
`--basetemp=.pytest_cache/agent-tmp`. Test hợp đồng bao phủ DTO/metadata, dữ kiện
ẩn không ảnh hưởng classification, request độc lập, chu kỳ verdict/restart, lỗi
trước solver và kiểm tra import AST tuyệt đối/tương đối của package Agent.

## 7. AgentAPI và nghiệm thu task 28 ngày 23/11/2026

Nhánh `feat/d-engine-agent-api` đã đồng bộ task 26/27 tại `c853b6b`: đủ bộ bảy
puzzle và các extension/DPLL mới. Bộ phân loại cấp thấp vẫn nhận AgentKnowledge;
snapshot GUI và API GameEngine giữ nguyên. Adapter mới nằm trong
`griductive/engine/agent_api.py`, không đặt ở package Agent và không đưa Puzzle
cho LogicAgent.

### Nối LogicAgent thật

```python
from griductive.agent.logic_agent import RunStatus
from griductive.engine.agent_api import AgentAPI
from griductive.engine.game_engine import GameEngine
from griductive.engine.puzzle_loader import load_puzzle

engine = GameEngine(load_puzzle("puzzles/3x3/p3x3_04.json"))
api = AgentAPI(engine)
agent = api.create_agent()
hint = agent.hint()  # chỉ đọc KB công khai, không mở thẻ
result = agent.run(api)
assert result.status is RunStatus.SOLVED
assert engine.is_solved

engine.restart()
agent = api.create_agent()  # tạo lại KB/trace từ đúng các thẻ hiện đang mở
```

`AgentAPI` thực hiện cả `ClueEncoder` và `GameInterface` mà LogicAgent hiện dùng:

| API | Hợp đồng |
| --- | --- |
| `size` | Kích thước công khai, lấy từ AgentKnowledge |
| `public_cards()` | Tuple PublicCard chỉ gồm cell, status dạng chuỗi và clue dictionary đã lọc của thẻ mở |
| `create_agent()` | Agent mới dùng DPLL thật và dữ kiện công khai hiện tại; không mặc định dùng StubSolver |
| `var_of(cell)` | Dùng VarMap chung, cùng thứ tự biến với encoder/Engine |
| `encode_clue(data)` | Từ chối metadata/trường không dùng rồi gọi encoder chung; giữ cùng VarMap để biến phụ không trùng |
| `submit_verdict(cell, status)` | Đổi chuỗi sang Status, gọi Engine, trả protocol VerdictResponse(result, clue) của Agent |

Hai kiểu VerdictResponse vẫn có vai trò riêng: Engine trả `new_clue` dạng Clue,
adapter trả `clue` dạng dictionary cho protocol có sẵn của Agent. Không tự sửa
thuật toán Agent, fakes/test của Thúy hoặc schema JSON để ép hai interface giống nhau.

### Ranh giới dữ liệu

- Khởi tạo Agent chỉ đọc `get_agent_knowledge()`, không đọc `get_public_state()`.
  Hai tuple clue/status của Engine đều theo thứ tự thẻ mở row-major, một clue
  trên một status; adapter kiểm tra số lượng trước khi ghép thành PublicCard.
- Dictionary gửi sang Agent chỉ có id/type và các trường ngữ nghĩa tương ứng
  của tám loại clue ở mục 2. Region chỉ giữ kind và index/of/cells có ý nghĩa.
  Không chuyển tên/nghề, params, trường dư, snapshot GUI hoặc đáp án ẩn.
- Sau ACCEPTED, adapter chiếu lại `new_clue` qua cùng bộ lọc trước khi trả cho
  Agent. Việc một clue đã được mở không làm metadata tùy ý trở thành dữ kiện hợp lệ.
  Dictionary/list được dựng mới, sửa payload không sửa Engine hoặc request khác.
- NOT_PROVABLE/CONTRADICTED không trả clue và không đổi dữ kiện. Thẻ đã mở,
  tọa độ/status sai hoặc lỗi classifier không được thêm vào KB.
- Engine kiểm tra kiểu và tham số của clue sắp mở trước khi thay đổi tập thẻ
  mở. Clue không được hỗ trợ gây lỗi và giữ nguyên trạng thái; metadata GUI vẫn
  được sao chép theo hợp đồng cũ, còn adapter Agent luôn lọc bỏ.
  Kiểm tra này không thay thế evaluator/uniqueness offline về tính đúng của puzzle.

Sau Restart hoặc sau khi người chơi mở thẻ qua GUI, tạo lại Agent từ
`api.create_agent()` trước khi tiếp tục Hint/Auto Solve; Agent cũ có KB/trace
riêng và không tự đồng bộ với thao tác bên ngoài. Load puzzle khác thì tạo
Engine và AgentAPI mới. Không dùng đồng thời nhiều thao tác sửa bàn.

Đây là hợp đồng API giữa các module tin cậy trong cùng tiến trình. Adapter giữ
callback tới các thao tác công khai của Engine; không cung cấp sandbox chống mã
Python cố ý introspect callback/bộ nhớ. Công cụ uniqueness offline không được dùng
làm nguồn dữ kiện cho Agent.

### Kết quả kiểm chứng

`tests/test_engine_agent_api.py` chạy LogicAgent + encoder + DPLL + Engine thật
trên bảy màn và mẫu regression. Test chặn việc đọc snapshot GUI, gắn metadata
chứa đáp án lên cả clue mở/úp, rồi yêu cầu mọi màn SOLVED và trace không chứa
metadata đó. Kiểm tra thêm hidden-data independence của KB/phân loại/Hint,
payload độc lập, lọc PARITY/COMPARE và region, verdict bị từ chối, input sai,
clue đầu ra lỗi, Restart và KB mâu thuẫn. Các test AgentKnowledge và kiến trúc
Agent không import Engine vẫn được giữ.

Kết quả: **90 test tích hợp/hợp đồng qua**; toàn bộ **527 passed,
97 subtests passed**, không có skip. Mẫu 3x3 mở 8 thẻ, 4x4 mở 15 thẻ và
5x5 mở 24 thẻ. [CSV bàn giao](../results/raw/20261123_engine_agent_api.csv) ghi
status, số lượt và SAT calls của Agent; không tính SAT calls kiểm tra lại ở
Engine, nên không so trực tiếp với CSV lộ trình task 26.

```powershell
python -m pytest tests/test_engine_agent_api.py tests/test_agent_knowledge.py tests/test_engine_verdict.py -q -rs
python -m pytest tests/ unit_tests/dpll.py unit_tests/dpll_stats.py -q -rs
```

Đường API đã được kiểm chứng độc lập với GUI. Chưa nối các nút GUI hoặc
`main.py --solve`; đó là caller có thể dùng ví dụ trên cho phần tích hợp tiếp.
Task sẵn sàng để review/merge, không tự đổi bảng phân công hoặc trạng thái PR.
