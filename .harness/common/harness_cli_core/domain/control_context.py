from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_cli_core.app.output import fail_payload
from harness_cli_core.domain.control_state import as_str_list, load_control_slice
from harness_cli_core.domain.mission_documents import mission_document_item
from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_layout import control_graph_root, control_runtime_root, control_status_path
from harness_cli_core.infra.runtime_paths import load_runtime_config, resolve_path


def control_relpath(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def path_item(root: Path, kind: str, path_value: str, *, required: bool, source: str) -> dict[str, Any]:
    path = resolve_path(root, path_value) or (root / path_value)
    return {
        "kind": kind,
        "path": path_value,
        "required": required,
        "exists": path.exists(),
        "source": source,
    }


def mission_document_items(root: Path, mission_id: str) -> list[dict[str, Any]]:
    document_types = (
        "discovery-brief",
        "dependency-impact",
        "product-definition",
        "product-domain-model",
        "product-evidence",
        "scope-strategy",
        "use-case-model",
        "acceptance-scenarios",
        "interaction",
        "solution",
        "tech-design",
        "task-order",
        "execution-result",
        "code-review",
        "verification-report",
        "delivery-package",
        "acceptance-result",
        "finishing-branch",
        "retrospective",
    )
    return [mission_document_item(root, mission_id, document_type) for document_type in document_types]


def selected_mission_slice(
    root: Path,
    layout: dict[str, Any],
    mission_id: str,
) -> tuple[dict[str, Any], dict[str, Any], Path, dict[str, Any]]:
    status_path = control_status_path(layout)
    status_doc = load_yaml(status_path) if status_path.exists() else {}
    status_doc = status_doc if isinstance(status_doc, dict) else {}
    entry = status_doc.get(mission_id) if isinstance(status_doc.get(mission_id), dict) else {}
    if not entry:
        return status_doc, {}, control_graph_root(layout) / "mission-slices" / f"{mission_id}.yaml", {}
    slice_path, mission_slice = load_control_slice(layout, root, mission_id, entry)
    return status_doc, entry, slice_path, mission_slice


def build_context_index(root: Path, layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    _status_doc, entry, slice_path, mission_slice = selected_mission_slice(root, layout, mission_id)
    if not entry:
        payload = fail_payload("control.context-index", "missing_mission", f"mission not found: {mission_id}")
        payload["runtime_layout"] = layout
        return payload
    if not mission_slice:
        payload = fail_payload("control.context-index", "missing_mission_slice", f"Mission Slice not found: {slice_path}")
        payload["runtime_layout"] = layout
        return payload

    work_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
    primary_nodes = as_str_list(work_graph.get("primary_nodes"))
    required_context = [
        path_item(root, "project_context", "project-context.md", required=True, source="project"),
        path_item(root, "mission_slice", control_relpath(root, slice_path), required=True, source="work_graph"),
    ]
    upstream_artifacts: list[dict[str, Any]] = []
    for node_id in primary_nodes:
        matches = sorted((control_graph_root(layout) / "nodes").glob(f"**/{node_id}.yaml"))
        if not matches:
            continue
        node = load_yaml(matches[0])
        brief = str(node.get("execution_brief_artifact") or "")
        if brief:
            upstream_artifacts.append(path_item(root, "execution_brief", brief, required=True, source="work_graph_node"))
    upstream_artifacts.extend(item for item in mission_document_items(root, mission_id) if item.get("exists"))
    mission_contract = control_runtime_root(layout) / "missions" / mission_id / "mission-contract.md"
    if mission_contract.exists():
        upstream_artifacts.append(path_item(root, "mission_contract", control_relpath(root, mission_contract), required=False, source="mission"))
    runtime_config = load_runtime_config(root)
    spec_config = runtime_config.get("spec") if isinstance(runtime_config.get("spec"), dict) else {}
    spec_enabled = bool(spec_config.get("enabled", False))
    delta_specs: list[dict[str, Any]] = []
    if spec_enabled:
        spec_roots = [
            control_runtime_root(layout) / "artifacts" / mission_id / "product" / "specs",
            control_runtime_root(layout) / "stages" / mission_id / "specs",
        ]
        seen: set[str] = set()
        for spec_root in spec_roots:
            for path in sorted(spec_root.glob("**/spec.md")) if spec_root.exists() else []:
                rel = control_relpath(root, path)
                if rel in seen:
                    continue
                seen.add(rel)
                delta_specs.append(path_item(root, "delta_spec", rel, required=True, source="mission_delta_spec"))
    all_items = required_context + upstream_artifacts + delta_specs
    missing_context = [item for item in all_items if item.get("required") and not item.get("exists")]
    return {
        "status": "PASS",
        "runtime_layout": layout,
        "mission_id": mission_id,
        "required_context": required_context,
        "upstream_artifacts": upstream_artifacts,
        "delta_specs": delta_specs,
        "project_context": required_context[0],
        "missing_context": missing_context,
        "findings": [],
    }
