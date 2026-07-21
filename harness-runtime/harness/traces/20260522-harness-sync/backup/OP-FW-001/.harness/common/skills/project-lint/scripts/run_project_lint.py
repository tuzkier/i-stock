#!/usr/bin/env python3
"""Run deterministic project-level Harness lint checks.

This linter checks the target project. It intentionally avoids semantic code
review and model judging; those belong to reviewers and evals.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - runtime guard
    raise SystemExit("PyYAML is required to run project-lint") from exc


DEFAULT_CONFIG = Path("project-knowledge/engineering/policies/project-lint.yaml")
SOURCE_REPO_CONFIG = Path("project-knowledge/engineering/policies/project-lint.yaml")
DEFAULT_REPORT_DIR = Path("harness-runtime/harness/traces/{mission_id}/project-lint")
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt", ".swift", ".rb", ".php"}


@dataclass
class Finding:
    level: str
    rule_id: str
    category: str
    message: str
    remediation: str
    paths: list[str]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def resolve_config_path(root: Path, requested: str | None) -> Path:
    if requested:
        path = Path(requested)
        return path if path.is_absolute() else root / path
    installed = root / DEFAULT_CONFIG
    if installed.exists():
        return installed
    source_repo = root / SOURCE_REPO_CONFIG
    if source_repo.exists():
        return source_repo
    return installed


def validate_profile(config: dict[str, Any], config_path: Path, findings: list[Finding]) -> None:
    if not config:
        add(
            findings,
            "FAIL",
            "P000",
            "profile",
            f"Project lint profile is missing or empty: {config_path}",
            "Create project-knowledge/engineering/policies/project-lint.yaml from the installed template or run project-lint bootstrap in the target project.",
            [str(config_path)],
        )
        return
    if config.get("schema_version") != 1:
        add(
            findings,
            "FAIL",
            "P000",
            "profile",
            "Project lint profile schema_version must be 1.",
            "Update the project lint profile to schema_version: 1.",
            [str(config_path)],
        )
    if config.get("mode") not in {"blocking", "advisory"}:
        add(
            findings,
            "FAIL",
            "P000",
            "profile",
            "Project lint profile mode must be blocking or advisory.",
            "Set mode: blocking for Gate-enforced projects or mode: advisory for warning-only rollout.",
            [str(config_path)],
        )


def add(
    findings: list[Finding],
    level: str,
    rule_id: str,
    category: str,
    message: str,
    remediation: str,
    paths: list[str] | None = None,
) -> None:
    findings.append(Finding(level, rule_id, category, message, remediation, paths or []))


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def match_any(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def detect_changed_files(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=str(root),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    return sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())


def read_changed_files(args: argparse.Namespace, root: Path) -> list[str]:
    files: list[str] = []
    for item in args.changed_file or []:
        files.append(item)
    if args.changed_files_file:
        path = Path(args.changed_files_file)
        if not path.is_absolute():
            path = root / path
        if path.exists():
            files.extend(line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    if not files and not args.no_git_diff:
        files.extend(detect_changed_files(root))
    return sorted(set(file.replace("\\", "/") for file in files))


def load_command_evidence(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    evidence: list[dict[str, Any]] = []
    for file in files:
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("command_evidence"), list):
            evidence.extend(item for item in data["command_evidence"] if isinstance(item, dict))
        elif isinstance(data, dict):
            evidence.append(data)
    return evidence


def command_evidence_refs(path: Path | None, root: Path, mission_id: str | None) -> list[str]:
    if path is None and mission_id:
        path = root / "harness-runtime" / "harness" / "traces" / mission_id / "cmd"
    if path is None or not path.exists():
        return []
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    refs: list[str] = []
    for file in files:
        try:
            refs.append(str(file.relative_to(root)))
        except ValueError:
            refs.append(str(file))
    return refs


def find_default_command_evidence(root: Path, mission_id: str | None) -> list[dict[str, Any]]:
    if not mission_id:
        return []
    return load_command_evidence(root / "harness-runtime" / "harness" / "traces" / mission_id / "cmd")


def is_code_change(path: str, config: dict[str, Any]) -> bool:
    code_config = config.get("code_change") if isinstance(config.get("code_change"), dict) else {}
    ignore_patterns = [str(item) for item in as_list(code_config.get("ignore_patterns"))]
    if match_any(path, ignore_patterns):
        return False
    patterns = [str(item) for item in as_list(code_config.get("patterns"))]
    if patterns:
        return match_any(path, patterns)
    return Path(path).suffix in SOURCE_SUFFIXES


def check_protected_paths(config: dict[str, Any], changed_files: list[str], findings: list[Finding]) -> None:
    changed_config = config.get("changed_files") if isinstance(config.get("changed_files"), dict) else {}
    protected = [str(item) for item in as_list(changed_config.get("protected_paths"))]
    if not protected:
        return
    violations = [path for path in changed_files if match_any(path, protected)]
    if violations:
        add(
            findings,
            "FAIL",
            "P001",
            "changed_files",
            "Changed files include protected Harness framework assets.",
            "Do not edit installed .harness framework assets inside a target project. Use the Harness install/update workflow or move the change into project runtime config.",
            violations,
        )


def check_command_evidence(config: dict[str, Any], changed_files: list[str], evidence: list[dict[str, Any]], findings: list[Finding]) -> None:
    code_files = [path for path in changed_files if is_code_change(path, config)]
    if not code_files:
        return
    command_config = config.get("commands") if isinstance(config.get("commands"), dict) else {}
    required = [str(item) for item in as_list(command_config.get("required_for_code_change"))] or ["test"]
    accepted = {str(item) for item in as_list(command_config.get("accepted_results"))} or {"pass"}
    passed_kinds = {str(item.get("kind")) for item in evidence if str(item.get("result", "")).lower() in accepted}
    missing = [kind for kind in required if kind not in passed_kinds]
    if missing:
        add(
            findings,
            "FAIL",
            "P002",
            "command_evidence",
            f"Code changed but required command evidence is missing or not passing: {', '.join(missing)}.",
            "Run the required local command evidence collector or project test command, then pass the generated command evidence JSON to project-lint.",
            code_files,
        )


def check_agent_instructions(root: Path, config: dict[str, Any], findings: list[Finding]) -> None:
    instruction_config = config.get("agent_instructions") if isinstance(config.get("agent_instructions"), dict) else {}
    if instruction_config.get("enabled") is False:
        return
    rel = str(instruction_config.get("path") or "AGENTS.md")
    path = root / rel
    if not path.exists():
        add(
            findings,
            "WARN",
            "P003",
            "agent_instructions",
            f"Agent instruction file is missing: {rel}.",
            "Create AGENTS.md with setup, test, style, and delivery guidance for coding agents.",
            [rel],
        )
        return
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    required = instruction_config.get("required_keywords") if isinstance(instruction_config.get("required_keywords"), dict) else {}
    missing: list[str] = []
    for section, keywords in required.items():
        values = [str(item).lower() for item in as_list(keywords)]
        if values and not any(keyword in text for keyword in values):
            missing.append(str(section))
    if missing:
        add(
            findings,
            "WARN",
            "P003",
            "agent_instructions",
            f"Agent instruction file lacks project guidance keywords for: {', '.join(missing)}.",
            "Update AGENTS.md so future agents can find setup commands, test commands, code style, and delivery checks without rediscovery.",
            [rel],
        )


def flatten_tool_calls(data: Any) -> list[str]:
    calls: list[str] = []
    if isinstance(data, dict):
        if isinstance(data.get("tool"), str):
            calls.append(data["tool"])
        if isinstance(data.get("name"), str) and data.get("type") == "tool_call":
            calls.append(data["name"])
        for value in data.values():
            calls.extend(flatten_tool_calls(value))
    elif isinstance(data, list):
        for item in data:
            calls.extend(flatten_tool_calls(item))
    return calls


def check_trace(config: dict[str, Any], trace_path: Path | None, findings: list[Finding]) -> None:
    trace_config = config.get("trace") if isinstance(config.get("trace"), dict) else {}
    if trace_config.get("enabled") is False or trace_path is None or not trace_path.exists():
        return
    try:
        data = json.loads(trace_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        add(
            findings,
            "FAIL",
            "P004",
            "trace",
            f"Trace file is not valid JSON: {trace_path}",
            "Write trace as JSON before running trace lint, or omit --trace if no machine-readable trace exists.",
            [str(trace_path)],
        )
        return
    max_repeats = int(trace_config.get("same_tool_max_repeats") or 3)
    calls = flatten_tool_calls(data)
    current = ""
    count = 0
    for tool in calls:
        if tool == current:
            count += 1
        else:
            current = tool
            count = 1
        if count > max_repeats:
            add(
                findings,
                "FAIL",
                "P004",
                "trace",
                f"Tool {tool} was called {count} times consecutively.",
                "Stop repeating the same tool call. Inspect the previous outputs, change strategy, or escalate the blocker.",
                [str(trace_path)],
            )
            return


def run_external_commands(root: Path, config: dict[str, Any], findings: list[Finding]) -> None:
    external = config.get("external_commands") if isinstance(config.get("external_commands"), dict) else {}
    for index, item in enumerate(as_list(external.get("items")), start=1):
        if not isinstance(item, dict) or not item.get("command"):
            continue
        command = str(item["command"])
        rule_id = str(item.get("id") or f"P900-{index}")
        try:
            proc = subprocess.run(command, cwd=str(root), shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=int(item.get("timeout_seconds") or 120))
        except subprocess.TimeoutExpired:
            add(findings, "FAIL", rule_id, "external_command", f"External project lint command timed out: {command}", "Fix or disable the external lint command in project-lint.yaml.", [])
            continue
        if proc.returncode != 0:
            output = (proc.stdout or "")[-2000:]
            add(
                findings,
                "FAIL" if str(item.get("severity", "FAIL")).upper() == "FAIL" else "WARN",
                rule_id,
                "external_command",
                f"External project lint command failed: {command}\n{output}",
                "Follow the command output remediation, then rerun project-lint.",
                [],
            )


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Project Lint Report",
        "",
        f"Status: {payload['status']}",
        f"Gate Effect: {payload['gate_effect']}",
        f"Generated At: {payload['generated_at']}",
        "",
        "## Findings",
        "",
    ]
    findings = payload.get("findings") or []
    if not findings:
        lines.append("No findings.")
    for item in findings:
        lines.extend(
            [
                f"### {item['rule_id']} {item['level']}",
                "",
                item["message"],
                "",
                f"Remediation: {item['remediation']}",
                "",
            ]
        )
        if item.get("paths"):
            lines.append("Paths:")
            for path in item["paths"]:
                lines.append(f"- `{path}`")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_reports(root: Path, config: dict[str, Any], mission_id: str | None, output_dir: str | None, payload: dict[str, Any]) -> None:
    if output_dir:
        report_dir = Path(output_dir)
    elif mission_id:
        reports = config.get("reports") if isinstance(config.get("reports"), dict) else {}
        template = str(reports.get("output_dir_template") or DEFAULT_REPORT_DIR)
        report_dir = Path(template.format(mission_id=mission_id))
    else:
        return
    if not report_dir.is_absolute():
        report_dir = root / report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "project-lint-report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (report_dir / "project-lint-report.md").write_text(render_markdown(payload), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    config_path = resolve_config_path(root, args.config)
    config = load_yaml(config_path)
    profile_findings: list[Finding] = []
    validate_profile(config, config_path, profile_findings)
    if config.get("enabled") is False:
        payload = {
            "schema_version": 1,
            "control": "project_lint",
            "status": "PASS",
            "mode": "advisory",
            "gate_effect": "allow",
            "generated_at": now(),
            "config": str(config_path),
            "mission_id": args.mission_id,
            "changed_files": [],
            "command_evidence_refs": [],
            "findings": [],
        }
        write_reports(root, config, args.mission_id, args.output_dir, payload)
        return payload

    changed_files = read_changed_files(args, root)
    command_evidence_path = Path(args.command_evidence).resolve() if args.command_evidence else None
    evidence = load_command_evidence(command_evidence_path) if command_evidence_path else find_default_command_evidence(root, args.mission_id)
    trace_path = Path(args.trace).resolve() if args.trace else None

    findings: list[Finding] = profile_findings
    check_protected_paths(config, changed_files, findings)
    check_command_evidence(config, changed_files, evidence, findings)
    check_agent_instructions(root, config, findings)
    check_trace(config, trace_path, findings)
    run_external_commands(root, config, findings)

    status = "FAIL" if any(item.level == "FAIL" for item in findings) else "WARN" if any(item.level == "WARN" for item in findings) else "PASS"
    mode = str(config.get("mode") or "blocking")
    if mode not in {"blocking", "advisory"}:
        mode = "blocking"
    gate_effect = "allow" if status == "PASS" else "block" if mode == "blocking" and status == "FAIL" else "warn"
    payload = {
        "schema_version": 1,
        "control": "project_lint",
        "status": status,
        "mode": mode,
        "gate_effect": gate_effect,
        "generated_at": now(),
        "config": str(config_path),
        "mission_id": args.mission_id,
        "changed_files": changed_files,
        "command_evidence_count": len(evidence),
        "command_evidence_refs": command_evidence_refs(command_evidence_path, root, args.mission_id),
        "findings": [item.__dict__ for item in findings],
    }
    write_reports(root, config, args.mission_id, args.output_dir, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--config")
    parser.add_argument("--profile", dest="config", help="Alias for --config")
    parser.add_argument("--mission-id")
    parser.add_argument("--changed-file", action="append")
    parser.add_argument("--changed-files-file")
    parser.add_argument("--command-evidence")
    parser.add_argument("--trace")
    parser.add_argument("--output-dir")
    parser.add_argument("--no-git-diff", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    payload = run(args)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Project Lint: {payload['status']}")
        for item in payload["findings"]:
            print(f"[{item['level']}] {item['rule_id']} {item['category']}: {item['message']}")
    return 1 if payload.get("gate_effect") == "block" else 0


if __name__ == "__main__":
    sys.exit(main())
