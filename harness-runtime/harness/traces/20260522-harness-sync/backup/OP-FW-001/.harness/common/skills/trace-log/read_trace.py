#!/usr/bin/env python3
"""
读取 trace-log 内容。

支持：
- 读取全文
- 读取特定章节（当前位置 / 关键决策 / 阻塞与修复 / 执行日志）
- 读取特定日期的日志（自动跨归档文件查找）
- 读取最近 N 条日志
- 恢复摘要（跨会话恢复时的最小读取）
"""

import sys
import argparse
import re
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


def _read(path):
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _get_section(content, section_name):
    """Extract a ## section's content (including heading)."""
    if not content:
        return None
    pattern = rf"^##\s+{re.escape(section_name)}"
    lines = content.split("\n")
    start = None
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            start = i
            break
    if start is None:
        return None
    result = [lines[start]]
    for i in range(start + 1, len(lines)):
        if re.match(r"^##\s+", lines[i]):
            break
        result.append(lines[i])
    return "\n".join(result)


def _get_logs_by_date(content, date):
    """Extract log entries for a specific date."""
    if not content:
        return None
    lines = content.split("\n")
    result = []
    capturing = False
    for line in lines:
        if re.match(rf"^###\s+{re.escape(date)}", line):
            capturing = True
            result.append(line)
        elif capturing:
            if re.match(r"^###\s+\d{4}-\d{2}-\d{2}", line) or re.match(r"^##\s+", line):
                break
            result.append(line)
    return "\n".join(result) if result else None


def _get_recent_logs(content, count):
    """Get the most recent N log entries."""
    if not content:
        return None
    log_section = _get_section(content, "执行日志")
    if not log_section:
        return None
    entries = []
    current_date = ""
    for line in log_section.split("\n"):
        if re.match(r"^###\s+\d{4}-\d{2}-\d{2}", line):
            current_date = line
        elif line.strip().startswith("* `"):
            entries.append((current_date, line))

    recent = entries[-count:]
    result = []
    last_date = ""
    for date_heading, entry in recent:
        if date_heading != last_date:
            result.append(date_heading)
            last_date = date_heading
        result.append(entry)
    return "\n".join(result)


def cmd_section(args):
    content = _read(MAIN_FILE)
    if not content:
        print("trace-log.md 不存在", file=sys.stderr)
        sys.exit(1)
    section = _get_section(content, args.section)
    if section:
        print(section)
    else:
        print(f"未找到章节: {args.section}", file=sys.stderr)


def cmd_date(args):
    content = _read(MAIN_FILE)
    result = _get_logs_by_date(content, args.date) if content else None
    if not result and ARCHIVE_DIR.exists():
        for f in sorted(ARCHIVE_DIR.glob("trace-log-*.md"), reverse=True):
            arc = _read(f)
            result = _get_logs_by_date(arc, args.date)
            if result:
                break
    if result:
        print(result)
    else:
        print(f"未找到 {args.date} 的日志", file=sys.stderr)


def cmd_recent(args):
    content = _read(MAIN_FILE)
    if not content:
        print("trace-log.md 不存在", file=sys.stderr)
        sys.exit(1)
    result = _get_recent_logs(content, args.n)
    if result:
        print(result)
    else:
        print("没有日志条目", file=sys.stderr)


def cmd_recover(args):
    """Output the minimal info needed for cross-session recovery."""
    content = _read(MAIN_FILE)
    if not content:
        print("trace-log.md 不存在", file=sys.stderr)
        sys.exit(1)

    parts = []

    pos = _get_section(content, "当前位置")
    if pos:
        parts.append(pos)

    blocks = _get_section(content, "阻塞与修复")
    if blocks:
        has_unresolved = "❌" in blocks
        if has_unresolved:
            parts.append(blocks)
        else:
            parts.append("## 阻塞与修复\n（无未解决阻塞）")

    recent = _get_recent_logs(content, args.n if hasattr(args, "n") else 5)
    if recent:
        parts.append(f"## 最近执行日志\n\n{recent}")

    print("\n\n".join(parts))


def cmd_full(args):
    content = _read(MAIN_FILE)
    if not content:
        print("trace-log.md 不存在", file=sys.stderr)
        sys.exit(1)
    print(content)


def main():
    parser = argparse.ArgumentParser(description="读取 trace-log")
    sub = parser.add_subparsers(dest="cmd")

    p_sec = sub.add_parser("section", help="读取特定章节")
    p_sec.add_argument("section", help="章节名（当前位置 / 关键决策 / 阻塞与修复 / 执行日志）")

    p_date = sub.add_parser("date", help="读取特定日期的日志")
    p_date.add_argument("date", help="日期 YYYY-MM-DD")

    p_rec = sub.add_parser("recent", help="读取最近 N 条日志")
    p_rec.add_argument("-n", type=int, default=10, help="条目数（默认 10）")

    p_recover = sub.add_parser("recover", help="跨会话恢复摘要（当前位置 + 未解决阻塞 + 最近日志）")
    p_recover.add_argument("-n", type=int, default=5, help="最近日志条数（默认 5）")

    sub.add_parser("full", help="读取全文")

    args = parser.parse_args()
    if args.cmd is None:
        cmd_full(args)
    else:
        {"section": cmd_section, "date": cmd_date, "recent": cmd_recent,
         "recover": cmd_recover, "full": cmd_full}[args.cmd](args)


if __name__ == "__main__":
    main()
