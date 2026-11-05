# Griductive Solver

Bộ giải Griductive **không đoán mò** bằng logic mệnh đề, mã hoá CNF và bộ giải SAT DPLL tự cài.

## 1. Thành viên

| Mã  | Họ tên | Vai trò chính                      | Module phụ trách                        |
| --- | ------ | ---------------------------------- | --------------------------------------- |
| A   | Thúy   | Nhóm trưởng, Logic Agent, tích hợp | `griductive/agent/`, `main.py`          |
| B   | Phong  | DPLL, thực nghiệm                  | `griductive/sat/`, `experiments/`       |
| C   | Duy    | Encoder CNF, extension             | `griductive/logic/`, `griductive/core/` |
| D   | Kiệt   | Game Engine, dữ liệu puzzle        | `griductive/engine/`, `puzzles/`        |
| E   | Vy     | GUI, báo cáo, video                | `griductive/gui/`, `docs/report/`       |

Người phụ trách module là người review đầu tiên cho mọi thay đổi trong module đó.

## 2. Cài đặt và chạy

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python main.py                                    # mở GUI
python main.py --solve puzzles/3x3/p3x3_01.json   # chạy Agent trên terminal
python -m experiments.run_experiments             # chạy toàn bộ thực nghiệm
python -m pytest tests/                           # chạy test
```

Yêu cầu: Python 3.10 trở lên.

## 3. Cấu trúc thư mục

```
griductive-solver/
├── main.py                     # điểm vào: GUI hoặc --solve
├── README.md
├── requirements.txt
├── .gitignore
│
├── griductive/                 # package chính
│   ├── core/                   # dùng chung, KHÔNG chứa logic giải
│   │   ├── constants.py        #   Enum: Status, VerdictResult, ClueType, RegionKind
│   │   ├── types.py            #   dataclass: Cell, Clue, Region, Puzzle
│   │   └── regions.py          #   row / column / neighbors / explicit -> danh sách ô
│   │
│   ├── engine/                 # GAME ENGINE (giữ lời giải ẩn + clue chưa lộ)
│   │   ├── puzzle_loader.py    #   đọc và kiểm tra puzzle JSON
│   │   ├── game_engine.py      #   reveal protocol, nhận verdict từ người chơi
│   │   └── verdict.py          #   ACCEPTED / NOT_PROVABLE / CONTRADICTED
│   │
│   ├── logic/                  # BIỂU DIỄN LOGIC + CNF
│   │   ├── variable_map.py     #   ô <-> biến mệnh đề (tất định)
│   │   ├── evaluator.py        #   evaluator ngữ nghĩa trực tiếp (không dùng CNF)
│   │   ├── cnf_encoder.py      #   clue -> CNF
│   │   ├── kb_builder.py       #   KB_t = CNF(clue đã lộ) + unit clauses, đếm biến/clause
│   │   └── extensions/         #   ít nhất 2 extension (mỗi file: encoder + evaluator)
│   │
│   ├── sat/                    # DPLL
│   │   ├── dpll.py
│   │   └── stats.py            #   decisions, propagations, backtracks, runtime
│   │
│   ├── agent/                  # LOGIC AGENT (chỉ thấy thông tin công khai)
│   │   ├── logic_agent.py      #   vòng lặp suy diễn, Hint, Auto Solve
│   │   ├── entailment.py       #   CRIMINAL / INNOCENT / UNKNOWN / INCONSISTENT
│   │   ├── uniqueness.py       #   kiểm tra nghiệm duy nhất
│   │   └── trace.py            #   deduction trace
│   │
│   └── gui/                    # GIAO DIỆN
│       ├── app.py
│       ├── board_view.py
│       ├── card_widget.py
│       ├── clue_panel.py
│       └── assets/             #   ảnh avatar, icon
│
├── puzzles/                    # dữ liệu puzzle (JSON)
│   ├── 3x3/                    #   p3x3_01.json, p3x3_02.json, ...
│   ├── 4x4/
│   └── 5x5/
│
├── experiments/                # script thực nghiệm
│   ├── run_experiments.py
│   ├── metrics.py
│   └── plot_results.py
│
├── results/                    # kết quả thực nghiệm (giữ cả case lỗi/timeout)
│   ├── raw/                    #   CSV: YYYYMMDD_<mô_tả>.csv
│   └── figures/                #   biểu đồ dùng trong báo cáo
│
├── tests/                      # pytest, mỗi module một file test_<module>.py
│
├── docs/
│   ├── interface.md            # hợp đồng giữa các module (xem mục 4)
│   ├── report/                 # mã nguồn báo cáo (LaTeX/Word), Report.pdf xuất ra đây
│   └── meetings/               # biên bản họp: YYYY-MM-DD_<chủ_đề>.md
│
└── scripts/
    └── make_submission.py      # đóng gói thư mục nộp bài
