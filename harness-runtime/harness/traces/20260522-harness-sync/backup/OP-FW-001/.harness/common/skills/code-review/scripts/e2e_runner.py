#!/usr/bin/env python3
"""Run or materialize a Harness E2E control-plane plan."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def run_command(command: str, cwd: Path, timeout: int, output_path: Path | None = None) -> dict[str, Any]:
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
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    return {
        "command": command,
        "status": status,
        "exit_code": exit_code,
        "started_at": started,
        "ended_at": now(),
        "duration_seconds": round(time.monotonic() - start, 3),
        "output_excerpt": output[-12000:],
    }


def planned_result(command: str) -> dict[str, Any]:
    return {
        "command": command,
        "status": "planned",
        "exit_code": None,
        "started_at": now(),
        "ended_at": now(),
        "duration_seconds": 0,
        "output_excerpt": "",
    }


def path_exists(root: Path, rel: str) -> bool:
    return bool(rel) and (root / rel).exists()


def collect_report_paths(root: Path, paths: list[str]) -> list[str]:
    reports: list[str] = []
    for rel in paths:
        if not rel:
            continue
        path = root / rel
        if path.is_file():
            reports.append(rel)
        elif path.is_dir():
            reports.extend(str(item.relative_to(root)) for item in path.rglob("*") if item.is_file())
    return sorted(set(reports))


def collect_artifacts(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    artifact_policy = plan.get("artifact_policy") if isinstance(plan.get("artifact_policy"), dict) else {}
    initial = artifact_policy.get("collect") if isinstance(artifact_policy.get("collect"), dict) else {}
    html_report = initial.get("html_report", "") if path_exists(root, str(initial.get("html_report", ""))) else ""
    traces = set(str(item) for item in initial.get("trace") or [] if path_exists(root, str(item)))
    videos = set(str(item) for item in initial.get("video") or [] if path_exists(root, str(item)))
    screenshots = set(str(item) for item in initial.get("screenshots") or [] if path_exists(root, str(item)))

    candidates = [
        "playwright-report/index.html",
        "apps/frontend/playwright-report/index.html",
        "cypress/reports/index.html",
        "apps/frontend/cypress/reports/index.html",
    ]
    html_report = html_report or next((rel for rel in candidates if path_exists(root, rel)), "")
    scan_roots = [
        "test-results",
        "apps/frontend/test-results",
        "cypress/screenshots",
        "apps/frontend/cypress/screenshots",
        "cypress/videos",
        "apps/frontend/cypress/videos",
        str(artifact_policy.get("artifact_root") or ""),
    ]
    for rel_root in scan_roots:
        base = root / rel_root
        if not rel_root or not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(root))
            suffix = path.suffix.lower()
            name = path.name.lower()
            if suffix == ".zip" or "trace" in name:
                traces.add(rel)
            elif suffix in {".webm", ".mp4"}:
                videos.add(rel)
            elif suffix in {".png", ".jpg", ".jpeg"}:
                screenshots.add(rel)
    return {
        "html_report": html_report,
        "trace": sorted(traces),
        "video": sorted(videos),
        "screenshots": sorted(screenshots),
    }


def parse_flaky_and_skips(output: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    flaky: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    if re.search(r"\bflaky\b|\bretr(y|ied|ies)\b", output, flags=re.IGNORECASE):
        flaky.append({"reason": "runner_output_mentions_retry_or_flaky"})
    skip_matches = re.findall(r"(\d+)\s+(?:skipped|pending)", output, flags=re.IGNORECASE)
    for value in skip_matches:
        skipped.append({"count": int(value), "reason": "runner_reported_skipped_tests"})
    return flaky, skipped


def run_plan(root: Path, plan: dict[str, Any], execute: bool, install: bool, timeout: int) -> dict[str, Any]:
    mission_id = plan.get("mission_id")
    artifact_root = ((plan.get("artifact_policy") or {}).get("artifact_root") or f"harness-runtime/harness/traces/{mission_id or 'unknown'}/e2e")
    artifact_dir = root / str(artifact_root)

    install_results = []
    if install:
        for action in plan.get("install_actions") or []:
            if not isinstance(action, dict):
                continue
            command = str(action.get("command") or "")
            if not command:
                continue
            result = run_command(command, root, timeout) if execute else planned_result(command)
            install_results.append({**action, "result": result})

    tool_runs = []
    selected_tools = {
        str(detail.get("selected_tool"))
        for obligation in plan.get("obligations") or plan.get("tasks") or []
        if isinstance(obligation, dict)
        for detail in (obligation.get("capabilities") or {}).values()
        if isinstance(detail, dict) and detail.get("selected_tool")
    }
    seen_commands: set[str] = set()
    for tool in plan.get("toolchain") or []:
        if not isinstance(tool, dict):
            continue
        tool_name = str(tool.get("tool"))
        if selected_tools and tool_name not in selected_tools:
            continue
        for command in tool.get("commands") or []:
            command = str(command)
            if not command or command in seen_commands:
                continue
            seen_commands.add(command)
            output_path = artifact_dir / f"{tool_name.replace('/', '_').replace('@', '')}-output.txt"
            if not tool.get("configured") and execute:
                result = {
                    "command": command,
                    "status": "blocked",
                    "exit_code": None,
                    "started_at": now(),
                    "ended_at": now(),
                    "duration_seconds": 0,
                    "output_excerpt": "E2E tool is not configured; resolver reported missing capability.",
                }
            else:
                result = run_command(command, root, timeout, output_path) if execute else planned_result(command)
            reports = collect_report_paths(root, [str(path) for path in tool.get("report_paths") or []])
            flaky, skipped = parse_flaky_and_skips(result.get("output_excerpt") or "")
            tool_runs.append({
                "tool": tool_name,
                "category": tool.get("category"),
                "configured": tool.get("configured"),
                "available": tool.get("available"),
                "result": result,
                "report_paths": reports,
                "declared_report_paths": tool.get("report_paths") or [],
                "flaky_signals": flaky,
                "skipped_tests": skipped,
            })

    statuses = [entry["result"]["status"] for entry in [*install_results, *tool_runs]]
    if not statuses:
        status = "WARN"
    elif "fail" in statuses:
        status = "FAIL"
    elif "blocked" in statuses:
        status = "BLOCKED"
    elif statuses and all(status == "planned" for status in statuses):
        status = "PLANNED"
    else:
        status = "PASS"

    return {
        "schema_version": 1,
        "type": "e2e_run",
        "mission_id": mission_id,
        "status": status,
        "mode": "execute" if execute else "plan_only",
        "install_results": install_results,
        "tool_runs": tool_runs,
        "artifacts": collect_artifacts(root, plan),
        "flaky_signals": [item for run in tool_runs for item in run.get("flaky_signals") or []],
        "skipped_tests": [item for run in tool_runs for item in run.get("skipped_tests") or []],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--mission-id")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output")
    parser.add_argument("--execute", action="store_true", help="Actually run E2E commands. Default only materializes planned commands.")
    parser.add_argument("--install", action="store_true", help="Include install actions from the plan.")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    plan = load_json(Path(args.plan))
    if args.mission_id and not plan.get("mission_id"):
        plan["mission_id"] = args.mission_id
    result = run_plan(root, plan, args.execute, args.install, args.timeout)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] in {"FAIL", "BLOCKED"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
