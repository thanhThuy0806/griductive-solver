# Task 27 — Kiểm tra nghiệm duy nhất bằng brute force

Nhánh `feat/d-puzzle-uniqueness-bruteforce`, dựa trên task 26 tại `45e7c84`.
Công cụ kiểm tra dữ liệu dùng loader và evaluator hiện có; không thay phần
`agent/uniqueness.py` của Thúy. Không thay schema JSON hoặc luồng Game Engine.

## Định nghĩa và API

Một nghiệm là cách gán Boolean cho mọi ô (`True` = CRIMINAL), thỏa **tất cả clue**
và trạng thái thẻ mở ban đầu. Clue của thẻ úp vẫn tham gia kiểm tra. Điều này
khác với khả năng giải tuần tự chỉ từ thông tin công khai: task 26 kiểm tra riêng
lộ trình đó.

```python
from griductive.engine.puzzle_loader import load_puzzle
from griductive.engine.puzzle_uniqueness import check_uniqueness

puzzle = load_puzzle("puzzles/3x3/p3x3_01.json")
result = check_uniqueness(puzzle)
assert result.status == "UNIQUE"
assert result.assignments_checked == 256
```

`check_uniqueness(puzzle: Puzzle) -> UniquenessResult` yêu cầu puzzle đã qua
loader, không sửa đầu vào. Các trạng thái ô ẩn không được dùng trong tìm nghiệm.

| Trường kết quả | Ý nghĩa |
| --- | --- |
| `status` | `UNSAT`, `UNIQUE`, `MULTIPLE` |
| `solutions` | Tuple chứa 0, 1 hoặc 2 ánh xạ ô → Boolean, theo thứ tự duyệt |
| `assignments_checked` | Số cách gán đã được kiểm tra, không tính lượt kiểm tra evaluator ban đầu |
| `runtime_ms` | Thời gian tìm nghiệm, gồm kiểm tra evaluator ban đầu |

Result là frozen dataclass; từng dictionary nghiệm vẫn có thể sửa nhưng độc lập
với nhau và với puzzle. `MULTIPLE` chỉ chứng minh ít nhất hai nghiệm, không phải
đếm tổng số nghiệm.

Thuật toán cố định ô mở, lấy các ô chưa mở theo row-major, rồi duyệt
`itertools.product((False, True), repeat=số_ô_chưa_mở)`. Với mỗi cách gán, evaluator
kiểm tra clue và dừng kiểm tra cách gán đó ở clue sai đầu tiên. Lưu tối đa hai bản
sao nghiệm; không giữ toàn bộ không gian cách gán. Chỉ dừng sớm khi có nghiệm thứ
hai; `UNSAT` và `UNIQUE` luôn cần duyệt hết. CNF/DPLL không tham gia thuật toán.

Trước vòng duyệt, gọi riêng từng evaluator với một cách gán đầy đủ gồm các ô mở
và các ô còn lại gán False. Giá trị đúng/sai ở lượt này không dùng để loại nghiệm;
lỗi thiếu evaluator hay lỗi dữ liệu được truyền cho bên gọi thay vì báo UNSAT.

## Chạy kiểm chứng

Từ thư mục gốc repository:

```powershell
python -m griductive.engine.puzzle_uniqueness
python -m griductive.engine.puzzle_uniqueness puzzles/3x3/p3x3_01.json
python -m griductive.engine.puzzle_uniqueness puzzles/5x5/p5x5_01.json
```

Lệnh cuối dành cho khi đã có file 5×5 phù hợp. Không có đường dẫn: đọc mọi `.json`
trong `puzzles/3x3`, `4x4`, `5x5` theo vị trí repository, kể cả chạy từ thư mục khác.
Đường dẫn truyền rõ được hiểu tương đối với thư mục hiện tại. Không đọc nguồn chờ
trong `docs/puzzle_sources/`.

Mỗi file có tên, kích thước, kết luận, số cách gán và runtime. MULTIPLE in hai
nghiệm. Sau UNIQUE, CLI mới đối chiếu nghiệm với đáp án lưu; không khớp sẽ báo
`ERROR: unique solution does not match stored answer`. Lỗi từng file không cản
kiểm tra file tiếp theo. Exit code 0 chỉ khi mọi file được chọn UNIQUE và khớp
đáp án; code 1 khi có lỗi, UNSAT, MULTIPLE hoặc không tìm thấy file. Ctrl+C trả
code 130 cùng thông báo chưa kiểm chứng xong.

Không có timeout. Bàn 5×5 với một ô mở cần tối đa 16.777.216 cách gán; thời gian
phụ thuộc clue và máy. Bài chạy bị ngắt không được coi là bằng chứng duy nhất.

## Kết quả và bàn giao

Mẫu `p3x3_01.json`: **UNIQUE**, duyệt **256** cách gán, nghiệm khớp đáp án lưu.
Đã chạy cả lệnh mặc định và lệnh truyền rõ file, cùng kết quả. Runtime tham khảo
khoảng 0,3 ms trên máy kiểm tra ngày 13/11/2026; không dùng làm ngưỡng nghiệm thu.

Test bao phủ 0/1/ít nhất 2 nghiệm, nghiệm cuối thứ tự duyệt, không dùng đáp án ẩn,
clue ẩn mâu thuẫn với trạng thái mở, input không bị sửa, witness độc lập và lỗi
evaluator. Đối chiếu DPLL trên các ca xác định trước bao phủ sáu clue/bốn region.
Test CLI bao phủ tìm file mặc định, không có file, lỗi từng file, đáp án sai và
hai witness. Fixture 4×4/5×5 với ít ô chưa mở chỉ kiểm tra xử lý kích thước.

Kiểm thử toàn bộ: **322 passed, 97 subtests passed, 1 skipped**. Skip duy nhất
là readiness của task 26 do thiếu bộ bảy màn chính thức.

```powershell
python -m pytest tests/ unit_tests/dpll.py unit_tests/dpll_stats.py -q -rs
```

Test dataset tự kiểm tra brute force trên các màn 3×3/4×4, bên cạnh kiểm tra DPLL
đang có. Full brute force 5×5 chạy riêng bằng CLI, không nằm trong test nhanh.
Nếu thư mục tạm mặc định của pytest bị lỗi quyền, thêm
`--basetemp=.pytest_cache/bruteforce-tmp`. Nếu chưa có `python` trên PATH, dùng
`C:\Users\TuanKiet\.local\bin\python3.12.exe`.

**Công cụ và mẫu hiện có đã kiểm chứng; bộ bảy màn chưa được nghiệm thu.**
[Task 26](puzzle_dataset.md) vẫn thiếu màn chính thức và evaluator cho clue mới.
Giữ Draft PR dựa trên nhánh task 26. Khi có dữ liệu/hỗ trợ, chạy CLI đầy đủ trên
3 màn 3×3, 3 màn 4×4 và 1 màn 5×5, đối chiếu DPLL và đáp án rồi ghi kết quả.
Chỉ hoàn tất mục tiêu "mỗi puzzle có đúng một nghiệm" khi đủ bảy màn đều đạt,
đã review và merge; không coi test readiness bị skip là đã nghiệm thu.
