"""Handlers for `harness tech-design ...` commands.

Stage-4 technical_analysis M2.1 — typed CLI outputs that replace prompt-only
prerequisite judgments before tech-design Steps 2 and 4.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.interaction import DEP_IMPACT_TRIGGER_KEYWORDS


def cmd_tech_design_check_dep_impact_trigger(args: argparse.Namespace) -> int:
    """Auto-detect whether tech-design Step 1 must dispatch the
    dependency-impact skill before Step 2.
    """
    root = Path(root_arg(args))
    mission_id = args.mission
    candidates: list[Path] = []
    mc = (
        root / "harness-runtime" / "harness" / "missions" / mission_id / "mission-contract.md"
    )
    if mc.exists():
        candidates.append(mc)
    for product_name in (
        "product-definition.md",
        "product-domain-model.md",
        "product-evidence.md",
    ):
        product_path = (
            root
            / "harness-runtime"
            / "harness"
            / "stages"
            / mission_id
            / "product"
            / product_name
        )
        if product_path.exists():
            candidates.append(product_path)
    sol = root / "harness-runtime" / "harness" / "stages" / mission_id / "solution.md"
    if sol.exists():
        candidates.append(sol)

    if not candidates:
        return emit_payload(
            args,
            fail_payload(
                "tech-design.check-dep-impact-trigger",
                "missing_upstream",
                f"No mission-contract / product definition / solution found under mission {mission_id}.",
            ),
        )

    matched_signals: set[str] = set()
    reasons: list[dict[str, str]] = []
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        text_lower = text.lower()
        for phrase, signal in DEP_IMPACT_TRIGGER_KEYWORDS:
            if phrase.lower() in text_lower and signal not in matched_signals:
                matched_signals.add(signal)
                reasons.append(
                    {
                        "signal": signal,
                        "source": path.name,
                        "evidence": phrase,
                    }
                )

    required = bool(matched_signals)
    payload = {
        "status": "PASS",
        "control": "tech-design.check-dep-impact-trigger",
        "mission_id": mission_id,
        "required": required,
        "signals": sorted(matched_signals),
        "reasons": reasons,
        "findings": [],
    }
    return emit_payload(args, payload)


def cmd_tech_design_check_capability_trigger(args: argparse.Namespace) -> int:
    """Auto-detect whether tech-design Step 4 must dispatch the
    agent-capability-designer for the ``## Agent 实现`` section.
    """
    root = Path(root_arg(args))
    mission_id = args.mission
    matched_signals: set[str] = set()
    reasons: list[dict[str, str]] = []

    mc = (
        root / "harness-runtime" / "harness" / "missions" / mission_id / "mission-contract.md"
    )
    if mc.exists():
        text = mc.read_text(encoding="utf-8")
        if "## Agent Engineering" in text or "## Agent 工程" in text:
            matched_signals.add("agent_engineering_section")
            reasons.append(
                {
                    "signal": "agent_engineering_section",
                    "source": "mission-contract.md",
                    "evidence": "## Agent Engineering",
                }
            )

    prd_contract = (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "contracts"
        / "prd.contract.yaml"
    )
    if prd_contract.exists():
        try:
            doc = yaml.safe_load(prd_contract.read_text(encoding="utf-8")) or {}
            cc = doc.get("control_contract") or {}
            acr = cc.get("agent_capability_requirements") or []
            if acr:
                matched_signals.add("agent_capability_requirements")
                reasons.append(
                    {
                        "signal": "agent_capability_requirements",
                        "source": "prd.contract.yaml",
                        "evidence": f"{len(acr)} requirement(s)",
                    }
                )
        except yaml.YAMLError:
            pass

    required = bool(matched_signals)
    payload = {
        "status": "PASS",
        "control": "tech-design.check-capability-trigger",
        "mission_id": mission_id,
        "required": required,
        "signals": sorted(matched_signals),
        "reasons": reasons,
        "findings": [],
    }
    return emit_payload(args, payload)


__all__ = [
    "cmd_tech_design_check_dep_impact_trigger",
    "cmd_tech_design_check_capability_trigger",
]
