"""Handler for `harness alignment check`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from harness_cli_core.app.output import emit_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.findings import apply_compat_warning, finding
from harness_cli_core.domain.interaction import (
    DOMAIN_REF_RE,
    TRACE_REF_RE,
    alignment_current_payload,
    collect_known_upstream_refs,
    collect_refs_from_value,
    interaction_prd_feedback_required,
    known_domain_refs,
)
from harness_cli_core.infra.runtime_paths import relpath


# Per-stage prefixes that the stage itself is allowed to introduce (so the
# alignment scan doesn't punish a stage for defining new ids it owns).
_SELF_PREFIXES_BY_STAGE: dict[str, tuple[str, ...]] = {
    "interaction": (
        "SURF-",
        "PS-",
        "UIC-",
        "FLOW-",
        "STATE-",
        "INT-",
        "VAL-",
        "E2E-",
        "SCN-",
        "DEC-",
        "CHG-",
        "CONS-",
        "SCREEN-",
        "NAV-",
        "KPC-",
    ),
    "solution": ("DEC-",),
    "technical_analysis": (
        "MOD-",
        "IF-",
        "INT-",
        "DATA-",
        "VS-",
        "DEC-",
        "PR-",
        "AFF-",
        "OPEN-TA-",
        "T-EXEC-",
        "SPIKE-",
    ),
    "breakdown": (
        "TASK-",
        "T-",
        "AT-",
        "PT-",
        "DEC-NEED-",
        "E2E-REPLAY-",
        "QOS-PERF-BASELINE",
        "OPEN-TA-",
        "T-EXEC-",
        "SPIKE-",
        "EV-AGT",
        "RULE-",
        "EX-",
        "Q-",
        "re-PT-",
        "RV-",
        "OBL-",
    ),
    "verify": ("E2E-",),
}


def cmd_alignment_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    stage = args.stage
    findings: list[dict[str, object]] = []

    known_upstream = collect_known_upstream_refs(root, mission, stage)
    _, current_payload, current_path = alignment_current_payload(root, mission, stage)
    current_refs = collect_refs_from_value(current_payload, TRACE_REF_RE)
    current_domain_refs = collect_refs_from_value(current_payload, DOMAIN_REF_RE)
    known_domain = known_domain_refs(root, mission)

    if not current_refs:
        findings.append(
            finding(
                "FAIL",
                "MISSING_ALIGNMENT_EVIDENCE",
                f"{stage} artifact must include explicit trace refs to upstream PRD/domain/interaction/solution artifacts.",
                path=relpath(root, current_path) if current_path else None,
            )
        )

    if known_domain:
        for ref in sorted(current_domain_refs - known_domain):
            findings.append(
                finding(
                    "FAIL",
                    "UNKNOWN_DOMAIN_REF",
                    f"{stage} references unknown domain id {ref}.",
                    ref=ref,
                    path=relpath(root, current_path) if current_path else None,
                )
            )

    self_refs = {
        ref
        for ref in current_refs
        if ref.startswith(_SELF_PREFIXES_BY_STAGE.get(stage, ()))
    }
    for ref in sorted(current_refs - known_upstream - self_refs):
        findings.append(
            finding(
                "FAIL",
                "BROKEN_UPSTREAM_TRACE",
                f"{stage} trace ref {ref} is not present in known upstream artifacts.",
                ref=ref,
                path=relpath(root, current_path) if current_path else None,
            )
        )

    text_blob = json.dumps(current_payload, ensure_ascii=False)
    if "{{" in text_blob:
        findings.append(
            finding(
                "FAIL",
                "MISSING_ALIGNMENT_EVIDENCE",
                f"{stage} trace/alignment fields still contain placeholders.",
                path=relpath(root, current_path) if current_path else None,
            )
        )

    if stage == "interaction" and interaction_prd_feedback_required(root, mission):
        findings.append(
            finding(
                "FAIL",
                "PRD_FEEDBACK_REQUIRED",
                "Interaction changed scenario/domain/permission/scope and must return to PRD or Decision Gate.",
            )
        )

    status, failed_checks = apply_compat_warning(args, findings)
    return emit_payload(
        args,
        {
            "status": status,
            "control": "alignment.check",
            "mission_id": mission,
            "stage": stage,
            "known_upstream_refs_count": len(known_upstream),
            "current_refs": sorted(current_refs),
            "findings": findings,
            "failed_checks": failed_checks,
        },
    )


__all__ = ["cmd_alignment_check"]