```

### Quy tắc phụ thuộc giữa các package

```
core  <-  logic  <-  sat
core  <-  engine
core, logic, sat  <-  agent
core, engine, agent  <-  gui
```

- `agent` **không được import** `engine`. Agent chỉ nhận clue đã lộ và verdict đã chứng minh qua tham số truyền vào, để đảm bảo không đọc được lời giải ẩn.

- `engine` có thể gọi `agent` thông qua interface (ví dụ để phân biệt NOT_PROVABLE và CONTRADICTED), nhưng không đưa lời giải ẩn cho agent.

- `core` không import package nào khác trong dự án.

## 4. Hợp đồng dữ liệu (chốt tuần 1)

**Mã ô**: cột chữ HOA + hàng số, ví dụ `A1`, `C2` (cột từ trái sang phải, hàng từ trên xuống dưới).

**Status**: `"CRIMINAL"`, `"INNOCENT"`. **Kết quả phân loại của Agent**: `CRIMINAL`, `INNOCENT`, `UNKNOWN`, `INCONSISTENT`.

**Kết quả khi người chơi gọi verdict**: `ACCEPTED`, `NOT_PROVABLE`, `CONTRADICTED`.

**CNF**: danh sách clause, mỗi clause là list số nguyên kiểu DIMACS (`[1, -2]` là `C1 ∨ ¬C2`), biến đánh số từ 1.

Ví dụ clue (JSON):

```json
{"id": "c01", "type": "FACT",      "cell": "A1", "status": "INNOCENT"}
{"id": "c02", "type": "SAME",      "a": "A1", "b": "B2"}
{"id": "c03", "type": "DIFFERENT", "a": "A1", "b": "B2"}
{"id": "c04", "type": "EXACTLY",   "k": 2, "region": {"kind": "ROW", "index": 2}}
{"id": "c05", "type": "AT_LEAST",  "k": 1, "region": {"kind": "COL", "index": "B"}}
{"id": "c06", "type": "AT_MOST",   "k": 1, "region": {"kind": "NEIGHBORS", "of": "B2"}}
{"id": "c07", "type": "EXACTLY",   "k": 0, "region": {"kind": "CELLS", "cells": ["A1", "C3"]}}
```

Ví dụ puzzle (JSON):

```json
{
  "size": 3,
  "characters": [
    {
      "cell": "A1",
      "name": "Abel",
      "job": "Astronaut",
      "status": "INNOCENT",
      "revealed": true,
      "clue": {
        "id": "c01",
        "type": "FACT",
        "cell": "B1",
        "status": "CRIMINAL"
      }
    }
  ]
}
```

Mã clue (`id`) là duy nhất trong một puzzle, dạng `c01`, `c02`, ... và dùng lại trong trace và GUI.

Mọi thay đổi định dạng phải cập nhật `docs/interface.md` bằng PR và báo cả nhóm.

## 5. Quy tắc đặt tên

### 5.1 File và thư mục

| Loại                         | Quy tắc                                                                   | Ví dụ                              |
| ---------------------------- | ------------------------------------------------------------------------- | ---------------------------------- |
| File Python, thư mục package | `snake_case`, chữ thường, không dấu, không khoảng trắng                   | `cnf_encoder.py`, `logic_agent.py` |
| File test                    | `test_<tên_module>.py`                                                    | `test_sat_dpll.py`                 |
| File puzzle                  | `p<N>x<N>_<số thứ tự 2 chữ số>.json`                                      | `p4x4_03.json`                     |
| Kết quả thực nghiệm          | `YYYYMMDD_<mô_tả>.csv`                                                    | `20261120_all_puzzles.csv`         |
| Biểu đồ                      | `fig_<nội_dung>.png`                                                      | `fig_runtime_by_size.png`          |
| Biên bản họp                 | `YYYY-MM-DD_<chủ_đề>.md`                                                  | `2026-11-12_milestone1.md`         |
| Tài liệu khác                | tên tiếng Anh `snake_case` hoặc `kebab-case`, nhất quán trong một thư mục | `interface.md`                     |

Không commit file có dấu tiếng Việt hoặc khoảng trắng trong tên.

### 5.2 Code Python

| Đối tượng                | Quy tắc                                                                             | Ví dụ                                                         |
| ------------------------ | ----------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Biến, hàm, phương thức   | `snake_case`                                                                        | `unit_propagate`, `build_kb`                                  |
| Lớp                      | `PascalCase`                                                                        | `GameEngine`, `LogicAgent`, `DpllSolver`                      |
| Hằng số, thành viên Enum | `UPPER_SNAKE_CASE`                                                                  | `NOT_PROVABLE`, `AT_LEAST`                                    |
| Hàm/thành viên nội bộ    | tiền tố `_`                                                                         | `_pick_variable`                                              |
| Loại clue, loại vùng     | trùng đúng tên trong đề                                                             | `FACT`, `SAME`, `DIFFERENT`, `EXACTLY`, `AT_LEAST`, `AT_MOST` |
| Biến mệnh đề             | chỉ dùng số nguyên dương cho biến chính `C_i`; biến phụ đánh số tiếp sau biến chính | biến chính `1..N*N`, biến phụ từ `N*N+1`                      |

Quy ước chung:

- Theo PEP 8, độ dài dòng tối đa 100 ký tự.

- Mọi hàm public có type hint và docstring một dòng nêu mục đích.

- Comment và tên biến bằng tiếng Anh. Báo cáo và tài liệu nhóm bằng tiếng Việt.

- Không hard-code CNF theo từng puzzle. Mọi clue phải đi qua `cnf_encoder.py`.

- Không dùng `print` rải rác trong thư viện. Dùng `logging` hoặc trả dữ liệu về cho nơi gọi.

### 5.3 Git

**Nhánh**: `<loại>/<mã thành viên>-<mô-tả-ngắn>` (chữ thường, dấu gạch ngang).

| Loại       | Dùng cho                        | Ví dụ                          |
| ---------- | ------------------------------- | ------------------------------ |
| `feat`     | tính năng mới                   | `feat/b-dpll-unit-propagation` |
| `fix`      | sửa lỗi                         | `fix/c-exactly-k0-encoding`    |
| `test`     | thêm test                       | `test/c-evaluator-vs-cnf`      |
| `docs`     | báo cáo, tài liệu               | `docs/e-report-skeleton`       |
| `refactor` | đổi cấu trúc, không đổi hành vi | `refactor/a-trace-format`      |

Nhánh chính: `main` (luôn chạy được, không push trực tiếp). Nhánh tích hợp tuỳ chọn: `dev`.

**Commit message**: `<loại>(<phạm vi>): <mô tả ngắn, thể mệnh lệnh, tiếng Anh>`

Phạm vi: `core`, `engine`, `logic`, `sat`, `agent`, `gui`, `exp`, `puzzles`, `docs`, `report`.

```
feat(sat): add unit propagation with conflict detection
fix(logic): handle AT_MOST when k equals region size
test(logic): cross-check evaluator against CNF on all assignments
docs(report): add CNF derivation for EXACTLY clue
```

**Pull Request**

- Tiêu đề giống commit message. Mô tả ghi: làm gì, cách test, ảnh chụp nếu là GUI.

- Mỗi PR nhỏ, một mục đích. Ít nhất **1 người khác** review, người phụ trách module là reviewer ưu tiên.

- Chỉ merge khi test chạy qua. Dùng "Squash and merge" để lịch sử gọn.
- Xoá nhánh sau khi merge.

**Tag**: `m1-modules` (12/11), `m2-e2e` (19/11), `freeze` (22/11), `final` (27/11).

**Issue**: mỗi task trong bảng timeline là một Issue, tiêu đề dạng `[B] DPLL: branching + backtracking`, gán người phụ trách. Nhãn: `engine`, `logic`, `sat`, `agent`, `gui`, `exp`, `report`, `blocked`.

### 5.4 Cột CSV của kết quả thực nghiệm

Dùng chung tên cột để mọi người đọc được kết quả của nhau:

```
puzzle,size,primary_vars,aux_vars,clauses,sat_calls,decisions,propagations,backtracks,steps,runtime_ms,status,note
```

`status` nhận: `SOLVED`, `STUCK`, `INCONSISTENT`, `TIMEOUT`, `ERROR`. Không xoá dòng lỗi/timeout.

## 6. Quy trình làm việc

1. Nhận Issue, tạo nhánh từ `main` mới nhất: `git switch main && git pull && git switch -c feat/b-...`.

2. Commit nhỏ, thường xuyên. Chạy `python -m pytest tests/` trước khi push.

3. Mở PR, gắn người review, liên kết Issue (`Closes #12`).

4. Review trong vòng 24 giờ. Sửa theo góp ý rồi merge.

5. Họp nhóm ngắn mỗi tuần để cập nhật bảng timeline.

**Definition of Done** cho một task: code chạy được, có test (hoặc demo) cho phần chính, đã được review và merge vào `main`, đã cập nhật bảng timeline sang `Done`.

## 7. Đóng gói nộp bài

```bash
python scripts/make_submission.py StudentID1_StudentID2_StudentID3_StudentID4_StudentID5
# copy Report.pdf vào thư mục vừa tạo, rồi nén thành .zip
```

Cấu trúc theo yêu cầu của đề:

```
StudentID1_StudentID2_.../
├── Source/
│   ├── main.py
│   ├── README.md
│   ├── requirements.txt
│   └── griductive/, puzzles/, tests/, experiments/
└── Report.pdf          # có link video Google Drive
```

Trước khi nộp: giải nén vào thư mục sạch, cài `requirements.txt`, chạy `python main.py`, và mở link video bằng cửa sổ ẩn danh để kiểm tra quyền truy cập. Không dùng link YouTube.
