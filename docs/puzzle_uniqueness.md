# Task 27 — Kiểm tra nghiệm duy nhất bằng brute force

Nhánh `feat/d-puzzle-uniqueness-bruteforce`, đã đồng bộ task 26 tại `424f2da`
ngày 23/11/2026. Bộ nghiệm thu gồm đúng bảy màn trong
[test_set.json](puzzle_sources/test_set.json); mẫu FACT được kiểm tra thêm riêng.
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

Không có đường dẫn: đọc mọi `.json`
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

Kết quả lịch sử ngày 13/11/2026: **322 passed, 97 subtests passed, 1 skipped**.
Skip khi đó là readiness của task 26; xem cập nhật bộ dữ liệu bên dưới.

```powershell
python -m pytest tests/ unit_tests/dpll.py unit_tests/dpll_stats.py -q -rs
```

Test dataset tự kiểm tra brute force trên các màn 3×3/4×4, bên cạnh kiểm tra DPLL
đang có. Full brute force 5×5 chạy riêng bằng CLI, không nằm trong test nhanh.
Nếu thư mục tạm mặc định của pytest bị lỗi quyền, thêm
`--basetemp=.pytest_cache/bruteforce-tmp`. Nếu chưa có `python` trên PATH, dùng
`C:\Users\TuanKiet\.local\bin\python3.12.exe`.

**Cập nhật 23/11/2026:** [task 26](puzzle_dataset.md) có đủ bộ 3/3/1 và manifest
nguồn. Sau khi đối chiếu đề bài, bộ test dùng một bản phỏng theo tutorial và sáu
màn tự biên soạn từ cơ chế suy luận chính thức; không yêu cầu bảy bản xuất gốc.
PARITY/COMPARE của Duy đã được tích hợp vào nhánh dataset cùng DPLL mới của Phong.
Test nhanh đối chiếu brute force với DPLL cho mọi màn 3x3/4x4, và không còn skip
readiness. Bàn 5x5 vẫn kiểm tra đầy đủ bằng CLI riêng, không đưa vòng duyệt lớn
vào test nhanh. Kết quả của lần chạy đầy đủ được ghi trong tài liệu task 26.
Nghiệm thu của nhóm vẫn cần review và merge, tách khỏi trạng thái test xanh.

## Nghiệm thu đầy đủ task 27 ngày 23/11/2026

Giữ nguyên thuật toán brute force đã có. Không dùng SAT để cắt nhánh, không thêm
unit clause từ status ẩn và không giới hạn số cách gán khi kết luận UNIQUE.
Các thay đổi mới tập trung vào đồng bộ dữ liệu/phụ thuộc, bổ sung kiểm thử và
lưu bằng chứng của lần chạy đầy đủ, bao gồm 5x5.

| Puzzle | Ô chưa mở | Không gian gán | Brute force | DPLL trên biến ô |
| --- | ---: | ---: | --- | --- |
| `p3x3_02.json` | 8 | 256 | UNIQUE | UNIQUE, cùng đáp án |
| `p3x3_03.json` | 8 | 256 | UNIQUE | UNIQUE, cùng đáp án |
| `p3x3_04.json` | 8 | 256 | UNIQUE | UNIQUE, cùng đáp án |
| `p4x4_01.json` | 15 | 32.768 | UNIQUE | UNIQUE, cùng đáp án |
| `p4x4_02.json` | 15 | 32.768 | UNIQUE | UNIQUE, cùng đáp án |
| `p4x4_03.json` | 15 | 32.768 | UNIQUE | UNIQUE, cùng đáp án |
| `p5x5_01.json` | 24 | 16.777.216 | UNIQUE | UNIQUE, cùng đáp án |

Mẫu regression `p3x3_01.json` cũng UNIQUE sau 256 cách gán. Các màn được kiểm
tra bằng tất cả clue (kể cả thẻ úp) và chỉ status mở ban đầu. Không nhầm phép
kiểm tra offline này với dữ kiện được phép đưa vào vòng suy luận Agent.
Tổng bộ bảy màn duyệt **16.876.288** cách gán. CLI hoàn tất với exit code 0;
riêng màn 5x5 mất **108.764,109 ms** (khoảng 108,8 giây) trong lần chạy này.

Đối chiếu DPLL sử dụng `agent.uniqueness.count_solutions` với `DpllSolver` thật:
encode toàn bộ clue, thêm unit của thẻ mở ban đầu, lấy model rồi chặn model trên
biến chính. Mỗi màn cần hai SAT calls: một SAT và một UNSAT. Việc đối chiếu đáp
án lưu chỉ thực hiện sau khi mỗi thuật toán đã tìm nghiệm; hai witness cùng
khớp đáp án nên khớp nhau. Không dùng status ẩn để dựng công thức tìm nghiệm.

Bằng chứng:

- [Log CLI đầy đủ](../results/raw/20261123_puzzle_uniqueness.txt): kết luận,
  số cách gán đã duyệt và runtime cho từng file; đường dẫn được chuẩn hóa về
  tương đối với repository để không phụ thuộc thư mục máy cá nhân.
- [Bảng đối chiếu](../results/raw/20261123_puzzle_uniqueness.csv): tách bộ bảy màn
  khỏi regression, kết quả brute force/DPLL, witness, runtime và SHA-256 của
  từng file puzzle sau chuẩn hóa UTF-8/LF. Witness trong bảng là dữ liệu offline,
  không truyền cho Agent.

Test nhanh bổ sung EVEN/ODD, MORE/EQUAL/LESS và so sánh hai vùng có giao nhau.
Kiểm tra preflight phát hiện evaluator extension bị thiếu dù clue trước đó sai.
Một test cấm gọi encoder/DPLL trong brute force. Với từng fixture 3x3/4x4,
test còn yêu cầu số cách gán đã duyệt bằng toàn bộ không gian ô chưa mở.
Các ca UNSAT, MULTIPLE, đáp án lưu sai, không sửa input và lỗi CLI vẫn được giữ.

Kết quả: **75 test liên quan**, toàn bộ **506 passed, 97 subtests passed**,
không có skip. Lần chạy đầy đủ 5x5 được thực hiện riêng, không đưa 16 triệu
cách gán vào suite nhanh. Môi trường: Windows, Python 3.12.13; không timeout.

```powershell
python -m pytest tests/test_puzzle_uniqueness.py tests/test_puzzle_dataset.py -q -rs
python -m griductive.engine.puzzle_uniqueness
python -m pytest tests/ unit_tests/dpll.py unit_tests/dpll_stats.py -q -rs
```

Không thay `agent/uniqueness.py`, GUI hoặc vòng Auto Solve. Bộ kiểm chứng đã sẵn
sàng để reviewer đối chiếu trước khi đánh dấu task Done và merge.
