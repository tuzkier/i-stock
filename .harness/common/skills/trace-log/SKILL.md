---
name: trace-log
description: '当需要记录或恢复 Harness 执行日志时使用；技能开始/完成、Stage Gate、Checkpoint、escalation、审查结论、回退、sub-agent 结束或会话恢复时触发。'
---

# 执行日志 — 执行日志

## 概述

自动记录每轮执行的关键信息，支持跨会话恢复和决策回溯。

## 何时使用

- **主路径（默认）**：主 Agent 在每轮恢复协议与自治循环中调度本技能，无需 sub-agent 参与
- 由自治循环自动集成（通常不需要手动触发）
- 跨会话恢复时自动读取

## 记录内容

| 字段 | 说明 |
|------|------|
| timestamp | 时间戳 |
| phase | 当前阶段 |
| 技能 | 使用的技能 |
| decision | 做出的决策 |
| outcome | 结果 |
| 上下文 | 关键上下文 |

按 `workflow.md` 执行详细步骤。
#!/usr/bin/env python3
"""
写入 trace-log 内容。

支持：
- 追加执行日志（自动时间戳 + 按日期分组）
- 更新当前位置
- 追加关键决策
- 追加阻塞记录
- 初始化新 Mission 的 trace-log
- 自动归档（超限时将旧日志移入 trace-archive/）
"""

import sys
import argparse
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

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
TIME_SCRIPT = RUNTIME_ROOT / "scripts" / "get_time.sh"

MAX_TOTAL_LINES = 500
MAX_LOG_LINES = 300
ARCHIVE_DAYS = 5

INITIAL_TEMPLATE = """# Trace Log

**Mission:** {mission_id}
**Last Updated:** {timestamp}

## 当前位置

- **阶段**: {stage}
- **Skill**: {skill}
- **状态**: {status}
- **下一步**: {next_step}

## 关键决策

| 时间 | 决策 | 理由 | 影响 |
|------|------|------|------|

## 阻塞与修复

| 时间 | 问题 | 解决方式 | 是否解决 |
|------|------|---------|---------|

## 执行日志

"""


def _run_time_script(flag: str = "") -> str:
    """Call the global time script. Falls back to local datetime if unavailable."""
    try:
        if TIME_SCRIPT.exists():
            cmd = ["bash", str(TIME_SCRIPT)]
            if flag:
                cmd.append(flag)
            out = subprocess.check_output(cmd, cwd=str(WORKSPACE_ROOT))
            return out.decode("utf-8", errors="ignore").strip()
    except Exception:
        pass
    if flag == "--short":
        return datetime.now().strftime("%H:%M")
    if flag == "--date":
        return datetime.now().strftime("%Y-%m-%d")
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _now() -> str:
    full = _run_time_script()
    parts = full.split()
    return f"{parts[0]} {parts[1][:5]}" if len(parts) >= 2 else full


def _now_full() -> str:
    return _run_time_script()


def _today() -> str:
    return _run_time_script("--date")


def _time_only() -> str:
    return _run_time_script("--short")


def _ensure_file():
    """Ensure main file exists; return content."""
    if MAIN_FILE.exists():
        return MAIN_FILE.read_text(encoding="utf-8")
    return None


def _write_file(content: str):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    MAIN_FILE.write_text(content, encoding="utf-8")


def _get_section_range(lines, section_name):
    """Find a ## section's start index and end index (exclusive)."""
    pattern = rf"^##\s+{re.escape(section_name)}"
    start = None
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            start = i
            break
    if start is None:
        return None, None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^##\s+", lines[i]):
            end = i
            break
    return start, end


def cmd_init(args):
    """Initialize trace-log for a new Mission."""
    # 归档旧文件，避免直接覆盖丢失
    if MAIN_FILE.exists():
        old_content = MAIN_FILE.read_text(encoding="utf-8")
        if old_content.strip():
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            existing = sorted(ARCHIVE_DIR.glob("trace-log-*.md"))
            next_num = len(existing) + 1
            archive_name = f"trace-log-{next_num:03d}.md"
            (ARCHIVE_DIR / archive_name).write_text(old_content, encoding="utf-8")
            print(f"旧 trace-log 已归档: {archive_name}", file=sys.stderr)

    ts = _now()
    content = INITIAL_TEMPLATE.format(
        mission_id=args.mission or "unknown",
        timestamp=ts,
        stage=args.stage or "intake",
        skill=args.skill or "intake",
        status=args.status or "done",
        next_step=args.next_step or "discovery 或 prd",
    )
    if args.log_message:
        content += f"### {_today()}\n\n* `{_time_only()}` - {args.log_message}\n\n"
    _write_file(content)
    print(f"trace-log 已初始化: Mission={args.mission}", file=sys.stderr)


