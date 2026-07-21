# 执行日志工作流

**Goal:** 记录每次执行的关键动作、决策和结果，让跨会话恢复有据可依。

**Your Role:** 你是执行日志记录器。你只通过脚本读写 trace，不手工编辑日志文件，并按场景选择 recover / init / log / position / decision / block / resolve 等操作。

**核心原则：** 所有读写通过脚本完成，不直接手工编辑 `trace-log.md`。脚本自动处理时间戳（使用全局 `scripts/get_time.sh`）、格式和归档。

**执行主体：** 默认由**主 Agent**按 `autonomy-loop` 与 `core` 恢复协议执行下文 recover / log / position 等操作。仅当你通过任务项工具派出 sub-agent 承担阶段性执行时，才需要该 sub-agent 在交还结果前执行「 sub-agent 」一节（一行 log）；不派出 sub-agent 则可忽略该节。

---

<workflow skill="trace-log" version="2">

<step n="1" goal="选择日志操作">
 - 根据当前场景选择一个操作：`recover`、`init`、`log`、`sub-agent`、`position`、`decision`、`block`、`resolve` 或其他读取操作。
 - 条件：当前场景是会话开始或恢复上下文
  - 选择 `recover`。
 - 条件：当前场景是任务接入完成任务契约后
  - 选择 `init`。
 - 条件：当前场景是技能开始、完成、跳过、失败，或 Gate / Work Graph / Git / escalation / reviewer 事件
  - 选择 `log`。
 - 条件：当前场景是 sub-agent 即将交回阶段工作结果
  - 选择 `sub-agent`，只写一条 log；不执行 recover，不更新 position。
 - 条件：当前场景是技能开始或结束，需要更新当前位置
  - 选择 `position`。
 - 条件：当前场景是记录关键决策、阻塞或阻塞解决
  - 分别选择 `decision`、`block` 或 `resolve`。
</step>

<step n="2" goal="通过脚本执行">
 - 按「操作列表」中对应小节调用 `read_trace.py`、`write_trace.py` 或 `check_trace.py`。
 - Hard gate：不得直接手工编辑 `trace-log.md`；所有时间戳由脚本统一生成。
 - 条件：trace-log.md 尚未 init 且当前操作是 sub-agent 一行 log
  - 跳过写入，并在返回主 Agent 时注明需要先 init 执行日志。
</step>

<step n="3" goal="容量和位置约束">
 - 依赖脚本自动处理容量管理：总行数、日志章节长度和旧日志归档。
 - 确认当前 Mission 日志路径和归档路径符合「文件位置」小节。
</step>

</workflow>

---

## 操作列表

调度此技能时，根据当前场景选择对应操作。

### recover — 跨会话恢复

**场景：** 每次会话开始或恢复上下文时。

```bash
python3 .harness/common/skills/trace-log/read_trace.py recover
```

输出当前位置 + 未解决阻塞 + 最近 5 条日志。这是恢复协议的核心读取。

### init — 初始化

**场景：** 任务接入完成任务契约后。

```bash
python3 .harness/common/skills/trace-log/write_trace.py init \
 --mission "<mission-id>" \
 --log-message "[intake] ✅ 完成 mission-contract.md"
```

可选参数：`--stage`、`--skill`、`--status`、`--next-step`（均有默认值）。

### log — 记录执行日志

**场景：** 技能开始、完成、跳过、失败时。

```bash
python3 .harness/common/skills/trace-log/write_trace.py log "<一行描述>"
```

约定格式：

**技能执行：**
- 开始：`[skill] 🔄 开始`
- 完成：`[skill] ✅ 完成 <产出物>`
- 跳过：`[skill] ⏭️ 跳过（原因）`
- 失败：`[skill] ❌ <问题>`

**Gate 与 Work Graph 推进：**
- Stage Gate 通过：`[stage-gate] ✅ PASS <stage> -> graph operation applied`
- Stage Gate 失败：`[stage-gate] ❌ FAIL <阶段名>：<失败项>`
- Board Router 生成 Mission Slice：`[board-router] Mission Slice <mission-id> -> <node-id>`
- Work Graph operation 应用：`[stage-gate] applied <operation-id> after continue`
- Checkpoint 暂停：`[checkpoint] ⏸️ 等待用户确认：<阶段名>`
- Checkpoint 通过：`[checkpoint] ✅ 用户已确认，继续推进`

