from __future__ import annotations

import re
import shutil
from pathlib import Path

from harness_cli_core.infra.runtime_paths import relpath, runtime_harness_root


COMMON_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = COMMON_ROOT.parent

PROJECT_KNOWLEDGE_REQUIRED_PATHS = [
    "_index.md",
    "context/overview.md",
    "context/constraints.md",
    "context/tech-stack.md",
    "context/repository-map.md",
    "context/risks.md",
    "product/capabilities.md",
    "product/scope-boundaries.md",
    "product/workflows/README.md",
    "specs/_index.md",
    "design/system-overview.md",
    "design/modules/README.md",
    "design/decisions/README.md",
    "engineering/conventions/README.md",
    "engineering/patterns/README.md",
    "engineering/policies/README.md",
    "engineering/policies/stage-rules.yaml",
    "engineering/policies/project-lint.yaml",
    "engineering/task-splitting/README.md",
    "engineering/testing/README.md",
    "operations/README.md",
    "operations/verification/README.md",
    "operations/installation/README.md",
    "operations/troubleshooting/README.md",
    "lessons/README.md",
    "lessons/quality/README.md",
    "lessons/bug-fix/README.md",
    "glossary/README.md",
]

KNOWLEDGE_STAGE_DOMAINS = {
    "intake": ["context", "product", "specs", "lessons"],
    "discovery": ["context", "product", "specs", "design", "lessons"],
    "prd": ["context", "product", "specs"],
    "solution": ["context", "product", "specs", "design"],
    "interaction": ["context", "product", "design"],
    "technical_analysis": ["context", "specs", "design", "engineering"],
    "technical-analysis": ["context", "specs", "design", "engineering"],
    "breakdown": ["context", "specs", "design", "engineering"],
    "execute": ["context", "specs", "engineering", "operations"],
    "code-review": ["context", "specs", "engineering", "lessons"],
    "verify": ["context", "specs", "engineering", "operations", "lessons"],
    "delivery": ["product", "operations", "lessons"],
    "retrospective": ["context", "engineering", "operations", "lessons"],
    "finishing-branch": ["operations", "lessons"],
}


def project_knowledge_root(root: Path) -> Path:
    return root / "project-knowledge"


def project_knowledge_template_root() -> Path:
    for candidate in (
        root_template := PACKAGE_ROOT / "project-knowledge",
        PACKAGE_ROOT.parent / "project-knowledge",
    ):
        if candidate.exists():
            return candidate
    return root_template


def behavior_specs_root(root: Path) -> Path:
    installed = project_knowledge_root(root) / "specs"
    source_repo = root / "package" / "project-knowledge" / "specs"
    if installed.exists():
        return installed
    if source_repo.exists():
        return source_repo
    return installed


def behavior_specs_template_root() -> Path:
    return project_knowledge_template_root() / "specs"


def copy_tree_missing(src: Path, dst: Path, *, replace: bool = False) -> list[str]:
    created: list[str] = []
    for item in src.rglob("*"):
        if item.is_dir():
            (dst / item.relative_to(src)).mkdir(parents=True, exist_ok=True)
            continue
        rel = item.relative_to(src)
        target = dst / rel
        if target.exists() and not replace:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        created.append(str(rel))
    return created


def knowledge_markdown_files(root: Path) -> list[Path]:
    knowledge_root = project_knowledge_root(root)
    if not knowledge_root.exists():
        return []
    return sorted(
        path for path in knowledge_root.rglob("*.md")
        if path.is_file() and path.name != "_index.md"
    )


def knowledge_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    block = text[4:end].strip()
    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def knowledge_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").title()


def knowledge_domain(relative: Path) -> str:
    return relative.parts[0] if relative.parts else "root"


def knowledge_index_rows(root: Path) -> list[dict[str, str]]:
    knowledge_root = project_knowledge_root(root)
    rows: list[dict[str, str]] = []
    for path in knowledge_markdown_files(root):
        rel = path.relative_to(knowledge_root)
        meta = knowledge_frontmatter(path)
        rows.append({
            "topic": knowledge_title(path),
            "path": str(rel),
            "domain": meta.get("knowledge_type") or knowledge_domain(rel),
            "tags": meta.get("tags", knowledge_domain(rel)),
            "used_by": meta.get("used_by_stages", ""),
            "source": meta.get("source", ""),
            "status": meta.get("status", ""),
        })
    return rows


