"""Create the submission folder StudentID1_StudentID2_.../ with Source/.

Usage: python scripts/make_submission.py 2312xxx_2312yyy_2312zzz_2312aaa_2312bbb
Then copy Report.pdf into that folder and zip it.
"""
import shutil
import sys
from pathlib import Path

INCLUDE = ["main.py", "README.md", "requirements.txt", "griductive", "puzzles", "tests", "experiments"]


def main() -> None:
    out = Path(sys.argv[1])
    src = out / "Source"
    src.mkdir(parents=True, exist_ok=True)
    for item in INCLUDE:
        p = Path(item)
        if p.is_dir():
            shutil.copytree(p, src / p.name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(p, src / p.name)
    print(f"Created {out}/. Now copy Report.pdf into it, then zip.")


if __name__ == "__main__":
    main()
