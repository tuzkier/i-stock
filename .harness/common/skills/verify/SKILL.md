---
name: verify
description: '当代码审查通过准备确认最终状态时使用。当用户说"验证一下""测试通过了吗""确认完成"时必须使用。当你想说"应该没问题""看起来对了"时——停下，用这个技能用证据说话。'
---

# 验证 — 完成前验证

## 铁律

```
没有运行验证命令并确认输出，不许宣称测试通过。
没有可观察的实际结果证据，不许宣称需求已满足。
```

如果你在这条消息中没有运行验证命令，就不能声称测试通过。
如果你没有记录 expected vs actual 的 result evidence，就不能把任何验收场景 / 条件标记为 pass。

## 概述

证据优先原则。每个结论必须有两类证据支撑：命令证据证明验证过程运行过，结果证据证明用户可观察结果符合预期。

## 阶段能力

verify 对应 RUP 测试工作流。它要证明：每条验收场景 / 条件都有明确预期结果、真实可观察实际结果、命令证据和结果证据；质量与运行约束和高优先级风险已被验证、接受、阻断或回流；验证有效性审查员确认这些证据足以支撑交付判断。

## 何时使用

- 所有任务项完成且 code-review 通过
- 准备交付前的最终确认
- 用户说"验证一下"、"测试过了吗"、"搞定了吗"
- 任何时候你想说"完成了"、"修好了"、"通过了"

## 何时不使用

- code-review 还未通过（→ 先完成审查）

<HARD-GATE>
以下流程每一步都必须执行。跳过任何一步 = 说谎。
</HARD-GATE>

## 验证门控

```
1. 确定：什么命令能证明验证过程运行过？什么可观察结果能证明需求结果正确？
2. 运行：执行完整命令（重新运行，完整执行）
3. 观察：打开页面 / 调 API / 跑 CLI / 查数据，记录 expected vs actual
4. 阅读：完整输出，检查退出码，统计失败数
5. 验证：命令输出和实际结果是否同时支持这个结论？
 - 否 → 用证据说明实际状态
 - 是 → 带证据陈述结论
6. 只有这时：才能做出结论
```

## 禁用词

以下词语出现在你的输出中 = 你在跳过验证：

`应该能通过` / `大概没问题` / `似乎正确` / `看起来对了` / `理论上可以` / `我觉得没问题`

**替代**：运行命令 → 贴输出 → 陈述事实。

## 反合理化

| 借口 | 现实 |
|------|------|
| "应该能行了" | 运行验证命令 |
| "我有信心" | 信心 ≠ 证据 |
| "就这一次" | 没有例外 |
| "Linter 通过了" | Linter ≠ 编译器 ≠ 测试 |
| "Agent 说成功了" | 独立验证 |
| "我累了" | 疲劳不是跳过验证的理由 |
| "部分检查就够了" | 部分检查什么也证明不了 |

## 验证对照表

| 结论 | 需要的证据 | 不够格的证据 |
|------|-----------|-------------|
| 测试通过 | 测试命令输出：0 failures | 之前的运行结果 |
| 验收场景 / 条件已满足 | command evidence + result evidence（expected 与 actual 匹配） | 测试通过 |
| 构建成功 | 构建命令：exit 0 | linter 通过 |
| 缺陷已修复 | 测试原始症状：通过 | 代码改了 |
| 回归测试有效 | Red-Green 循环已验证 | 测试只通过了一次 |

## Stage Element Model

本阶段必须维护的关键要素见 `.harness/docs/methodologies/stage-element-model.md#verify`。摘要：

| Element | Used By | Failure If Missing |
|---|---|---|
| 验收场景 / 条件 Under Verification | Delivery | 验证不对应需求 |
| Expected Result | verification report | 只跑命令没有预期 |
| Actual Result | Delivery | 结论无事实基础 |
| Command Evidence | Audit / Stage Gate | 无法复现 |
| Result Evidence | Delivery | 测试通过不等于验收场景 / 条件通过 |

