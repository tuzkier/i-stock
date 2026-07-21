from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.breakdown import delta_spec_files, find_delta_spec, resolve_execution_brief_contract
from harness_cli_core.domain.knowledge import behavior_specs_root, behavior_specs_template_root
from harness_cli_core.domain.prd_lint import PRD_IMPL_LEAK_PATTERNS
from harness_cli_core.infra.runtime_paths import relpath


def cmd_spec_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    specs_root = behavior_specs_root(root)
    index = specs_root / "_index.md"
    findings: list[dict[str, object]] = []
    if not index.exists():
        findings.append({"level": "FAIL", "code": "project_knowledge_specs_index_missing", "message": f"{relpath(root, index)} not found; run 'harness spec init' to scaffold"})
    capability = args.capability
    if capability:
        capability_spec = specs_root / capability / "spec.md"
        if not capability_spec.exists():
            findings.append({"level": "FAIL", "code": "capability_spec_missing", "message": f"{relpath(root, capability_spec)} not found; run 'harness spec init --capability {capability}' to scaffold"})
    payload = {
        "status": "PASS" if not findings else "FAIL",
        "control": "spec.check",
        "spec_root": relpath(root, specs_root),
        "index_exists": index.exists(),
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_spec_init(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    specs_root = behavior_specs_root(root)
    template_root = behavior_specs_template_root()
    created: list[str] = []
    if args.capability:
        capability_dir = specs_root / args.capability
        capability_spec = capability_dir / "spec.md"
        if capability_spec.exists() and not args.replace:
            return emit_payload(args, fail_payload("spec.init", "capability_spec_exists", f"capability spec already exists: {relpath(root, capability_spec)}; pass --replace to overwrite"))
        capability_dir.mkdir(parents=True, exist_ok=True)
        capability_spec.write_text(
            f"# {args.capability} Specification\n\n"
            "## Purpose\n<一句话说明该 capability 的职责边界（仅描述外部可观测行为）>\n\n"
            "## Requirements\n\n"
            "### Requirement: <需求名称>\n"
            "系统 SHALL <外部可观测的行为>。\n\n"
            "#### Scenario: <场景名称>\n"
            "GIVEN <前置条件>\n"
            "WHEN <触发动作>\n"
            "THEN <可观测结果>\n",
            encoding="utf-8",
        )
        created.append(relpath(root, capability_spec))
        return emit_payload(args, {"status": "PASS", "control": "spec.init", "spec_root": relpath(root, specs_root), "created": created, "findings": []})
    index = specs_root / "_index.md"
    template_index = template_root / "_index.md"
    if index.exists() and not args.replace:
        return emit_payload(args, fail_payload("spec.init", "project_knowledge_specs_exists", f"behavior specs already initialized at {relpath(root, specs_root)}; pass --replace to overwrite, or use --capability <name> to scaffold a new capability"))
    if not template_index.exists():
        return emit_payload(args, fail_payload("spec.init", "missing_project_knowledge_specs_template", "project-knowledge specs template not found in package"))
    specs_root.mkdir(parents=True, exist_ok=True)
    if not index.exists() or args.replace:
        index.write_text(template_index.read_text(encoding="utf-8"), encoding="utf-8")
        created.append(relpath(root, index))
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "spec.init",
            "spec_root": relpath(root, specs_root),
            "created": created,
            "next_step": "spec.enabled is true by default; scaffold capability specs with `harness spec init --capability <name>` as needed.",
            "findings": [],
        },
    )


# ---------------------------------------------------------------------------
# spec delta-lint / scan / diff-list (prd / discovery flavored)
# ---------------------------------------------------------------------------


def cmd_spec_delta_lint(args: argparse.Namespace) -> int:
    """Validate delta spec structure: heading levels + anti-patterns."""
    root = Path(root_arg(args))
    mission = args.mission
    capability = args.capability

    spec_path = find_delta_spec(root, mission, capability)
    if spec_path is None:
        expected = root / "harness-runtime" / "harness" / "artifacts" / mission / "product" / "specs" / capability / "spec.md"
        return emit_payload(
            args,
            fail_payload("spec.delta-lint", "missing_spec", f"Delta spec not found: {expected}"),
        )

    text = spec_path.read_text(encoding="utf-8")
    findings: list[dict[str, Any]] = []

    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("### Scenario") and not stripped.startswith("#### Scenario"):
            findings.append(
                {
                    "rule": "scenario_heading_level",
                    "location": f"line {i}",
                    "evidence": stripped[:60],
                    "message": "Scenario heading must be #### (4 hashes), not ###.",
                }
            )

    for pattern in PRD_IMPL_LEAK_PATTERNS:
        for m in re.finditer(pattern, text):
            findings.append(
                {
                    "rule": "implementation_leak_in_spec",
                    "location": f"line {text[: m.start()].count(chr(10)) + 1}",
                    "evidence": m.group(0),
                    "message": (
                        f"Implementation detail '{m.group(0)}' leaked into spec. "
                        "Write only externally observable behavior."
                    ),
                }
            )

    payload: dict[str, Any] = {
        "status": "PASS" if not findings else "FAIL",
        "control": "spec.delta-lint",
        "mission": mission,
        "capability": capability,
        "spec_path": relpath(root, spec_path),
        "total_findings": len(findings),
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_spec_scan_from_prd(args: argparse.Namespace) -> int:
    """Infer affected capabilities from PRD trace anchors when discovery is skipped."""
    root = Path(root_arg(args))
    mission = args.mission
    prd_path = (
        Path(args.from_prd)
        if args.from_prd
        else root / "harness-runtime" / "harness" / "artifacts" / mission / "product" / "product-definition.md"
    )
    if not prd_path.exists() and not args.from_prd:
        legacy_prd_path = root / "harness-runtime" / "harness" / "stages" / mission / "product" / "product-definition.md"
        if legacy_prd_path.exists():
            prd_path = legacy_prd_path

    if not prd_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "spec.scan",
                "missing_product_definition",
                f"Product definition artifact not found: {prd_path}",
            ),
        )

    text = prd_path.read_text(encoding="utf-8")

    requirement_ids = sorted(set(re.findall(r"\b(?:REQ|SCN|US|UC|RULE)-[A-Za-z0-9-]+\b", text)))

    spec_index = behavior_specs_root(root) / "_index.md"
    existing_capabilities: list[str] = []
    if spec_index.exists():
        idx_text = spec_index.read_text(encoding="utf-8")
        existing_capabilities = re.findall(r"^-\s+(\S+)", idx_text, re.MULTILINE)

    payload: dict[str, Any] = {
        "status": "PASS",
        "control": "spec.scan",
        "mission": mission,
        "source": "prd",
        "extracted_requirement_ids": requirement_ids,
        "extracted_fr_ids": [],
        "extracted_nfr_ids": [],
        "existing_capabilities": existing_capabilities,
        "findings": [],
    }
    return emit_payload(args, payload)


