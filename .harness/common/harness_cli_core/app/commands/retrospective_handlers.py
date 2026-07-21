"""Handlers for the retrospective family of CLI commands.

Covers four top-level CLI subcommands:

* ``harness mission artifacts`` / ``mission retrospective-data`` —
  retrospective inputs assembled per-mission.
* ``harness project-context add-lesson|drift-scan|lint`` —
  ``project-context.md`` lifecycle.
* ``harness retrospective harness-gap-init|harness-gap-emit`` —
  harness-gap YAML store.
* ``harness harness-gap pattern-scan`` and ``harness agent-eval drift`` —
  cross-mission analysis.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from collections import defaultdict
from pathlib import Path

from harness_cli_core.app.commands.context_handlers import project_context_path
from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.retrospective import (
    read_approvals_for_mission,
    read_stage_effectiveness,
    read_trace_events,
    stage_dir,
)
from harness_cli_core.infra.io import load_yaml, write_yaml
from harness_cli_core.infra.runtime_paths import mission_artifact_dir, relpath, runtime_harness_root
from harness_cli_core.infra.time import today


def cmd_mission_artifacts(args: argparse.Namespace) -> int:
    """Return artifact index for a mission stage that Gate has accepted."""
    root = Path(root_arg(args))
    mission = args.mission
    stage_filter = getattr(args, "stage", None)
    harness_root = runtime_harness_root(root)
    stages_root = harness_root / "stages" / mission
    artifacts_root = mission_artifact_dir(root, mission)
    artifact_defs = [
        ("prd", "product/product-definition.md", "product/product-definition.md"),
        ("prd", "product/product-domain-model.md", "product/product-domain-model.md"),
        ("prd", "product/product-evidence.md", "product/product-evidence.md"),
        ("solution", "solution/solution.md", "solution.md"),
        ("tech-design", "technical-analysis/tech-design.md", "tech-design.md"),
        ("interaction", "interaction/interaction.md", "interaction.md"),
        ("execution-brief", "breakdown/execution-brief.md", "execution-brief.md"),
        ("verification-report", "verify/verification-report.md", "verification-report.md"),
        ("code-review", "code-review/code-review.md", "code-review.md"),
        ("acceptance-result", "delivery/acceptance-result.md", "acceptance-result.md"),
        ("delivery", "delivery/delivery-package.md", "delivery.md"),
        ("retrospective", "retrospective/retrospective.md", "retrospective.md"),
    ]
    artifacts = []
    for stage, artifact_name, legacy_name in artifact_defs:
        canonical_path = artifacts_root / artifact_name
        legacy_path = stages_root / legacy_name
        path = canonical_path if canonical_path.exists() or not legacy_path.exists() else legacy_path
        artifacts.append(
            {
                "stage": stage,
                "path": relpath(root, path),
                "exists": path.exists(),
                "source": "artifacts" if path == canonical_path else "stages",
            }
        )
    if stage_filter:
        artifacts = [a for a in artifacts if a["stage"] == stage_filter]
    findings: list[dict] = []
    existing = [a for a in artifacts if a["exists"]]
    if not existing:
        findings.append(
            {
                "level": "WARN",
                "code": "no_artifacts_found",
                "message": f"No artifacts found for mission {mission}. Stage may not have started yet.",
            }
        )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "mission.artifacts",
            "mission": mission,
            "artifacts": artifacts,
            "count": len(existing),
            "findings": findings,
        },
    )


def cmd_mission_retrospective_data(args: argparse.Namespace) -> int:
    """Aggregate retrospective input data for a mission."""
    root = Path(root_arg(args))
    mission = args.mission
    findings: list[dict] = []

    trace_events = read_trace_events(root, mission)
    approvals = read_approvals_for_mission(root, mission)
    effectiveness = read_stage_effectiveness(root, mission)

    stages: list[dict] = []
    for stage_key, er in effectiveness.items():
        stages.append(
            {
                "stage": stage_key,
                "rounds_used": er.get("rounds_used"),
                "last_verdict": er.get("last_verdict"),
                "checkpoints": er.get("checkpoints", []),
                "stop_events": [
                    e for e in trace_events if e.get("stage") == stage_key and e.get("type") == "stop_event"
                ],
                "approvals": [a for a in approvals if a.get("stage") == stage_key],
                "trace_event_count": sum(
                    1 for e in trace_events if e.get("stage") == stage_key
                ),
            }
        )

    cross_stage_failures = [
        e for e in trace_events if e.get("status") == "fail" or e.get("type") == "gate_fail"
    ]

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "mission.retrospective-data",
            "mission": mission,
            "stages": stages,
            "cross_stage_failures": cross_stage_failures,
            "trace_event_count": len(trace_events),
            "approval_count": len(approvals),
            "findings": findings,
        },
    )


def cmd_project_context_add_lesson(args: argparse.Namespace) -> int:
    """Append a lesson to the project-context.md 历史教训 section."""
    root = Path(root_arg(args))
    lesson_text = (args.lesson or "").strip()
    if not lesson_text:
        return emit_payload(
            args,
            fail_payload(
                "project-context.add-lesson",
                "empty_lesson",
                "--lesson is required and must not be empty.",
            ),
        )
    ctx_path = project_context_path(root)
    if not ctx_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "project-context.add-lesson",
                "project_context_missing",
                f"project-context.md does not exist at {ctx_path}; run 'harness context init' first.",
            ),
        )
    date_str = getattr(args, "date", None) or today()
    source = getattr(args, "source", None)
    entry = f"- {date_str} {lesson_text}"
    if source:
        entry = entry + f" (source: {source})"

    content = ctx_path.read_text(encoding="utf-8")
    section_pattern = re.compile(
        r"(##\s*历史教训[^\n]*\n)(.*?)(\n##|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    m = section_pattern.search(content)
    if m:
        new_section = m.group(1) + m.group(2).rstrip() + "\n" + entry + "\n"
        new_content = content[: m.start()] + new_section + content[m.end():]
    else:
        new_content = content.rstrip() + "\n\n## 历史教训\n\n" + entry + "\n"

    ctx_path.write_text(new_content, encoding="utf-8")
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "project-context.add-lesson",
            "lesson": entry,
            "path": str(ctx_path.relative_to(root)),
            "findings": [],
        },
    )


def cmd_project_context_drift_scan(args: argparse.Namespace) -> int:
    """Scan project-context.md for stale or duplicate lessons."""
    root = Path(root_arg(args))
    ctx_path = project_context_path(root)
    if not ctx_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "project-context.drift-scan",
                "project_context_missing",
                f"project-context.md does not exist at {ctx_path}; run 'harness context init' first.",
            ),
        )
    content = ctx_path.read_text(encoding="utf-8")
    findings: list[dict] = []

    lesson_lines = re.findall(r"^- (\d{4}-\d{2}-\d{2}) (.+)$", content, re.MULTILINE)

    seen: dict[str, list[str]] = {}
    for date_str, text in lesson_lines:
        key = text.strip().lower()
        seen.setdefault(key, []).append(date_str)
    for text, dates in seen.items():
        if len(dates) > 1:
            findings.append(
                {
                    "level": "WARN",
                    "code": "duplicate_lesson",
                    "message": f"Duplicate lesson found on dates {dates}: '{text[:80]}'",
                }
            )

    today_dt = dt.date.today()
    stale_threshold = 365
    stale_count = 0
    for date_str, _ in lesson_lines:
        try:
            lesson_dt = dt.date.fromisoformat(date_str)
            if (today_dt - lesson_dt).days > stale_threshold:
                stale_count += 1
        except ValueError:
            findings.append(
                {
                    "level": "WARN",
                    "code": "invalid_date_format",
                    "message": f"Lesson date '{date_str}' does not match YYYY-MM-DD format.",
                }
            )

    if stale_count > 0:
        findings.append(
            {
                "level": "INFO",
                "code": "stale_lessons",
                "message": f"{stale_count} lesson(s) are older than {stale_threshold} days and may be stale.",
            }
        )

    status = "WARN" if any(f["level"] == "WARN" for f in findings) else "PASS"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "project-context.drift-scan",
            "lesson_count": len(lesson_lines),
            "stale_count": stale_count,
            "findings": findings,
        },
    )


def cmd_project_context_lint(args: argparse.Namespace) -> int:
    """Lint project-context.md for format compliance."""
    root = Path(root_arg(args))
    ctx_path = project_context_path(root)
    if not ctx_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "project-context.lint",
                "project_context_missing",
                "project-context.md does not exist; run 'harness context init' first.",
            ),
        )
    content = ctx_path.read_text(encoding="utf-8")
    findings: list[dict] = []

    for i, line in enumerate(content.splitlines(), 1):
        if line.startswith("- ") and not re.match(r"^- \d{4}-\d{2}-\d{2} ", line):
            findings.append(
                {
                    "level": "WARN",
                    "code": "missing_date_prefix",
                    "message": f"Line {i}: lesson entry missing YYYY-MM-DD date prefix: {line[:80]}",
                }
            )

    status = "WARN" if findings else "PASS"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "project-context.lint",
            "findings": findings,
        },
    )


def cmd_retrospective_harness_gap_init(args: argparse.Namespace) -> int:
    """Initialize the harness-gap YAML store for a mission."""
    root = Path(root_arg(args))
    mission = args.mission
    sdir = stage_dir(root, mission)
    gap_path = sdir / "harness-gap.yaml"
    if gap_path.exists():
        return emit_payload(
            args,
            {
                "status": "PASS",
                "control": "retrospective.harness-gap-init",
                "mission": mission,
                "path": str(gap_path.relative_to(root)),
                "created": False,
                "findings": [
                    {
                        "level": "INFO",
                        "code": "already_exists",
                        "message": "harness-gap.yaml already exists.",
                    }
                ],
            },
        )
    sdir.mkdir(parents=True, exist_ok=True)
    doc = {"mission": mission, "gaps": []}
    write_yaml(gap_path, doc)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "retrospective.harness-gap-init",
            "mission": mission,
            "path": str(gap_path.relative_to(root)),
            "created": True,
            "findings": [],
        },
    )


def cmd_retrospective_harness_gap_emit(args: argparse.Namespace) -> int:
    """Append a gap record to harness-gap.yaml."""
    root = Path(root_arg(args))
    mission = args.mission
    sdir = stage_dir(root, mission)
    canonical_retro_md = mission_artifact_dir(root, mission) / "retrospective" / "retrospective.md"
    legacy_retro_md = sdir / "retrospective.md"
    retro_md = canonical_retro_md if canonical_retro_md.exists() else legacy_retro_md
    if not retro_md.exists():
        return emit_payload(
            args,
            fail_payload(
                "retrospective.harness-gap-emit",
                "retrospective_md_missing",
                "retrospective.md not found at "
                f"{relpath(root, canonical_retro_md)} or {relpath(root, legacy_retro_md)}; write Step 3 first.",
            ),
        )
    gap_path = sdir / "harness-gap.yaml"
    if not gap_path.exists():
        doc = {"mission": mission, "gaps": []}
    else:
        doc = load_yaml(gap_path) or {"mission": mission, "gaps": []}
    gaps = doc.setdefault("gaps", [])
    gap_id = args.gap_id
    if any(g.get("gap_id") == gap_id for g in gaps):
        return emit_payload(
            args,
            fail_payload(
                "retrospective.harness-gap-emit",
                "duplicate_gap_id",
                f"gap_id '{gap_id}' already exists in harness-gap.yaml.",
            ),
        )
    gap_record = {
        "gap_id": gap_id,
        "pattern_key": args.pattern_key,
        "target_kind": args.target_kind,
        "severity": getattr(args, "severity", "medium"),
        "description": args.description,
        "first_seen": getattr(args, "first_seen", None) or today(),
        "repeat_count": 1,
        "status": "open",
    }
    if getattr(args, "verification_ref", None):
        gap_record["verification_ref"] = args.verification_ref
    gaps.append(gap_record)
    write_yaml(gap_path, doc)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "retrospective.harness-gap-emit",
            "mission": mission,
            "gap_id": gap_id,
            "path": str(gap_path.relative_to(root)),
            "findings": [],
        },
    )


def cmd_harness_gap_pattern_scan(args: argparse.Namespace) -> int:
    """Scan harness-gap.yaml for recurring gap patterns."""
    root = Path(root_arg(args))
    mission = args.mission
    min_repeat = getattr(args, "min_repeat", 2)
    gap_path = stage_dir(root, mission) / "harness-gap.yaml"
    if not gap_path.exists():
        return emit_payload(
            args,
            {
                "status": "PASS",
                "control": "harness-gap.pattern-scan",
                "mission": mission,
                "patterns": [],
                "findings": [
                    {
                        "level": "INFO",
                        "code": "no_gap_file",
                        "message": "harness-gap.yaml not found; no gaps recorded.",
                    }
                ],
            },
        )
    doc = load_yaml(gap_path) or {}
    gaps = doc.get("gaps", [])
    by_key: dict[str, list[dict]] = defaultdict(list)
    for g in gaps:
        by_key[g.get("pattern_key", "unknown")].append(g)
    patterns: list[dict] = []
    findings: list[dict] = []
    for pattern_key, gap_list in by_key.items():
        total_repeat = sum(g.get("repeat_count", 1) for g in gap_list)
        if total_repeat >= min_repeat:
            patterns.append(
                {
                    "pattern_key": pattern_key,
                    "gap_count": len(gap_list),
                    "total_repeat_count": total_repeat,
                    "gap_ids": [g["gap_id"] for g in gap_list],
                }
            )
            findings.append(
                {
                    "level": "WARN",
                    "code": "recurring_pattern",
                    "message": f"Pattern '{pattern_key}' appears {total_repeat} time(s) across {len(gap_list)} gap(s).",
                }
            )
    return emit_payload(
        args,
        {
            "status": "WARN" if patterns else "PASS",
            "control": "harness-gap.pattern-scan",
            "mission": mission,
            "patterns": patterns,
            "findings": findings,
        },
    )


def _extract_pass_rate(text: str) -> float | None:
    m = re.search(
        r"通过率[:：]\s*([0-9.]+)%|pass\s+rate[:：]\s*([0-9.]+)%",
        text,
        re.IGNORECASE,
    )
    if m:
        val = m.group(1) or m.group(2)
        try:
            return float(val) / 100.0
        except ValueError:
            return None
    return None


def cmd_agent_eval_drift(args: argparse.Namespace) -> int:
    """Compare agent-eval pass rates between current and baseline missions."""
    root = Path(root_arg(args))
    mission = args.mission
    baseline_mission = getattr(args, "baseline_mission", None)
    threshold = getattr(args, "threshold", 0.1)
    findings: list[dict] = []

    current_report = stage_dir(root, mission) / "agent-eval-report.md"
    if not current_report.exists():
        findings.append(
            {
                "level": "WARN",
                "code": "eval_report_missing",
                "message": f"agent-eval-report.md not found for mission {mission}; agent evaluation was not performed.",
            }
        )
        return emit_payload(
            args,
            {
                "status": "WARN",
                "control": "agent-eval.drift",
                "mission": mission,
                "baseline": None,
                "drift_summary": None,
                "regressions": [],
                "findings": findings,
            },
        )
    if not baseline_mission:
        findings.append(
            {
                "level": "WARN",
                "code": "no_baseline",
                "message": (
                    "No --baseline mission provided; cannot compute drift. "
                    "Establish a baseline by passing --baseline <mission-id> on a known-good mission."
                ),
            }
        )
        return emit_payload(
            args,
            {
                "status": "WARN",
                "control": "agent-eval.drift",
                "mission": mission,
                "baseline": None,
                "drift_summary": None,
                "regressions": [],
                "findings": findings,
            },
        )
    baseline_report = stage_dir(root, baseline_mission) / "agent-eval-report.md"
    if not baseline_report.exists():
        findings.append(
            {
                "level": "WARN",
                "code": "baseline_report_missing",
                "message": f"agent-eval-report.md not found for baseline mission {baseline_mission}.",
            }
        )
        return emit_payload(
            args,
            {
                "status": "WARN",
                "control": "agent-eval.drift",
                "mission": mission,
                "baseline": baseline_mission,
                "drift_summary": None,
                "regressions": [],
                "findings": findings,
            },
        )

    current_text = current_report.read_text(encoding="utf-8")
    baseline_text = baseline_report.read_text(encoding="utf-8")
    current_rate = _extract_pass_rate(current_text)
    baseline_rate = _extract_pass_rate(baseline_text)

    regressions: list[dict] = []
    status = "PASS"
    if current_rate is not None and baseline_rate is not None:
        delta = current_rate - baseline_rate
        if delta < -threshold:
            regressions.append(
                {
                    "type": "pass_rate_regression",
                    "delta": round(delta, 4),
                    "threshold": threshold,
                    "message": (
                        f"Pass rate dropped from {baseline_rate:.1%} to {current_rate:.1%} "
                        f"(delta={delta:.1%}, threshold={-threshold:.1%})."
                    ),
                }
            )
            status = "WARN"
            findings.append(
                {
                    "level": "WARN",
                    "code": "pass_rate_regression",
                    "message": regressions[-1]["message"],
                }
            )
    else:
        status = "WARN"
        findings.append(
            {
                "level": "WARN",
                "code": "pass_rate_not_found",
                "message": "Could not extract pass rate from one or both eval reports.",
            }
        )

    return emit_payload(
        args,
        {
            "status": status,
            "control": "agent-eval.drift",
            "mission": mission,
            "baseline": baseline_mission,
            "drift_summary": {
                "current_pass_rate": current_rate,
                "baseline_pass_rate": baseline_rate,
                "delta": round(current_rate - baseline_rate, 4)
                if current_rate is not None and baseline_rate is not None
                else None,
                "threshold": threshold,
            },
            "regressions": regressions,
            "findings": findings,
        },
    )


__all__ = [
    "cmd_mission_artifacts",
    "cmd_mission_retrospective_data",
    "cmd_project_context_add_lesson",
    "cmd_project_context_drift_scan",
    "cmd_project_context_lint",
    "cmd_retrospective_harness_gap_init",
    "cmd_retrospective_harness_gap_emit",
    "cmd_harness_gap_pattern_scan",
    "cmd_agent_eval_drift",
]
