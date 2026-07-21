from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_python(path: Path, forwarded: list[str], *, cwd: str | None = None) -> int:
    if not path.exists():
        print(f"harness: missing wrapped script: {path}", file=sys.stderr)
        return 64
    completed = subprocess.run([sys.executable, str(path), *forwarded], cwd=cwd, text=True)
    return completed.returncode


def run_python_capture(path: Path, forwarded: list[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    if not path.exists():
        return subprocess.CompletedProcess(
            args=[sys.executable, str(path), *forwarded],
            returncode=64,
            stdout="",
            stderr=f"harness: missing wrapped script: {path}\n",
        )
    return subprocess.run([sys.executable, str(path), *forwarded], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
