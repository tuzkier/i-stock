"""Handlers for `harness discovery ...` and `harness graphify ...` commands.

discovery-improvement-plan M2.1 — typed CLI outputs replacing prompt-only
HARD-GATE judgments in discovery/workflow.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.approvals import (
    load_approvals,
    next_approval_id,
    write_approvals,
)
from harness_cli_core.domain.discovery import (
    DEPENDENCY_TRIGGER_KEYWORDS,
    GRAPHIFY_INDEX_FRESH_HOURS,
)
from harness_cli_core.infra.runtime_paths import relpath
from harness_cli_core.infra.time import now_iso


def cmd_graphify_status(args: argparse.Namespace) -> int:
    """Return typed Graphify index status for the current project root.

    Discovery workflow Step 2 brownfield HARD-GATE consumes this to decide
    whether ``degradations[]`` must record ``graphify_unavailable`` /
    ``graphify_stale``. The check is purely on-disk so the result remains
    deterministic, offline-safe, and fast inside hooks.

    Reports three orthogonal facts so downstream hooks / reviewers can give
    actionable guidance:

    - ``cli_installed``: ``graphify`` (or ``python -m graphify``) is on PATH.
    - ``available`` / ``indexed``: ``graphify-out/`` exists and is non-empty.
    - ``fresh``: ``graphify-out/`` mtime is within ``GRAPHIFY_INDEX_FRESH_HOURS``.

    When ``cli_installed=False`` the user must install the PyPI package
    (``graphifyy``) before any other graphify command works.
    """
    root = Path(root_arg(args))
    candidates = [root / "graphify-out", Path.cwd() / "graphify-out"]
    index_dir = next((p for p in candidates if p.exists() and p.is_dir()), None)
    cli_installed = shutil.which("graphify") is not None

    payload: dict[str, Any] = {
        "status": "PASS" if (cli_installed and index_dir) else "WARN",
        "control": "graphify.status",
        "cli_installed": cli_installed,
        "available": index_dir is not None,
        "indexed": False,
        "fresh": False,
        "last_index_at": None,
        "target_repo": None,
        "findings": [],
    }

    if not cli_installed:
        payload["findings"].append(
            {
                "level": "WARN",
                "code": "graphify_not_installed",
                "message": (
                    "`graphify` CLI not found on PATH. Install the PyPI package "
                    "first (`uv tool install graphifyy` / `pipx install graphifyy` / "
                    "`pip install graphifyy`), then run `graphify .` in the project "
                    "root to build the knowledge graph. Note the PyPI name is "
                    "`graphifyy` (double y); the CLI command stays `graphify`."
                ),
            }
        )

    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            payload["target_repo"] = result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    if not payload["target_repo"]:
        payload["target_repo"] = root.resolve().name

    if index_dir:
        has_content = any(index_dir.iterdir())
        payload["indexed"] = has_content
        if has_content:
            mtime_dt = dt.datetime.fromtimestamp(index_dir.stat().st_mtime, tz=dt.timezone.utc)
            payload["last_index_at"] = mtime_dt.isoformat()
            age_hours = (dt.datetime.now(tz=dt.timezone.utc) - mtime_dt).total_seconds() / 3600
            payload["fresh"] = age_hours < GRAPHIFY_INDEX_FRESH_HOURS
            if not payload["fresh"]:
                payload["status"] = "WARN"
                payload["findings"].append(
                    {
                        "level": "WARN",
                        "code": "graphify_index_stale",
                        "message": (
                            f"Index last touched {int(age_hours)}h ago (threshold "
                            f"{GRAPHIFY_INDEX_FRESH_HOURS}h); run `graphify .` "
                            "or record `graphify_stale` in degradations[]."
                        ),
                    }
                )
        else:
            payload["status"] = "WARN"
            payload["findings"].append(
                {
                    "level": "WARN",
                    "code": "graphify_index_empty",
                    "message": "graphify-out/ exists but is empty; run `graphify .` to populate it.",
                }
            )
    else:
        payload["findings"].append(
            {
                "level": "WARN",
                "code": "graphify_not_indexed",
                "message": (
                    "No graphify-out/ directory found; for brownfield missions record "
                    "`graphify_unavailable` in degradations[] or run `graphify .`."
                ),
            }
        )

    return emit_payload(args, payload)


def cmd_discovery_skip(args: argparse.Namespace) -> int:
    """Record an explicit decision to skip the discovery stage for a mission."""
    reason = (args.reason or "").strip()
    if not reason:
        return emit_payload(
            args,
            fail_payload(
                "discovery.skip",
                "missing_reason",
                "--reason is required; explain why discovery is being skipped for this mission.",
            ),
        )
    root = Path(root_arg(args))
    document, records = load_approvals(root)
    record = {
        "approval_id": next_approval_id(records),
        "mission_id": args.mission,
        "type": "discovery_skip",
        "stage": "discovery",
        "checkpoint": "",
        "status": "approved",
        "decided_at": now_iso(),
        "comment": reason,
    }
    records.append(record)
    path = write_approvals(root, document, records)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "discovery.skip",
            "approval": record,
            "approvals_path": relpath(root, path),
            "findings": [],
        },
    )


def cmd_discovery_check_dependency_trigger(args: argparse.Namespace) -> int:
    """Decide whether discovery Step 6 must trigger the dependency-impact skill."""
    root = Path(root_arg(args))
    contract_path = (
        root / "harness-runtime" / "harness" / "missions" / args.mission / "mission-contract.md"
    )
    if not contract_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "discovery.check-dependency-trigger",
                "missing_mission_contract",
                (
                    f"mission-contract.md not found: {relpath(root, contract_path)}; "
                    "mission must be initialized before discovery scans dependencies."
                ),
            ),
        )

    text = contract_path.read_text(encoding="utf-8")
    text_lower = text.lower()

    reasons: list[dict[str, str]] = []
    matched_signals: set[str] = set()

    for keyword, signal_id in DEPENDENCY_TRIGGER_KEYWORDS:
        if keyword.lower() in text_lower and signal_id not in matched_signals:
            matched_signals.add(signal_id)
            reasons.append(
                {
                    "signal": signal_id,
                    "source": "mission_contract_keyword",
                    "evidence": keyword,
                }
            )

    candidates = [root / "graphify-out", Path.cwd() / "graphify-out"]
    index_dir = next(
        (p for p in candidates if p.exists() and p.is_dir() and any(p.iterdir())),
        None,
    )
    if index_dir is not None and "brownfield" not in matched_signals:
        matched_signals.add("brownfield")
        reasons.append(
            {
                "signal": "brownfield",
                "source": "graphify_index_present",
                "evidence": relpath(root, index_dir),
            }
        )

    required = bool(matched_signals)
    payload = {
        "status": "PASS",
        "control": "discovery.check-dependency-trigger",
        "mission_id": args.mission,
        "required": required,
        "signals": sorted(matched_signals),
        "reasons": reasons,
        "findings": [],
    }
    return emit_payload(args, payload)


def cmd_discovery_agent_eng_eval(args: argparse.Namespace) -> int:
    """Append a typed Agent-engineering decision-matrix evaluation to the
    discovery-brief contract.

    Decision rule: all four booleans true → recommended:agentize; otherwise →
    deterministic. ``agentize`` without 4-of-4 is rejected.
    """
    root = Path(root_arg(args))
    contract_path = (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / args.mission
        / "contracts"
        / "discovery-brief.contract.yaml"
    )
    if not contract_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "discovery.agent-eng-eval",
                "missing_contract",
                (
                    f"discovery-brief contract not found: {relpath(root, contract_path)}; "
                    "run `harness contract fill --template discovery-brief` first."
                ),
            ),
        )
    document = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    contract = (
        document.get("control_contract")
        if isinstance(document.get("control_contract"), dict)
        else None
    )
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "discovery.agent-eng-eval",
                "invalid_contract",
                "discovery-brief contract is missing the `control_contract:` root.",
            ),
        )

    bools = (args.autonomy, args.runtime_context, args.multi_step, args.uncertainty)
    if args.recommendation:
        recommended = args.recommendation
    else:
        recommended = "agentize" if all(bools) else "deterministic"

    if recommended == "agentize" and not all(bools):
        return emit_payload(
            args,
            fail_payload(
                "discovery.agent-eng-eval",
                "agentize_requires_all_four",
                (
                    "--recommendation agentize requires autonomy && runtime_context && "
                    "multi_step && uncertainty all true (M4.3 strict-mode preview)."
                ),
            ),
        )

    candidate: dict[str, Any] = {
        "component": args.component,
        "autonomy": bool(args.autonomy),
        "runtime_context": bool(args.runtime_context),
        "multi_step_reasoning": bool(args.multi_step),
        "uncertainty": bool(args.uncertainty),
        "recommended": recommended,
    }
    if args.notes:
        candidate["notes"] = args.notes

    candidates_list = contract.get("agent_engineering_candidates")
    if not isinstance(candidates_list, list):
        candidates_list = []
    replaced = False
    for i, existing in enumerate(list(candidates_list)):
        if isinstance(existing, dict) and existing.get("component") == args.component:
            candidates_list[i] = candidate
            replaced = True
            break
    if not replaced:
        candidates_list.append(candidate)
    contract["agent_engineering_candidates"] = candidates_list

    contract_path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "discovery.agent-eng-eval",
            "contract_path": relpath(root, contract_path),
            "candidate": candidate,
            "replaced_existing": replaced,
            "findings": [],
        },
    )


def cmd_discovery_summary(args: argparse.Namespace) -> int:
    """Render a standardized summary of a discovery-brief contract."""
    root = Path(root_arg(args))
    contract_path = (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / args.mission
        / "contracts"
        / "discovery-brief.contract.yaml"
    )
    if not contract_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "discovery.summary",
                "missing_contract",
                (
                    f"discovery-brief contract not found: {relpath(root, contract_path)}; "
                    "run `harness contract fill --template discovery-brief` first."
                ),
            ),
        )
    try:
        document = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return emit_payload(
            args,
            fail_payload(
                "discovery.summary",
                "invalid_contract",
                f"discovery-brief contract is not valid YAML: {exc}",
            ),
        )
    contract = (
        document.get("control_contract")
        if isinstance(document.get("control_contract"), dict)
        else {}
    )
    if not contract:
        return emit_payload(
            args,
            fail_payload(
                "discovery.summary",
                "invalid_contract",
                "discovery-brief contract is missing the `control_contract:` root.",
            ),
        )

    def items(key: str) -> list[dict[str, Any]]:
        value = contract.get(key)
        return [it for it in value if isinstance(it, dict)] if isinstance(value, list) else []

    capabilities = items("affected_capabilities")
    roles = items("roles")
    scenarios = items("scenarios")
    existing = items("existing_solutions")
    assumptions = items("design_assumptions")
    candidates = items("agent_engineering_candidates")
    degradations = items("degradations")

    def count_by(items_list: list[dict[str, Any]], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in items_list:
            label = str(item.get(key) or "unspecified")
            counts[label] = counts.get(label, 0) + 1
        return counts

    summary: dict[str, Any] = {
        "mission_id": args.mission,
        "stage": contract.get("stage"),
        "affected_capabilities": {
            "total": len(capabilities),
            "by_confidence": count_by(capabilities, "confidence"),
        },
        "roles": {"total": len(roles)},
        "scenarios": {
            "total": len(scenarios),
            "by_kind": count_by(scenarios, "kind"),
        },
        "existing_solutions": {
            "total": len(existing),
            "by_source": count_by(existing, "source"),
        },
        "design_assumptions": {
            "total": len(assumptions),
            "by_downstream": count_by(assumptions, "impact_on"),
        },
        "agent_engineering_candidates": {
            "total": len(candidates),
            "by_recommendation": count_by(candidates, "recommended"),
        },
        "degradations": {
            "total": len(degradations),
            "by_kind": count_by(degradations, "kind"),
        },
    }

    findings: list[dict[str, str]] = []
    if not capabilities:
        findings.append(
            {
                "level": "WARN",
                "code": "no_affected_capabilities",
                "message": (
                    "discovery-brief.contract.yaml.affected_capabilities is empty; "
                    "downstream PRD has no capability impact baseline."
                ),
            }
        )
    if not roles:
        findings.append(
            {
                "level": "WARN",
                "code": "no_roles",
                "message": "discovery-brief.contract.yaml.roles is empty; user-impact analysis is missing.",
            }
        )
    if not scenarios:
        findings.append(
            {
                "level": "WARN",
                "code": "no_scenarios",
                "message": (
                    "discovery-brief.contract.yaml.scenarios is empty; "
                    "happy_path / exception coverage cannot be audited."
                ),
            }
        )

    payload: dict[str, Any] = {
        "status": "WARN" if findings else "PASS",
        "control": "discovery.summary",
        "contract_path": relpath(root, contract_path),
        "summary": summary,
        "findings": findings,
    }

    if args.format == "user":
        lines = [
            f"# Discovery Brief Summary — {args.mission}",
            "",
            f"- affected_capabilities: {summary['affected_capabilities']['total']} "
            f"({', '.join(f'{k}={v}' for k, v in summary['affected_capabilities']['by_confidence'].items()) or 'none'})",
            f"- roles: {summary['roles']['total']}",
            f"- scenarios: {summary['scenarios']['total']} "
            f"({', '.join(f'{k}={v}' for k, v in summary['scenarios']['by_kind'].items()) or 'none'})",
            f"- existing_solutions: {summary['existing_solutions']['total']} "
            f"({', '.join(f'{k}={v}' for k, v in summary['existing_solutions']['by_source'].items()) or 'none'})",
            f"- design_assumptions: {summary['design_assumptions']['total']}",
            f"- agent_engineering_candidates: {summary['agent_engineering_candidates']['total']} "
            f"({', '.join(f'{k}={v}' for k, v in summary['agent_engineering_candidates']['by_recommendation'].items()) or 'none'})",
            f"- degradations: {summary['degradations']['total']}",
        ]
        if findings:
            lines.append("")
            lines.append("## Gaps")
            for f in findings:
                lines.append(f"- [{f['level']}] {f['code']}: {f['message']}")
        payload["display"] = "\n".join(lines)

    return emit_payload(args, payload)


__all__ = [
    "cmd_graphify_status",
    "cmd_discovery_skip",
    "cmd_discovery_check_dependency_trigger",
    "cmd_discovery_agent_eng_eval",
    "cmd_discovery_summary",
]
