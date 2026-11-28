# Phân tích Thực nghiệm Bộ giải DPLL — Griductive

**Tệp CSV nguồn:** `dpll_experiments.csv`  
**Tổng số lượt chạy được giữ lại:** 30 (giữ nguyên toàn bộ `SOLVED`, `TIMEOUT`, `STUCK`, `INCONSISTENT`, `ERROR`)

## 1. Bảng tổng hợp theo Cấu hình và Kích thước lưới

| config | size | grid | total_runs | solved | timeout | stuck | inconsistent | error | solve_rate_pct | avg_primary_vars | avg_aux_vars | avg_clauses | avg_sat_calls | avg_decisions | avg_propagations | avg_backtracks | avg_steps | avg_runtime_ms | max_runtime_ms | avg_sat_runtime_ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dpll_full | 3 | 3x3 | 12 | 12 | 0 | 0 | 0 | 0 | 100.0 | 9.0 | 0.0 | 101.0 | 57.5 | 16.5 | 331.5 | 1.5 | 8.0 | 8.21 | 14.77 | 2.94 |
| dpll_full | 4 | 4x4 | 12 | 12 | 0 | 0 | 0 | 0 | 100.0 | 16.0 | 0.0 | 174.8 | 186.0 | 73.2 | 1767.5 | 4.0 | 15.0 | 37.14 | 63.55 | 20.08 |
| dpll_full | 5 | 5x5 | 6 | 6 | 0 | 0 | 0 | 0 | 100.0 | 25.0 | 0.0 | 262.5 | 445.5 | 510.5 | 5866.0 | 1.0 | 24.0 | 83.96 | 114.73 | 51.26 |

## 2. Bảng kết quả chi tiết từng màn chơi (Giữ toàn bộ các trường hợp)

| puzzle_id | size | config | status | primary_vars | aux_vars | clauses | sat_calls | decisions | propagations | backtracks | steps | runtime_ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p3x3_01 | 3 | dpll_full | SOLVED | 9 | 0 | 18 | 72 | 0 | 368 | 0 | 8 | 3.1897 |  |
| p3x3_01 | 3 | dpll_full | SOLVED | 9 | 0 | 18 | 72 | 0 | 368 | 0 | 8 | 3.0685 |  |
| p3x3_01 | 3 | dpll_full | SOLVED | 9 | 0 | 18 | 72 | 0 | 368 | 0 | 8 | 3.1159 |  |
| p3x3_02 | 3 | dpll_full | SOLVED | 9 | 0 | 237 | 50 | 15 | 326 | 0 | 8 | 14.7692 |  |
| p3x3_02 | 3 | dpll_full | SOLVED | 9 | 0 | 237 | 50 | 15 | 326 | 0 | 8 | 12.2986 |  |
| p3x3_02 | 3 | dpll_full | SOLVED | 9 | 0 | 237 | 50 | 15 | 326 | 0 | 8 | 11.9293 |  |
| p3x3_03 | 3 | dpll_full | SOLVED | 9 | 0 | 75 | 56 | 19 | 323 | 0 | 8 | 5.9805 |  |
| p3x3_03 | 3 | dpll_full | SOLVED | 9 | 0 | 75 | 56 | 19 | 323 | 0 | 8 | 6.113 |  |
| p3x3_03 | 3 | dpll_full | SOLVED | 9 | 0 | 75 | 56 | 19 | 323 | 0 | 8 | 5.8741 |  |
| p3x3_04 | 3 | dpll_full | SOLVED | 9 | 0 | 74 | 52 | 32 | 309 | 6 | 8 | 10.9563 |  |
| p3x3_04 | 3 | dpll_full | SOLVED | 9 | 0 | 74 | 52 | 32 | 309 | 6 | 8 | 10.4657 |  |
| p3x3_04 | 3 | dpll_full | SOLVED | 9 | 0 | 74 | 52 | 32 | 309 | 6 | 8 | 10.7721 |  |
| p4x4_01 | 4 | dpll_full | SOLVED | 16 | 0 | 263 | 203 | 20 | 1947 | 2 | 15 | 27.2065 |  |
| p4x4_01 | 4 | dpll_full | SOLVED | 16 | 0 | 263 | 203 | 20 | 1947 | 2 | 15 | 27.0258 |  |
| p4x4_01 | 4 | dpll_full | SOLVED | 16 | 0 | 263 | 203 | 20 | 1947 | 2 | 15 | 27.176 |  |
| p4x4_02 | 4 | dpll_full | SOLVED | 16 | 0 | 209 | 163 | 216 | 1457 | 14 | 15 | 63.5462 |  |
| p4x4_02 | 4 | dpll_full | SOLVED | 16 | 0 | 209 | 163 | 216 | 1457 | 14 | 15 | 63.4704 |  |
| p4x4_02 | 4 | dpll_full | SOLVED | 16 | 0 | 209 | 163 | 216 | 1457 | 14 | 15 | 61.2712 |  |
| p4x4_03 | 4 | dpll_full | SOLVED | 16 | 0 | 152 | 174 | 9 | 1823 | 0 | 15 | 38.7414 |  |
| p4x4_03 | 4 | dpll_full | SOLVED | 16 | 0 | 152 | 174 | 9 | 1823 | 0 | 15 | 38.0443 |  |
| p4x4_03 | 4 | dpll_full | SOLVED | 16 | 0 | 152 | 174 | 9 | 1823 | 0 | 15 | 39.309 |  |
| p4x4_04 | 4 | dpll_full | SOLVED | 16 | 0 | 75 | 204 | 48 | 1843 | 0 | 15 | 20.1586 |  |
| p4x4_04 | 4 | dpll_full | SOLVED | 16 | 0 | 75 | 204 | 48 | 1843 | 0 | 15 | 19.984 |  |
| p4x4_04 | 4 | dpll_full | SOLVED | 16 | 0 | 75 | 204 | 48 | 1843 | 0 | 15 | 19.8058 |  |
| p5x5_01 | 5 | dpll_full | SOLVED | 25 | 0 | 399 | 366 | 894 | 4967 | 2 | 24 | 114.7339 |  |
| p5x5_01 | 5 | dpll_full | SOLVED | 25 | 0 | 399 | 366 | 894 | 4967 | 2 | 24 | 113.9849 |  |
| p5x5_01 | 5 | dpll_full | SOLVED | 25 | 0 | 399 | 366 | 894 | 4967 | 2 | 24 | 111.426 |  |
| p5x5_02 | 5 | dpll_full | SOLVED | 25 | 0 | 126 | 525 | 127 | 6765 | 0 | 24 | 54.7496 |  |
| p5x5_02 | 5 | dpll_full | SOLVED | 25 | 0 | 126 | 525 | 127 | 6765 | 0 | 24 | 55.3178 |  |
| p5x5_02 | 5 | dpll_full | SOLVED | 25 | 0 | 126 | 525 | 127 | 6765 | 0 | 24 | 53.5272 |  |

