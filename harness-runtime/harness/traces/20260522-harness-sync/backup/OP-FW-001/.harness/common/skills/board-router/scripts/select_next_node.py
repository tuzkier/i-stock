#!/usr/bin/env python3
"""Select the next Work Graph node and write a Mission Slice skeleton."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

WORK_GRAPH_SCRIPTS = Path(__file__).resolve().parents[2] / "work-graph" / "scripts"
if str(WORK_GRAPH_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))

from work_graph_lib import (
    Finding,
    as_str_list,
    finding_dict,
    lane_action_snapshot,
    lane_registry,
    load_nodes,
    load_yaml,
    resolve_graph_root,
    lane_stage_for_node,
    status_from_findings,
    write_yaml,
)


def load_runtime_config(root: Path) -> dict[str, Any]:
    for path in (root / "harness-runtime" / "config" / "harness.yaml", root / "package" / "harness-runtime" / "config" / "harness.yaml"):
        config = load_yaml(path)
        if config:
            return config
    return {}


def work_graph_config(root: Path) -> dict[str, Any]:
    config = load_runtime_config(root)
    work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
    return work_graph


def lane_actions(root: Path, findings: list[Finding]) -> dict[str, dict[str, Any]]:
    return lane_registry(root, findings)


def selection_strategy(root: Path) -> dict[str, Any]:
    work_graph = work_graph_config(root)
    strategy = work_graph.get("selection_strategy") if isinstance(work_graph.get("selection_strategy"), dict) else {}
    return {
        "relevance_first": bool(strategy.get("relevance_first", True)),
        "status_order": as_str_list(strategy.get("status_order")) or ["ready", "active"],
        "tie_breakers": as_str_list(strategy.get("tie_breakers")) or ["node_priority", "lane_action_priority", "updated_at", "node_id"],
    }


def schedulable_lanes(actions: dict[str, dict[str, Any]]) -> list[str]:
    return list(actions)


def validate_board(board: dict[str, Any], nodes: dict[str, dict[str, Any]], findings: list[Finding]) -> None:
    lanes = board.get("lanes") if isinstance(board.get("lanes"), dict) else {}
    for lane, node_ids in lanes.items():
        if not isinstance(node_ids, list):
            findings.append(Finding("FAIL", "invalid_board_lane", f"Board lane {lane} must be a list"))
            continue
        for node_id in node_ids:
            node_id = str(node_id)
            if node_id not in nodes:
                findings.append(Finding("FAIL", "board_unknown_node", f"Board lane {lane} references unknown node {node_id}"))
                continue
            if nodes[node_id].get("lane") != lane:
                findings.append(Finding("FAIL", "board_lane_mismatch", f"{node_id} is in board lane {lane}, but node lane is {nodes[node_id].get('lane')}"))


def priority_rank(value: Any) -> int:
    text = str(value or "P9").upper()
    match = re.match(r"^P(\d+)$", text)
    if match:
        return int(match.group(1))
    return 9


def updated_rank(value: Any) -> str:
    return str(value or "")


def relation_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


def node_reference_ids(node: dict[str, Any]) -> set[str]:
    refs = set(as_str_list(node.get("inputs")) + as_str_list(node.get("outputs")))
    relations = node.get("relations") if isinstance(node.get("relations"), dict) else {}
    for value in relations.values():
        refs.update(relation_values(value))
    return refs


def flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(flatten_strings(item))
        return result
    if isinstance(value, dict):
        result = []
        for item in value.values():
            result.extend(flatten_strings(item))
        return result
    return []


def query_terms(values: list[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        text = str(value).strip().casefold()
        if not text:
            continue
        terms.append(text)
        terms.extend(part for part in re.split(r"[^0-9a-zA-Z\u4e00-\u9fff]+", text) if part)
    return sorted(set(terms), key=lambda item: (-len(item), item))


def relevance_profile(
    node_id: str,
    node: dict[str, Any],
    context: dict[str, list[str]],
) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []
    primary_nodes = set(context.get("primary_nodes") or [])
    related_nodes = set(context.get("related_nodes") or [])
    specs = set(context.get("specs") or [])
    refs = node_reference_ids(node)
    node_specs = set(flatten_strings(node.get("specs")))

    if node_id in primary_nodes:
        score += 1000
        reasons.append("primary_node")
    if node_id in related_nodes:
        score += 700
        reasons.append("related_node")
    if refs & primary_nodes:
        score += 600
        reasons.append("relates_to_primary_node")
    if refs & related_nodes:
        score += 350
        reasons.append("relates_to_related_node")
    if specs and node_specs & specs:
        score += 250
        reasons.append("spec_overlap")

    searchable = " ".join(
        [
            node_id,
            str(node.get("kind") or ""),
            str(node.get("title") or ""),
            str(node.get("lane") or ""),
            str(node.get("status") or ""),
            *sorted(refs),
            *flatten_strings(node.get("specs")),
        ]
    ).casefold()
    for term in query_terms(context.get("query") or []):
        if term and term in searchable:
            score += 100
            reasons.append(f"query:{term}")

    return {"score": score, "reasons": sorted(set(reasons))}


def build_context(queries: list[str], primary_nodes: list[str], related_nodes: list[str], specs: list[str]) -> dict[str, list[str]]:
    return {
        "query": [str(item) for item in queries if str(item).strip()],
        "primary_nodes": [str(item) for item in primary_nodes if str(item).strip()],
        "related_nodes": [str(item) for item in related_nodes if str(item).strip()],
        "specs": [str(item) for item in specs if str(item).strip()],
    }


def runtime_harness_root(root: Path) -> Path:
    candidate = root / "harness-runtime" / "harness"
    if candidate.exists():
        return candidate
    return root / "harness-runtime" / "harness"


def relpath(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def update_mission_status(root: Path, mission_id: str, slice_payload: dict[str, Any], slice_path: Path) -> None:
    status_path = runtime_harness_root(root) / "mission-status.yaml"
    status = load_yaml(status_path)
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    control_plane = slice_payload.get("control_plane") if isinstance(slice_payload.get("control_plane"), dict) else {}
    lane_action = slice_payload.get("lane_action") if isinstance(slice_payload.get("lane_action"), dict) else {}
    work_graph = slice_payload.get("work_graph") if isinstance(slice_payload.get("work_graph"), dict) else {}
    stages = entry.get("stages") if isinstance(entry.get("stages"), dict) else {}
    stage = str(control_plane.get("stage") or "")
    lane = str(control_plane.get("lane") or "")
    if stage:
        stages.setdefault(stage, "pending")
    entry.update(
        {
            "title": entry.get("title") or slice_payload.get("objective") or mission_id,
            "status": entry.get("status") or "active",
            "current_lane": lane,
            "current_stage": stage,
            "stages": stages,
            "work_graph": {
                **(entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}),
                "mission_slice": relpath(root, slice_path),
                "primary_nodes": work_graph.get("primary_nodes") or [],
                "related_nodes": work_graph.get("related_nodes") or [],
                "operation": slice_payload.get("operation"),
                "lane": lane,
                "stage": stage,
                "lane_action": lane_action,
            },
        }
    )
    status[mission_id] = entry
    write_yaml(status_path, status)


def select_node(
    board: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    actions: dict[str, dict[str, Any]],
    strategy: dict[str, Any],
    context: dict[str, list[str]],
    config: dict[str, Any],
    findings: list[Finding],
) -> tuple[str | None, dict[str, Any] | None, dict[str, Any] | None]:
    lanes = board.get("lanes") if isinstance(board.get("lanes"), dict) else {}
    status_order = as_str_list(strategy.get("status_order")) or ["ready", "active"]
    status_rank = {status: index for index, status in enumerate(status_order)}
    candidates: list[tuple[tuple[Any, ...], str, dict[str, Any], dict[str, Any]]] = []
    for lane in schedulable_lanes(actions):
        for node_id in lanes.get(lane, []) or []:
            node_id = str(node_id)
            node = nodes.get(node_id)
            if not node:
                continue
            status = str(node.get("status") or "")
            if status not in status_rank:
                continue
            _lane_id, _stage_id, action = lane_stage_for_node(config, node, findings)
            accepts_kinds = as_str_list(action.get("accepts_kinds"))
            node_kind = str(node.get("kind") or "")
            if accepts_kinds and node_kind not in accepts_kinds:
                continue
            profile = action.get("operation_profiles") if isinstance(action.get("operation_profiles"), dict) else {}
            target_lane = str((profile.get("advance_lane") or {}).get("to_lane") or "")
            target_action = actions.get(target_lane) if target_lane else None
            target_accepts_kinds = as_str_list(target_action.get("accepts_kinds")) if isinstance(target_action, dict) else []
            if str(action.get("graph_operation") or "") == "advance_lane" and target_accepts_kinds and node_kind not in target_accepts_kinds:
                # Primary advance_lane wouldn't place this node kind into the
                # target lane. However, the same stage's operation_profiles
                # may declare additional operations (notably `split_node` for
                # breakdown→execute, where a `requirement` is split into
                # `task` children that the target lane DOES accept). Only skip
                # the node when no alternative profile can place it; otherwise
                # the primary node of the active mission silently disappears
                # from the board and selection falls through to unrelated
                # nodes. (Allowed operations are the keys of operation_profiles
                # — `allowed_graph_operations` is a slice-time mirror and is
                # not populated on the registry action dict.)
                alt_works = False
                for alt, alt_profile in profile.items():
                    if alt == "advance_lane" or not isinstance(alt_profile, dict):
                        continue
                    if alt == "split_node":
                        child_lane = str(alt_profile.get("default_child_lane") or "")
                        child_kinds = as_str_list(alt_profile.get("allowed_child_kinds"))
                        child_lane_action = actions.get(child_lane) if child_lane else None
                        child_lane_accepts = (
                            as_str_list(child_lane_action.get("accepts_kinds"))
                            if isinstance(child_lane_action, dict)
                            else []
                        )
                        if not (child_kinds and child_lane_accepts and any(
                            k in child_lane_accepts for k in child_kinds
                        )):
                            continue
                        # split_node profile is valid for this kind. But if
                        # this node has already been split (some output sits
                        # in the split target lane and matches an allowed
                        # child kind), don't re-include — re-splitting is
                        # redundant and would create duplicate work. In that
                        # case selection should fall through to the children.
                        outputs = as_str_list(node.get("outputs"))
                        already_split = False
                        for out_id in outputs:
                            out_node = nodes.get(out_id) or {}
                            # Normalize via lane_stage_for_node so legacy
                            # lane aliases (e.g. "in_progress" → development-lane)
                            # don't false-negative the already-split detection.
                            out_lane, _, _ = lane_stage_for_node(config, out_node)
                            if (
                                out_lane == child_lane
                                and str(out_node.get("kind") or "") in child_kinds
                            ):
                                already_split = True
                                break
                        if already_split:
                            continue
                        alt_works = True
                        break
                    # Other operations (merge_nodes / batch / etc.) are meta
                    # operations whose validity for THIS node depends on
                    # external context; do not blanket-rescue the node here —
                    # if split_node does not apply, fall through to skip.
                if not alt_works:
                    continue
            action_priority = len(actions) - list(actions).index(lane) if lane in actions else 0
            relevance = relevance_profile(node_id, node, context)
            relevance_score = int(relevance["score"]) if strategy.get("relevance_first") else 0
            sort_key = (
                -relevance_score,
                priority_rank(node.get("priority")),
                -action_priority,
                status_rank[status],
                -len(updated_rank(node.get("updated_at"))),
                updated_rank(node.get("updated_at")),
                node_id,
            )
            candidates.append((sort_key, node_id, node, relevance))
    if not candidates:
        return None, None, None
    _sort_key, node_id, node, relevance = sorted(candidates, key=lambda item: item[0])[0]
    return node_id, node, relevance


def related_candidates(
    nodes: dict[str, dict[str, Any]],
    selected_id: str,
    context: dict[str, list[str]],
) -> dict[str, list[dict[str, Any]]]:
    candidates: dict[str, list[dict[str, Any]]] = {"deferred": [], "blocked": []}
    for node_id, node in nodes.items():
        if node_id == selected_id:
            continue
        lane = str(node.get("lane") or "")
        status = str(node.get("status") or "")
        bucket = "deferred" if lane == "deferred" or status == "deferred" else "blocked" if lane == "blocked" or status == "blocked" else ""
        if not bucket:
            continue
        relevance = relevance_profile(node_id, node, context)
        if int(relevance["score"]) <= 0:
            continue
        candidates[bucket].append(
            {
                "id": node_id,
                "title": str(node.get("title") or ""),
                "lane": lane,
                "status": status,
                "relevance_score": relevance["score"],
                "reasons": relevance["reasons"],
            }
        )
    for bucket in candidates:
        candidates[bucket] = sorted(candidates[bucket], key=lambda item: (-int(item["relevance_score"]), item["id"]))
    return candidates


def mission_slice(
    mission_id: str,
    node_id: str,
    node: dict[str, Any],
    config: dict[str, Any],
    relevance: dict[str, Any] | None,
    candidates: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    findings: list[Finding] = []
    lane, stage, action = lane_stage_for_node(config, node, findings)
    control_plane = {
        "lane": lane,
        "stage": stage,
    }
    lane_action = lane_action_snapshot(lane, action, mission_id)
    directly_related = set(as_str_list(node.get("inputs")) + as_str_list(node.get("outputs")))
    discovered_related = {item["id"] for items in candidates.values() for item in items}
    return {
        "mission_id": mission_id,
        "objective": f"推进 {node_id}: {node.get('title')}",
        "control_plane": control_plane,
        "lane_action": lane_action,
        "work_graph": {
            "primary_nodes": [node_id],
            "related_nodes": sorted(directly_related | discovered_related),
            "selection": {
                "relevance_score": int((relevance or {}).get("score") or 0),
                "reasons": (relevance or {}).get("reasons") or [],
            },
        },
        "related_candidates": candidates,
        "operation": lane_action["graph_operation"],
        "acceptance_criteria": [
            f"{node_id} advanced from {lane}/{stage}",
            "graph operation applied by work-graph script",
            "board/index/tree regenerated from nodes",
        ],
    }


def run(
    root: Path,
    mission_id: str,
    write_slice: bool,
    queries: list[str] | None = None,
    primary_nodes: list[str] | None = None,
    related_nodes: list[str] | None = None,
    specs: list[str] | None = None,
) -> dict[str, Any]:
    graph_root = resolve_graph_root(root)
    findings: list[Finding] = []
    actions = lane_actions(root, findings)
    config = load_runtime_config(root)
    strategy = selection_strategy(root)
    context = build_context(queries or [], primary_nodes or [], related_nodes or [], specs or [])
    nodes, _paths, load_findings = load_nodes(graph_root)
    findings.extend(load_findings)
    board = load_yaml(graph_root / "boards" / "main.yaml")
    validate_board(board, nodes, findings)
    selected_id: str | None = None
    selected_node: dict[str, Any] | None = None
    selected_relevance: dict[str, Any] | None = None
    candidates: dict[str, list[dict[str, Any]]] = {"deferred": [], "blocked": []}
    slice_payload: dict[str, Any] | None = None
    if not findings:
        selected_id, selected_node, selected_relevance = select_node(board, nodes, actions, strategy, context, config, findings)
        if not selected_id or selected_node is None:
            level = "FAIL" if write_slice else "INFO"
            message = "Board has no ready or active node in schedulable lanes"
            if not write_slice:
                message += "; no-write selection may create a new seed node before writing a Mission Slice"
            findings.append(Finding(level, "no_ready_node", message))
        else:
            expanded_context = {
                **context,
                "primary_nodes": sorted(set(context["primary_nodes"] + [selected_id])),
                "related_nodes": sorted(set(context["related_nodes"] + as_str_list(selected_node.get("inputs")) + as_str_list(selected_node.get("outputs")))),
            }
            candidates = related_candidates(nodes, selected_id, expanded_context)
            slice_payload = mission_slice(mission_id, selected_id, selected_node, config, selected_relevance, candidates)
            if write_slice:
                slice_path = graph_root / "mission-slices" / f"{mission_id}.yaml"
                write_yaml(slice_path, slice_payload)
                update_mission_status(root, mission_id, slice_payload, slice_path)
    status = status_from_findings(findings)
    return {
        "status": status,
        "control": "board_router_select_next_node",
        "graph_root": str(graph_root),
        "selection_strategy": strategy,
        "selection_context": context,
        "selected_node": {"id": selected_id, **(selected_node or {})} if selected_node else None,
        "selected_relevance": selected_relevance,
        "related_candidates": candidates,
        "mission_slice": slice_payload,
        "findings": [finding_dict(item) for item in findings],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--primary-node", action="append", default=[])
    parser.add_argument("--related-node", action="append", default=[])
    parser.add_argument("--spec", action="append", default=[])
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run(
        Path(args.root).resolve(),
        args.mission_id,
        not args.no_write,
        args.query,
        args.primary_node,
        args.related_node,
        args.spec,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Board Router select: {payload['status']}")
        if payload.get("selected_node"):
            print(f"Selected: {payload['selected_node']['id']}")
        for item in payload["findings"]:
            print(f"[{item['level']}] {item['code']}: {item['message']}")
    return 1 if payload["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