def render_knowledge_index(root: Path) -> str:
    rows = knowledge_index_rows(root)
    lines = [
        "---",
        "knowledge_type: index",
        "status: active",
        "source: generated",
        "---",
        "",
        "# Project Knowledge Index",
        "",
        "This file is generated by `harness knowledge index`.",
        "",
        "## Knowledge Map",
        "",
        "| Topic | Path | Domain | Tags | Used By Stages | Source | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['topic']} | {row['path']} | {row['domain']} | "
            f"{row['tags']} | {row['used_by']} | {row['source']} | {row['status']} |"
        )
    lines.extend([
        "",
        "## Rules",
        "",
        "- Runtime evidence stays in `harness-runtime/harness/`.",
        "- Long-lived team knowledge lands in `project-knowledge/`.",
        "- Do not copy whole stage artifacts here. Promote only stable knowledge.",
        "- Each promoted entry should keep source mission, status, and last verified date.",
        "",
    ])
    return "\n".join(lines)


PROMOTION_ARTIFACT_CANDIDATES = [
    ("discovery/discovery-brief.md", "context/product", "Discovery facts, affected capabilities, risks, and scope evidence"),
    ("discovery/dependency-impact.md", "context/design", "Dependency impact findings and external constraints"),
    ("product/product-definition.md", "product/specs", "Product workflows, capability boundaries, behavior specs"),
    ("product/business-object-analysis.md", "product/specs", "Business object model (OBJ-xx) and stable product vocabulary"),
    ("product/business-use-cases.md", "product/specs", "Business use cases and long-lived user journeys"),
    ("product/use-case-model.md", "product/system-use-cases", "System use cases (SUC-*) realized by the long-lived prototype: curate into the project SUC registry with id/title/surface + page_entry/anchor (join SUC titles with the interaction surface_bindings) so the prototype frame shows this mission's SUC alongside existing project SUCs"),
    ("product/scope-strategy.md", "product/context", "Scope decisions, out-of-scope boundaries, and later candidates"),
    ("product/product-domain-model.md", "product/specs", "DDD domain model: bounded contexts, aggregates, commands, events, invariants, states, permissions"),
    ("product/product-evidence.md", "product/specs", "Product evidence, spec alignment, and impact records"),
    ("interaction/interaction.md", "product/design", "Interaction decisions, prototype patch summary, and promotion candidates"),
    ("interaction/interaction-spec/README.md", "product/design", "Interaction specification entry and use-case realization index"),
    ("interaction/interaction-spec/buc-index.md", "product/workflows", "Stable business use case index and E2E priorities"),
    ("interaction/interaction-spec/buc-coverage.md", "product/workflows/specs", "Use-case and behavior coverage evidence"),
    ("interaction/interaction-spec/_shared/surface-registry.md", "product/ui-surfaces", "Stable UI surface registry"),
    ("interaction/interaction-spec/_shared/domain-ui-mapping.md", "product/ui-surfaces/specs", "Domain object to UI surface mapping"),
    ("interaction/interaction-spec/_shared/consistency-report.md", "product/design", "Interaction consistency decisions and gaps"),
    ("interaction/visual-interaction/visual-interaction-manifest.json", "product", "Visual prototype manifest and evidence registry; points to the long-lived prototype project entry"),
    ("solution/solution.md", "design", "Architecture overview or design decisions"),
    ("technical-analysis/tech-design.md", "design/engineering", "Module details, conventions, implementation patterns"),
    ("breakdown/execution-brief.md", "engineering", "Reusable task splitting or workflow patterns"),
    ("execute/execution-result.md", "engineering", "Implementation evidence and reusable engineering patterns"),
    ("code-review/code-review.md", "engineering/lessons", "Review rules, quality lessons, accepted tradeoffs"),
    ("verify/verification-report.md", "operations/engineering", "Verification runbooks and testing patterns"),
    ("verify/acceptance-result.md", "product/operations", "Accepted product behavior or operator validation steps"),
    ("delivery/delivery-package.md", "operations/lessons", "Delivery summary, follow-up candidates, handoff facts"),
    ("retrospective/retrospective.md", "lessons/context", "Lessons and context updates"),
    ("finishing-branch/finishing-branch.md", "operations/lessons", "Branch close facts and final mission state"),
]

