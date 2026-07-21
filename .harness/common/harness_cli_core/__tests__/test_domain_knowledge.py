"""Unit tests for knowledge promotion helpers."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.knowledge import (  # noqa: E402
    apply_knowledge_promotion,
    knowledge_promotion_candidates,
)


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_promotion_candidates_scan_artifact_store_layout(tmp_path: Path) -> None:
    mission = "M-1"
    artifacts = tmp_path / "harness-runtime" / "harness" / "artifacts" / mission
    _write(artifacts / "product" / "product-definition.md", "# PRD\n")
    _write(artifacts / "product" / "specs" / "cap-a" / "spec.md", "# Cap A\n")
    _write(
        artifacts / "interaction" / "visual-interaction" / "visual-interaction-manifest.json",
        "{}\n",
    )

    candidates = knowledge_promotion_candidates(tmp_path, mission)

    sources = {item["source_artifact"]: item for item in candidates}
    assert f"harness-runtime/harness/artifacts/{mission}/product/product-definition.md" in sources
    assert f"harness-runtime/harness/artifacts/{mission}/product/specs/cap-a/spec.md" in sources
    # The operable prototype lives in the project-owned prototype project dir, not the
    # mission artifact, so it is never a copy candidate.
    assert all(item["artifact_kind"] != "operable_prototype" for item in candidates)
    assert sources[
        f"harness-runtime/harness/artifacts/{mission}/interaction/visual-interaction/visual-interaction-manifest.json"
    ]["artifact_kind"] == "stage_artifact"


def test_promotion_candidates_keep_legacy_stage_fallback(tmp_path: Path) -> None:
    mission = "M-1"
    stages = tmp_path / "harness-runtime" / "harness" / "stages" / mission
    _write(stages / "solution.md", "# Solution\n")
    _write(stages / "specs" / "cap-legacy" / "spec.md", "# Legacy Cap\n")

    candidates = knowledge_promotion_candidates(tmp_path, mission)

    sources = {item["source_artifact"]: item for item in candidates}
    assert f"harness-runtime/harness/stages/{mission}/solution.md" in sources
    assert sources[f"harness-runtime/harness/stages/{mission}/specs/cap-legacy/spec.md"]["artifact_kind"] == "delta_spec"


def test_apply_promotion_writes_specs_and_ledger_without_copying_prototype(tmp_path: Path) -> None:
    mission = "M-1"
    artifacts = tmp_path / "harness-runtime" / "harness" / "artifacts" / mission
    _write(
        artifacts / "product" / "specs" / "cap-a" / "spec.md",
        "# Cap A — 差量规格\n\n## ADDED Requirements\n\n### Requirement: A\n",
    )
    _write(
        artifacts / "interaction" / "visual-interaction" / "visual-interaction-manifest.json",
        "{}\n",
    )
    _write(tmp_path / "project-knowledge" / "_index.md", "# Index\n")

    result = apply_knowledge_promotion(tmp_path, mission)

    spec_target = tmp_path / "project-knowledge" / "specs" / "cap-a" / "spec.md"
    prototype_target = tmp_path / "project-knowledge" / "product" / "prototype" / "index.html"
    ledger_target = tmp_path / "project-knowledge" / "operations" / "knowledge-promotions" / f"{mission}.md"
    assert spec_target.exists()
    spec_text = spec_target.read_text(encoding="utf-8")
    assert "knowledge_type: behavior_spec" in spec_text
    assert "### Requirement: A" in spec_text
    # promote never copies the operable prototype into project-knowledge; it travels with the
    # branch merge from the project-owned prototype project dir.
    assert not prototype_target.exists()
    assert all(item.get("kind") != "operable_prototype" for item in result["applied"])
    assert ledger_target.exists()
    assert result["ledger_path"] == f"project-knowledge/operations/knowledge-promotions/{mission}.md"
    assert result["skipped"] == []


def test_apply_promotion_merges_delta_specs_into_existing_behavior_spec(tmp_path: Path) -> None:
    mission = "M-2"
    _write(
        tmp_path / "project-knowledge" / "specs" / "cap-a" / "spec.md",
        "# Cap A Specification\n\n"
        "## Purpose\nBaseline behavior.\n\n"
        "## Requirements\n\n"
        "### Requirement: Keep\n"
        "系统 SHALL keep existing behavior.\n\n"
        "#### Scenario: Keep works\n"
        "GIVEN baseline\n"
        "WHEN keep\n"
        "THEN preserved\n\n"
        "### Requirement: Change\n"
        "系统 SHALL use old behavior.\n\n"
        "### Requirement: Remove\n"
        "系统 SHALL remove old behavior.\n",
    )
    _write(
        tmp_path / "harness-runtime" / "harness" / "artifacts" / mission / "product" / "specs" / "cap-a" / "spec.md",
        "# Cap A — 差量规格\n\n"
        "## ADDED Requirements\n\n"
        "### Requirement: Add\n"
        "系统 SHALL add new behavior.\n\n"
        "#### Scenario: Add works\n"
        "GIVEN new input\n"
        "WHEN add\n"
        "THEN visible\n\n"
        "## MODIFIED Requirements\n\n"
        "### Requirement: Change\n"
        "系统 SHALL use changed behavior.\n\n"
        "#### Scenario: Change works\n"
        "GIVEN changed input\n"
        "WHEN change\n"
        "THEN visible\n\n"
        "## REMOVED Requirements\n\n"
        "- **Requirement: Remove**：旧行为已废弃。\n",
    )

    result = apply_knowledge_promotion(tmp_path, mission)

    spec_text = (tmp_path / "project-knowledge" / "specs" / "cap-a" / "spec.md").read_text(encoding="utf-8")
    assert "### Requirement: Keep" in spec_text
    assert "### Requirement: Add" in spec_text
    assert "系统 SHALL use changed behavior." in spec_text
    assert "### Requirement: Remove" not in spec_text
    assert "## Promotion History" in spec_text
    assert result["skipped"] == []


def test_apply_promotion_is_idempotent_for_behavior_specs(tmp_path: Path) -> None:
    mission = "M-3"
    _write(
        tmp_path / "harness-runtime" / "harness" / "artifacts" / mission / "product" / "specs" / "cap-a" / "spec.md",
        "# Cap A — 差量规格\n\n"
        "## ADDED Requirements\n\n"
        "### Requirement: A\n"
        "系统 SHALL add behavior.\n\n"
        "#### Scenario: A works\n"
        "GIVEN input\n"
        "WHEN act\n"
        "THEN output\n",
    )

    apply_knowledge_promotion(tmp_path, mission)
    apply_knowledge_promotion(tmp_path, mission)

    spec_text = (tmp_path / "project-knowledge" / "specs" / "cap-a" / "spec.md").read_text(encoding="utf-8")
    assert spec_text.count("### Requirement: A") == 1
    assert spec_text.count(f"- mission:{mission} from `harness-runtime/harness/artifacts/{mission}/product/specs/cap-a/spec.md`") == 1
