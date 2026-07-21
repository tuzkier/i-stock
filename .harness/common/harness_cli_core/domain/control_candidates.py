from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_cli_core.app.output import status_from_findings
from harness_cli_core.domain.control_state import as_str_list, load_control_slice
from harness_cli_core.domain.control_status import collect_control_status, control_active_slice_ids
from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_layout import control_status_path


def node_status_by_id(status_payload: dict[str, Any]) -> dict[str, str]:
    nodes = (status_payload.get("work_graph") or {}).get("ready_nodes") or []
    nodes += (status_payload.get("work_graph") or {}).get("blocked_nodes") or []
    return {str(node.get("id") or ""): str(node.get("status") or "") for node in nodes if isinstance(node, dict)}


def build_continue_candidates(root: Path, layout: dict[str, Any], *, mission: str | None = None) -> dict[str, Any]:
    status_payload = collect_control_status(root, layout, mission=mission)
    status_path = control_status_path(layout)
    status_doc = load_yaml(status_path) if status_path.exists() else {}
    status_doc = status_doc if isinstance(status_doc, dict) else {}
    active_set = set(control_active_slice_ids(status_doc, root, layout))
    node_status = node_status_by_id(status_payload)
    candidates: list[dict[str, Any]] = []
    findings = list(status_payload.get("consistency_findings") or [])

    mission_ids = [item.get("mission_id") for item in (status_payload.get("missions") or {}).get("open", []) if isinstance(item, dict)]
    for mission_id in [str(item) for item in mission_ids if item]:
        entry = status_doc.get(mission_id) if isinstance(status_doc.get(mission_id), dict) else {}
        slice_path, mission_slice = load_control_slice(layout, root, mission_id, entry)
        control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
        slice_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
        primary_nodes = as_str_list(slice_graph.get("primary_nodes"))
        node_id = primary_nodes[0] if primary_nodes else ""
        blocked_reasons: list[str] = []
        if not mission_slice:
            blocked_reasons.append("missing_mission_slice")
        if node_id and node_status.get(node_id) == "blocked":
            blocked_reasons.append("primary_node_blocked")
        if not node_id:
            blocked_reasons.append("missing_primary_node")
        candidates.append({
            "mission_id": mission_id,
            "node_id": node_id,
            "lane": control_plane.get("lane") or "",
            "stage": control_plane.get("stage") or "",
            "status": entry.get("status") or "",
            "sources": [source for source in ("mission_status", "mission_slice" if mission_slice else "", "active_mission" if mission_id in active_set else "") if source],
            "ranking_reasons": [
                "active mission with open Mission Slice" if mission_id in active_set else "open mission",
                f"started_at={entry.get('started_at') or ''}",
            ],
            "blocked_reasons": blocked_reasons,
            "mission_slice_path": str(slice_path),
        })

    candidates.sort(key=lambda item: (1 if item["blocked_reasons"] else 0, 0 if item["mission_id"] in active_set else 1, item["mission_id"]))
    return {
        "status": status_from_findings(findings),
        "runtime_layout": layout,
        "candidates": candidates,
        "requires_selection": len(candidates) > 1,
        "state_summary": {
            "active_count": len((status_payload.get("missions") or {}).get("active") or []),
            "open_count": len((status_payload.get("missions") or {}).get("open") or []),
            "ready_node_count": len((status_payload.get("work_graph") or {}).get("ready_nodes") or []),
            "blocked_node_count": len((status_payload.get("work_graph") or {}).get("blocked_nodes") or []),
        },
        "consistency_findings": findings,
    }
