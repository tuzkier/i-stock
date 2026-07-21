"""Handlers for `harness review ...` commands (code-review-improvement-plan M2.1).

These commands surface the code-review stage gate checks (readiness, reviewer
selection, diff snapshot, TDD toolchain status, E2E status) as typed JSON
payloads. The contract loader and reviewer-selection logic live in
``harness_cli_core.domain.code_review``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.code_review import select_reviewers
from harness_cli_core.domain.contracts import (
    code_review_contract_path,
    load_code_review_contract,
)
from harness_cli_core.infra.runtime_paths import relpath, runtime_harness_root


def cmd_review_check_ready(args: argparse.Namespace) -> int:
    """Verify code-review.contract.yaml is ready for stage complete:
    pending_reviewer_recheck=false AND no unresolved High findings.
    """
    root = Path(root_arg(args))
    artifact, contract, error_code = load_code_review_contract(root, args.mission)
    if error_code == "code_review_contract_missing":
        return emit_payload(
            args,
            fail_payload(
                "review.check-ready",
                "code_review_contract_missing",
                f"code-review.contract.yaml not found at {relpath(root, artifact)}",
            ),
        )
    if error_code == "code_review_contract_invalid_yaml":
        return emit_payload(
            args,
            fail_payload(
                "review.check-ready",
                "code_review_contract_invalid_yaml",
                f"Failed to parse {artifact}",
            ),
        )
    if error_code == "code_review_contract_invalid_root":
        return emit_payload(
            args,
            fail_payload(
                "review.check-ready",
                "code_review_contract_invalid_root",
                "code-review.contract.yaml root is not an object",
            ),
        )
    if error_code == "code_review_contract_invalid_shape" or contract is None:
        return emit_payload(
            args,
            fail_payload(
                "review.check-ready",
                "code_review_contract_invalid_shape",
                "code-review.contract.yaml control_contract not an object",
            ),
        )

    findings: list[dict] = []
    eff = (
        contract.get("effectiveness_review")
        if isinstance(contract.get("effectiveness_review"), dict)
        else {}
    )
    if eff.get("pending_reviewer_recheck"):
        findings.append(
            {
                "level": "FAIL",
                "code": "pending_reviewer_recheck",
                "message": "effectiveness_review.pending_reviewer_recheck=true; re-run reviewers",
            }
        )
    finding_list = contract.get("findings") if isinstance(contract.get("findings"), list) else []
    open_high = [
        f
        for f in finding_list
        if isinstance(f, dict)
        and (f.get("severity") or "").lower() == "high"
        and (f.get("status") or "open").lower() != "resolved"
    ]
    for f in open_high:
        findings.append(
            {
                "level": "FAIL",
                "code": "unresolved_high_finding",
                "finding_id": f.get("id"),
                "message": f"High-severity finding {f.get('id')!r} is unresolved",
            }
        )
    status = "PASS" if not findings else "FAIL"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "review.check-ready",
            "mission": args.mission,
            "findings": findings,
            "unresolved_high_count": len(open_high),
        },
    )


def cmd_review_select_reviewers(args: argparse.Namespace) -> int:
    """Select reviewers for the current mission's code-review stage.

    Reads an optional --diff-summary JSON file (array of feature keywords).
    Always includes correctness-reviewer and tdd-reviewer; additional reviewers
    are triggered by diff keyword matching.
    """
    features: list[str] = []
    diff_summary = getattr(args, "diff_summary", None)
    if diff_summary:
        try:
            raw = Path(diff_summary).read_text(encoding="utf-8")
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                features = [str(f).lower() for f in parsed]
        except (OSError, json.JSONDecodeError):
            pass

    selected, excluded = select_reviewers(features)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "review.select-reviewers",
            "mission": args.mission,
            "selected": selected,
            "excluded": excluded,
            "findings": [],
        },
    )


def cmd_review_snapshot_diff(args: argparse.Namespace) -> int:
    """Capture a diff snapshot for the current review round.

    Runs `git diff` relative to the base ref (--base defaults to HEAD~1) and
    writes the result to harness-runtime/harness/traces/<mission>/diff-snapshot.patch.
    """
    root = Path(root_arg(args))
    mission = args.mission
    base = getattr(args, "base", "HEAD~1") or "HEAD~1"
    snapshot_dir = runtime_harness_root(root) / "traces" / mission
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / "diff-snapshot.patch"
    try:
        result = subprocess.run(
            ["git", "diff", base],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(root),
        )
        snapshot_path.write_text(result.stdout, encoding="utf-8")
        lines = result.stdout.count("\n")
    except Exception as exc:  # noqa: BLE001 — surface any git invocation failure
        return emit_payload(
            args,
            fail_payload(
                "review.snapshot-diff",
                "snapshot_diff_error",
                f"git diff failed: {exc}",
            ),
        )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "review.snapshot-diff",
            "mission": mission,
            "snapshot_path": relpath(root, snapshot_path),
            "diff_lines": lines,
            "findings": [],
        },
    )


def cmd_review_toolchain_status(args: argparse.Namespace) -> int:
    """Report TDD toolchain gate status.

    Reads harness-runtime/harness/traces/<mission>/tdd/toolchain-status.json.
    Returns BLOCKED when the file is missing (toolchain check not yet run).
    """
    root = Path(root_arg(args))
    mission = args.mission
    status_file = runtime_harness_root(root) / "traces" / mission / "tdd" / "toolchain-status.json"
    if not status_file.exists():
        return emit_payload(
            args,
            {
                "status": "BLOCKED",
                "control": "review.toolchain-status",
                "mission": mission,
                "findings": [
                    {
                        "level": "FAIL",
                        "code": "toolchain_status_missing",
                        "message": (
                            f"toolchain-status.json not found at {relpath(root, status_file)}; "
                            "run `harness review toolchain-status` after tdd stage"
                        ),
                    }
                ],
            },
        )
    try:
        data = json.loads(status_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return emit_payload(
            args,
            fail_payload(
                "review.toolchain-status",
                "toolchain_status_unreadable",
                f"Cannot parse toolchain-status.json: {exc}",
            ),
        )
    ts = data.get("status", "UNKNOWN")
    findings: list[dict] = []
    if ts == "FAIL":
        for cap in data.get("missing_capabilities") or []:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "missing_capability",
                    "message": f"Missing capability: {cap}",
                }
            )
        if not findings:
            findings.append({"level": "FAIL", "code": "toolchain_fail", "message": "Toolchain status FAIL"})
    status = "PASS" if ts in ("PASS", "WARN") else "FAIL" if ts == "FAIL" else "WARN"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "review.toolchain-status",
            "mission": mission,
            "toolchain_status": ts,
            "findings": findings,
        },
    )


def cmd_review_e2e_status(args: argparse.Namespace) -> int:
    """Report E2E control-plane gate status.

    Reads harness-runtime/harness/traces/<mission>/e2e/e2e-status.json.
    Returns BLOCKED when the file is missing.
    """
    root = Path(root_arg(args))
    mission = args.mission
    status_file = runtime_harness_root(root) / "traces" / mission / "e2e" / "e2e-status.json"
    if not status_file.exists():
        return emit_payload(
            args,
            {
                "status": "BLOCKED",
                "control": "review.e2e-status",
                "mission": mission,
                "findings": [
                    {
                        "level": "FAIL",
                        "code": "e2e_status_missing",
                        "message": (
                            f"e2e-status.json not found at {relpath(root, status_file)}; "
                            "run e2e gate before code-review"
                        ),
                    }
                ],
            },
        )
    try:
        data = json.loads(status_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return emit_payload(
            args,
            fail_payload(
                "review.e2e-status",
                "e2e_status_unreadable",
                f"Cannot parse e2e-status.json: {exc}",
            ),
        )
    ts = data.get("status", "UNKNOWN")
    findings: list[dict] = []
    if ts not in ("PASS", "WARN"):
        findings.append({"level": "FAIL", "code": "e2e_fail", "message": f"E2E status: {ts}"})
    status = "PASS" if ts in ("PASS", "WARN") else "FAIL"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "review.e2e-status",
            "mission": mission,
            "e2e_status": ts,
            "findings": findings,
        },
    )


__all__ = [
    "cmd_review_check_ready",
    "cmd_review_select_reviewers",
    "cmd_review_snapshot_diff",
    "cmd_review_toolchain_status",
    "cmd_review_e2e_status",
    "code_review_contract_path",
]
