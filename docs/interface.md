# Hợp đồng dữ liệu puzzle JSON và loader

Schema v1 triển khai ngày 12/11/2026, giữ tên trường theo README. Đây là hợp đồng
cho dữ liệu đầu vào; kiểm tra tính đúng logic và nghiệm duy nhất là bước riêng.
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
`a` và `b` được phép giống nhau: loader không đánh giá tính đúng logic của clue.
`k` là integer (không nhận Boolean), `0 <= k <= số ô trong region`.

Region chỉ nhận đúng các trường theo loại:

| `kind` | Trường thêm | Quy định |
| --- | --- | --- |
| `ROW` | `index` | Integer từ 1 đến size |
| `COL` | `index` | Một chữ cột HOA trong bàn, ví dụ `B` |
| `NEIGHBORS` | `of` | Tọa độ ô trung tâm trong bàn |
| `CELLS` | `cells` | Danh sách tọa độ trong bàn, không trùng |

Hàng xóm gồm ngang, dọc và chéo, không gồm ô trung tâm. Góc/biên/giữa lần lượt
có 3/5/8 hàng xóm. `CELLS` có thể rỗng; khi đó k phải bằng 0.
Tất cả kết quả resolve region được sắp theo thứ tự hàng trước, cột sau.

```json
{"id": "c02", "type": "SAME", "a": "A1", "b": "B2"}
{"id": "c03", "type": "DIFFERENT", "a": "A1", "b": "B2"}
{"id": "c04", "type": "EXACTLY", "k": 2, "region": {"kind": "ROW", "index": 2}}
{"id": "c05", "type": "AT_LEAST", "k": 1, "region": {"kind": "COL", "index": "B"}}
{"id": "c06", "type": "AT_MOST", "k": 1, "region": {"kind": "NEIGHBORS", "of": "B2"}}
{"id": "c07", "type": "EXACTLY", "k": 0, "region": {"kind": "CELLS", "cells": []}}
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
Dataclass `frozen=True` trong `core.types`:

- `Puzzle(size: int, characters: tuple[Cell, ...])`.
- `Cell(cell, name, job, status: Status, revealed: bool, clue: Clue)`;
  cell/name/job là string.
- `Clue(id: str, type: ClueType, cell?, status?, a?, b?, k?, region?)`.
  Các trường không thuộc loại clue có giá trị `None`; status dùng `Status`,
  k dùng int, region dùng `Region`, cell/a/b dùng string.
- `Region(kind: RegionKind, index?, of_cell?, cells?)`.
  index dùng int cho ROW, string cho COL; JSON `of` ánh xạ thành `of_cell`;
  cells dùng tuple string. Trường không dùng là `None`, khác với tuple rỗng.

`resolve_region(region: Region, size: int) -> tuple[str, ...]` kiểm tra trường
và tọa độ của region, trả kết quả tất định. Core chỉ phụ thuộc thư viện chuẩn và
chính core; không import engine, encoder hoặc SAT.

Dataclass không tự validate khi khởi tạo trực tiếp. Dữ liệu đầu vào bên ngoài
phải đi qua `load_puzzle(path)` hoặc `parse_puzzle(data)`. Loader không sửa dữ
liệu nguồn, không giữ tham chiếu tới các list/dictionary có thể thay đổi.

**Ranh giới thông tin:** Puzzle và Cell chứa status cùng clue ẩn, chỉ dành cho
Game Engine. `revealed` ở đây là cấu hình khởi đầu; Engine quản lý trạng thái
chơi riêng. Agent không nhận Puzzle/Cell đầy đủ; Engine chỉ cung cấp clue đã
mở và trạng thái công khai. Public-state API sẽ được chốt trong task Engine.

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
python -m unittest discover -s tests -v
# Hoặc khi đã cài requirements.txt:
python -m pytest tests/
python -c "from griductive.engine.puzzle_loader import load_puzzle; print(load_puzzle('puzzles/3x3/p3x3_01.json'))"
```

Loader không kiểm tra clue đúng với đáp án, KB nhất quán, nghiệm duy nhất hay
khả năng giải tuần tự. Các kiểm tra này cần evaluator/SAT/Agent trong task sau.
`main.py` hiện vẫn là skeleton; đọc được puzzle chưa đồng nghĩa GUI/solver đã chạy.
