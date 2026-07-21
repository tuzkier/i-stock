from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_cli_core.infra.runtime_paths import resolve_path


DOCUMENT_TYPE_PATHS: dict[str, list[tuple[str, str]]] = {
    "discovery": [("discovery", "discovery-brief.md")],
    "discovery-brief": [("discovery", "discovery-brief.md")],
    "dependency-impact": [("discovery", "dependency-impact.md")],
    "product-definition": [("product", "product-definition.md"), ("product", "prd.md")],
    "prd": [("product", "prd.md"), ("product", "product-definition.md")],
    "product-domain-model": [("product", "product-domain-model.md")],
    "product-evidence": [("product", "product-evidence.md")],
    "scope-strategy": [("product", "scope-strategy.md")],
    "use-case-model": [("product", "use-case-model.md"), ("product", "business-use-cases.md")],
    "business-use-cases": [("product", "business-use-cases.md"), ("product", "use-case-model.md")],
    "business-objects": [("product", "business-objects.md"), ("product", "business-object-analysis.md")],
    "business-object-analysis": [("product", "business-object-analysis.md"), ("product", "business-objects.md")],
    "acceptance-scenarios": [("product", "acceptance-scenarios.md")],
    "interaction": [("interaction", "interaction.md")],
    "solution": [("solution", "solution.md")],
    "tech-design": [("technical-analysis", "tech-design.md")],
    "technical-analysis": [("technical-analysis", "tech-design.md")],
    "task-order": [("breakdown", "execution-brief.md")],
    "execution-brief": [("breakdown", "execution-brief.md")],
    "execution-result": [("execute", "execution-result.md")],
    "code-review": [("code-review", "code-review.md")],
    "verification-report": [("verify", "verification-report.md")],
    "delivery-package": [("delivery", "delivery-package.md")],
    "acceptance-result": [("delivery", "acceptance-result.md")],
    "finishing-branch": [("finishing-branch", "finishing-branch.md")],
    "retrospective": [("retrospective", "retrospective.md")],
}


def supported_document_types() -> list[str]:
    return sorted(DOCUMENT_TYPE_PATHS)


def mission_document_candidates(mission_id: str, document_type: str) -> list[str]:
    return [
        f"harness-runtime/harness/artifacts/{mission_id}/{stage}/{filename}"
        for stage, filename in DOCUMENT_TYPE_PATHS.get(document_type, [])
    ]


def mission_document_item(root: Path, mission_id: str, document_type: str, *, required: bool = False) -> dict[str, Any]:
    candidates = mission_document_candidates(mission_id, document_type)
    selected = next(
        (candidate for candidate in candidates if (resolve_path(root, candidate) or root / candidate).exists()),
        candidates[0] if candidates else "",
    )
    exists = bool(selected and (resolve_path(root, selected) or root / selected).exists())
    return {
        "kind": document_type,
        "path": selected,
        "required": required,
        "exists": exists,
        "source": "mission_document_rule",
        "candidates": [
            {
                "path": candidate,
                "exists": bool((resolve_path(root, candidate) or root / candidate).exists()),
            }
            for candidate in candidates
        ],
    }
