#!/usr/bin/env python3
"""Apply deterministic Work Graph operations to node facts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

from check_graph_consistency import run as check_graph_consistency
from work_graph_lib import (
    Finding,
    LEGACY_LANE_STAGE,
    as_str_list,
    finding_dict,
    load_nodes,
    load_yaml,
    now,
    resolve_graph_root,
    status_from_findings,
    write_views,
    write_yaml,
)


TRANSACTION_LOCK_NAME = "control-plane.lock"


def normalize_legacy_lane_stage(node: dict[str, Any]) -> dict[str, Any]:
    lane = str(node.get("lane") or "")
    if lane in LEGACY_LANE_STAGE:
        mapped_lane, mapped_stage = LEGACY_LANE_STAGE[lane]
        node = {**node, "lane": mapped_lane}
        node.setdefault("stage", mapped_stage)
    return node


def normalize_legacy_operation(operation: dict[str, Any]) -> dict[str, Any]:
    operation = {**operation}
    operation_type = str(operation.get("type") or "")
    if operation_type == "advance_lane":
        from_lane = str(operation.get("from_lane") or "")
        to_lane = str(operation.get("to_lane") or "")
        mapped_from = LEGACY_LANE_STAGE.get(from_lane)
        mapped_to = LEGACY_LANE_STAGE.get(to_lane)
        if mapped_from and mapped_to:
            from_new_lane, from_stage = mapped_from
            to_new_lane, to_stage = mapped_to
            if from_new_lane == to_new_lane:
                operation.update({"type": "advance_stage", "lane": from_new_lane, "from_stage": from_stage, "to_stage": to_stage})
                operation.pop("from_lane", None)
                operation.pop("to_lane", None)
            else:
                operation.update({"from_lane": from_new_lane, "to_lane": to_new_lane, "to_stage": to_stage})
    if operation_type in {"create_node"} and isinstance(operation.get("target"), dict):
        operation["target"] = normalize_legacy_lane_stage(operation["target"])
    if operation_type == "split_node" and isinstance(operation.get("children"), list):
        operation["children"] = [normalize_legacy_lane_stage(child) if isinstance(child, dict) else child for child in operation["children"]]
    if operation_type == "merge_nodes" and isinstance(operation.get("target"), dict):
        operation["target"] = normalize_legacy_lane_stage(operation["target"])
    if operation_type == "batch" and isinstance(operation.get("operations"), list):
        operation["operations"] = [normalize_legacy_operation(child) if isinstance(child, dict) else child for child in operation["operations"]]
    return operation


def append_unique(values: list[str], additions: list[str]) -> list[str]:
    result = [str(item) for item in values]
    for item in additions:
        item = str(item)
        if item not in result:
            result.append(item)
    return result


def runtime_config(root: Path) -> dict[str, Any]:
    for path in (
        root / "harness-runtime" / "config" / "harness.yaml",
        root / "package" / "harness-runtime" / "config" / "harness.yaml",
    ):
        config = load_yaml(path)
        if config:
            return config
    return {}


def node_kind_directory(root: Path, kind: str) -> str:
    config = runtime_config(root)
    work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
    node_kinds = work_graph.get("node_kinds") if isinstance(work_graph.get("node_kinds"), dict) else {}
    spec = node_kinds.get(kind) if isinstance(node_kinds.get(kind), dict) else {}
    return str(spec.get("directory") or f"{kind}s")


def node_path(root: Path, graph_root: Path, node: dict[str, Any]) -> Path:
    kind = str(node.get("kind") or "nodes")
    directory = node_kind_directory(root, kind)
    return graph_root / "nodes" / directory / f"{node['id']}.yaml"


def operation_trace(node: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    trace = node.get("trace") if isinstance(node.get("trace"), dict) else {}
    if operation.get("mission_id"):
        trace["updated_by_mission"] = str(operation["mission_id"])
    trace["last_graph_operation"] = str(operation.get("operation_id") or "")
    return trace


def apply_create_node(root: Path, operation: dict[str, Any], graph_root: Path, nodes: dict[str, dict[str, Any]], paths: dict[str, Path], findings: list[Finding]) -> None:
    """Create a brand-new seed node with no precondition on existing graph state.

    Bootstraps an empty Work Graph; every other operation requires existing nodes.
    """
    target = operation.get("target")
    if not isinstance(target, dict):
        findings.append(Finding("FAIL", "missing_create_target", "create_node requires target"))
        return
    node_id = str(target.get("id") or "")
    if not node_id or not target.get("kind") or not target.get("title") or not target.get("lane") or not target.get("stage") or not target.get("status"):
        findings.append(Finding("FAIL", "invalid_create_target", "create_node target requires id, kind, title, lane, stage, status"))
        return
    if node_id in nodes:
        findings.append(Finding("FAIL", "duplicate_node_id", f"create_node target already exists: {node_id}"))
        return
    relations = target.get("relations") if isinstance(target.get("relations"), dict) else {}
    prepared = {
        **target,
        "inputs": as_str_list(target.get("inputs")),
        "outputs": as_str_list(target.get("outputs")),
        "relations": relations,
        "updated_at": now(),
    }
    trace = prepared.get("trace") if isinstance(prepared.get("trace"), dict) else {}
    if operation.get("mission_id"):
        trace["created_by_mission"] = str(operation["mission_id"])
        trace["updated_by_mission"] = str(operation["mission_id"])
    trace["last_graph_operation"] = str(operation.get("operation_id") or "")
    prepared["trace"] = trace
    write_yaml(node_path(root, graph_root, prepared), prepared)


def apply_advance_lane(operation: dict[str, Any], nodes: dict[str, dict[str, Any]], paths: dict[str, Path], findings: list[Finding]) -> None:
    node_id = str(operation.get("node_id") or "")
    if node_id not in nodes:
        findings.append(Finding("FAIL", "unknown_node", f"advance_lane references unknown node: {node_id}"))
        return
    node = nodes[node_id]
    from_lane = str(operation.get("from_lane") or "")
    to_lane = str(operation.get("to_lane") or "")
    if not to_lane:
        findings.append(Finding("FAIL", "missing_to_lane", "advance_lane requires to_lane"))
        return
    if from_lane and node.get("lane") != from_lane:
        findings.append(Finding("FAIL", "lane_precondition_failed", f"{node_id} lane is {node.get('lane')}, expected {from_lane}"))
        return
    node["lane"] = to_lane
    if operation.get("to_stage"):
        node["stage"] = str(operation["to_stage"])
    if operation.get("status"):
        node["status"] = str(operation["status"])
    node["updated_at"] = now()
    node["trace"] = operation_trace(node, operation)
    write_yaml(paths[node_id], node)


def apply_advance_stage(operation: dict[str, Any], nodes: dict[str, dict[str, Any]], paths: dict[str, Path], findings: list[Finding]) -> None:
    node_id = str(operation.get("node_id") or "")
    if node_id not in nodes:
        findings.append(Finding("FAIL", "unknown_node", f"advance_stage references unknown node: {node_id}"))
        return
    node = nodes[node_id]
    lane = str(operation.get("lane") or "")
    from_stage = str(operation.get("from_stage") or "")
    to_stage = str(operation.get("to_stage") or "")
    if not to_stage:
        findings.append(Finding("FAIL", "missing_to_stage", "advance_stage requires to_stage"))
        return
    if lane and node.get("lane") != lane:
        findings.append(Finding("FAIL", "lane_precondition_failed", f"{node_id} lane is {node.get('lane')}, expected {lane}"))
        return
    if from_stage and node.get("stage") != from_stage:
        findings.append(Finding("FAIL", "stage_precondition_failed", f"{node_id} stage is {node.get('stage')}, expected {from_stage}"))
        return
    node["stage"] = to_stage
    if operation.get("status"):
        node["status"] = str(operation["status"])
    node["updated_at"] = now()
    node["trace"] = operation_trace(node, operation)
    write_yaml(paths[node_id], node)


def apply_split_node(root: Path, operation: dict[str, Any], graph_root: Path, nodes: dict[str, dict[str, Any]], paths: dict[str, Path], findings: list[Finding]) -> None:
    node_id = str(operation.get("node_id") or "")
    parent = nodes.get(node_id)
    if parent is None:
        findings.append(Finding("FAIL", "unknown_node", f"split_node references unknown node: {node_id}"))
        return
    children = operation.get("children")
    if not isinstance(children, list) or not children:
        findings.append(Finding("FAIL", "missing_split_children", "split_node requires non-empty children"))
        return
    child_ids: list[str] = []
    prepared_children: list[dict[str, Any]] = []
    for child in children:
        if not isinstance(child, dict):
            findings.append(Finding("FAIL", "invalid_split_child", "split_node children must be objects"))
            continue
        child_id = str(child.get("id") or "")
        if not child_id or not child.get("kind") or not child.get("title") or not child.get("lane") or not child.get("stage") or not child.get("status"):
            findings.append(Finding("FAIL", "invalid_split_child", "split_node child requires id, kind, title, lane, stage, status"))
            continue
        if child_id in nodes or child_id in child_ids:
            findings.append(Finding("FAIL", "duplicate_split_child", f"split_node child already exists: {child_id}"))
            continue
        relations = child.get("relations") if isinstance(child.get("relations"), dict) else {}
        relations["split_from"] = node_id
        prepared = {
            **child,
            "inputs": append_unique(as_str_list(child.get("inputs")), [node_id]),
            "outputs": as_str_list(child.get("outputs")),
            "relations": relations,
            "updated_at": now(),
        }
        prepared["trace"] = operation_trace(prepared, operation)
        child_ids.append(child_id)
        prepared_children.append(prepared)
    if findings:
        return
    parent["outputs"] = append_unique(as_str_list(parent.get("outputs")), child_ids)
    parent["updated_at"] = now()
    parent["trace"] = operation_trace(parent, operation)
    write_yaml(paths[node_id], parent)
    for child in prepared_children:
        write_yaml(node_path(root, graph_root, child), child)


def apply_merge_nodes(root: Path, operation: dict[str, Any], graph_root: Path, nodes: dict[str, dict[str, Any]], paths: dict[str, Path], findings: list[Finding]) -> None:
    node_ids = as_str_list(operation.get("node_ids"))
    if len(node_ids) < 2:
        findings.append(Finding("FAIL", "invalid_merge_sources", "merge_nodes requires at least two node_ids"))
        return
    missing = [node_id for node_id in node_ids if node_id not in nodes]
    if missing:
        findings.append(Finding("FAIL", "unknown_node", f"merge_nodes references unknown nodes: {', '.join(missing)}"))
        return
    target = operation.get("target")
    if not isinstance(target, dict):
        findings.append(Finding("FAIL", "missing_merge_target", "merge_nodes requires target"))
        return
    target_id = str(target.get("id") or "")
    if not target_id or not target.get("kind") or not target.get("title") or not target.get("lane") or not target.get("stage") or not target.get("status"):
        findings.append(Finding("FAIL", "invalid_merge_target", "merge_nodes target requires id, kind, title, lane, stage, status"))
        return
    if target_id in nodes:
        findings.append(Finding("FAIL", "duplicate_merge_target", f"merge_nodes target already exists: {target_id}"))
        return
    relations = target.get("relations") if isinstance(target.get("relations"), dict) else {}
    relations["merged_from"] = node_ids
    prepared_target = {
        **target,
        "inputs": append_unique(as_str_list(target.get("inputs")), node_ids),
        "outputs": as_str_list(target.get("outputs")),
        "relations": relations,
        "updated_at": now(),
    }
    prepared_target["trace"] = operation_trace(prepared_target, operation)
    for node_id in node_ids:
        source = nodes[node_id]
        source["outputs"] = append_unique(as_str_list(source.get("outputs")), [target_id])
        source_relations = source.get("relations") if isinstance(source.get("relations"), dict) else {}
        source_relations["merged_into"] = target_id
        source["relations"] = source_relations
        source["updated_at"] = now()
        source["trace"] = operation_trace(source, operation)
        write_yaml(paths[node_id], source)
    write_yaml(node_path(root, graph_root, prepared_target), prepared_target)


def apply_terminal_lane(operation: dict[str, Any], nodes: dict[str, dict[str, Any]], paths: dict[str, Path], findings: list[Finding], lane: str, reason_key: str) -> None:
    node_id = str(operation.get("node_id") or "")
    node = nodes.get(node_id)
    if node is None:
        findings.append(Finding("FAIL", "unknown_node", f"{operation.get('type')} references unknown node: {node_id}"))
        return
    node["status"] = lane
    node["updated_at"] = now()
    trace = operation_trace(node, operation)
    if operation.get("reason"):
        trace[reason_key] = str(operation["reason"])
    node["trace"] = trace
    write_yaml(paths[node_id], node)


def apply_supersede_node(operation: dict[str, Any], nodes: dict[str, dict[str, Any]], paths: dict[str, Path], findings: list[Finding]) -> None:
    node_id = str(operation.get("node_id") or "")
    replacement = nodes.get(node_id)
    if replacement is None:
        findings.append(Finding("FAIL", "unknown_node", f"supersede_node references unknown replacement node: {node_id}"))
        return
    superseded_ids = as_str_list(operation.get("node_ids")) or as_str_list(operation.get("supersedes"))
    if not superseded_ids:
        findings.append(Finding("FAIL", "missing_superseded_nodes", "supersede_node requires node_ids or supersedes"))
        return
    missing = [item for item in superseded_ids if item not in nodes]
    if missing:
        findings.append(Finding("FAIL", "unknown_node", f"supersede_node references unknown nodes: {', '.join(missing)}"))
        return

    replacement_relations = replacement.get("relations") if isinstance(replacement.get("relations"), dict) else {}
    replacement_relations["supersedes"] = append_unique(as_str_list(replacement_relations.get("supersedes")), superseded_ids)
    replacement["relations"] = replacement_relations
    replacement["updated_at"] = now()
    replacement["trace"] = operation_trace(replacement, operation)
    write_yaml(paths[node_id], replacement)

    for superseded_id in superseded_ids:
        superseded = nodes[superseded_id]
        relations = superseded.get("relations") if isinstance(superseded.get("relations"), dict) else {}
        relations["superseded_by"] = node_id
        superseded["relations"] = relations
        superseded["status"] = "done"
        current_artifact = superseded.get("artifact") if isinstance(superseded.get("artifact"), dict) else {}
        artifact_state = current_artifact.get("artifact_state") if isinstance(current_artifact.get("artifact_state"), dict) else {}
        if current_artifact:
            artifact_state.update({"status": "superseded", "superseded_by": node_id, "superseded_by_mission": str(operation.get("mission_id") or "")})
            current_artifact["artifact_state"] = artifact_state
            superseded["artifact"] = current_artifact
        superseded["updated_at"] = now()
        superseded["trace"] = operation_trace(superseded, operation)
        write_yaml(paths[superseded_id], superseded)


def boolish(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1", "required"}:
            return True
        if normalized in {"false", "no", "0", "optional", ""}:
            return False
    return default


def safe_rel_path(value: Any, findings: list[Finding], field: str) -> Path | None:
    text = str(value or "")
    if not text:
        findings.append(Finding("FAIL", "invalid_supplementary_artifact", f"supplementary_artifacts.{field} is required"))
        return None
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        findings.append(Finding("FAIL", "supplementary_artifact_path_escape", f"supplementary_artifacts.{field} must be a relative path inside the harness workspace"))
        return None
    return path


def copy_supplementary_artifacts(root: Path, artifact: dict[str, Any], findings: list[Finding]) -> list[dict[str, str]]:
    specs = artifact.get("supplementary_artifacts")
    if not isinstance(specs, list):
        return []
    copied: list[dict[str, str]] = []
    for index, spec in enumerate(specs, start=1):
        if not isinstance(spec, dict):
            findings.append(Finding("FAIL", "invalid_supplementary_artifact", "supplementary_artifacts entries must be objects"))
            continue
        required = boolish(spec.get("required"), default=True)
        source_glob = spec.get("source_stage_artifact_glob")
        if source_glob:
            glob_rel = safe_rel_path(source_glob, findings, "source_stage_artifact_glob")
            canonical_dir_rel = safe_rel_path(spec.get("canonical_artifact_dir"), findings, "canonical_artifact_dir")
            if glob_rel is None or canonical_dir_rel is None:
                continue
            strip_prefix = spec.get("strip_source_prefix")
            strip_root = root / strip_prefix if strip_prefix else None
            if strip_root is not None:
                strip_rel = safe_rel_path(strip_prefix, findings, "strip_source_prefix")
                if strip_rel is None:
                    continue
                strip_root = root / strip_rel
            matches = sorted(path for path in root.glob(str(glob_rel)) if path.is_file())
            if required and not matches:
                findings.append(Finding("FAIL", "missing_supplementary_artifact", f"Required supplementary artifact glob matched no files: {source_glob}"))
                continue
            for source in matches:
                try:
                    relative_name = source.relative_to(strip_root) if strip_root is not None else Path(source.name)
                except ValueError:
                    findings.append(Finding("FAIL", "supplementary_artifact_strip_mismatch", f"{source} is not under strip_source_prefix {strip_prefix}"))
                    continue
                canonical = root / canonical_dir_rel / relative_name
                canonical.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, canonical)
                copied.append(
                    {
                        "id": str(spec.get("id") or f"supplementary-{index}"),
                        "source_stage_artifact": str(source.relative_to(root)),
                        "canonical_artifact": str(canonical.relative_to(root)),
                    }
                )
            continue

        source_rel = safe_rel_path(spec.get("source_stage_artifact"), findings, "source_stage_artifact")
        canonical_rel = safe_rel_path(spec.get("canonical_artifact"), findings, "canonical_artifact")
        if source_rel is None or canonical_rel is None:
            continue
        source = root / source_rel
        canonical = root / canonical_rel
        if not source.exists():
            if required:
                findings.append(Finding("FAIL", "missing_supplementary_artifact", f"Required supplementary artifact not found: {source_rel}"))
            continue
        if not source.is_file():
            findings.append(Finding("FAIL", "invalid_supplementary_artifact", f"Supplementary artifact must be a file: {source_rel}"))
            continue
        canonical.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, canonical)
        copied.append(
            {
                "id": str(spec.get("id") or f"supplementary-{index}"),
                "source_stage_artifact": str(source_rel),
                "canonical_artifact": str(canonical_rel),
            }
        )
    return copied


def promote_artifact(root: Path, operation: dict[str, Any], nodes: dict[str, dict[str, Any]], paths: dict[str, Path], findings: list[Finding]) -> None:
    artifact = operation.get("work_graph_artifact")
    if not isinstance(artifact, dict):
        return
    node_id = str(artifact.get("node_id") or operation.get("node_id") or "")
    if not node_id:
        findings.append(Finding("FAIL", "invalid_work_graph_artifact", "work_graph_artifact missing node_id"))
        return
    node = nodes.get(node_id)
    if node is None:
        findings.append(Finding("FAIL", "unknown_node", f"work_graph_artifact references unknown node: {node_id}"))
        return
    required = ("artifact_version", "promoted_by_mission", "source_stage_artifact", "canonical_artifact")
    for field in required:
        if not artifact.get(field):
            findings.append(Finding("FAIL", "invalid_work_graph_artifact", f"work_graph_artifact missing {field}"))
    if any(item.level == "FAIL" for item in findings):
        return
    source = root / str(artifact["source_stage_artifact"])
    canonical = root / str(artifact["canonical_artifact"])
    if not source.exists():
        findings.append(Finding("FAIL", "source_artifact_missing", f"Source stage artifact not found: {artifact['source_stage_artifact']}"))
        return
    canonical.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, canonical)
    source_contract = artifact.get("source_contract_artifact")
    canonical_contract = artifact.get("canonical_contract")
    if source_contract or canonical_contract:
        if not (source_contract and canonical_contract):
            findings.append(Finding("FAIL", "invalid_work_graph_artifact", "source_contract_artifact and canonical_contract must be provided together"))
            return
        source_contract_path = root / str(source_contract)
        canonical_contract_path = root / str(canonical_contract)
        if not source_contract_path.exists():
            findings.append(Finding("FAIL", "source_contract_missing", f"Source contract artifact not found: {source_contract}"))
            return
        canonical_contract_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_contract_path, canonical_contract_path)
    supplementary_artifacts = copy_supplementary_artifacts(root, artifact, findings)
    if any(item.level == "FAIL" for item in findings):
        return
    current_artifact = node.get("artifact") if isinstance(node.get("artifact"), dict) else {}
    history = current_artifact.get("history") if isinstance(current_artifact.get("history"), list) else []
    if current_artifact:
        history.append({key: value for key, value in current_artifact.items() if key != "history"})
    artifact_state = artifact.get("artifact_state") if isinstance(artifact.get("artifact_state"), dict) else {}
    artifact_state = {
        "status": str(artifact_state.get("status") or "accepted"),
        "accepted_by_mission": str(artifact_state.get("accepted_by_mission") or artifact["promoted_by_mission"]),
        "accepted_at": now(),
        "supersedes": as_str_list(artifact_state.get("supersedes")),
        "superseded_by": artifact_state.get("superseded_by"),
    }
    node["artifact"] = {
        "node_id": node_id,
        "artifact_version": str(artifact["artifact_version"]),
        "promoted_by_mission": str(artifact["promoted_by_mission"]),
        "source_stage_artifact": str(artifact["source_stage_artifact"]),
        "canonical_artifact": str(artifact["canonical_artifact"]),
        "source_contract_artifact": str(source_contract or ""),
        "canonical_contract": str(canonical_contract or ""),
        "supplementary_artifacts": supplementary_artifacts,
        "artifact_state": artifact_state,
        "history": history,
    }
    changelog = canonical.parent / "changelog.md"
    if not changelog.exists():
        changelog.write_text("# Changelog\n\n", encoding="utf-8")
    reason = str(artifact.get("change_reason") or operation.get("reason") or "promoted by Stage Gate")
    with changelog.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n".join(
                [
                    f"## {artifact['artifact_version']} - {artifact['promoted_by_mission']}",
                    "",
                    f"- promoted_at: {now()}",
                    f"- source: {artifact['source_stage_artifact']}",
                    f"- canonical: {artifact['canonical_artifact']}",
                    f"- reason: {reason}",
                    "",
                ]
            )
        )
    write_yaml(paths[node_id], node)


def apply_operation_payload(root: Path, graph_root: Path, operation: dict[str, Any], findings: list[Finding]) -> None:
    operation = normalize_legacy_operation(operation)
    operation_type = str(operation.get("type") or "")
    if any(item.level == "FAIL" for item in findings):
        return
    nodes, paths, load_findings = load_nodes(graph_root)
    findings.extend(load_findings)
    if any(item.level == "FAIL" for item in load_findings):
        return
    initial_failures = sum(1 for item in findings if item.level == "FAIL")
    if operation_type == "create_node":
        apply_create_node(root, operation, graph_root, nodes, paths, findings)
    elif operation_type == "advance_stage":
        apply_advance_stage(operation, nodes, paths, findings)
    elif operation_type == "advance_lane":
        apply_advance_lane(operation, nodes, paths, findings)
    elif operation_type == "split_node":
        apply_split_node(root, operation, graph_root, nodes, paths, findings)
    elif operation_type == "merge_nodes":
        apply_merge_nodes(root, operation, graph_root, nodes, paths, findings)
    elif operation_type == "block_node":
        apply_terminal_lane(operation, nodes, paths, findings, "blocked", "block_reason")
    elif operation_type == "defer_node":
        apply_terminal_lane(operation, nodes, paths, findings, "deferred", "defer_reason")
    elif operation_type == "supersede_node":
        apply_supersede_node(operation, nodes, paths, findings)
    elif operation_type == "batch":
        operations = operation.get("operations")
        if not isinstance(operations, list) or not operations:
            findings.append(Finding("FAIL", "invalid_batch_operation", "batch operation requires non-empty operations"))
            return
        parent_id = str(operation.get("operation_id") or "batch")
        for index, child in enumerate(operations, start=1):
            if not isinstance(child, dict):
                findings.append(Finding("FAIL", "invalid_batch_operation", "batch operations must be objects"))
                return
            child_operation = {**child}
            child_operation.setdefault("operation_id", f"{parent_id}__{index}")
            if operation.get("mission_id"):
                child_operation.setdefault("mission_id", operation.get("mission_id"))
            apply_operation_payload(root, graph_root, child_operation, findings)
            if any(item.level == "FAIL" for item in findings):
                return
    else:
        findings.append(Finding("FAIL", "unsupported_operation", f"Unsupported graph operation type: {operation_type}"))
    if sum(1 for item in findings if item.level == "FAIL") == initial_failures:
        nodes, paths, load_findings = load_nodes(graph_root)
        findings.extend(load_findings)
        if not any(item.level == "FAIL" for item in load_findings):
            promote_artifact(root, operation, nodes, paths, findings)


def file_snapshot(root: Path, rel_roots: list[Path]) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for rel_root in rel_roots:
        base = root / rel_root
        if not base.exists():
            continue
        if base.is_file():
            snapshot[str(base.relative_to(root))] = base.read_bytes()
            continue
        for path in sorted(item for item in base.rglob("*") if item.is_file()):
            snapshot[str(path.relative_to(root))] = path.read_bytes()
    return snapshot


def changed_files(before: dict[str, bytes], after: dict[str, bytes]) -> list[str]:
    keys = sorted(set(before) | set(after))
    return [key for key in keys if before.get(key) != after.get(key)]


def transaction_root(root: Path) -> Path:
    return root / "harness-runtime" / "harness" / "state" / "transactions"


def transaction_id(operation: dict[str, Any]) -> str:
    raw_id = str(operation.get("operation_id") or "operation")
    safe_id = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in raw_id).strip("-") or "operation"
    return f"TX-{now().replace(':', '').replace('.', '-')}-{safe_id}"


def transaction_journal_path(tx_root: Path, tx_id: str) -> Path:
    return tx_root / f"{tx_id}.json"


def write_transaction_journal(path: Path, journal: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def add_transaction_step(journal: dict[str, Any], step: dict[str, Any]) -> None:
    steps = journal.setdefault("steps", [])
    if isinstance(steps, list):
        steps.append(step)


class ControlPlaneLock:
    def __init__(self, tx_root: Path, tx_id: str):
        self.path = tx_root / TRANSACTION_LOCK_NAME
        self.tx_id = tx_id
        self.fd: int | None = None

    def __enter__(self) -> "ControlPlaneLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError(f"control-plane lock already exists: {self.path}") from exc
        os.write(self.fd, self.tx_id.encode("utf-8"))
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        self.path.unlink(missing_ok=True)


def copy_tree_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def cleanup_staging_root(root: Path, staging_root: Path) -> dict[str, Any]:
    step: dict[str, Any] = {
        "id": "cleanup_staging",
        "staging_root": str(staging_root.relative_to(root)),
    }
    if not staging_root.exists():
        step["status"] = "not_found"
        return step
    try:
        shutil.rmtree(staging_root)
    except OSError as exc:
        step["status"] = "failed"
        step["error"] = str(exc)
        return step
    step["status"] = "removed"
    return step


def staging_rel_roots(root: Path, extra_rel_roots: list[Path] | None = None) -> list[Path]:
    rels: list[Path] = []
    graph_root = resolve_graph_root(root)
    try:
        rels.append(graph_root.relative_to(root))
    except ValueError:
        pass
    rels.append(Path("harness-runtime") / "harness" / "work-graph" / "artifacts")
    for rel in (
        Path("harness-runtime") / "config",
        Path("package") / "harness-runtime" / "config",
    ):
        if (root / rel).exists():
            rels.append(rel)
    rels.extend(extra_rel_roots or [])
    result: list[Path] = []
    for rel in rels:
        if rel not in result:
            result.append(rel)
    return result


def prepare_staging_root(root: Path, operation_path: Path, staging_root: Path, rel_roots: list[Path]) -> Path:
    for rel in rel_roots:
        copy_tree_if_exists(root / rel, staging_root / rel)
    # Source stage artifacts are read during promotion. Copy only Harness stage
    # artifacts, not arbitrary project files.
    copy_tree_if_exists(root / "harness-runtime" / "harness" / "stages", staging_root / "harness-runtime" / "harness" / "stages")
    copy_tree_if_exists(root / "harness-runtime" / "harness" / "missions", staging_root / "harness-runtime" / "harness" / "missions")
    if operation_path.is_relative_to(root):
        operation_rel = operation_path.relative_to(root)
    else:
        operation_rel = Path("harness-runtime") / "harness" / "state" / "transactions" / "operation.yaml"
    copy_tree_if_exists(operation_path, staging_root / operation_rel)
    return staging_root / operation_rel


def snapshot_changed_files(root: Path, tx_dir: Path, files: list[str]) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    before_root = tx_dir / "before"
    for rel_text in files:
        rel = Path(rel_text)
        original = root / rel
        snapshot = before_root / rel
        item: dict[str, Any] = {"original": rel_text, "existed": original.exists()}
        if original.exists():
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, snapshot)
            item["before"] = str(snapshot.relative_to(root))
        snapshots.append(item)
    return snapshots


def commit_changed_files(staging_root: Path, root: Path, files: list[str]) -> list[str]:
    committed: list[str] = []
    for rel_text in files:
        rel = Path(rel_text)
        src = staging_root / rel
        dst = root / rel
        if not src.exists():
            if dst.exists():
                dst.unlink()
            committed.append(rel_text)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        committed.append(rel_text)
    return committed


def rollback_changed_files(root: Path, tx_dir: Path, snapshots: list[dict[str, Any]]) -> list[str]:
    restored: list[str] = []
    for item in snapshots:
        rel = Path(str(item["original"]))
        original = root / rel
        if item.get("existed"):
            before_rel = item.get("before")
            if not before_rel:
                raise RuntimeError(f"missing rollback snapshot for {rel}")
            before_path = root / str(before_rel)
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(before_path, original)
        elif original.exists():
            original.unlink()
        restored.append(str(rel))
    return restored


def validate_staged_tree(staging_root: Path) -> dict[str, Any]:
    return check_graph_consistency(staging_root)


def run_direct(root: Path, operation_path: Path) -> dict:
    graph_root = resolve_graph_root(root)
    operation = load_yaml(operation_path)
    findings: list[Finding] = []
    if not operation.get("operation_id"):
        findings.append(Finding("FAIL", "missing_operation_id", f"Operation missing operation_id: {operation_path}"))
    if not findings:
        apply_operation_payload(root, graph_root, operation, findings)
    if not any(item.level == "FAIL" for item in findings):
        nodes, _paths, load_findings = load_nodes(graph_root)
        findings.extend(load_findings)
        write_views(graph_root, nodes)
        log_path = graph_root / "operations.log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"applied_at": now(), "operation": operation}, ensure_ascii=False) + "\n")
    status = status_from_findings(findings)
    return {
        "status": status,
        "control": "work_graph_apply_operation",
        "graph_root": str(graph_root),
        "operation": operation.get("operation_id"),
        "findings": [finding_dict(item) for item in findings],
    }


def run_staged(
    root: Path,
    operation_path: Path,
    *,
    dry_run: bool,
    extra_rel_roots: list[Path] | None = None,
    operation_commit_rel: Path | None = None,
    after_stage: Callable[[Path, Path, dict[str, Any]], list[Finding] | None] | None = None,
) -> dict:
    operation = load_yaml(operation_path)
    tx_id = transaction_id(operation)
    tx_root = transaction_root(root)
    tx_dir = tx_root / tx_id
    staging_root = tx_dir / "staging"
    journal_path = transaction_journal_path(tx_root, tx_id)
    journal: dict[str, Any] = {
        "transaction_id": tx_id,
        "status": "planned",
        "started_at": now(),
        "ended_at": "",
        "mission_id": operation.get("mission_id"),
        "operation_id": operation.get("operation_id"),
        "staging_root": str(staging_root.relative_to(root)),
        "steps": [],
        "rollback": {"snapshots": []},
    }
    write_transaction_journal(journal_path, journal)
    rel_roots = staging_rel_roots(root, extra_rel_roots)
    before = file_snapshot(root, rel_roots)
    add_transaction_step(journal, {"id": "preflight", "inputs": [str(operation_path)]})
    write_transaction_journal(journal_path, journal)
    staged_operation = prepare_staging_root(root, operation_path, staging_root, rel_roots)
    payload = run_direct(staging_root, staged_operation)
    payload.update(
        {
            "staged": True,
            "dry_run": dry_run,
            "transaction_id": tx_id,
            "transaction_journal": str(journal_path.relative_to(root)),
            "staging_root": str(staging_root.relative_to(root)),
        }
    )
    if payload["status"] == "PASS" and operation_commit_rel is not None:
        commit_target = staging_root / operation_commit_rel
        commit_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged_operation, commit_target)
    if payload["status"] == "PASS" and after_stage is not None:
        extra_findings = after_stage(staging_root, staged_operation, payload) or []
        if extra_findings:
            payload.setdefault("findings", []).extend(finding_dict(item) for item in extra_findings)
            if any(item.level == "FAIL" for item in extra_findings):
                payload["status"] = "FAIL"
    after = file_snapshot(staging_root, rel_roots)
    files = changed_files(before, after)
    add_transaction_step(journal, {"id": "plan_changes", "change_set": files})
    journal["status"] = "staged"
    write_transaction_journal(journal_path, journal)

    staged_validation: dict[str, Any] | None = None
    if payload["status"] == "PASS":
        staged_validation = validate_staged_tree(staging_root)
        add_transaction_step(journal, {"id": "validate_staged_tree", "status": staged_validation.get("status"), "findings": staged_validation.get("findings") or []})
        write_transaction_journal(journal_path, journal)
        if staged_validation.get("status") == "FAIL":
            payload["status"] = "FAIL"
            payload.setdefault("findings", []).extend(staged_validation.get("findings") or [])

    payload.update(
        {
            "staged": True,
            "dry_run": dry_run,
            "changed_files": files,
            "staged_validation": staged_validation,
            "transaction_id": tx_id,
            "transaction_journal": str(journal_path.relative_to(root)),
            "staging_root": str(staging_root.relative_to(root)),
        }
    )
    if payload["status"] != "PASS":
        journal["status"] = "failed"
        journal["ended_at"] = now()
        write_transaction_journal(journal_path, journal)
        return payload
    if dry_run:
        add_transaction_step(journal, cleanup_staging_root(root, staging_root))
        journal["ended_at"] = now()
        write_transaction_journal(journal_path, journal)
        return payload

    snapshots: list[dict[str, Any]] = []
    try:
        with ControlPlaneLock(tx_root, tx_id):
            snapshots = snapshot_changed_files(root, tx_dir, files)
            journal["rollback"] = {"snapshots": snapshots}
            add_transaction_step(journal, {"id": "stage_files", "changed_files": files})
            write_transaction_journal(journal_path, journal)
            committed = commit_changed_files(staging_root, root, files)
            add_transaction_step(journal, {"id": "commit", "committed_files": committed})
            post_check = validate_staged_tree(root)
            add_transaction_step(journal, {"id": "post_commit_check", "status": post_check.get("status"), "findings": post_check.get("findings") or []})
            if post_check.get("status") == "FAIL":
                raise RuntimeError("post-commit graph consistency check failed")
            journal["status"] = "committed"
            journal["ended_at"] = now()
            write_transaction_journal(journal_path, journal)
        add_transaction_step(journal, cleanup_staging_root(root, staging_root))
        write_transaction_journal(journal_path, journal)
    except Exception as exc:
        rollback_status = "not_started"
        rollback_error = ""
        try:
            restored = rollback_changed_files(root, tx_dir, snapshots)
            rollback_status = "rolled_back"
            add_transaction_step(journal, {"id": "rollback", "restored_files": restored})
            graph_check = validate_staged_tree(root)
            add_transaction_step(journal, {"id": "rollback_graph_check", "status": graph_check.get("status"), "findings": graph_check.get("findings") or []})
        except Exception as rollback_exc:  # pragma: no cover - defensive boundary
            rollback_status = "failed"
            rollback_error = str(rollback_exc)
        journal["status"] = "rolled_back" if rollback_status == "rolled_back" else "failed"
        journal["ended_at"] = now()
        journal["error"] = str(exc)
        if rollback_error:
            journal["rollback_error"] = rollback_error
        write_transaction_journal(journal_path, journal)
        payload["status"] = "FAIL" if rollback_status == "rolled_back" else "BLOCKED"
        payload.setdefault("findings", []).append(
            finding_dict(
                Finding(
                    "FAIL" if rollback_status == "rolled_back" else "BLOCKED",
                    "transaction_commit_failed",
                    f"{exc}; rollback={rollback_status}{': ' + rollback_error if rollback_error else ''}",
                )
            )
        )
        return payload
    return payload


def run(
    root: Path,
    operation_path: Path,
    *,
    dry_run: bool = False,
    staged: bool = False,
    extra_rel_roots: list[Path] | None = None,
    operation_commit_rel: Path | None = None,
    after_stage: Callable[[Path, Path, dict[str, Any]], list[Finding] | None] | None = None,
) -> dict:
    if dry_run or staged:
        return run_staged(
            root,
            operation_path,
            dry_run=dry_run,
            extra_rel_roots=extra_rel_roots,
            operation_commit_rel=operation_commit_rel,
            after_stage=after_stage,
        )
    rel_roots = staging_rel_roots(root, extra_rel_roots)
    before = file_snapshot(root, rel_roots)
    payload = run_direct(root, operation_path)
    after = file_snapshot(root, rel_roots)
    payload.update({"staged": False, "dry_run": False, "changed_files": changed_files(before, after)})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--operation", required=True)
    parser.add_argument("--dry-run", action="store_true", help="run in staging and report changed files without committing")
    parser.add_argument("--staged", action="store_true", help="apply through a staging root before committing changed files")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    operation = Path(args.operation)
    if not operation.is_absolute():
        operation = root / operation
    payload = run(root, operation, dry_run=args.dry_run, staged=args.staged)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Work Graph apply operation: {payload['status']}")
        for item in payload["findings"]:
            print(f"[{item['level']}] {item['code']}: {item['message']}")
    return 0 if payload["status"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    sys.exit(main())
