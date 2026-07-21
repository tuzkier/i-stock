#!/usr/bin/env python3
"""Check control-plane reports for Stage Gate consumption."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # pragma: no cover - runtime guard
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# Mirrors run_project_lint.SOURCE_SUFFIXES so the gate's freshness check and the
# linter that produced the report agree on what counts as a code change.
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt", ".swift", ".rb", ".php"}


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: str = ""


def add(findings: list[Finding], level: str, code: str, message: str, path: str = "") -> None:
    findings.append(Finding(level, code, message, path))


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None or not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def resolve_harness_config(root: Path) -> dict[str, Any]:
    for rel in ("harness-runtime/config/harness.yaml", "harness-runtime/config/harness.yaml"):
        config = load_yaml(root / rel)
        if config:
            return config
    return {}


def resolve_lint_profile(root: Path, harness_config: dict[str, Any]) -> dict[str, Any]:
    project_lint = harness_config.get("project_lint") if isinstance(harness_config.get("project_lint"), dict) else {}
    candidates: list[Path] = []
    configured = str(project_lint.get("profile") or "").strip()
    if configured:
        path = Path(configured)
        candidates.append(path if path.is_absolute() else root / path)
    candidates.append(root / "project-knowledge/engineering/policies/project-lint.yaml")
    candidates.append(root / "project-knowledge/engineering/policies/project-lint.yaml")
    for candidate in candidates:
        profile = load_yaml(candidate)
        if profile:
            return profile
    return {}


def match_any(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def _as_pattern_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def is_code_change(path: str, profile: dict[str, Any]) -> bool:
    code_config = profile.get("code_change") if isinstance(profile.get("code_change"), dict) else {}
    ignore = _as_pattern_list(code_config.get("ignore_patterns"))
    if ignore and match_any(path, ignore):
        return False
    patterns = _as_pattern_list(code_config.get("patterns"))
    if patterns:
        return match_any(path, patterns)
    return Path(path).suffix in SOURCE_SUFFIXES


def git_changed_files(root: Path) -> list[str]:
    try:
        inside = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return []
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
    return sorted({line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()})


def current_code_changes(root: Path, profile: dict[str, Any], override: list[str] | None) -> list[str]:
    files = override if override is not None else git_changed_files(root)
    return sorted({f.replace("\\", "/") for f in files if is_code_change(f, profile)})


def load_report(path: Path, findings: list[Finding]) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add(findings, "FAIL", "invalid_control_report_json", f"{path}: {exc}", str(path))
        return None
    if not isinstance(data, dict):
        add(findings, "FAIL", "invalid_control_report", f"{path}: root must be an object", str(path))
        return None
    return data


def validate_report(path: Path, report: dict[str, Any], findings: list[Finding]) -> None:
    for field in ("schema_version", "control", "status", "gate_effect", "findings"):
        if field not in report:
            add(findings, "FAIL", "invalid_control_report", f"{path}: missing {field}", str(path))
    if report.get("schema_version") != 1:
        add(findings, "FAIL", "invalid_control_report", f"{path}: schema_version must be 1", str(path))
    if report.get("status") not in {"PASS", "WARN", "FAIL"}:
        add(findings, "FAIL", "invalid_control_report", f"{path}: invalid status {report.get('status')}", str(path))
    if report.get("gate_effect") not in {"allow", "warn", "block"}:
        add(findings, "FAIL", "invalid_control_report", f"{path}: invalid gate_effect {report.get('gate_effect')}", str(path))
    if not isinstance(report.get("findings"), list):
        add(findings, "FAIL", "invalid_control_report", f"{path}: findings must be a list", str(path))


def discover_reports(root: Path, mission_id: str | None, explicit: list[str]) -> list[Path]:
    reports = [Path(item) if Path(item).is_absolute() else root / item for item in explicit]
    if mission_id:
        traces = root / "harness-runtime" / "harness" / "traces" / mission_id
        reports.extend(sorted((traces / "controls").glob("*/*.json")))
        reports.extend(sorted((traces / "project-lint").glob("project-lint-report.json")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for report in reports:
        resolved = report.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(report)
    return unique


def enforce_project_lint_freshness(
    root: Path,
    loaded_reports: dict[str, dict[str, Any]],
    findings: list[Finding],
    changed_files_override: list[str] | None,
) -> None:
    """When the project changed code, a fresh project_lint report is mandatory.

    This is config-driven (project_lint.enabled + require_for_code_change) and runs
    on every gate, so a missing or stale report fails the gate the moment a
    code-touching stage tries to advance — not several stages later."""
    harness_config = resolve_harness_config(root)
    project_lint = harness_config.get("project_lint") if isinstance(harness_config.get("project_lint"), dict) else {}
    if not (project_lint.get("enabled") and project_lint.get("require_for_code_change")):
        return
    profile = resolve_lint_profile(root, harness_config)
    code_files = current_code_changes(root, profile, changed_files_override)
    if not code_files:
        return
    report = loaded_reports.get("project_lint")
    if report is None:
        add(
            findings,
            "FAIL",
            "missing_required_control_report",
            "Code changed but no project_lint control report exists. Run `harness lint project --mission <id>` before this gate.",
        )
        return
    covered = {str(item).replace("\\", "/") for item in report.get("changed_files") or []}
    uncovered = [path for path in code_files if path not in covered]
    if uncovered:
        preview = ", ".join(uncovered[:20])
        add(
            findings,
            "FAIL",
            "stale_control_report",
            "project_lint report does not cover current code changes; rerun `harness lint project` for the latest diff. "
            f"Uncovered: {preview}",
        )


def prototype_manifest_path(root: Path, mission_id: str | None) -> Path:
    """Mirrors run_project_lint.prototype_manifest_path so the gate, the linter and
    the underlying checkers agree on which manifest is in play. Resolves the same
    candidate set as ``harness_cli_core.domain.interaction.load_visual_manifest``
    (artifacts ``interaction/visual-interaction/`` plus legacy artifacts / stage_dir
    fallbacks) so a manifest stored at a fallback location cannot silently bypass the
    ``require_for_prototype`` gate. Falls back to the canonical path when the CLI
    core is unavailable."""
    canonical = (
        root / "harness-runtime" / "harness" / "artifacts" / (mission_id or "")
        / "interaction" / "visual-interaction" / "visual-interaction-manifest.json"
    )
    if not mission_id:
        return canonical
    common_root = Path(__file__).resolve().parents[3]
    if str(common_root) not in sys.path:
        sys.path.insert(0, str(common_root))
    try:
        from harness_cli_core.domain.interaction import load_visual_manifest
    except Exception:  # noqa: BLE001 - degrade to canonical path when core absent
        return canonical
    try:
        resolved, _ = load_visual_manifest(root, mission_id)
    except Exception:  # noqa: BLE001 - keep the gate deterministic
        return canonical
    return resolved


def enforce_project_lint_prototype(
    root: Path,
    mission_id: str | None,
    loaded_reports: dict[str, dict[str, Any]],
    findings: list[Finding],
) -> None:
    """When the mission produced a visual-interaction manifest (interaction /
    prototype stage), a fresh project_lint report is mandatory so the prototype
    trace constraint (SURF↔SUC↔OBJ) is enforced at the Stage Gate — not only at
    verify. Config-driven (project_lint.enabled + require_for_prototype)."""
    harness_config = resolve_harness_config(root)
    project_lint = harness_config.get("project_lint") if isinstance(harness_config.get("project_lint"), dict) else {}
    if not (project_lint.get("enabled") and project_lint.get("require_for_prototype")):
        return
    if not mission_id:
        return
    manifest = prototype_manifest_path(root, mission_id)
    if not manifest.exists():
        return
    report = loaded_reports.get("project_lint")
    if report is None:
        add(
            findings,
            "FAIL",
            "missing_required_control_report",
            "Prototype manifest exists but no project_lint control report covers it. "
            "Run `harness lint project --mission <id>` before this gate.",
        )
        return
    recorded = report.get("prototype_manifest_mtime")
    current = manifest.stat().st_mtime
    if not isinstance(recorded, (int, float)) or recorded + 1e-6 < current:
        add(
            findings,
            "FAIL",
            "stale_control_report",
            "project_lint report does not cover the current prototype manifest; "
            "rerun `harness lint project` after the latest interaction output.",
        )


def check(
    root: Path,
    mission_id: str | None,
    reports: list[str],
    required_controls: list[str],
    changed_files_override: list[str] | None = None,
) -> dict[str, Any]:
    findings: list[Finding] = []
    report_paths = discover_reports(root, mission_id, reports)
    seen_controls: set[str] = set()
    loaded_reports: dict[str, dict[str, Any]] = {}
    controls: list[dict[str, Any]] = []
    for path in report_paths:
        if not path.exists():
            add(findings, "FAIL", "missing_control_report", f"Control report not found: {path}", str(path))
            continue
        report = load_report(path, findings)
        if report is None:
            continue
        validate_report(path, report, findings)
        control_name = str(report.get("control") or "")
        if control_name:
            seen_controls.add(control_name)
            loaded_reports[control_name] = report
        gate_effect = report.get("gate_effect")
        if gate_effect == "block":
            add(findings, "FAIL", "control_report_blocks_gate", f"{control_name or path.name} gate_effect=block", str(path))
        elif gate_effect == "warn":
            add(findings, "WARN", "control_report_warns_gate", f"{control_name or path.name} gate_effect=warn", str(path))
        controls.append({"path": str(path), "control": control_name, "status": report.get("status"), "gate_effect": gate_effect})

    for control in required_controls:
        if control and control not in seen_controls:
            add(findings, "FAIL", "missing_required_control_report", f"Required control report missing: {control}")

    enforce_project_lint_freshness(root, loaded_reports, findings, changed_files_override)
    enforce_project_lint_prototype(root, mission_id, loaded_reports, findings)

    if not findings:
        add(findings, "PASS", "control_reports_valid", "Control-plane reports allow Stage Gate to continue")
    status = "FAIL" if any(item.level == "FAIL" for item in findings) else "WARN" if any(item.level == "WARN" for item in findings) else "PASS"
    return {"status": status, "controls": controls, "findings": [item.__dict__ for item in findings]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--mission-id")
    parser.add_argument("--report", action="append", default=[])
    parser.add_argument("--required-control", action="append", default=[])
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    override = args.changed_file if args.changed_file else None
    payload = check(Path(args.root).resolve(), args.mission_id, args.report, args.required_control, override)
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload["status"])
    return 1 if payload["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
