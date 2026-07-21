from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.control_state import as_str_list
from harness_cli_core.domain.manifest import load_manifest
from harness_cli_core.domain.mission import (
    MissionStatusFilters,
    build_mission_new_id_payload,
    build_mission_status_payload,
    close_mission,
    complete_mission_stage,
    create_mission_slice,
    initialize_mission_runtime,
    reset_mission_stage,
    update_mission_stage,
)
from harness_cli_core.domain.mission_documents import (
    mission_document_candidates,
    mission_document_item,
    supported_document_types,
)
from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_paths import load_runtime_config, mission_status_path, relpath, resolve_path


COMMON_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = COMMON_ROOT / "skills"
WORK_GRAPH_SCRIPTS = SKILLS_ROOT / "work-graph" / "scripts"


def work_graph_nodes_by_id(root: Path) -> tuple[dict[str, dict[str, Any]], str | None]:
    if str(WORK_GRAPH_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))
    from work_graph_lib import load_nodes, resolve_graph_root

    nodes, _paths, findings = load_nodes(resolve_graph_root(root))
    if findings:
        return nodes, "; ".join(item.message for item in findings)
    return nodes, None


def load_graph(root: Path) -> tuple[Path, dict[str, dict[str, Any]], dict[str, Path], str | None]:
    if str(WORK_GRAPH_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))
    from work_graph_lib import load_nodes, resolve_graph_root

    graph_root = resolve_graph_root(root)
    nodes, paths, findings = load_nodes(graph_root)
    if findings:
        return graph_root, nodes, paths, "; ".join(item.message for item in findings)
    return graph_root, nodes, paths, None


def write_graph_views(graph_root: Path, nodes: dict[str, dict[str, Any]]) -> None:
    if str(WORK_GRAPH_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))
    from work_graph_lib import write_views

    write_views(graph_root, nodes)


def run_graph_check(root: Path) -> tuple[int, str]:
    check_script = SKILLS_ROOT / "work-graph" / "scripts" / "check_graph_consistency.py"
    result = subprocess.run(
        [sys.executable, str(check_script), "--root", str(root), "--json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.returncode, result.stdout


def resolve_lane_stage(root: Path, action_name: str) -> tuple[str, str, dict[str, Any] | None]:
    if str(WORK_GRAPH_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))
    from work_graph_lib import lane_action_registry, lane_of_stage, lane_stage_for_node

    config = load_runtime_config(root)
    actions = lane_action_registry(root)
    if action_name in actions:
        action = actions[action_name]
        return action_name, str(action.get("stage") or ""), action
    lane = lane_of_stage(config, action_name)
    if lane:
        resolved_lane, stage, action = lane_stage_for_node(config, {"id": "<mission-slice>", "lane": lane, "stage": action_name})
        return resolved_lane, stage, action
    return "", "", None


def validate_graph_operation_for_lane(operation: dict[str, Any], lane_action: dict[str, Any]) -> str | None:
    if str(WORK_GRAPH_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))
    from work_graph_lib import Finding, validate_graph_operation_structure, validate_operation_against_profile

    structure_errors = validate_graph_operation_structure(operation)
    if structure_errors:
        return "; ".join(structure_errors)
    findings: list[Finding] = []
    validate_operation_against_profile(operation, lane_action, findings)
    if findings:
        return "; ".join(item.message for item in findings)
    return None


def mission_status_filters(args: argparse.Namespace) -> MissionStatusFilters:
    return MissionStatusFilters(
        mission=args.mission,
        active=bool(args.active),
        open_only=bool(args.open_only),
        status_filter=list(args.status_filter or []),
        current_stage=list(args.current_stage or []),
        stage=list(args.stage or []),
        stage_status=list(args.stage_status or []),
        ids_only=bool(args.ids_only),
    )


def cmd_mission_init(args: argparse.Namespace) -> int:
    return emit_payload(args, initialize_mission_runtime(Path(root_arg(args)), replace=bool(args.replace)))