PROMOTION_LEGACY_CANDIDATES = [
    ("mission-contract.md", "context", "Mission boundaries or durable constraints"),
    ("product/product-definition.md", "product/specs", "Product workflows, capability boundaries, behavior specs"),
    ("product/business-object-analysis.md", "product/specs", "Business object model (OBJ-xx) and stable product vocabulary"),
    ("product/business-use-cases.md", "product/specs", "Business use cases and long-lived user journeys"),
    ("product/use-case-model.md", "product/system-use-cases", "System use cases (SUC-*) realized by the long-lived prototype: curate into the project SUC registry with id/title/surface + page_entry/anchor (join SUC titles with the interaction surface_bindings) so the prototype frame shows this mission's SUC alongside existing project SUCs"),
    ("product/scope-strategy.md", "product/context", "Scope decisions, out-of-scope boundaries, and later candidates"),
    ("product/product-domain-model.md", "product/specs", "DDD domain model: bounded contexts, aggregates, commands, events, invariants, states, permissions"),
    ("product/product-evidence.md", "product/specs", "Product evidence, spec alignment, and impact records"),
    ("interaction.md", "product/design", "Interaction decisions, prototype patch summary, and promotion candidates"),
    ("interaction-spec/README.md", "product/design", "Interaction specification entry and use-case realization index"),
    ("interaction-spec/buc-index.md", "product/workflows", "Business use case index and E2E priorities"),
    ("interaction-spec/buc-coverage.md", "product/workflows/specs", "Use-case and behavior coverage evidence"),
    ("interaction-spec/_shared/surface-registry.md", "product/ui-surfaces", "Stable UI surface registry"),
    ("interaction-spec/_shared/domain-ui-mapping.md", "product/ui-surfaces/specs", "Domain object to UI surface mapping"),
    ("visual-interaction/visual-interaction-manifest.json", "product", "Visual prototype manifest and evidence registry; points to the long-lived prototype project entry"),
    ("solution.md", "design", "Architecture overview or design decisions"),
    ("tech-design.md", "design/engineering", "Module details, conventions, implementation patterns"),
    ("execution-brief.md", "engineering", "Reusable task splitting or workflow patterns"),
    ("execution-result.md", "engineering", "Implementation evidence and reusable engineering patterns"),
    ("code-review.md", "engineering/lessons", "Review rules, quality lessons, accepted tradeoffs"),
    ("verification-report.md", "operations/engineering", "Verification runbooks and testing patterns"),
    ("acceptance-result.md", "product/operations", "Accepted product behavior or operator validation steps"),
    ("delivery-package.md", "operations/lessons", "Delivery summary, follow-up candidates, handoff facts"),
    ("retrospective.md", "lessons/context", "Lessons and context updates"),
]


def _append_candidate(
    result: list[dict[str, str]],
    *,
    root: Path,
    path: Path,
    target: str,
    rationale: str,
    source_root: str,
    kind: str = "stage_artifact",
) -> None:
    result.append({
        "source_artifact": relpath(root, path),
        "target_domain": target,
        "promotion_rule": rationale,
        "source_root": source_root,
        "artifact_kind": kind,
    })