def cmd_log(args):
    """Append an execution log entry with auto-timestamp and date grouping."""
    content = _ensure_file()
    if not content:
        print("错误：trace-log.md 不存在，请先 --type init", file=sys.stderr)
        sys.exit(1)

    lines = content.split("\n")
    start, end = _get_section_range(lines, "执行日志")
    if start is None:
        lines.append(f"\n## 执行日志\n\n### {_today()}\n\n* `{_time_only()}` - {args.content}\n")
        _write_file("\n".join(lines))
        _maybe_archive()
        return

    date_heading = f"### {_today()}"
    entry = f"* `{_time_only()}` - {args.content}"

    date_idx = None
    for i in range(start + 1, end):
        if lines[i].strip() == date_heading:
            date_idx = i
            break

    if date_idx is None:
        insert_pos = start + 1
        while insert_pos < end and lines[insert_pos].strip() == "":
            insert_pos += 1
        lines[insert_pos:insert_pos] = [date_heading, "", entry, ""]
    else:
        insert_pos = date_idx + 1
        for i in range(date_idx + 1, end):
            if re.match(r"^###\s+\d{4}-\d{2}-\d{2}", lines[i]):
                insert_pos = i
                break
            insert_pos = i + 1
        while insert_pos > date_idx + 1 and lines[insert_pos - 1].strip() == "":
            insert_pos -= 1
        lines.insert(insert_pos, entry)

    _update_last_updated(lines)
    _write_file("\n".join(lines))
    _maybe_archive()
    print(f"trace-log: {args.content}", file=sys.stderr)


def cmd_position(args):
    """Update the 当前位置 section (replace mode)."""
    content = _ensure_file()
    if not content:
        print("错误：trace-log.md 不存在", file=sys.stderr)
        sys.exit(1)

    lines = content.split("\n")
    start, end = _get_section_range(lines, "当前位置")
    if start is None:
        print("错误：找不到「当前位置」章节", file=sys.stderr)
        sys.exit(1)

    new_section = [
        "## 当前位置",
        "",
        f"- **阶段**: {args.stage or ''}",
        f"- **Skill**: {args.skill or ''}",
        f"- **状态**: {args.status or 'in-progress'}",
        f"- **下一步**: {args.next_step or ''}",
        "",
    ]
    lines[start:end] = new_section
    _update_last_updated(lines)
    _write_file("\n".join(lines))
    print(f"trace-log 当前位置已更新: stage={args.stage}, skill={args.skill}", file=sys.stderr)


def cmd_decision(args):
    """Append a row to 关键决策 table."""
    content = _ensure_file()
    if not content:
        print("错误：trace-log.md 不存在", file=sys.stderr)
        sys.exit(1)

    lines = content.split("\n")
    start, end = _get_section_range(lines, "关键决策")
    if start is None:
        print("错误：找不到「关键决策」章节", file=sys.stderr)
        sys.exit(1)

    date_short = datetime.now().strftime("%m-%d %H:%M")
    row = f"| {date_short} | {args.content} | {args.reason or ''} | {args.impact or ''} |"

    insert_pos = end
    for i in range(end - 1, start, -1):
        if lines[i].strip():
            insert_pos = i + 1
            break
    lines.insert(insert_pos, row)
    _update_last_updated(lines)
    _write_file("\n".join(lines))
    print(f"trace-log 决策已记录: {args.content}", file=sys.stderr)


def cmd_block(args):
    """Append a row to 阻塞与修复 table."""
    content = _ensure_file()
    if not content:
        print("错误：trace-log.md 不存在", file=sys.stderr)
        sys.exit(1)

    lines = content.split("\n")
    start, end = _get_section_range(lines, "阻塞与修复")
    if start is None:
        print("错误：找不到「阻塞与修复」章节", file=sys.stderr)
        sys.exit(1)

    date_short = datetime.now().strftime("%m-%d %H:%M")
    resolved = "✅" if args.resolved else "❌"
    row = f"| {date_short} | {args.content} | {args.fix or ''} | {resolved} |"

    insert_pos = end
    for i in range(end - 1, start, -1):
        if lines[i].strip():
            insert_pos = i + 1
            break
    lines.insert(insert_pos, row)
    _update_last_updated(lines)
    _write_file("\n".join(lines))
    print(f"trace-log 阻塞已记录: {args.content}", file=sys.stderr)


def cmd_resolve(args):
    """Mark a blocker as resolved by matching keyword in the 阻塞与修复 table."""
    content = _ensure_file()
    if not content:
        print("错误：trace-log.md 不存在", file=sys.stderr)
        sys.exit(1)

    lines = content.split("\n")
    start, end = _get_section_range(lines, "阻塞与修复")
    if start is None:
        return

    keyword = args.keyword
    for i in range(start + 1, end):
        if keyword in lines[i] and "❌" in lines[i]:
            lines[i] = lines[i].replace("❌", "✅")
            if args.fix:
                parts = lines[i].rsplit("|", 3)
                if len(parts) >= 3:
                    parts[-3] = f" {args.fix} "
                    lines[i] = "|".join(parts)
            _update_last_updated(lines)
            _write_file("\n".join(lines))
            print(f"trace-log 阻塞已解决: {keyword}", file=sys.stderr)
            return

    print(f"未找到包含 '{keyword}' 的未解决阻塞", file=sys.stderr)