def cmd_mission_create_slice(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    objective = (getattr(args, "objective", None) or "").strip()
    title = (getattr(args, "title", None) or "").strip()
    if objective and title and objective != title:
        return emit_payload(args, fail_payload("mission.create_slice", "conflicting_objective", "--objective and --title must match when both are provided"))
    objective = objective or title
    operation_name = args.operation or ""
    operation_manifest = args.graph_operation_manifest or args.graph_operation
    if args.graph_operation and not args.graph_operation_manifest:
        candidate = Path(args.graph_operation).expanduser()
        if not candidate.suffix and not candidate.is_absolute() and not (root / candidate).exists():
            operation_name = args.graph_operation
            operation_manifest = None
    operation_path = resolve_path(root, operation_manifest)
    graph_operation = None
    if operation_path:
        if not operation_path.exists():
            return emit_payload(args, fail_payload("mission.create_slice", "missing_graph_operation", f"graph operation manifest not found: {operation_path}"))
        graph_operation = load_manifest(operation_path)
        if not graph_operation:
            return emit_payload(args, fail_payload("mission.create_slice", "invalid_graph_operation", f"graph operation manifest is empty or invalid: {operation_path}"))
    return emit_payload(
        args,
        create_mission_slice(
            root,
            mission_id=args.mission,
            lane_action_name=args.lane_action,
            primary_nodes=as_str_list(args.primary_node),
            related_nodes=as_str_list(args.related_node),
            input_nodes=as_str_list(args.input_node),
            output_nodes=as_str_list(args.output_node),
            graph_operation=graph_operation,
            requested_operation=operation_name,
            objective=objective,
            replace=bool(args.replace),
            resolve_lane_stage=lambda action_name: resolve_lane_stage(root, action_name),
            validate_graph_operation=validate_graph_operation_for_lane,
            work_graph_nodes_by_id=lambda: work_graph_nodes_by_id(root),
            today_value=dt.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d"),
        ),
    )


def cmd_mission_reset_stage(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    now = dt.datetime.now(ZoneInfo("Asia/Shanghai"))
    return emit_payload(
        args,
        reset_mission_stage(
            root,
            args.mission,
            args.stage,
            as_str_list(args.primary_node),
            as_str_list(args.related_node),
            args.output_node_policy,
            args.preserve_stage_history,
            args.preserve_checkpoints,
            args.reason,
            resolve_lane_stage=lambda stage: resolve_lane_stage(root, stage),
            load_graph=lambda: load_graph(root),
            write_views=write_graph_views,
            run_graph_check=lambda: run_graph_check(root),
            now_value=now.isoformat(),
            today_value=now.strftime("%Y-%m-%d"),
        ),
    )


def cmd_mission_status(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    status_path = mission_status_path(root)
    if not status_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "mission.status",
                "mission_status_uninitialized",
                f"mission-status file not found: {relpath(root, status_path)}; run 'harness mission init' to initialize",
            ),
        )
    status = load_yaml(status_path)
    return emit_payload(
        args,
        build_mission_status_payload(root, status, mission_status_filters(args), lambda: work_graph_nodes_by_id(root)),
    )


def cmd_mission_stage_start(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    return emit_payload(args, update_mission_stage(root, args.mission, args.stage, "in-progress", lambda: work_graph_nodes_by_id(root)))


def cmd_mission_stage_complete(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    return emit_payload(args, complete_mission_stage(root, args.mission, args.stage, lambda: work_graph_nodes_by_id(root)))


def cmd_mission_close(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    return emit_payload(
        args,
        close_mission(
            root,
            args.mission,
            args.strategy,
            today_value=dt.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d"),
            pr_url=getattr(args, "pr_url", None),
            kept_reason=getattr(args, "kept_reason", None),
        ),
    )


def cmd_mission_new_id(args: argparse.Namespace) -> int:
    date_str = getattr(args, "date", None) or dt.datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
    return emit_payload(args, build_mission_new_id_payload(getattr(args, "slug", None) or "", date_str))


def cmd_mission_document(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    document_type = str(args.type or "").strip()
    candidates = mission_document_candidates(args.mission, document_type)
    if not candidates:
        payload = fail_payload(
            "mission.document",
            "unknown_document_type",
            f"unknown document type: {document_type}",
        )
        payload["mission_id"] = args.mission
        payload["document_type"] = document_type
        payload["supported_types"] = supported_document_types()
        return emit_payload(args, payload)

    item = mission_document_item(root, args.mission, document_type)
    exists = bool(item["exists"])
    payload = {
        "status": "PASS" if exists else "FAIL",
        "control": "mission.document",
        "mission_id": args.mission,
        "document_type": document_type,
        "path": item["path"],
        "exists": exists,
        "candidates": item["candidates"],
        "rule": "harness-runtime/harness/artifacts/<mission-id>/<stage-or-domain>/<document-file>",
        "findings": []
        if exists
        else [
            {
                "level": "FAIL",
                "code": "document_missing",
                "message": item["path"],
            }
        ],
    }
    if not getattr(args, "json", False):
        print(item["path"])
        return 0 if exists else 1
    return emit_payload(args, payload)