def knowledge_promotion_candidates(root: Path, mission: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    mission_contract = runtime_harness_root(root) / "missions" / mission / "mission-contract.md"
    if mission_contract.exists():
        _append_candidate(
            result,
            root=root,
            path=mission_contract,
            target="context",
            rationale="Mission boundaries, durable constraints, and accepted scope decisions",
            source_root="missions",
            kind="mission_contract",
        )

    artifact_dir = runtime_harness_root(root) / "artifacts" / mission
    for artifact, target, rationale in PROMOTION_ARTIFACT_CANDIDATES:
        path = artifact_dir / artifact
        if path.exists():
            _append_candidate(
                result,
                root=root,
                path=path,
                target=target,
                rationale=rationale,
                source_root="artifacts",
                kind="stage_artifact",
            )
    legacy_dir = artifact_dir / "legacy"
    for artifact, target, rationale in PROMOTION_LEGACY_CANDIDATES:
        path = legacy_dir / artifact
        if path.exists():
            _append_candidate(
                result,
                root=root,
                path=path,
                target=target,
                rationale=rationale,
                source_root="artifacts/legacy",
                kind="legacy_stage_artifact",
            )

    stage_dir = runtime_harness_root(root) / "stages" / mission
    for artifact, target, rationale in PROMOTION_LEGACY_CANDIDATES:
        path = stage_dir / artifact
        if path.exists():
            _append_candidate(
                result,
                root=root,
                path=path,
                target=target,
                rationale=rationale,
                source_root="stages",
                kind="legacy_stage_artifact",
            )

    for specs_dir, source_root in (
        (artifact_dir / "product" / "specs", "artifacts"),
        (legacy_dir / "specs", "artifacts/legacy"),
        (stage_dir / "specs", "stages"),
    ):
        if not specs_dir.exists():
            continue
        for spec_path in sorted(specs_dir.rglob("spec.md")):
            _append_candidate(
                result,
                root=root,
                path=spec_path,
                target="specs",
                rationale="Merge accepted delta spec into long-lived behavior specs",
                source_root=source_root,
                kind="delta_spec",
            )
    return result


def _read_promoted_source(root: Path, source_artifact: str) -> Path:
    path = root / source_artifact
    if not path.exists():
        raise FileNotFoundError(source_artifact)
    return path


def _prepend_frontmatter(text: str, meta: dict[str, str]) -> str:
    if text.startswith("---\n"):
        return text
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {value}")
    lines.extend(["---", "", text.rstrip(), ""])
    return "\n".join(lines)


def _capability_from_spec(path: Path) -> str:
    if path.name == "spec.md" and path.parent.name:
        return path.parent.name
    match = re.search(r"specs/([^/]+)/spec\.md$", path.as_posix())
    return match.group(1) if match else path.parent.name


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    return text[end + 4 :].lstrip("\n")


def _extract_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## ") and lines[index].strip() != heading:
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def _requirement_blocks(section_text: str) -> dict[str, str]:
    lines = section_text.splitlines()
    blocks: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []
    for line in lines:
        if line.strip() == "---":
            continue
        if line.startswith("## "):
            break
        match = re.match(r"^### Requirement:\s*(.+?)\s*$", line)
        if match:
            if current_name and current_lines:
                blocks[current_name] = "\n".join(current_lines).strip()
            current_name = match.group(1).strip()
            current_lines = [line]
            continue
        if current_name:
            current_lines.append(line)
    if current_name and current_lines:
        blocks[current_name] = "\n".join(current_lines).strip()
    return blocks


def _removed_requirement_names(section_text: str) -> list[str]:
    names: list[str] = []
    for line in section_text.splitlines():
        match = re.search(r"\*\*Requirement:\s*(.+?)\*\*", line)
        if match:
            names.append(match.group(1).strip())
            continue
        match = re.search(r"Requirement:\s*([^—-]+)", line)
        if match:
            names.append(match.group(1).strip())
    return names


def _requirements_body(text: str) -> tuple[str, dict[str, str], str]:
    body = _strip_frontmatter(text).rstrip()
    before, marker, after = body.partition("## Requirements")
    if not marker:
        return body + "\n\n## Requirements", {}, ""
    history_match = re.search(r"(?ms)(?:^---\s*\n\n)?## Promotion History\n\n.*$", after)
    if history_match:
        requirement_section = after[: history_match.start()]
        tail = history_match.group(0).strip()
    else:
        requirement_section = after
        tail = ""
    header = (before.rstrip() + "\n\n## Requirements").strip()
    return header, _requirement_blocks(requirement_section), tail


def _append_promotion_history(tail: str, entry: str) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for line in tail.splitlines():
        stripped = line.strip()
        if stripped.startswith("- mission:"):
            if stripped in seen:
                continue
            seen.add(stripped)
        lines.append(line)
    if entry in seen:
        return "\n".join(lines).rstrip()
    if not any(line.strip() == "## Promotion History" for line in lines):
        if lines:
            lines.extend(["", "## Promotion History", ""])
        else:
            lines.extend(["---", "", "## Promotion History", ""])
    lines.append(entry)
    return "\n".join(lines).rstrip()


def _render_full_spec(capability: str, existing_text: str | None, delta_text: str, mission: str, source_artifact: str) -> tuple[str, list[str]]:
    delta_body = _strip_frontmatter(delta_text)
    added = _requirement_blocks(_extract_section(delta_body, "## ADDED Requirements"))
    modified = _requirement_blocks(_extract_section(delta_body, "## MODIFIED Requirements"))
    removed = _removed_requirement_names(_extract_section(delta_body, "## REMOVED Requirements"))
    changes: list[str] = []

    existing_body = _strip_frontmatter(existing_text) if existing_text else ""
    if existing_text and "## Requirements" in existing_body:
        header, requirements, tail = _requirements_body(existing_text)
    else:
        title = re.search(r"^#\s+(.+?)(?:\s+—\s+差量规格)?\s*$", delta_body, re.MULTILINE)
        spec_title = title.group(1).strip() if title else capability
        header = (
            "---\n"
            "knowledge_type: behavior_spec\n"
            "status: active\n"
            f"source: mission:{mission}\n"
            f"source_artifact: {source_artifact}\n"
            "confidence: accepted\n"
            "---\n\n"
            f"# {spec_title} Specification\n\n"
            "## Purpose\n"
            "从已验收任务差量规格首次建立的长期行为契约。\n\n"
            "## Requirements"
        )
        requirements = {}
        tail = ""
        changes.append("initialized")

    for name in removed:
        if name in requirements:
            requirements.pop(name, None)
            changes.append(f"removed:{name}")
        else:
            changes.append(f"remove_missing:{name}")

    for name, block in modified.items():
        requirements[name] = block
        changes.append(f"modified:{name}")

    for name, block in added.items():
        if name in requirements:
            changes.append(f"added_already_present:{name}")
            continue
        requirements[name] = block
        changes.append(f"added:{name}")

    rendered = header.rstrip() + "\n\n"
    if requirements:
        rendered += "\n\n".join(block.rstrip() for block in requirements.values()) + "\n"
    else:
        rendered += "_No active requirements._\n"
    history_entry = f"- mission:{mission} from `{source_artifact}`"
    if tail:
        rendered += "\n" + _append_promotion_history(tail, history_entry) + "\n"
    else:
        rendered += "\n---\n\n## Promotion History\n\n" + history_entry + "\n"
    return rendered, changes


def _promotion_ledger_text(
    *,
    mission: str,
    candidates: list[dict[str, str]],
    applied: list[dict[str, str]],
    skipped: list[dict[str, str]],
) -> str:
    lines = [
        "---",
        "knowledge_type: operation",
        "status: active",
        f"source: mission:{mission}",
        "confidence: accepted",
        "---",
        "",
        f"# Knowledge Promotion Ledger: {mission}",
        "",
        "本文件记录本 Mission 结束时已执行的知识沉淀。运行时产物仍保留在 `harness-runtime/harness/artifacts/`；长期、可继承内容落入 `project-knowledge/`。",
        "",
        "## Applied",
        "",
        "| Source | Target | Kind |",
        "|---|---|---|",
    ]
    for item in applied:
        lines.append(f"| `{item['source_artifact']}` | `{item['target']}` | {item['kind']} |")
    if not applied:
        lines.append("| - | - | - |")
    lines.extend([
        "",
        "## Skipped Or Manual Merge Needed",
        "",
        "| Source | Reason |",
        "|---|---|",
    ])
    for item in skipped:
        lines.append(f"| `{item['source_artifact']}` | {item['reason']} |")
    if not skipped:
        lines.append("| - | - |")
    lines.extend([
        "",
        "## Candidate Inventory",
        "",
        "| Source Artifact | Target Domain | Promotion Rule |",
        "|---|---|---|",
    ])
    for candidate in candidates:
        lines.append(
            f"| `{candidate['source_artifact']}` | `{candidate['target_domain']}` | {candidate['promotion_rule']} |"
        )
    lines.append("")
    return "\n".join(lines)


def apply_knowledge_promotion(root: Path, mission: str, *, replace_existing: bool = False) -> dict[str, object]:
    knowledge_root = project_knowledge_root(root)
    candidates = knowledge_promotion_candidates(root, mission)
    applied: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    for candidate in candidates:
        source = _read_promoted_source(root, candidate["source_artifact"])
        kind = candidate.get("artifact_kind", "")
        if kind == "delta_spec":
            capability = _capability_from_spec(source)
            target = knowledge_root / "specs" / capability / "spec.md"
            existing_text = None if replace_existing or not target.exists() else target.read_text(encoding="utf-8")
            text, changes = _render_full_spec(
                capability,
                existing_text,
                source.read_text(encoding="utf-8"),
                mission,
                candidate["source_artifact"],
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            applied.append({
                "source_artifact": candidate["source_artifact"],
                "target": relpath(root, target),
                "kind": "behavior_spec",
                "merge": ",".join(changes),
            })
    ledger = knowledge_root / "operations" / "knowledge-promotions" / f"{mission}.md"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        _promotion_ledger_text(mission=mission, candidates=candidates, applied=applied, skipped=skipped),
        encoding="utf-8",
    )
    applied.append({
        "source_artifact": f"harness-runtime/harness/artifacts/{mission}",
        "target": relpath(root, ledger),
        "kind": "promotion_ledger",
    })

    return {
        "candidates": candidates,
        "applied": applied,
        "skipped": skipped,
        "ledger_path": relpath(root, ledger),
    }