def cmd_spec_scan_capabilities(args: argparse.Namespace) -> int:
    """Discovery-flavor: enumerate capabilities under project-knowledge/specs/
    and tag each with a heuristic confidence vs the mission scope_in paths.
    """
    root = Path(root_arg(args))
    specs_dir = behavior_specs_root(root)
    if not specs_dir.exists() or not specs_dir.is_dir():
        return emit_payload(
            args,
            fail_payload(
                "spec.scan",
                "specs_dir_missing",
                f"{relpath(root, specs_dir)} not found; run `harness spec init` first.",
            ),
        )

    scope_in: list[str] = list(getattr(args, "scope_in", None) or [])
    scope_in_lower = [s.lower() for s in scope_in]

    capabilities: list[dict[str, Any]] = []
    for entry in sorted(specs_dir.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        spec_md = entry / "spec.md"
        record: dict[str, Any] = {
            "capability": name,
            "spec_path": relpath(root, spec_md) if spec_md.exists() else None,
            "confidence": "ASSUMED",
            "matched_scope": [],
        }
        if scope_in_lower:
            name_lower = name.lower()
            for raw, lower in zip(scope_in, scope_in_lower):
                if name_lower in lower:
                    record["matched_scope"].append(raw)
            if record["matched_scope"]:
                record["confidence"] = "CONFIRMED"
        capabilities.append(record)

    findings: list[dict[str, str]] = []
    if not capabilities:
        findings.append(
            {
                "level": "WARN",
                "code": "no_capabilities",
                "message": (
                    f"{relpath(root, specs_dir)} is empty; if the mission is greenfield this is "
                    "expected, otherwise scaffold capabilities with `harness spec init "
                    "--capability <name>`."
                ),
            }
        )

    payload = {
        "status": "PASS" if not findings else "WARN",
        "control": "spec.scan",
        "mode": "discovery",
        "mission_id": args.mission,
        "spec_root": relpath(root, specs_dir),
        "scope_in": scope_in,
        "capabilities": capabilities,
        "summary": {
            "total": len(capabilities),
            "confirmed": sum(1 for c in capabilities if c["confidence"] == "CONFIRMED"),
            "uncertain": sum(1 for c in capabilities if c["confidence"] == "UNCERTAIN"),
            "assumed": sum(1 for c in capabilities if c["confidence"] == "ASSUMED"),
        },
        "findings": findings,
    }
    return emit_payload(args, payload)


def cmd_spec_scan(args: argparse.Namespace) -> int:
    """Dispatch `harness spec scan` to the discovery or PRD flavor.

    ``--scope-in`` triggers the discovery flavor; without it we fall back to
    the PRD flavor that extracts requirement / scenario anchors from the
    product definition.
    """
    if getattr(args, "scope_in", None):
        return cmd_spec_scan_capabilities(args)
    return cmd_spec_scan_from_prd(args)


def cmd_spec_diff_list(args: argparse.Namespace) -> int:
    """Enumerate mission delta specs under the artifact-store spec roots
    and report each Scenario's coverage state vs ``tasks[].traces_to``.
    """
    root = Path(root_arg(args))
    _artifact, contract, _err = resolve_execution_brief_contract(root, args.mission)
    traces: set[str] = set()
    if isinstance(contract, dict):
        for task in contract.get("tasks") or []:
            if not isinstance(task, dict):
                continue
            for entry in task.get("traces_to") or []:
                if isinstance(entry, str):
                    traces.add(entry)
    deltas: list[dict] = []
    for spec_md in delta_spec_files(root, args.mission):
        capability = spec_md.parent.name
        text = spec_md.read_text(encoding="utf-8")
        scenarios: list[dict] = []
        for line in text.splitlines():
            line_strip = line.strip()
            if line_strip.startswith("### Scenario:") or line_strip.startswith("#### Scenario:"):
                name = line_strip.split(":", 1)[1].strip()
                candidate_ids = {f"{capability}/spec.md#{name}", name}
                covered = bool(candidate_ids & traces) or any(name in t for t in traces)
                scenarios.append(
                    {
                        "name": name,
                        "covered": covered,
                        "trace_id": f"{capability}/spec.md#{name}",
                    }
                )
        deltas.append(
            {
                "capability": capability,
                "spec_path": relpath(root, spec_md),
                "scenarios": scenarios,
            }
        )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "spec.diff.list",
            "mission": args.mission,
            "deltas": deltas,
        },
    )
