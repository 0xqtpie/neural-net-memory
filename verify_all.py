#!/usr/bin/env python3
"""Full offline verification from a clean checkout. No third-party packages."""
from pathlib import Path
import subprocess
import sys
import time


def main():
    root = Path(__file__).resolve().parent
    commands = [
        ["generate.py", "--check"],
        ["-m", "unittest", "discover", "-s", "tests", "-v"],
        ["run_suite.py", "check", "--exact"],
        ["baseline_replication.py", "--check"],
        ["project_tools.py", "summary"],
        ["project_tools.py", "sources"],
        ["project_tools.py", "controls"],
    ]
    started = time.perf_counter()
    for argv in commands:
        subprocess.run([sys.executable] + argv, cwd=root, check=True, timeout=120)
    print(f"PASS: complete offline pilot verification in {time.perf_counter()-started:.3f}s")


if __name__ == "__main__":
    main()
