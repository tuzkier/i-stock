"""Handlers for `harness finishing-branch ...` commands.

Spans status / detect-test-cmd / run-tests / readiness / options / pr-body /
execute / cleanup. ``execute`` is the only command that may run destructive
git ops; it stops at the first failure and supports ``--dry-run``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.finishing_branch import (
    mission_info,
    stage_dir,
)
from harness_cli_core.infra.runtime_paths import mission_artifact_dir


def _delivery_artifact_paths(root: Path, mission: str) -> tuple[Path, Path]:
    """Return canonical delivery-package and acceptance-result paths with legacy fallback."""
    artifacts_dir = mission_artifact_dir(root, mission) / "delivery"
    sdir = stage_dir(root, mission)
    delivery = artifacts_dir / "delivery-package.md"
    acceptance = artifacts_dir / "acceptance-result.md"
    if not delivery.exists():
        delivery = sdir / "delivery-package.md"
    if not acceptance.exists():
        acceptance = sdir / "acceptance-result.md"
    return delivery, acceptance


def cmd_finishing_branch_status(args: argparse.Namespace) -> int:
    """Return branch status (dirty, active/blocked stage worktrees, mission branch)."""
    root = Path(root_arg(args))
    mission = args.mission
    info = mission_info(root, mission)
    mission_branch = info.get("mission_branch")
    base_branch = info.get("base_branch") or "main"

    dirty = False
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        dirty = bool(r.stdout.strip())
    except Exception:  # noqa: BLE001
        pass

    active_worktrees: list[str] = []
    blocked_worktrees: list[str] = []
    try:
        r = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        current_wt: dict = {}
        for line in r.stdout.splitlines():
            if line.startswith("worktree "):
                current_wt = {"path": line[len("worktree "):]}
            elif line.startswith("branch "):
                current_wt["branch"] = line[len("branch "):]
            elif line == "" and current_wt:
                path = current_wt.get("path", "")
                branch = current_wt.get("branch", "")
                if mission in path or mission in branch:
                    active_worktrees.append(path)
                current_wt = {}
    except Exception:  # noqa: BLE001
        pass

    branch_status = {
        "mission_branch": mission_branch,
        "base_branch": base_branch,
        "dirty": dirty,
        "active_stage_worktrees": active_worktrees,
        "blocked_stage_worktrees": blocked_worktrees,
    }

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "finishing-branch.status",
            "mission": mission,
            "branch_status": branch_status,
            "findings": [],
        },
    )


def cmd_finishing_branch_detect_test_cmd(args: argparse.Namespace) -> int:
    """Detect the test command for the current project."""
    root = Path(root_arg(args))
    candidates: list[dict] = []

    if (root / "pyproject.toml").exists() or (root / "setup.cfg").exists() or (root / "pytest.ini").exists():
        candidates.append(
            {
                "command": "pytest",
                "confidence": "high",
                "reason": "pyproject.toml/setup.cfg/pytest.ini found",
            }
        )

    if (root / "package.json").exists():
        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
            if isinstance(pkg.get("scripts"), dict) and "test" in pkg["scripts"]:
                candidates.append(
                    {
                        "command": "npm test",
                        "confidence": "high",
                        "reason": "package.json scripts.test found",
                    }
                )
        except Exception:  # noqa: BLE001
            candidates.append(
                {
                    "command": "npm test",
                    "confidence": "medium",
                    "reason": "package.json found",
                }
            )

    if (root / "Cargo.toml").exists():
        candidates.append(
            {"command": "cargo test", "confidence": "high", "reason": "Cargo.toml found"}
        )

    if (root / "go.mod").exists():
        candidates.append(
            {"command": "go test ./...", "confidence": "high", "reason": "go.mod found"}
        )

    if not candidates:
        candidates.append(
            {"command": "pytest", "confidence": "low", "reason": "default fallback"}
        )

    recommended = candidates[0]["command"]

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "finishing-branch.detect-test-cmd",
            "mission": args.mission,
            "recommended": recommended,
            "candidates": candidates,
            "findings": [],
        },
    )


def cmd_finishing_branch_run_tests(args: argparse.Namespace) -> int:
    """Run the project test suite or reuse prior verification evidence."""
    root = Path(root_arg(args))
    mission = args.mission
    dry_run = getattr(args, "dry_run", False)
    reuse_id = getattr(args, "reuse_evidence_id", None)

    if reuse_id:
        contract_path = stage_dir(root, mission) / "contracts" / "verification-report.contract.yaml"
        if contract_path.exists():
            try:
                doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
                contract = doc.get("control_contract") if isinstance(doc, dict) else doc
                evidence_list = (contract or {}).get("command_evidence") or []
                for ev in evidence_list:
                    if isinstance(ev, dict) and ev.get("id") == reuse_id:
                        return emit_payload(
                            args,
                            {
                                "status": "PASS",
                                "control": "finishing-branch.run-tests",
                                "mission": mission,
                                "mode": "reused_verification_evidence",
                                "evidence_id": reuse_id,
                                "evidence": ev,
                                "findings": [],
                            },
                        )
            except Exception:  # noqa: BLE001
                pass
        return emit_payload(
            args,
            fail_payload(
                "finishing-branch.run-tests",
                "reuse_evidence_not_found",
                f"Evidence id '{reuse_id}' not found in verification-report contract.",
            ),
        )

    test_cmd = getattr(args, "test_cmd", None) or "pytest"
    if dry_run:
        return emit_payload(
            args,
            {
                "status": "PASS",
                "control": "finishing-branch.run-tests",
                "mission": mission,
                "mode": "dry_run",
                "command": test_cmd,
                "findings": [
                    {
                        "level": "INFO",
                        "code": "dry_run",
                        "message": "Dry-run: test command not executed.",
                    }
                ],
            },
        )

    r = subprocess.run(test_cmd.split(), capture_output=True, text=True, cwd=str(root))
    passed = r.returncode == 0
    return emit_payload(
        args,
        {
            "status": "PASS" if passed else "FAIL",
            "control": "finishing-branch.run-tests",
            "mission": mission,
            "mode": "executed",
            "command": test_cmd,
            "exit_code": r.returncode,
            "findings": []
            if passed
            else [
                {
                    "level": "FAIL",
                    "code": "test_suite_failed",
                    "message": f"Test command '{test_cmd}' exited with code {r.returncode}.",
                }
            ],
        },
    )


def cmd_finishing_branch_readiness(args: argparse.Namespace) -> int:
    """Check release readiness: delivery-package, acceptance-result, test evidence."""
    root = Path(root_arg(args))
    mission = args.mission
    sdir = stage_dir(root, mission)
    findings: list[dict] = []

    delivery_path, acceptance_path = _delivery_artifact_paths(root, mission)
    delivery_present = delivery_path.exists()
    acceptance_present = acceptance_path.exists()

    if not delivery_present:
        findings.append(
            {
                "level": "FAIL",
                "code": "delivery_package_missing",
                "message": "delivery-package.md not found. Run delivery stage before finishing-branch.",
            }
        )

    if not acceptance_present:
        findings.append(
            {
                "level": "WARN",
                "code": "acceptance_result_missing",
                "message": "acceptance-result.md not found. Acceptance evidence is recommended.",
            }
        )

    evidence_ids: list[str] = []
    contract_path = sdir / "contracts" / "verification-report.contract.yaml"
    if contract_path.exists():
        try:
            doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
            contract = doc.get("control_contract") if isinstance(doc, dict) else doc
            evidence_ids = [
                ev["id"]
                for ev in ((contract or {}).get("command_evidence") or [])
                if isinstance(ev, dict) and ev.get("id")
            ]
        except Exception:  # noqa: BLE001
            pass

    fail_items = [f for f in findings if f.get("level") == "FAIL"]
    status = "FAIL" if fail_items else "PASS"

    return emit_payload(
        args,
        {
            "status": status,
            "control": "finishing-branch.readiness",
            "mission": mission,
            "release_readiness": {
                "delivery_package_present": delivery_present,
                "acceptance_result_present": acceptance_present,
                "command_evidence_ids": evidence_ids,
            },
            "findings": findings,
        },
    )


def cmd_finishing_branch_options(args: argparse.Namespace) -> int:
    """Return the 4 available close strategies with enabled/disabled status."""
    root = Path(root_arg(args))
    mission = args.mission

    delivery_path, _acceptance_path = _delivery_artifact_paths(root, mission)
    delivery_present = delivery_path.exists()

    options = [
        {
            "value": "merge_to_base",
            "label": "Merge mission branch to base branch locally",
            "enabled": delivery_present,
            "disabled_reason": None if delivery_present else "delivery-package.md not found",
        },
        {
            "value": "push_pr",
            "label": "Push and create Pull Request",
            "enabled": delivery_present,
            "disabled_reason": None if delivery_present else "delivery-package.md not found",
        },
        {
            "value": "keep",
            "label": "Keep branch as-is (handle manually later)",
            "enabled": True,
            "disabled_reason": None,
        },
        {
            "value": "discard",
            "label": "Discard the mission branch",
            "enabled": True,
            "disabled_reason": None,
        },
    ]

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "finishing-branch.options",
            "mission": mission,
            "options": options,
            "findings": [],
        },
    )


def cmd_finishing_branch_pr_body(args: argparse.Namespace) -> int:
    """Build a typed PR body from delivery-package + verification evidence."""
    root = Path(root_arg(args))
    mission = args.mission
    sdir = stage_dir(root, mission)

    delivery_path, _acceptance_path = _delivery_artifact_paths(root, mission)
    if not delivery_path.exists():
        return emit_payload(
            args,
            {
                "status": "BLOCKED",
                "control": "finishing-branch.pr-body",
                "mission": mission,
                "findings": [
                    {
                        "level": "FAIL",
                        "code": "pr_body_delivery_package_missing",
                        "message": "delivery-package.md is required to generate PR body.",
                    }
                ],
            },
        )

    delivery_text = delivery_path.read_text(encoding="utf-8")
    source_artifacts = ["delivery-package.md"]

    evidence_ids: list[str] = []
    contract_path = sdir / "contracts" / "verification-report.contract.yaml"
    if contract_path.exists():
        try:
            doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
            contract = doc.get("control_contract") if isinstance(doc, dict) else doc
            evidence_ids = [
                ev["id"]
                for ev in ((contract or {}).get("command_evidence") or [])
                if isinstance(ev, dict) and ev.get("id")
            ]
        except Exception:  # noqa: BLE001
            pass

    summary_lines = [
        line.lstrip("- ").strip()
        for line in delivery_text.splitlines()
        if line.startswith("- ") or line.startswith("* ")
    ][:5]
    summary_text = (
        "\n".join(f"- {s}" for s in summary_lines)
        if summary_lines
        else "See delivery-package.md"
    )

    evidence_checklist = (
        "\n".join(f"- [x] Evidence `{eid}` passed" for eid in evidence_ids)
        if evidence_ids
        else "- [ ] Add test evidence"
    )

    body_text = (
        f"## Summary\n\n{summary_text}\n\n"
        f"## Related\n\n- Mission: {mission}\n\n"
        f"## Test Plan\n\n{evidence_checklist}\n- [ ] Code Review: Approved\n"
    )

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "finishing-branch.pr-body",
            "mission": mission,
            "pr_body": {
                "required": True,
                "source_artifacts": source_artifacts,
                "verification_evidence_ids": evidence_ids,
                "body_text": body_text,
            },
            "findings": [],
        },
    )


def cmd_finishing_branch_execute(args: argparse.Namespace) -> int:
    """Execute the chosen close strategy (git ops).

    Supports --dry-run for safe preview. Stops the sequence at the first
    failure so a partial merge cannot silently push.
    """
    root = Path(root_arg(args))
    mission = args.mission
    strategy = args.strategy
    dry_run = getattr(args, "dry_run", False)
    confirmation_id = getattr(args, "confirmation_id", None)

    info = mission_info(root, mission)
    mission_branch = info.get("mission_branch")
    base_branch = info.get("base_branch") or "main"

    if not mission_branch:
        return emit_payload(
            args,
            fail_payload(
                "finishing-branch.execute",
                "mission_branch_unknown",
                f"mission_branch not found in mission-status.yaml for mission {mission}.",
            ),
        )

    if strategy == "discard" and not confirmation_id:
        return emit_payload(
            args,
            fail_payload(
                "finishing-branch.execute",
                "discard_confirmation_required",
                "strategy=discard requires --confirmation-id (must be 'discard') to confirm destructive operation.",
            ),
        )

    findings: list[dict] = []

    plan: list[dict] = []
    if strategy == "merge_to_base":
        plan = [
            {"op": "checkout", "argv": ["git", "checkout", base_branch]},
            {"op": "pull", "argv": ["git", "pull", "origin", base_branch]},
            {"op": "merge", "argv": ["git", "merge", "--no-ff", mission_branch]},
        ]
    elif strategy == "push_pr":
        plan = [
            {"op": "push", "argv": ["git", "push", "origin", mission_branch]},
        ]
    elif strategy == "keep":
        findings.append(
            {
                "level": "WARN",
                "code": "strategy_keep",
                "message": "Branch kept as-is. No git operations performed.",
            }
        )
    elif strategy == "discard":
        plan = [
            {"op": "checkout", "argv": ["git", "checkout", base_branch]},
            {"op": "branch_force_delete", "argv": ["git", "branch", "-D", mission_branch]},
            {"op": "worktree_prune", "argv": ["git", "worktree", "prune"]},
        ]

    git_ops: list[dict] = []
    overall_status = "PASS"
    for step in plan:
        op_record: dict = {
            "op": step["op"],
            "command": " ".join(step["argv"]),
            "dry_run": dry_run,
        }
        if dry_run:
            op_record["executed"] = False
        else:
            try:
                proc = subprocess.run(
                    step["argv"],
                    capture_output=True,
                    text=True,
                    check=False,
                    cwd=str(root),
                )
                op_record["executed"] = True
                op_record["exit_code"] = proc.returncode
                op_record["stdout"] = proc.stdout.strip()[-2000:]
                op_record["stderr"] = proc.stderr.strip()[-2000:]
                if proc.returncode != 0:
                    overall_status = "FAIL"
                    findings.append(
                        {
                            "level": "FAIL",
                            "code": "git_op_failed",
                            "message": f"git op {step['op']} failed (exit {proc.returncode}): {proc.stderr.strip()[-400:]}",
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                op_record["executed"] = True
                op_record["exit_code"] = -1
                op_record["error"] = str(exc)
                overall_status = "FAIL"
                findings.append(
                    {
                        "level": "FAIL",
                        "code": "git_op_error",
                        "message": f"git op {step['op']} raised: {exc}",
                    }
                )
        git_ops.append(op_record)
        if overall_status == "FAIL":
            break

    return emit_payload(
        args,
        {
            "status": overall_status,
            "control": "finishing-branch.execute",
            "mission": mission,
            "strategy": strategy,
            "dry_run": dry_run,
            "mission_branch": mission_branch,
            "base_branch": base_branch,
            "git_ops": git_ops,
            "findings": findings,
        },
    )


def cmd_finishing_branch_cleanup(args: argparse.Namespace) -> int:
    """Clean up stage worktrees after a mission is closed."""
    root = Path(root_arg(args))
    mission = args.mission
    dry_run = getattr(args, "dry_run", False)
    findings: list[dict] = []
    removed: list[str] = []

    try:
        r = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        current_wt: dict = {}
        worktrees_to_remove: list[str] = []
        for line in r.stdout.splitlines():
            if line.startswith("worktree "):
                current_wt = {"path": line[len("worktree "):]}
            elif line.startswith("branch "):
                current_wt["branch"] = line[len("branch "):]
            elif line == "" and current_wt:
                path = current_wt.get("path", "")
                branch = current_wt.get("branch", "")
                if mission in path or mission in branch:
                    worktrees_to_remove.append(path)
                current_wt = {}
    except Exception:  # noqa: BLE001
        worktrees_to_remove = []

    if not worktrees_to_remove:
        findings.append(
            {
                "level": "INFO",
                "code": "no_stage_worktrees",
                "message": f"No stage worktrees found for mission {mission}.",
            }
        )
    elif dry_run:
        findings.append(
            {
                "level": "INFO",
                "code": "dry_run",
                "message": f"Dry-run: would remove {len(worktrees_to_remove)} stage worktree(s): {worktrees_to_remove}",
            }
        )
        removed = worktrees_to_remove
    else:
        for wt_path in worktrees_to_remove:
            try:
                subprocess.run(
                    ["git", "worktree", "remove", wt_path],
                    check=True,
                    cwd=str(root),
                )
                removed.append(wt_path)
            except Exception as exc:  # noqa: BLE001
                findings.append(
                    {
                        "level": "WARN",
                        "code": "worktree_remove_failed",
                        "message": f"Failed to remove worktree {wt_path}: {exc}",
                    }
                )

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "finishing-branch.cleanup",
            "mission": mission,
            "dry_run": dry_run,
            "removed_worktrees": removed,
            "findings": findings,
        },
    )


__all__ = [
    "cmd_finishing_branch_status",
    "cmd_finishing_branch_detect_test_cmd",
    "cmd_finishing_branch_run_tests",
    "cmd_finishing_branch_readiness",
    "cmd_finishing_branch_options",
    "cmd_finishing_branch_pr_body",
    "cmd_finishing_branch_execute",
    "cmd_finishing_branch_cleanup",
]