按 `workflow.md` 执行详细步骤。
#!/usr/bin/env python3
"""Collect deterministic command evidence for verify and quality protocols."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHECK_ORDER = ("test", "lint", "typecheck", "build", "security")
SCRIPT_ALIASES = {
    "test": ("test", "test:unit", "test:integration", "jest", "vitest", "mocha"),
    "lint": ("lint", "lint:check", "eslint"),
    "typecheck": ("typecheck", "type-check", "tsc"),
    "build": ("build", "compile"),
    "security": ("audit", "security", "scan"),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_package_scripts(cwd: Path) -> dict[str, str]:
    package_json = cwd / "package.json"
    if not package_json.exists():
        return {}
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts")
    return scripts if isinstance(scripts, dict) else {}


def detect_package_commands(cwd: Path) -> list[dict[str, str]]:
    scripts = load_package_scripts(cwd)
    commands: list[dict[str, str]] = []
    for kind in CHECK_ORDER:
        for script_name in SCRIPT_ALIASES[kind]:
            if script_name in scripts:
                commands.append({"kind": kind, "command": f"npm run {script_name}"})
                break
    return commands


def detect_make_commands(cwd: Path) -> list[dict[str, str]]:
    makefile = cwd / "Makefile"
    if not makefile.exists():
        return []
    text = makefile.read_text(encoding="utf-8", errors="ignore")
    commands: list[dict[str, str]] = []
    make_targets = {
        "test": "test",
        "lint": "lint",
        "typecheck": "typecheck",
        "build": "build",
    }
    for kind, target in make_targets.items():
        if re.search(rf"^{re.escape(target)}\s*:", text, flags=re.MULTILINE):
            commands.append({"kind": kind, "command": f"make {target}"})
    return commands


def detect_python_commands(cwd: Path) -> list[dict[str, str]]:
    pyproject = cwd / "pyproject.toml"
    pytest_ini = cwd / "pytest.ini"
    tests_dir = cwd / "tests"
    if pytest_ini.exists() or tests_dir.exists():
        return [{"kind": "test", "command": f"{shlex.quote(sys.executable)} -m pytest"}]
    if not pyproject.exists():
        return []
    text = pyproject.read_text(encoding="utf-8", errors="ignore")
    if "[tool.pytest.ini_options]" in text or "pytest" in text:
        return [{"kind": "test", "command": f"{shlex.quote(sys.executable)} -m pytest"}]
    return []


def detect_commands(cwd: Path) -> list[dict[str, str]]:
    commands = detect_package_commands(cwd)
    if commands:
        return commands
    if (cwd / "pnpm-lock.yaml").exists() or (cwd / "yarn.lock").exists():
        return []
    commands.extend(detect_make_commands(cwd))
    commands.extend(detect_python_commands(cwd))
    if (cwd / "go.mod").exists():
        commands.append({"kind": "test", "command": "go test ./..."})
        commands.append({"kind": "build", "command": "go build ./..."})
    if (cwd / "Cargo.toml").exists():
        commands.append({"kind": "test", "command": "cargo test"})
        commands.append({"kind": "build", "command": "cargo build"})
    return commands


def run_command(command: str, cwd: Path, timeout: int) -> dict[str, Any]:
    started = now()
    started_monotonic = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            env={**os.environ, "CI": os.environ.get("CI", "1")},
        )
        output = proc.stdout or ""
        exit_code = proc.returncode
        result = "pass" if exit_code == 0 else "fail"
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        output += "\n[TIMEOUT] command exceeded timeout"
        exit_code = 124
        result = "blocked"
    ended = now()
    return {
        "command": command,
        "cwd": str(cwd),
        "exit_code": exit_code,
        "started_at": started,
        "ended_at": ended,
        "duration_seconds": round(time.monotonic() - started_monotonic, 3),
        "result": result,
        "output": output[-12000:],
    }


def write_artifact(output_dir: Path, evidence_id: str, evidence: dict[str, Any]) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{evidence_id}.log"
    path.write_text(evidence.get("output", ""), encoding="utf-8")
    return str(path)


def write_evidence_store(store: Path, mission_id: str, evidence_id: str, entry: dict[str, Any], output: str) -> str:
    evidence_dir = store / mission_id / "cmd"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    log_path = evidence_dir / f"{evidence_id}.log"
    json_path = evidence_dir / f"{evidence_id}.json"
    log_path.write_text(output, encoding="utf-8")
    payload = {
        **entry,
        "schema_version": 1,
        "stdout_excerpt_path": str(log_path),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(json_path)


def collect(
    cwd: Path,
    timeout: int,
    output_dir: Path | None,
    no_run: bool = False,
    mission_id: str | None = None,
    store: Path | None = None,
) -> dict[str, Any]:
    detected = detect_commands(cwd)
    entries: list[dict[str, Any]] = []
    if not detected:
        unavailable = {
            "id": "CMD-UNAVAILABLE-001",
            "kind": "test",
            "command": "",
            "cwd": str(cwd),
            "exit_code": None,
            "started_at": now(),
            "ended_at": now(),
            "result": "unavailable",
            "summary": "No package.json scripts, pytest config, or tests directory detected.",
            "artifact": "",
        }
        if mission_id and store:
            unavailable["artifact"] = write_evidence_store(store, mission_id, unavailable["id"], unavailable, "")
        entries.append(unavailable)
        return {"status": "WARN", "command_evidence": entries}

    for index, item in enumerate(detected, start=1):
        evidence_id = f"CMD-{index:03d}"
        if no_run:
            evidence = {
                "command": item["command"],
                "cwd": str(cwd),
                "exit_code": None,
                "started_at": now(),
                "ended_at": now(),
                "duration_seconds": 0,
                "result": "planned",
                "output": "",
            }
        else:
            evidence = run_command(item["command"], cwd, timeout)
        artifact = ""
        if output_dir and evidence.get("output"):
            artifact = write_artifact(output_dir, evidence_id, evidence)
        entry = {
            "id": evidence_id,
            "kind": item["kind"],
            "command": evidence["command"],
            "cwd": evidence["cwd"],
            "exit_code": evidence["exit_code"],
            "started_at": evidence["started_at"],
            "ended_at": evidence["ended_at"],
            "result": evidence["result"],
            "summary": f"{item['kind']} command {evidence['result']}",
            "artifact": artifact,
        }
        if mission_id and store:
            entry["artifact"] = write_evidence_store(store, mission_id, evidence_id, entry, evidence.get("output", ""))
        entries.append(entry)
    status = "FAIL" if any(entry["result"] == "fail" for entry in entries) else "BLOCKED" if any(entry["result"] == "blocked" for entry in entries) else "PASS"
    return {"status": status, "command_evidence": entries}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=".", help="Project root where commands run")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output-dir", help="Directory for command output logs")
    parser.add_argument("--mission-id", help="Mission ID for persistent command evidence store")
    parser.add_argument("--store", default="harness-runtime/harness/traces", help="Evidence store root")
    parser.add_argument("--no-run", action="store_true", help="Only detect commands")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    cwd = Path(args.cwd).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    result = collect(cwd, args.timeout, output_dir, args.no_run, args.mission_id, Path(args.store).resolve() if args.mission_id else None)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Command Evidence: {result['status']}")
        for entry in result["command_evidence"]:
            print(f"[{entry['result'].upper()}] {entry['id']} {entry['kind']}: {entry['command'] or '<unavailable>'}")
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
