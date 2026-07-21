"""Handlers for the `harness prd ...` commands.

prd-improvement-plan M2.1 — typed CLI replacements for the prompt-only
HARD-GATE judgments in prd/workflow.md Steps 4 / 7 / 8.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.prd_lint import scan_anti_patterns, scan_domain_model


def cmd_prd_anti_pattern_scan(args: argparse.Namespace) -> int:
    """Scan a PRD artifact for 5 anti-pattern categories (plan Step 4)."""
    artifact = Path(args.artifact)
    if not artifact.exists():
        return emit_payload(
            args,
            fail_payload(
                "prd.anti-pattern-scan",
                "missing_artifact",
                f"Artifact not found: {args.artifact}",
            ),
        )

    text = artifact.read_text(encoding="utf-8")
    findings = scan_anti_patterns(text)

    payload: dict[str, Any] = {
        "status": "PASS" if not findings else "FAIL",
        "control": "prd.anti-pattern-scan",
        "artifact": str(artifact),
        "total_findings": len(findings),
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_prd_domain_model_lint(args: argparse.Namespace) -> int:
    """Validate product-domain-model.md DDD structure, anti-patterns, and traces."""
    artifact = Path(args.artifact)
    if not artifact.exists():
        return emit_payload(
            args,
            fail_payload(
                "prd.domain-model-lint",
                "missing_domain_model",
                f"Domain model artifact not found: {args.artifact}",
            ),
        )

    text = artifact.read_text(encoding="utf-8")

    product_definition_text: str | None = None
    if getattr(args, "product_definition", None):
        product_definition = Path(args.product_definition)
        if not product_definition.exists():
            return emit_payload(
                args,
                fail_payload(
                    "prd.domain-model-lint",
                    "missing_product_definition",
                    f"Product definition artifact not found: {args.product_definition}",
                ),
            )
        product_definition_text = product_definition.read_text(encoding="utf-8")

    contract: dict[str, Any] | None = None
    if getattr(args, "contract", None):
        contract_path = Path(args.contract)
        if not contract_path.exists():
            return emit_payload(
                args,
                fail_payload(
                    "prd.domain-model-lint",
                    "missing_prd_contract",
                    f"PRD contract not found: {args.contract}",
                ),
            )
        try:
            parsed = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
            candidate = parsed.get("control_contract") if isinstance(parsed, dict) else None
            contract = candidate if isinstance(candidate, dict) else {}
        except yaml.YAMLError:
            return emit_payload(
                args,
                fail_payload(
                    "prd.domain-model-lint",
                    "invalid_prd_contract",
                    f"PRD contract is not valid YAML: {args.contract}",
                ),
            )

    findings = scan_domain_model(
        text,
        product_definition_text=product_definition_text,
        contract=contract,
    )
    payload: dict[str, Any] = {
        "status": "PASS" if not findings else "FAIL",
        "control": "prd.domain-model-lint",
        "artifact": str(artifact),
        "product_definition": getattr(args, "product_definition", None),
        "contract": getattr(args, "contract", None),
        "total_findings": len(findings),
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_prd_agent_cap_eval(args: argparse.Namespace) -> int:
    """Typed input for Step 8 Agent Capability Requirements."""
    root = Path(root_arg(args))  # noqa: F841 — kept for future use
    mission = args.mission
    component = args.component

    valid_work_rights = {
        "read_context",
        "decide_action",
        "write_artifact",
        "dispatch_subagent",
        "request_human_input",
        "halt_for_review",
    }
    raw_rights = args.work_rights.split(",") if args.work_rights else []
    invalid = [r for r in raw_rights if r not in valid_work_rights]
    if invalid:
        return emit_payload(
            args,
            fail_payload(
                "prd.agent-cap-eval",
                "invalid_work_rights",
                (
                    f"Invalid work_rights: {', '.join(invalid)}. "
                    f"Valid: {', '.join(sorted(valid_work_rights))}"
                ),
            ),
        )

    if args.priority and args.priority not in ("P0", "P1", "P2"):
        return emit_payload(
            args,
            fail_payload(
                "prd.agent-cap-eval",
                "invalid_priority",
                f"Invalid priority: {args.priority}. Must be P0/P1/P2.",
            ),
        )

    payload: dict[str, Any] = {
        "status": "PASS",
        "control": "prd.agent-cap-eval",
        "mission": mission,
        "component": component,
        "work_rights": raw_rights,
        "priority": args.priority or "P2",
        "findings": [],
    }
    return emit_payload(args, payload)


__all__ = [
    "cmd_prd_anti_pattern_scan",
    "cmd_prd_domain_model_lint",
    "cmd_prd_agent_cap_eval",
]
