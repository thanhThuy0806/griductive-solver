# Task 26 - Bộ puzzle kiểm thử 3x3, 4x4, 5x5

Cập nhật 23/11/2026: đã có **7/7 màn** theo phân công nhóm: 3 màn 3x3,
3 màn 4x4 và 1 màn stress 5x5. Mẫu FACT cũ `p3x3_01.json` được giữ nguyên
làm regression riêng, không tính vào bộ bảy màn.

**Nguồn gốc:** một bản phỏng theo tutorial chính thức và sáu màn tự biên soạn
dựa trên các cơ chế suy luận trong hướng dẫn chính thức. Không gọi những JSON
này là bản xuất nguyên vẹn từ game. Các màn lớn được chọn qua tìm kiếm ứng viên
có seed, rồi kiểm chứng và xem lại từng clue; không tuyên bố tất cả được viết tay.

## Đối chiếu đề bài

Đề `AI - Project 2.pdf`, mục 2.1, 3.2 và 4.5, yêu cầu bàn vuông, tên theo alphabet,
sáu clue cơ bản, ít nhất hai extension và thực nghiệm trên nhiều màn 3x3/4x4.
5x5 là stress case tùy chọn trong đề và được đưa vào phân công nhóm này.
Đề không bắt buộc nhập màn từ game chính thức. Điều kiện nguồn chính thức trong
bản nháp ngày 13/11 là giả định cũ, được thay bằng yêu cầu tham khảo và ghi nguồn.

Chỉ dùng clue có trong code chung: FACT, SAME, DIFFERENT, EXACTLY, AT_LEAST,
AT_MOST, PARITY và COMPARE. Không cần chờ compound/connectivity để hoàn tất
bộ test này. Mỗi màn có một thẻ mở ban đầu, mọi clue đều đúng, có đúng một nghiệm
trên biến ô và mở hết được bằng chứng minh từ dữ kiện công khai.

## Tài liệu tham khảo và cách sử dụng

