# GUI: framework và wireframe

**Framework**: Tkinter (có sẵn trong Python, chạy bằng `python main.py`, dễ nối với Engine/Agent viết bằng Python).

## Bố cục

    +---------------------------------------------------------+
    | [Load: chọn 1/6 màn v] [Restart] [Hint] [Auto Solve]     |
    +------------------------------------+--------------------+
    |        A      B      C             | CLUE ĐÃ LỘ         |
    |   1  [thẻ]  [thẻ]  [thẻ]           | c01 ...            |
    |   2  [thẻ]  [thẻ]  [thẻ]           | c02 ... (bấm để    |
    |   3  [thẻ]  [thẻ]  [thẻ]           |  highlight ô)      |
    +------------------------------------+--------------------+
    | Đang chọn: B2   [CRIMINAL] [INNOCENT]                    |
    | Thông báo: ACCEPTED / NOT_PROVABLE / CONTRADICTED        |
    +---------------------------------------------------------+

## Chức năng 

- Load: chọn 1 trong 6 puzzle (mỗi cỡ 3x3, 4x4, 5x5 có 2 màn) rồi vào chơi luôn. Restart: chơi lại màn hiện tại.
- Auto Solve: animate từng bước giải của Agent.
- Hint: chỉ ra người có thể kết luận tiếp, hoặc người/clue nên xem.
- Bấm clue đã lộ: highlight các ô mà clue nhắc tới.
- Màu: thẻ úp (xám), CRIMINAL (đỏ), INNOCENT (xanh), đang chọn (viền cam), clue highlight (viền tím, nền vàng nhạt).