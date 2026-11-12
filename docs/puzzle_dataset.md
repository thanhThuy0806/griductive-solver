# Bộ puzzle kiểm thử — bản nháp

Kiểm tra nguồn ngày 13/11/2026. Mục tiêu: **3 màn 3×3, 3 màn 4×4, 1 màn 5×5**
từ Griductive chính thức, giữ nguyên logic và giải được từ thông tin công khai.
Hiện **0/7 màn được nhập**, không đánh dấu task Done. Mẫu FACT `p3x3_01.json`
được giữ làm regression, không tính vào bộ bảy màn. Không tạo màn thay thế.

## Nền triển khai

Nhánh `feat/d-puzzle-test-set` dựa trên `feat/d-game-engine-verdict` (`826a8fd`).
Đã đối chiếu remote: Engine/schema của Kiệt, core/encoder/evaluator của Duy,
entailment của Thúy và DPLL của Phong đã có trong nền này. Không lấy thêm GUI.
PR nền Engine: <https://github.com/thanhThuy0806/griductive-solver/pull/2>.

## Nguồn đã kiểm tra

- [Tác giả giới thiệu game](https://www.reddit.com/r/playmygame/comments/1r5fdze/griductive_a_detectivestyle_logic_puzzle_game/)
  từng nêu hỗ trợ 3×3, 4×4 và 5×5. Đây không phải bằng chứng rằng dữ liệu cả ba
  kích thước vẫn có sẵn trong phiên bản hiện tại.
- [Tài liệu ứng dụng Reddit](https://developers.reddit.com/apps/griductive)
  mô tả endpoint JSON cũ `data.griductive.com`; host này hiện trả trang HTML.
- [Tutorial chính thức](https://knotwise.games/games/griductive/tutorial): tìm được
  dữ liệu đầy đủ trong [client công khai](https://knotwise.games/_next/static/chunks/14bm8mnorovtd.js),
  export `tutorialPuzzle`, ID `griductive-tutorial`, ngày `tutorial`, bàn 3×3.
  Lưu wire JSON trong [puzzle_sources/griductive_tutorial.json](puzzle_sources/griductive_tutorial.json).
  Đây là ứng viên chờ hỗ trợ, **không phải JSON của loader dự án**.
  SHA-256 của JSON UTF-8 sau chuẩn hóa xuống dòng LF:
  `0BC8ED5254FCFBA4C5A54EF03F7A88AB69FFCC69C026890F38AE6A0D73AE40C3`.
- Client game hiện dùng CDN `data.knotwise.games/griductive/daily/YYYY/MM/DD.json`.
  Đã đọc bảy màn trong cửa sổ miễn phí, không truy cập màn bị khóa. Tất cả là 4 cột
  × 5 hàng (20 ô); không cắt hàng, thêm ô hoặc đổi sang bàn vuông.

| ID/ngày màn | JSON chính thức | Kích thước | Kết quả |
| --- | --- | --- | --- |
| griductive-2026-11-06 | [06/11](https://data.knotwise.games/griductive/daily/2026/11/06.json) | 4×5 | Không đúng kích thước; có clue ghép, liên thông, so sánh, chẵn/lẻ, flavor |
| griductive-2026-11-07 | [07/11](https://data.knotwise.games/griductive/daily/2026/11/07.json) | 4×5 | Không đúng kích thước; có clue duy nhất theo số hàng xóm, giao vùng, flavor |
| griductive-2026-11-08 | [08/11](https://data.knotwise.games/griductive/daily/2026/11/08.json) | 4×5 | Không đúng kích thước; có liên thông, hướng, tổng vùng, flavor |
| griductive-2026-11-09 | [09/11](https://data.knotwise.games/griductive/daily/2026/11/09.json) | 4×5 | Không đúng kích thước; có cực trị, giao vùng, chẵn/lẻ, flavor |
| griductive-2026-11-10 | [10/11](https://data.knotwise.games/griductive/daily/2026/11/10.json) | 4×5 | Không đúng kích thước; có clue ghép, giao vùng, flavor |
| griductive-2026-11-11 | [11/11](https://data.knotwise.games/griductive/daily/2026/11/11.json) | 4×5 | Không đúng kích thước; có liên thông, so sánh, chẵn/lẻ, flavor |
| griductive-2026-11-12 | [12/11](https://data.knotwise.games/griductive/daily/2026/11/12.json) | 4×5 | Không đúng kích thước; có clue ghép, duy nhất theo vùng, chẵn/lẻ, flavor |

`flavor` là lời thoại không mang ràng buộc; schema hiện bắt buộc mỗi thẻ có một
clue trong sáu loại cơ bản. Không thay lời thoại bằng FACT hay tự thêm ràng buộc.
Không lưu bảy màn 4×5 trong thư mục puzzle vì đã loại ngay ở tiêu chí kích thước.

## Ánh xạ tutorial và phần còn thiếu

Chỉ số `person`/`initialReveals` của nguồn tính từ 0 theo row-major; row/col tính
từ 1. Thẻ mở ban đầu là Hugo ở B3, INNOCENT. Đáp án CRIMINAL: B1, B2, A3.
Giữ nguyên tên, nghề, thứ tự và trạng thái trong file wire; không suy diễn clue mới.

| Thẻ | Atom gốc | Ánh xạ/điều kiện |
| --- | --- | --- |
| A1 Ada | all_units_have_at_least_n_traits | Chờ clue ghép: AT_LEAST 1 cho từng hàng, vẫn trên cùng thẻ |
| B1 Ben | both_traits_are_neighbors_in_unit | Chờ đếm và liên thông của hai tội phạm cột B; không thay bằng SAME |
| C1 Cara | number_of_traits_in_unit | EXACTLY 1, ROW 1 |
| A2 Dev | number_of_traits_in_unit | EXACTLY 1, ROW 2 |
| B2 Elle | is_one_of_n_traits_in_unit | Chờ ghép FACT B2 CRIMINAL và EXACTLY 2, COL B |
| C2 Finn | more_traits_in_unit_than_unit | Chờ so sánh số tội phạm COL A > COL C |
| A3 Gwen | number_of_traits | EXACTLY 3 trên CELLS gồm cả 9 ô |
| B3 Hugo | number_of_traits_in_unit | EXACTLY 0, COL C |
| C3 Isla | number_of_traits_in_unit | EXACTLY 1, NEIGHBORS của C3 |

Chưa xuất puzzle của loader: các ánh xạ khả dụng ở trên không đủ để giữ nguyên
toàn bộ màn. Không chia clue ghép sang thẻ khác, không bỏ clue dù có thể dư thừa
đối với một lộ trình giải. Nhóm tên/nghề chỉ được đổi thành CELLS khi đúng tập ô.

## Bảng bàn giao và điều kiện tiếp tục

Tên file dưới đây là **dự kiến**, chưa phải file tồn tại hay màn được nghiệm thu.

| Vị trí | Nguồn ứng viên | Trạng thái | Phụ trách/đầu vào cần có |
| --- | --- | --- | --- |
| p3x3_02.json | griductive-tutorial | Chờ hỗ trợ clue | Duy: core/encoder/evaluator cho clue ghép, liên thông, so sánh; Kiệt: loader/hợp đồng tương ứng |
| p3x3_03.json | Chưa có | Chờ nguồn | Kiệt: màn chính thức 3×3 đầy đủ, khác cách suy luận |
| p3x3_04.json | Chưa có | Chờ nguồn | Kiệt: màn chính thức 3×3 đầy đủ, khác hai màn trên |
| p4x4_01.json | Chưa có | Chờ nguồn | Kiệt: màn chính thức 4×4 đầy đủ |
| p4x4_02.json | Chưa có | Chờ nguồn | Kiệt: màn chính thức 4×4 với chuỗi suy luận khác |
| p4x4_03.json | Chưa có | Chờ nguồn | Kiệt: màn chính thức 4×4 với chuỗi suy luận khác |
| p5x5_01.json | Chưa có | Chờ nguồn | Kiệt: màn chính thức 5×5 để kiểm tra luồng mở thẻ/CNF |

Nguồn đầy đủ cần có bàn, tên/nghề, đáp án, clue trên từng thẻ và thẻ mở ban đầu;
chỉ ảnh một phần hay lời giải walkthrough chưa đủ để nhập. Nếu màn mới có clue
ngoài sáu loại hiện tại, ghi rõ atom/thẻ và chờ hỗ trợ tương ứng trước khi xuất.
Khả năng hỗ trợ bàn chữ nhật không giải quyết yêu cầu bộ dữ liệu bàn vuông.

Auto Solve/uniqueness của Thúy và runner thực nghiệm của Phong chưa cần cho
kiểm chứng này. Không sửa thay các module đó. Khi có nguồn/commit hỗ trợ mới,
đối chiếu API, lấy đúng phần phụ thuộc, nhập màn và chạy lại kiểm chứng; không
thiết lập theo dõi nền. Chỉ cập nhật hợp đồng khi thực sự triển khai API mới.

## Kiểm chứng và nghiệm thu

`tests/test_puzzle_dataset.py` tự tìm mọi file JSON chuẩn dưới `puzzles/`:

1. Loader kiểm tra cấu trúc, kích thước thư mục và số ô.
2. Evaluator trực tiếp kiểm tra mọi clue, kể cả clue chưa mở, với đáp án riêng.
3. Encoder tạo CNF của toàn bộ clue cùng unit clauses của **thẻ mở ban đầu**.
   Thay giá trị đáp án vào CNF để xác nhận đáp án thỏa mãn; sau đó thêm một clause
   loại đáp án trên biến ô và yêu cầu UNSAT. Không khóa các đáp án ẩn trong KB;
   biến phụ vẫn tự do, nên chỉ kiểm tra nghiệm duy nhất trên các biến ô.
4. Engine cung cấp snapshot công khai; chọn ô chưa mở đầu tiên theo row-major
   có classification bắt buộc, submit rồi lấy snapshot mới. Không dùng đáp án
   riêng để chọn nước đi. Nếu không có nước đi, báo tên file, bước và ô còn úp.

Test lộ trình ghi `reveal_steps`, `primary_vars`, `aux_vars`, `clauses` bằng pytest
properties (có trong JUnit XML). Mẫu hiện có: **8 lượt mở, 9 biến chính, 0 biến phụ,
10 clauses** ở CNF đầy đủ tính cả trạng thái ban đầu. Với 5×5 tương lai phải mở hết
25 ô theo cấu hình nguồn và ghi cùng số liệu; chưa đặt ngưỡng runtime theo máy.
Các ca âm chỉ dựng trong bộ nhớ để kiểm tra phát hiện clue sai, nhiều nghiệm và
bị kẹt; không tính chúng vào bộ bảy màn.

```powershell
python -m pytest tests/ unit_tests/dpll.py unit_tests/dpll_stats.py -q -rs
python -m pytest tests/test_puzzle_dataset.py -q -rs --junitxml=results/raw/puzzle_dataset.xml
```

Nếu `python` chưa có trên PATH, dùng Python 3.12 đã cài tại
`C:\Users\TuanKiet\.local\bin\python3.12.exe`.

Kết quả bản nháp: **299 passed, 97 subtests passed, 1 skipped**. Readiness bị skip
có chủ đích vì 0/7 màn chính thức; test xanh không có nghĩa bộ dữ liệu đã đủ.
Không đổi skip thành pass hoặc xóa điều kiện để nghiệm thu sớm.

Giữ Draft PR dựa trên nhánh Engine. Chuyển base về `main` khi nền Engine được
merge; chỉ ready khi đủ 3/3/1 màn chính thức, giữ logic gốc, cả bốn lớp kiểm chứng
đều đạt và không còn readiness skip/phụ thuộc bắt buộc. Task Done sau review và
merge. Chưa benchmark 5×5 vì chưa có nguồn màn phù hợp.