def _update_last_updated(lines):
    """Update the **Last Updated** line in the header."""
    ts = _now()
    for i, line in enumerate(lines):
        if line.startswith("**Last Updated:**"):
            lines[i] = f"**Last Updated:** {ts}"
            return


def _maybe_archive():
    """Check if archiving is needed and perform it."""
    content = MAIN_FILE.read_text(encoding="utf-8")
    lines = content.split("\n")
    total = len(lines)

    start, end = _get_section_range(lines, "执行日志")
    log_lines = (end - start) if start is not None and end is not None else 0

    need = False
    reason = ""
    if total > MAX_TOTAL_LINES:
        need, reason = True, f"总行数 {total} > {MAX_TOTAL_LINES}"
    elif log_lines > MAX_LOG_LINES:
        need, reason = True, f"日志行数 {log_lines} > {MAX_LOG_LINES}"

    if not need and start is not None:
        threshold = (datetime.now() - timedelta(days=ARCHIVE_DAYS)).strftime("%Y-%m-%d")
        for i in range(start + 1, end):
            m = re.match(r"^###\s+(\d{4}-\d{2}-\d{2})", lines[i])
            if m and m.group(1) < threshold:
                need, reason = True, f"存在 {ARCHIVE_DAYS} 天前的日志"
                break

    if not need:
        return

    threshold = (datetime.now() - timedelta(days=ARCHIVE_DAYS)).strftime("%Y-%m-%d")
    old_logs, new_content = _extract_old_logs(content, start, end, threshold)

    if not old_logs:
        old_logs, new_content = _extract_old_logs_force(content, start, end)

    if old_logs:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        existing = sorted(ARCHIVE_DIR.glob("trace-log-*.md"))
        next_num = len(existing) + 1
        archive_name = f"trace-log-{next_num:03d}.md"
        (ARCHIVE_DIR / archive_name).write_text(
            f"# Trace Log Archive #{next_num}\n\n## 执行日志\n\n{old_logs}\n",
            encoding="utf-8",
        )
        _write_file(new_content)
        print(f"已归档: {archive_name}（{reason}）", file=sys.stderr)


def _extract_old_logs(content, start, end, threshold):
    """Extract logs older than threshold date."""
    lines = content.split("\n")
    old, new_log = [], []
    in_old = False
    for i in range(start + 1, end):
        m = re.match(r"^###\s+(\d{4}-\d{2}-\d{2})", lines[i])
        if m:
            in_old = m.group(1) < threshold
        (old if in_old else new_log).append(lines[i])

    if not old:
        return None, content

    new_lines = lines[: start + 1] + new_log + lines[end:]
    return "\n".join(old), "\n".join(new_lines)


def _extract_old_logs_force(content, start, end):
    """Force-archive the older half of logs when date-based fails."""
    lines = content.split("\n")
    log_lines = lines[start + 1 : end]
    non_empty = [l for l in log_lines if l.strip()]
    if len(non_empty) < 20:
        return None, content

    split = len(log_lines) // 2
    old = log_lines[:split]
    kept = log_lines[split:]
    new_lines = lines[: start + 1] + kept + lines[end:]
    return "\n".join(old), "\n".join(new_lines)


def main():
    parser = argparse.ArgumentParser(description="写入 trace-log")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # init
    p_init = sub.add_parser("init", help="初始化 trace-log")
    p_init.add_argument("--mission", required=True, help="Mission ID")
    p_init.add_argument("--stage", default="intake")
    p_init.add_argument("--skill", default="intake")
    p_init.add_argument("--status", default="done")
    p_init.add_argument("--next-step", default="discovery 或 prd")
    p_init.add_argument("--log-message", help="初始日志条目")

    # log
    p_log = sub.add_parser("log", help="追加执行日志")
    p_log.add_argument("content", help="日志内容（一行）")

    # position
    p_pos = sub.add_parser("position", help="更新当前位置")
    p_pos.add_argument("--stage", required=True)
    p_pos.add_argument("--skill", required=True)
    p_pos.add_argument("--status", default="in-progress")
    p_pos.add_argument("--next-step", default="")

    # decision
    p_dec = sub.add_parser("decision", help="记录关键决策")
    p_dec.add_argument("content", help="决策内容")
    p_dec.add_argument("--reason", default="", help="理由")
    p_dec.add_argument("--impact", default="", help="影响")

    # block
    p_blk = sub.add_parser("block", help="记录阻塞")
    p_blk.add_argument("content", help="问题描述")
    p_blk.add_argument("--fix", default="", help="解决方式")
    p_blk.add_argument("--resolved", action="store_true", help="已解决")

    # resolve
    p_res = sub.add_parser("resolve", help="标记阻塞已解决")
    p_res.add_argument("keyword", help="匹配阻塞的关键词")
    p_res.add_argument("--fix", default="", help="解决方式")

    args = parser.parse_args()
    {
        "init": cmd_init,
        "log": cmd_log,
        "position": cmd_position,
        "decision": cmd_decision,
        "block": cmd_block,
        "resolve": cmd_resolve,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
