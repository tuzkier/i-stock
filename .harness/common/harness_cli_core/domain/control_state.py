from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_cli_core.app.output import finding
from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_layout import control_graph_root
from harness_cli_core.infra.runtime_paths import resolve_path


def as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def mission_summary(mission_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    return {
        "mission_id": mission_id,
        "status": entry.get("status") or "",
        "started_at": entry.get("started_at") or "",
        "current_lane": entry.get("current_lane") or work_graph.get("lane") or "",
        "current_stage": entry.get("current_stage") or "",
        "mission_slice": work_graph.get("mission_slice") or "",
        "last_operation_status": work_graph.get("last_operation_status") or "",
    }


def node_summary(path: Path, node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(node.get("id") or path.stem),
        "kind": str(node.get("kind") or ""),
        "title": str(node.get("title") or ""),
        "lane": str(node.get("lane") or ""),
        "stage": str(node.get("stage") or ""),
        "status": str(node.get("status") or ""),
        "priority": str(node.get("priority") or ""),
        "path": str(path),
    }


def load_control_nodes(layout: dict[str, Any]) -> list[dict[str, Any]]:
    nodes_root = control_graph_root(layout) / "nodes"
    if not nodes_root.exists():
        return []
    nodes: list[dict[str, Any]] = []
    for path in sorted(nodes_root.glob("**/*.yaml")):
        node = load_yaml(path)
        if node:
            nodes.append(node_summary(path, node))
    return nodes


def control_nodes_by_id(layout: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(node.get("id") or ""): node for node in load_control_nodes(layout) if node.get("id")}


def load_control_slice(
    layout: dict[str, Any],
    project_root: Path,
    mission_id: str,
    entry: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    path = resolve_path(project_root, str(work_graph.get("mission_slice") or ""))
    path = path or (control_graph_root(layout) / "mission-slices" / f"{mission_id}.yaml")
    return path, load_yaml(path)


def mission_slice_from_lane(mission_slice: dict[str, Any]) -> str:
    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    lane_action = mission_slice.get("lane_action") if isinstance(mission_slice.get("lane_action"), dict) else {}
    return str(
        control_plane.get("lane")
        or lane_action.get("lane")
        or mission_slice.get("from_lane")
        or control_plane.get("from_lane")
        or lane_action.get("from_lane")
        or ""
    )


def mission_slice_primary_nodes(mission_slice: dict[str, Any]) -> list[str]:
    work_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
    return as_str_list(work_graph.get("primary_nodes"))


def mission_slice_lane_consistency_findings(
    nodes_by_id: dict[str, dict[str, Any]],
    mission_id: str,
    mission_slice: dict[str, Any],
    *,
    source: str,
    blocking: bool,
    path: str = "",
) -> list[dict[str, Any]]:
    from_lane = mission_slice_from_lane(mission_slice)
    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    expected_stage = str(control_plane.get("stage") or "")
    findings: list[dict[str, Any]] = []
    for node_id in mission_slice_primary_nodes(mission_slice):
        node = nodes_by_id.get(node_id)
        if node is None:
            findings.append(finding(
                "BLOCKED" if blocking else "FAIL",
                "mission_slice_primary_node_missing",
                f"Mission Slice {mission_id} references unknown primary node {node_id}",
                source=source,
                blocking=blocking,
                mission_id=mission_id,
                path=path,
                node_id=node_id,
            ))
            continue
        node_lane = str(node.get("lane") or "")
        node_stage = str(node.get("stage") or "")
        if from_lane and node_lane != from_lane:
            findings.append(finding(
                "BLOCKED" if blocking else "FAIL",
                "mission_slice_primary_node_lane_mismatch",
                f"Mission Slice {mission_id} primary node {node_id} lane is {node_lane}, expected {from_lane}",
                source=source,
                blocking=blocking,
                mission_id=mission_id,
                path=path,
                node_id=node_id,
                node_lane=node_lane,
                expected_lane=from_lane,
            ))
        if expected_stage and node_stage != expected_stage:
            findings.append(finding(
                "BLOCKED" if blocking else "FAIL",
                "mission_slice_primary_node_stage_mismatch",
                f"Mission Slice {mission_id} primary node {node_id} stage is {node_stage}, expected {expected_stage}",
                source=source,
                blocking=blocking,
                mission_id=mission_id,
                path=path,
                node_id=node_id,
                node_stage=node_stage,
                expected_stage=expected_stage,
            ))
    return findings
"""Pure domain helpers for manifests, graph operations, and collections."""
