#!/usr/bin/env python3
"""Run or materialize a Harness TDD toolchain plan."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def run_command(command: str, cwd: Path, timeout: int) -> dict[str, Any]:
    started = now()
    start = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output = proc.stdout or ""
        exit_code = proc.returncode
        status = "pass" if exit_code == 0 else "fail"
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        output += "\n[TIMEOUT]"
        exit_code = 124
        status = "blocked"
    return {
        "command": command,
        "status": status,
        "exit_code": exit_code,
        "started_at": started,
        "ended_at": now(),
        "duration_seconds": round(time.monotonic() - start, 3),
        "output_excerpt": output[-12000:],
    }


def run_plan(root: Path, plan: dict[str, Any], execute: bool, install: bool, timeout: int) -> dict[str, Any]:
    install_results = []
    if install:
        for action in plan.get("install_actions") or []:
            command = action.get("command")
            if not command:
                continue
            result = run_command(command, root, timeout) if execute else {
                "command": command,
                "status": "planned",
                "exit_code": None,
                "started_at": now(),
                "ended_at": now(),
                "duration_seconds": 0,
                "output_excerpt": "",
            }
            install_results.append({**action, "result": result})

    tool_runs = []
    seen_commands: set[str] = set()
    for tool in plan.get("toolchain") or []:
        if not isinstance(tool, dict):
            continue
        for command in tool.get("commands") or []:
            if not command or command in seen_commands:
                continue
            seen_commands.add(command)
            rendered = (
                command
                .replace("<mission-id>", str(plan.get("mission_id")))
                .replace("<baseline>", str(plan.get("probe", {}).get("baseline_commit") or "HEAD~1"))
            )
            result = run_command(rendered, root, timeout) if execute else {
                "command": rendered,
                "status": "planned",
                "exit_code": None,
                "started_at": now(),
                "ended_at": now(),
                "duration_seconds": 0,
                "output_excerpt": "",
            }
            tool_runs.append({
                "tool": tool.get("tool"),
                "category": tool.get("category"),
                "configured": tool.get("configured"),
                "available": tool.get("available"),
                "result": result,
                "report_paths": tool.get("report_paths") or [],
            })

    statuses = [entry["result"]["status"] for entry in [*install_results, *tool_runs]]
    status = "FAIL" if "fail" in statuses else "BLOCKED" if "blocked" in statuses else "PLANNED" if statuses and all(s == "planned" for s in statuses) else "PASS"
    return {
        "schema_version": 1,
        "mission_id": plan.get("mission_id"),
        "status": status,
        "mode": "execute" if execute else "plan_only",
        "install_results": install_results,
        "tool_runs": tool_runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output")
    parser.add_argument("--execute", action="store_true", help="Actually run tool commands. Default only materializes planned commands.")
    parser.add_argument("--install", action="store_true", help="Include install actions from the plan.")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    result = run_plan(root, load_json(Path(args.plan)), args.execute, args.install, args.timeout)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] in {"FAIL", "BLOCKED"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
