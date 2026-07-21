#!/usr/bin/env python3
"""
检查 trace-log 文件状态。
"""

import sys
import argparse
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parents[3]
if (HARNESS_ROOT / "runtime").is_dir():
    WORKSPACE_ROOT = HARNESS_ROOT / "runtime"
elif HARNESS_ROOT.name == ".harness":
    WORKSPACE_ROOT = HARNESS_ROOT.parent
elif (HARNESS_ROOT / "common").is_dir():
    WORKSPACE_ROOT = HARNESS_ROOT.parent
else:
    WORKSPACE_ROOT = HARNESS_ROOT
RUNTIME_ROOT = (
    WORKSPACE_ROOT / "harness-runtime"
    if (WORKSPACE_ROOT / "harness-runtime").is_dir()
    else WORKSPACE_ROOT
)
STATE_DIR = RUNTIME_ROOT / "harness" / "state"
MAIN_FILE = STATE_DIR / "trace-log.md"
ARCHIVE_DIR = STATE_DIR / "trace-archive"


def main():
    parser = argparse.ArgumentParser(description="检查 trace-log 状态")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--exists", action="store_true", help="仅检查文件是否存在（exit code）")
    args = parser.parse_args()

    if args.exists:
        sys.exit(0 if MAIN_FILE.exists() else 1)

    if not MAIN_FILE.exists():
        print("trace-log.md 不存在")
        sys.exit(1)

    main_lines = len(MAIN_FILE.read_text(encoding="utf-8").split("\n"))

    archives = sorted(ARCHIVE_DIR.glob("trace-log-*.md")) if ARCHIVE_DIR.exists() else []
    total_archive_lines = 0
    for f in archives:
        total_archive_lines += len(f.read_text(encoding="utf-8").split("\n"))

    if args.stats:
        print(f"主文件行数: {main_lines}")
        print(f"归档文件数: {len(archives)}")
        print(f"归档总行数: {total_archive_lines}")
        print(f"总行数: {main_lines + total_archive_lines}")
    else:
        print(f"trace-log.md: {main_lines} 行, 归档: {len(archives)} 个文件")


if __name__ == "__main__":
    main()