## 3. Các biểu đồ đã xuất

- `01_runtime_by_puzzle.png`
- `02_scaling_by_size.png`
- `03_search_effort_per_puzzle.png`

## 4. Nhận xét chính (Observations)

- **Tỉ lệ hoàn thành tổng thể (giữ toàn bộ dòng kết quả):** 30/30 lượt chạy giải thành công (100.0%). Phân bố trạng thái: SOLVED: 30.
- **Độ mở rộng từ lưới 3x3 lên 5x5 (dpll_full):** số mệnh đề trung bình tăng từ 101.0 lên 262.5, số SAT calls trung bình tăng từ 57.5 lên 445.5 (7.75x), và thời gian chạy trung bình tăng từ 8.21 ms lên 83.96 ms (10.23x).
- **Hiệu quả lan truyền đơn vị (dpll_full):** 20,128 propagations so với 1,380 decisions (14.59 propagations/decision) và 24 backtracks (0.02 backtracks/decision).
- **Phân bổ thời gian chạy (dpll_full):** các lời gọi DPLL `solve()` chiếm 55.7% tổng thời gian (194.59 ms / 349.34 ms); phần còn lại là chi phí mã hóa manh mối (CNF encoding), dựng KB và kiểm chứng của engine.
- **Biến phụ (`aux_vars`):** bằng 0 trên tất cả màn chơi do bộ mã hóa CNF hiện tại mã hóa trực tiếp `EXACTLY`, `AT_MOST`, `AT_LEAST`, `PARITY` và `COMPARE` trên tập biến chính của các ô mà chưa tạo biến phụ (Tseitin / sequential counter).

## 5. Các trường hợp lỗi & quá thời gian (Failure Cases)

Không ghi nhận trường hợp lỗi hoặc quá thời gian trong bộ dữ liệu này (30/30 lượt chạy đều đạt trạng thái `SOLVED`). Mọi trạng thái không thành công (`TIMEOUT`, `STUCK`, `INCONSISTENT`, `ERROR`) đều được giữ nguyên tự động trong cả `failure_cases.csv` lẫn toàn bộ biểu đồ khi phát sinh.

## 6. Hạn chế hiện tại (Limitations)

- **Bùng nổ số mệnh đề CNF khi vùng lớn:** `PARITY` và `COMPARE` hiện liệt kê trực tiếp các phép gán vi phạm trên hợp hai vùng (tối đa `2^|region|`), còn `EXACTLY`/`AT_MOST`/`AT_LEAST` dùng tổ hợp trực tiếp thay vì mã hóa có biến phụ (như Sinz sequential counter hoặc chuỗi XOR Tseitin). Số mệnh đề tăng nhanh khi lưới lớn hơn `5x5` hoặc có nhiều ràng buộc chồng lấp.
- **DPLL không lưu trạng thái (stateless) giữa các truy vấn suy luận:** Mỗi kiểm tra kéo theo logic (`KB ^ C_i` và `KB ^ ¬C_i`) gọi `DpllSolver.solve()` lại từ đầu, chưa có học mệnh đề xung đột (CDCL), watched literals hay tái sử dụng trạng thái giữa các bước.
- **Chi phí gọi SAT lặp lại theo từng bước:** Dù đã có cơ chế tận dụng model mẫu (`use_witnesses=True`), việc phân loại tất cả các ô chưa rõ ở mỗi bước vẫn cần nhiều lần gọi SAT khi kích thước bàn cờ tăng.
- **Giới hạn hiệu năng Python thuần và rủi ro timeout:** Vì `DpllSolver` cài đặt bằng Python thuần, các màn `5x5` phức tạp hơn hoặc cấu hình tắt heuristic (`dpll_basic`) có thể gặp `TIMEOUT`; mọi dòng `TIMEOUT`, `STUCK`, `INCONSISTENT` và `ERROR` đều được giữ lại đầy đủ để tránh thiên lệch kết quả.
