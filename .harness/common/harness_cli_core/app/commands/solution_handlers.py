"""Handlers for `harness solution ...` commands.

design-Stage-4 M2.1 lane CLIs replacing prompt-only HARD-GATEs:

* ``solution decision-scan`` — anti-pattern + vague-mitigation scan.
* ``solution lane-action-validate`` — fail when the current mission slice
  modifies an artifact owned by a different design lane.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

import yaml

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.solution_lint import (
    SOLUTION_ANTI_PATTERN_PHRASES,
    SOLUTION_VAGUE_MITIGATION,
)


def cmd_solution_decision_scan(args: argparse.Namespace) -> int:
    """Anti-pattern + vague-mitigation scan for ``solution.md``.

    Findings are non-empty ⇒ status FAIL. Authors fix by rewriting the
    offending phrasing into a real decision (with tradeoff +
    accepted_alternatives).
    """
    artifact = Path(args.artifact)
    if not artifact.exists():
        return emit_payload(
            args,
            fail_payload(
                "solution.decision-scan",
                "missing_artifact",
                f"Artifact not found: {args.artifact}",
            ),
        )

    text = artifact.read_text(encoding="utf-8")
    findings: list[dict[str, Any]] = []

    # 1. Anti-pattern phrases at any line.
    text_lower = text.lower()
    lines = text.splitlines()
    for phrase, rule, message in SOLUTION_ANTI_PATTERN_PHRASES:
        idx = text_lower.find(phrase.lower())
        if idx == -1:
            continue
        line_no = text[:idx].count("\n") + 1
        findings.append(
            {
                "rule": rule,
                "location": f"line {line_no}",
                "evidence": phrase,
                "message": message,
            }
        )

    # 2. Vague mitigation inside risks: / mitigation: regions.
    in_risks_block = False
    risks_distance = 0
    for line_no, raw in enumerate(lines, 1):
        if raw.strip().startswith("risks:"):
            in_risks_block = True
            risks_distance = 0
            continue
        if in_risks_block:
            risks_distance += 1
            if risks_distance > 30:
                in_risks_block = False
                continue
        if "mitigation:" in raw or in_risks_block:
            for vague in SOLUTION_VAGUE_MITIGATION:
                if vague in raw and not raw.strip().startswith("#"):
                    findings.append(
                        {
                            "rule": "vague_mitigation",
                            "location": f"line {line_no}",
                            "evidence": vague,
                            "message": (
                                f"Vague phrase '{vague}' inside risk mitigation. "
                                "Replace with a concrete action + verification."
                            ),
                        }
                    )
                    break

    payload = {
        "status": "PASS" if not findings else "FAIL",
        "control": "solution.decision-scan",
        "artifact": str(artifact),
        "total_findings": len(findings),
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_solution_lane_action_validate(args: argparse.Namespace) -> int:
    """Lane action 单一性 兜底 — verify that within the current mission slice,
    only the active lane action's artifacts have been modified.

    Inspects ``git status --porcelain`` and the mission-slice file to determine
    the active design stage. Modifications to other-stage artifacts under
    ``harness-runtime/harness/stages/<mission>/`` trigger FAIL with offending
    paths.
    """
    root = Path(root_arg(args))
    mission_id = args.mission
    slice_path = (
        root / "harness-runtime" / "harness" / "missions" / mission_id / "mission-slice.yaml"
    )
    active_stage: str | None = None
    if slice_path.exists():
        try:
            slice_doc = yaml.safe_load(slice_path.read_text(encoding="utf-8")) or {}
            cp = slice_doc.get("control_plane") or {}
            active_stage = cp.get("stage")
        except yaml.YAMLError:
            pass
    active_stage = args.stage or active_stage

    if not active_stage:
        return emit_payload(
            args,
            fail_payload(
                "solution.lane-action-validate",
                "missing_stage",
                "stage not found in mission-slice and not provided via --stage.",
            ),
        )

    if active_stage not in {"solution", "interaction", "technical_analysis"}:
        return emit_payload(
            args,
            fail_payload(
                "solution.lane-action-validate",
                "unknown_stage",
                (
                    f"stage must be one of solution / interaction / technical_analysis; "
                    f"got {active_stage}."
                ),
            ),
        )

    lane_artifacts = {
        "solution": [
            f"harness-runtime/harness/artifacts/{mission_id}/solution/solution.md",
            f"harness-runtime/harness/stages/{mission_id}/solution.md",
        ],
        "interaction": [
            f"harness-runtime/harness/artifacts/{mission_id}/interaction/interaction.md",
            f"harness-runtime/harness/artifacts/{mission_id}/interaction/visual-interaction/",
            f"harness-runtime/harness/stages/{mission_id}/interaction.md",
            f"harness-runtime/harness/stages/{mission_id}/visual-interaction/",
        ],
        "technical_analysis": [
            f"harness-runtime/harness/artifacts/{mission_id}/technical-analysis/tech-design.md",
            f"harness-runtime/harness/stages/{mission_id}/tech-design.md",
        ],
    }
    other_lane_globs = (
        f"harness-runtime/harness/artifacts/{mission_id}/solution/solution.md",
        f"harness-runtime/harness/artifacts/{mission_id}/interaction/interaction.md",
        f"harness-runtime/harness/artifacts/{mission_id}/technical-analysis/tech-design.md",
        f"harness-runtime/harness/artifacts/{mission_id}/interaction/visual-interaction/",
        f"harness-runtime/harness/stages/{mission_id}/solution.md",
        f"harness-runtime/harness/stages/{mission_id}/interaction.md",
        f"harness-runtime/harness/stages/{mission_id}/tech-design.md",
        f"harness-runtime/harness/stages/{mission_id}/visual-interaction/",
    )
    permitted = set(lane_artifacts[active_stage])

    try:
        result = subprocess.run(
            # ``-uall`` expands untracked directories so a fresh write to an
            # other-lane artifact under an untracked stage dir is visible
            # (otherwise git collapses it into ``?? <dir>/``).
            ["git", "status", "--porcelain", "-uall"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return emit_payload(
            args,
            fail_payload(
                "solution.lane-action-validate",
                "git_unavailable",
                "git not on PATH; cannot inspect working tree state.",
            ),
        )

    findings: list[dict[str, Any]] = []
    for raw in result.stdout.splitlines():
        if not raw.strip():
            continue
        path = raw[3:].strip().strip('"')
        if not (
            path.startswith(f"harness-runtime/harness/stages/{mission_id}/")
            or path.startswith(f"harness-runtime/harness/artifacts/{mission_id}/")
        ):
            continue
        is_permitted = any(
            (path == p or (p.endswith("/") and path.startswith(p)))
            for p in permitted
        )
        if is_permitted:
            continue
        is_cross_lane = any(
            (path == g or (g.endswith("/") and path.startswith(g)))
            for g in other_lane_globs
        )
        if is_cross_lane:
            findings.append(
                {
                    "rule": "cross_lane_write",
                    "path": path,
                    "stage": active_stage,
                    "message": (
                        f"In stage={active_stage}, modifications to "
                        f"{path} are forbidden (other-lane artifact)."
                    ),
                }
            )

    payload = {
        "status": "PASS" if not findings else "FAIL",
        "control": "solution.lane-action-validate",
        "mission_id": mission_id,
        "stage": active_stage,
        "total_findings": len(findings),
        "findings": findings,
    }
    return emit_payload(args, payload)


__all__ = [
    "cmd_solution_decision_scan",
    "cmd_solution_lane_action_validate",
]