**Git 提交：**
- mission branch 就绪：`[git-workflow] ✅ prepare 完成：mission branch {branch}`
- stage worktree 就绪：`[git-workflow] ✅ start-stage <阶段名>：stage branch {branch}，worktree {path}`
- 阶段合并：`[git-workflow] ✅ commit-artifact <阶段名>：已合并 <stage-branch> → <mission-branch>`
- 分支收尾：`[git-workflow] ✅ close 完成：<mission-branch> 已合并/归档`

**异常与升级：**
- escalation 触发：`[escalation] ⚠️ 命中升级条件：<条件描述>，等待用户决策`
- 回退：`[回退] ⬅️ <来源> → <目标>，原因：<简述>`
- 中途纠偏触发：`[course-correction] 🔄 发现偏差：<描述>`
- systematic-debugging 触发：`[systematic-debugging] 🔍 开始调试：<症状>`

**审查闭环（3d）：**
- 审查员 PASS：`[reviewer:<角色>] ✅ PASS`
- 审查员 HOLD：`[reviewer:<角色>] 🔴 HOLD <阻断问题>`
- 循环上限触发 Decision Gate：`[decision-gate] 等待/用户决定：<概要>`

**sub-agent：**
- sub-agent 结束：`[subagent:<角色>] ✅ DONE <产出摘要>` 或 `[subagent:<角色>] ❌ BLOCKED <原因>`

### sub-agent — 结束前一条日志（仅 log，可选）

**场景：** 仅在使用任务项 sub-agent 执行阶段工作且即将把结果交回主 Agent 时。主 Agent 亲自跑技能时不需要本节。不执行 recover、不更新 position。

```bash
python3 .harness/common/skills/trace-log/write_trace.py log "[subagent:discovery-analyst] ✅ DONE harness-runtime/harness/artifacts/foo/discovery/discovery-brief.md"
```

若 `trace-log.md` 尚未 init，跳过写入并在返回主 Agent 时注明「需先 init 执行日志」。

### position — 更新当前位置

**场景：** 技能开始或结束时，更新"我在哪"。

```bash
python3 .harness/common/skills/trace-log/write_trace.py position \
 --stage "<阶段>" --skill "<skill名>" \
 --status "in-progress" --next-step "<预期下一步>"
```

### decision — 记录关键决策

**场景：** 执行过程中做了有影响的选择。

```bash
python3 .harness/common/skills/trace-log/write_trace.py decision "<决策>" \
 --reason "<理由>" --impact "<影响>"
```

### block — 记录阻塞

**场景：** 遇到阻碍执行的问题。

```bash
# 未解决
python3 .harness/common/skills/trace-log/write_trace.py block "<问题>"

# 已解决
python3 .harness/common/skills/trace-log/write_trace.py block "<问题>" --fix "<方式>" --resolved
```

### resolve — 标记阻塞已解决

**场景：** 之前记录的阻塞后来解决了。

```bash
python3 .harness/common/skills/trace-log/write_trace.py resolve "<关键词>" --fix "<方式>"
```

### 其他读取

```bash
# 读取特定章节
python3 .harness/common/skills/trace-log/read_trace.py section "当前位置"

# 读取特定日期（自动跨归档查找）
python3 .harness/common/skills/trace-log/read_trace.py date "2026-03-22"

# 读取最近 N 条
python3 .harness/common/skills/trace-log/read_trace.py recent -n 10

# 检查状态
python3 .harness/common/skills/trace-log/check_trace.py --stats
```

---

## 文件位置

```
harness-runtime/harness/state/trace-log.md # 当前 Mission 执行日志
harness-runtime/harness/state/trace-archive/ # 历史归档（脚本自动管理）
```

## 容量管理

脚本每次写入后自动检查：
- 总行数 > 500 → 归档旧日志
- 日志章节 > 300 行 → 归档旧日志
- 存在 5 天前的日志 → 归档旧日志

"当前位置"、"关键决策"、"阻塞与修复"不归档，只归档执行日志。

## 时间戳

所有时间戳统一使用全局 `scripts/get_time.sh`（Asia/Shanghai 时区），脚本自动调用，AI 不需要手动获取时间。
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