| Nguồn | Phần được tham khảo |
| --- | --- |
| [How to Play Griductive](https://knotwise.games/games/griductive/how-to-play) | Tutorial 3x3, đếm chính xác, tám hàng xóm và lộ trình mở thẻ |
| [Griductive Strategy](https://knotwise.games/games/griductive/strategy) | Giao vùng, sử dụng hết ngân sách số lượng, kết hợp parity/count và phối hợp các clue được mở ở những thời điểm khác nhau |
| [Tutorial tương tác](https://knotwise.games/games/griductive/tutorial) | Bàn, tên/nghề, đáp án và thẻ mở ban đầu của trường hợp tham khảo |

File [griductive_tutorial.json](puzzle_sources/griductive_tutorial.json) giữ dữ liệu
wire gốc đã lưu trước đây, chỉ dùng để đối chiếu, không phải input của loader.
Hướng dẫn chính thức hiện mô tả daily 4 cột x 5 hàng; không cắt các daily đó
thành bàn vuông hoặc nhận là màn gốc 4x4/5x5. Không dùng dữ liệu từ gói trả phí
hoặc sao chép puzzle từ repository bài tập của nhóm khác.

### Những thay đổi trong bản phỏng theo tutorial

`p3x3_02.json` giữ bàn 3x3, tên/nghề, đáp án và Hugo ở B3 mở ban đầu:

| Thẻ | Điều chỉnh so với tutorial |
| --- | --- |
| A1 Ada | Thu hẹp điều kiện mỗi hàng có ít nhất một tội phạm thành AT_LEAST 1 ở hàng 3 |
| B1 Ben | Giữ EXACTLY 2 ở cột B; bỏ phần liên thông chưa được hỗ trợ |
| B2 Elle | Giữ EXACTLY 2 ở cột B; bỏ FACT về chính Elle, vốn đã được chứng minh khi mở thẻ |
| Sáu thẻ còn lại | Chuyển trực tiếp sang EXACTLY hoặc COMPARE của dự án |

Đây là thay đổi nội dung puzzle có chủ ý, không khẳng định tương đương đầy đủ
với bản gốc. Đáp án và khả năng giải của phiên bản mới được kiểm tra riêng.

## Bộ so sánh cố định

[test_set.json](puzzle_sources/test_set.json) liệt kê chính xác bảy file, nguồn,
kiểu biên soạn và mức tối thiểu của `joint_steps`. Dùng danh sách này cho các
so sánh thực nghiệm; không đưa mẫu FACT vào cùng tập mà không ghi rõ.
Các tham số search trong manifest là thông tin biên soạn, không dùng khi chơi;
JSON đã chốt là đầu vào tái lập, không sinh puzzle ngẫu nhiên lúc chạy test.

| File | Trọng tâm | Thẻ mở | Lượt mở | Joint steps | Biến chính/phụ | Clauses đầy đủ |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `p3x3_02.json` | Tutorial phỏng theo: cột rỗng, hàng xóm, số lượng còn lại | B3 | 8 | 1 | 9/0 | 229 |
| `p3x3_03.json` | Hai ngân sách giao nhau và loại trừ nhị nguyên | A3 | 8 | 2 | 9/0 | 67 |
| `p3x3_04.json` | Parity kết hợp so sánh vùng nghiêm ngặt | B2 | 8 | 3 | 9/0 | 66 |
| `p4x4_01.json` | Ngân sách cột và đếm hàng xóm | A4 | 15 | 2 | 16/0 | 248 |
| `p4x4_02.json` | Giao các vùng hàng xóm, nhiều bước phối hợp | A4 | 15 | 7 | 16/0 | 194 |
| `p4x4_03.json` | Clue mới mở phối hợp parity và compare | A4 | 15 | 3 | 16/0 | 137 |
| `p5x5_01.json` | Stress 25 ô, trộn đếm, parity, compare và quan hệ | A5 | 24 | 5 | 25/0 | 375 |

`joint_steps` là số bước trong lộ trình row-major mà **không clue đã mở đơn lẻ
nào đủ chứng minh nước đi**, ngay cả khi được dùng tất cả trạng thái công khai
trước bước đó. Các clue phải phối hợp. Đây là thước đo cấu trúc suy luận, không
phải điểm độ khó được người chơi đánh giá. Không đồng nhất kích thước lớn hơn
với khó hơn: màn 4x4 thứ hai có nhiều joint steps hơn màn stress 5x5.

Mẫu FACT có 0 joint steps. Test giữ các ngưỡng của bảy màn để tránh vô tình
thay chúng bằng chuỗi FACT hoặc đưa quá nhiều đáp án vào trạng thái ban đầu.
Các seed/ứng viên được chọn cho bốn màn lớn: 260401/36, 260402/49,
260403/23 và 260501/23. Giao vùng được lưu bằng CELLS với đúng tập ô.

## Phụ thuộc đã tích hợp

Nhánh `feat/d-puzzle-test-set` kế thừa Engine, AgentKnowledge và công cụ kiểm
tra brute force đã có. Lấy thêm các commit sau, giữ tác giả và ghi nguồn cherry-pick:

| Commit nguồn | Nội dung |
| --- | --- |
| `09c2092` của Duy | PARITY/COMPARE, core/loader/projector và test; thống nhất Region.of với alias of_cell |
| `52ffda8`, `1d02e7c` của Phong | Bộ test DPLL, pure literal, MOM và timeout |

Không thay LogicAgent, GUI, main.py hoặc runner thực nghiệm của thành viên khác.
Lộ trình kiểm thử gọi EntailmentChecker qua cầu nối Engine thật; chưa phải phép
đo Auto Solve/GUI hay benchmark so sánh cấu hình solver.

## Kiểm chứng

`tests/test_puzzle_dataset.py` kiểm tra mọi JSON puzzle, gồm cả mẫu regression:

1. Loader kiểm tra schema, kích thước, tọa độ và thứ tự tên.
2. Evaluator độc lập kiểm tra từng clue với đáp án lưu.
3. Encoder tạo CNF của mọi clue cùng unit của **thẻ mở ban đầu**. Thay đáp án
   vào CNF rồi kiểm tra phần dư; thêm clause loại đáp án trên biến chính để
   chứng minh không có nghiệm thứ hai. Không khóa các status ẩn trong CNF.
4. Engine cung cấp AgentKnowledge. Chỉ phân loại ô chưa mở từ dữ kiện công khai,
   chọn ô bắt buộc đầu tiên theo row-major, submit rồi dựng lại dữ kiện.
5. Brute force độc lập đối chiếu mọi màn 3x3/4x4. Màn 5x5 chạy riêng bằng CLI.
6. Kiểm tra bộ 3/3/1, độ bao phủ tám loại clue/bốn region và ngưỡng joint steps.
   Không coi timeout là bằng chứng UNSAT/duy nhất.

Chạy từ gốc repository (Python 3.10+):

```powershell
python -m pytest tests/ unit_tests/dpll.py unit_tests/dpll_stats.py -q -rs
python -m pytest tests/test_puzzle_dataset.py -q -o junit_family=legacy --junitxml=results/raw/puzzle_dataset.xml
python -m griductive.engine.puzzle_uniqueness puzzles/5x5/p5x5_01.json
```

Nếu thư mục tạm mặc định bị lỗi quyền, tạo `.pytest_cache` rồi thêm
`--basetemp=.pytest_cache/task26`. Nếu chưa có `python` trên PATH của máy Kiệt,
dùng `C:\Users\TuanKiet\.local\bin\python3.12.exe`.

Kết quả 23/11/2026: dataset **44 passed**; toàn bộ **497 passed,
97 subtests passed**, không còn readiness skip. CLI brute force 5x5 đã duyệt đủ
**16.777.216** cách gán: **UNIQUE**, nghiệm khớp đáp án lưu, exit code 0.
Runtime riêng của vòng kiểm chứng này là **118.921,387 ms** (khoảng 118,9 giây);
đây là kết quả chạy thực, độc lập với DPLL, không suy ra từ test SAT.

[CSV kiểm chứng](../results/raw/20261123_puzzle_dataset.csv) lưu số biến/clause,
SAT calls, decisions, propagations, backtracks, số lượt mở, runtime, joint steps
và thứ tự mở. Chỉ đếm SAT trong luồng chơi công khai, gồm cả kiểm tra verdict
lần nữa của Engine; loại các truy vấn phụ để đo joint steps/uniqueness.
`clauses` là CNF đầy đủ, không phải số clause ban đầu. Runtime là một lượt đo
trên Windows với Python 3.12.13 và DPLL từ `1d02e7c` (pure literal/MOM bật,
không đặt timeout). Không đặt ngưỡng runtime cứng hoặc suy ra độ khó của con người.

Bộ dữ liệu đủ điều kiện kỹ thuật để review task 26. Trạng thái Done của nhóm
vẫn cần reviewer kiểm tra và merge; không tự thay đổi bảng phân công.
