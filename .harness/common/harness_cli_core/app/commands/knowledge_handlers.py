from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.knowledge import (
    KNOWLEDGE_STAGE_DOMAINS,
    PROJECT_KNOWLEDGE_REQUIRED_PATHS,
    apply_knowledge_promotion,
    copy_tree_missing,
    knowledge_domain,
    knowledge_index_rows,
    knowledge_markdown_files,
    knowledge_promotion_candidates,
    project_knowledge_root,
    project_knowledge_template_root,
    render_knowledge_index,
)
from harness_cli_core.infra.runtime_paths import relpath, resolve_path, runtime_harness_root


def cmd_knowledge_init(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    target = project_knowledge_root(root)
    template = project_knowledge_template_root()
    if target.exists() and any(target.iterdir()) and not args.replace:
        return emit_payload(args, fail_payload(
            "knowledge.init",
            "project_knowledge_exists",
            f"project-knowledge already exists at {relpath(root, target)}; pass --replace to overwrite template files.",
        ))
    if not template.exists():
        return emit_payload(args, fail_payload(
            "knowledge.init",
            "missing_project_knowledge_template",
            f"project-knowledge template not found: {template}",
        ))
    created = copy_tree_missing(template, target, replace=bool(args.replace))
    return emit_payload(args, {
        "status": "PASS",
        "control": "knowledge.init",
        "knowledge_root": relpath(root, target),
        "template": relpath(root, template),
        "created": created,
        "findings": [],
    })


def cmd_knowledge_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    knowledge_root = project_knowledge_root(root)
    findings: list[dict[str, object]] = []
    if not knowledge_root.exists():
        findings.append({
            "level": "FAIL",
            "code": "project_knowledge_missing",
            "message": "project-knowledge/ is missing; run `harness knowledge init`.",
        })
    for relative in PROJECT_KNOWLEDGE_REQUIRED_PATHS:
        path = knowledge_root / relative
        if not path.exists():
            findings.append({
                "level": "FAIL",
                "code": "required_knowledge_file_missing",
                "path": relative,
                "message": f"Required project knowledge file is missing: project-knowledge/{relative}",
            })
    index_path = knowledge_root / "_index.md"
    if index_path.exists():
        index_text = index_path.read_text(encoding="utf-8")
        for path in knowledge_markdown_files(root):
            relative = str(path.relative_to(knowledge_root))
            if relative not in index_text:
                findings.append({
                    "level": "WARN",
                    "code": "knowledge_file_not_indexed",
                    "path": relative,
                    "message": f"{relative} is not listed in project-knowledge/_index.md",
                })
    status = "FAIL" if any(f["level"] == "FAIL" for f in findings) else ("WARN" if findings else "PASS")
    return emit_payload(args, {
        "status": status,
        "control": "knowledge.check",
        "knowledge_root": relpath(root, knowledge_root),
        "required_count": len(PROJECT_KNOWLEDGE_REQUIRED_PATHS),
        "markdown_count": len(knowledge_markdown_files(root)),
        "findings": findings,
    })


def cmd_knowledge_index(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    knowledge_root = project_knowledge_root(root)
    if not knowledge_root.exists():
        return emit_payload(args, fail_payload(
            "knowledge.index",
            "project_knowledge_missing",
            "project-knowledge/ is missing; run `harness knowledge init` first.",
        ))
    rendered = render_knowledge_index(root)
    index_path = knowledge_root / "_index.md"
    if getattr(args, "check", False):
        current = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
        up_to_date = current == rendered
        return emit_payload(args, {
            "status": "PASS" if up_to_date else "FAIL",
            "control": "knowledge.index",
            "knowledge_root": relpath(root, knowledge_root),
            "index_path": relpath(root, index_path),
            "up_to_date": up_to_date,
            "indexed_count": len(knowledge_index_rows(root)),
            "findings": [] if up_to_date else [{
                "level": "FAIL",
                "code": "knowledge_index_stale",
                "message": "project-knowledge/_index.md is stale; run `harness knowledge index`.",
            }],
        })
    index_path.write_text(rendered, encoding="utf-8")
    return emit_payload(args, {
        "status": "PASS",
        "control": "knowledge.index",
        "knowledge_root": relpath(root, knowledge_root),
        "index_path": relpath(root, index_path),
        "indexed_count": len(knowledge_index_rows(root)),
        "findings": [],
    })


def cmd_knowledge_resolve(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    stage = args.stage
    capability = getattr(args, "capability", None)
    knowledge_root = project_knowledge_root(root)
    if not knowledge_root.exists():
        return emit_payload(args, fail_payload(
            "knowledge.resolve",
            "project_knowledge_missing",
            "project-knowledge/ is missing; run `harness knowledge init` first.",
        ))
    domains = KNOWLEDGE_STAGE_DOMAINS.get(stage, ["context"])
    paths: list[str] = []
    for required in ("_index.md",):
        if (knowledge_root / required).exists():
            paths.append(f"project-knowledge/{required}")
    for path in knowledge_markdown_files(root):
        rel = path.relative_to(knowledge_root)
        domain = knowledge_domain(rel)
        if domain not in domains:
            continue
        if capability:
            text = str(rel).lower()
            if capability.lower() not in text and domain == "specs":
                continue
        paths.append(f"project-knowledge/{rel}")
    if "engineering" in domains:
        for rel in (
            Path("engineering/policies/stage-rules.yaml"),
            Path("engineering/policies/project-lint.yaml"),
        ):
            if (knowledge_root / rel).exists():
                paths.append(f"project-knowledge/{rel}")
    return emit_payload(args, {
        "status": "PASS",
        "control": "knowledge.resolve",
        "stage": stage,
        "capability": capability,
        "domains": domains,
        "paths": paths,
        "findings": [],
    })


def cmd_knowledge_promote(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    knowledge_root = project_knowledge_root(root)
    if not knowledge_root.exists():
        return emit_payload(args, fail_payload(
            "knowledge.promote",
            "project_knowledge_missing",
            "project-knowledge/ is missing; run `harness knowledge init` first.",
        ))
    candidates = knowledge_promotion_candidates(root, mission)
    findings: list[dict[str, object]] = []
    promotion_result: dict[str, object] | None = None
    graph_merge: dict[str, object] | None = None
    if getattr(args, "apply", False):
        promotion_result = apply_knowledge_promotion(
            root,
            mission,
            replace_existing=bool(getattr(args, "replace_existing", False)),
        )
        candidates = promotion_result["candidates"]  # type: ignore[assignment]
        for skipped in promotion_result["skipped"]:  # type: ignore[index]
            findings.append({
                "level": "WARN",
                "code": "promotion_target_requires_manual_merge",
                "source_artifact": skipped["source_artifact"],
                "message": skipped["reason"],
            })
        # 闭环沉淀：把本 mission 的 behavior-graph 并入项目级累积图（两层模型 SSOT）。
        from harness_cli_core.domain import behavior_graph as _bg

        graph_merge = _bg.promote_mission_graph_to_project(root, mission)
    if not candidates:
        findings.append({
            "level": "WARN",
            "code": "no_promotion_sources_found",
            "message": f"No mission artifacts found for {mission}; promotion candidate plan is empty.",
        })
    plan_text = [
        f"# Knowledge Promotion Candidate Plan: {mission}",
        "",
        "This candidate plan is generated by `harness knowledge promote`.",
        "It lists possible sources and target domains only; an Agent must perform the semantic extraction before long-lived knowledge is written.",
        "",
        "## Candidates",
        "",
        "| Source Artifact | Target Domain | Promotion Rule |",
        "|---|---|---|",
    ]
    for candidate in candidates:
        plan_text.append(
            f"| `{candidate['source_artifact']}` | `{candidate['target_domain']}` | {candidate['promotion_rule']} |"
        )
    plan_text.extend([
        "",
        "## Rules",
        "",
        "- Promote only stable knowledge, not full stage artifacts.",
        "- Use Agent judgment to extract product knowledge, specs, design decisions, engineering patterns, runbooks, or lessons.",
        "- Keep source mission and status in promoted files.",
        "- Update `project-knowledge/_index.md` after promotion.",
        "",
    ])
    output = resolve_path(root, getattr(args, "output", None))
    if output is None:
        output = runtime_harness_root(root) / "artifacts" / mission / "retrospective" / "knowledge-promotion-plan.md"
    if getattr(args, "write_plan", False):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(plan_text), encoding="utf-8")
    return emit_payload(args, {
        "status": "WARN" if findings else "PASS",
        "control": "knowledge.promote",
        "mission": mission,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "plan_path": relpath(root, output),
        "written": bool(getattr(args, "write_plan", False)),
        "applied": promotion_result["applied"] if promotion_result else [],
        "skipped": promotion_result["skipped"] if promotion_result else [],
        "ledger_path": promotion_result["ledger_path"] if promotion_result else "",
        "behavior_graph_merge": graph_merge,
        "findings": findings,
    })
