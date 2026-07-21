---
name: work-graph
description: '当 board-router、stage-gate、harness-lint 需要应用 graph operation、重建派生视图、检查 Work Graph 一致性，或用户明确要求修复/重建 Work Graph 时使用；不作为新需求、任务推进或阶段执行入口。'
---

# Work Graph

Work Graph 是 Harness 的长期工作对象事实源。`nodes/**/*.yaml` 是唯一事实源；`boards/main.yaml`、`_index.yaml`、`indexes/*.yaml`、`trees/*.yaml` 是派生视图。

## 何时使用

- `board-router` 已经选定 node，并需要应用 graph operation。
- `stage-gate` PASS 后需要 promotion / advance / split / merge / defer / block 等图状态更新。
- `harness-lint` 或质量检查需要验证 Work Graph node 与派生视图是否一致。
- 用户明确要求“重建 Work Graph 索引”“检查 Work Graph 一致性”“修复 Work Graph 视图漂移”。

## 何时不使用

- 用户提出新任务 / 新需求 → 先走 `intake`。
- 当前 Mission 需要选择下一步 → 先走 `board-router` 或自治循环。
- 阶段文档或代码实现还没完成 → 继续对应阶段 skill。
- 只是想手写 board / index / tree → 禁止，必须通过脚本从 node 重建。

## 固定规则

- AI 只产出 graph operation manifest，不直接手写 board / index / tree。
- 固定、可枚举的 node 更新必须通过 `harness-cli` 调用 `harness graph apply` 执行。
- 每次 node 更新后必须通过 `harness-cli` 运行 `harness graph rebuild` 重建派生视图。
- 每次重建后必须通过 `harness-cli` 运行 `harness graph check` 校验一致性。

## 常用命令

```bash
harness graph rebuild --json
harness graph check --json
harness graph apply --operation <operation.yaml> --json
```

以上命令只展示 CLI 语义；实际执行入口、root 解析和失败处理统一由 `harness-cli` 技能完成。

## 操作 Manifest

当前固定脚本支持：

- `advance_lane`：推进单个 node lane。
- `batch`：一次 Mission Slice 中顺序应用多个 graph operation，常用于多 primary node 推进。
- `split_node`：把一个 node 拆成多个 child node，并建立 `outputs` / `inputs` / `relations.split_from`。
- `merge_nodes`：把多个 source node 汇合成一个 target node，并建立 `relations.merged_from` / `relations.merged_into`。
- `block_node`：把 node 移到 `blocked` lane / status，并记录 `trace.block_reason`。
- `defer_node`：把 node 移到 `deferred` lane / status，并记录 `trace.defer_reason`。
- `supersede_node`：用 replacement node 替代旧 node，并建立 `relations.supersedes` / `relations.superseded_by`。

`advance_lane` 示例：

```yaml
operation_id: OP-001
type: advance_lane
node_id: REQ-001
from_lane: prd
to_lane: solution
mission_id: M-20260507-001
work_graph_artifact:
  node_id: REQ-001
  artifact_set_id: AS-REQ-001-solution-v1
  artifact_version: v1
  promoted_by_mission: M-20260507-001
  artifact_refs:
    - artifact_id: M-20260507-001:solution
      role: solution
      path: harness-runtime/harness/artifacts/M-20260507-001/solution/solution.md
  change_reason: accepted solution update
  artifact_state:
    status: accepted
```

`split_node` 示例：

```yaml
operation_id: OP-SPLIT-001
type: split_node
node_id: REQ-001
mission_id: M-20260507-001
children:
  - id: SOL-001
    kind: solution
    title: 登录方案
    lane: solution
    status: ready
```

`merge_nodes` 示例：

```yaml
operation_id: OP-MERGE-001
type: merge_nodes
node_ids: [SOL-001, SOL-002]
mission_id: M-20260507-001
target:
  id: TECH-001
  kind: technical_design
  title: 统一技术设计
  lane: breakdown
  status: ready
```

`supersede_node` 示例：

```yaml
operation_id: OP-SUPERSEDE-001
type: supersede_node
node_id: SOL-002
node_ids: [SOL-001]
mission_id: M-20260507-001
```

`batch` 示例：

```yaml
operation_id: OP-BATCH-001
type: batch
mission_id: M-20260507-001
operations:
  - type: advance_lane
    node_id: SOL-001
    from_lane: solution
    to_lane: technical_analysis
  - type: advance_lane
    node_id: SOL-002
    from_lane: solution
    to_lane: technical_analysis
```

Artifact promotion 可附加在任意成功的 graph operation manifest 上；脚本以 `work_graph_artifact.node_id` 指向的 node 为准，把 `artifact_refs` 绑定到 node 的 accepted artifact set，更新 node 的 `artifact.artifact_state`，并在 `Work Graph node artifact history and operation log` 追加变更记录。产物正文只允许位于 `harness-runtime/harness/artifacts/...`；stage 和 Work Graph 只保存引用，不复制正文。后续新增操作仍应扩展为 manifest + 脚本处理，不改为手写派生视图。
#!/usr/bin/env python3
"""Check deterministic Work Graph consistency."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from work_graph_lib import (
    Finding,
    LANES,
    STATUSES,
    as_str_list,
    build_views,
    finding_dict,
    lane_registry,
    load_nodes,
    load_runtime_config,
    load_yaml,
    resolve_graph_root,
    status_from_findings,
)


def compare_lane_views(expected: dict[str, Any], actual: dict[str, Any], findings: list[Finding]) -> None:
    expected_lanes = expected["board"]["lanes"]
    actual_lanes = actual.get("lanes") if isinstance(actual.get("lanes"), dict) else {}
    for lane, expected_ids in expected_lanes.items():
        actual_ids = [str(item) for item in actual_lanes.get(lane, [])]
        if actual_ids != expected_ids:
            findings.append(
                Finding(
                    "FAIL",
                    "board_lane_mismatch",
                    f"Board lane {lane} is {actual_ids}, expected {expected_ids}",
                )
            )
    for lane, actual_ids in actual_lanes.items():
        for node_id in actual_ids or []:
            node_id = str(node_id)
            expected_lane = next((key for key, values in expected_lanes.items() if node_id in values), None)
            if expected_lane and expected_lane != lane:
                findings.append(
                    Finding("FAIL", "board_lane_mismatch", f"{node_id} appears in board lane {lane}, expected {expected_lane}")
                )


def check_relations(nodes: dict[str, dict[str, Any]], findings: list[Finding]) -> None:
    for node_id, node in nodes.items():
        for output_id in as_str_list(node.get("outputs")):
            if output_id not in nodes:
                findings.append(Finding("FAIL", "missing_output_node", f"{node_id} outputs unknown node {output_id}"))
                continue
            if node_id not in as_str_list(nodes[output_id].get("inputs")):
                findings.append(Finding("FAIL", "unclosed_output_relation", f"{node_id} outputs {output_id}, but {output_id} inputs do not include {node_id}"))
        for input_id in as_str_list(node.get("inputs")):
            if input_id not in nodes:
                findings.append(Finding("FAIL", "missing_input_node", f"{node_id} inputs unknown node {input_id}"))
                continue
            if node_id not in as_str_list(nodes[input_id].get("outputs")):
                findings.append(Finding("FAIL", "unclosed_input_relation", f"{node_id} inputs {input_id}, but {input_id} outputs do not include {node_id}"))


def check_node_kind_prefixes(root: Path, nodes: dict[str, dict[str, Any]], findings: list[Finding]) -> None:
    config = load_runtime_config(root)
    work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
    node_kinds = work_graph.get("node_kinds") if isinstance(work_graph.get("node_kinds"), dict) else {}
    for node_id, node in nodes.items():
        kind = str(node.get("kind") or "")
        spec = node_kinds.get(kind) if isinstance(node_kinds.get(kind), dict) else {}
        prefix = str(spec.get("prefix") or "")
        if prefix and not node_id.startswith(f"{prefix}-"):
            findings.append(Finding("FAIL", "node_kind_prefix_mismatch", f"{node_id} kind {kind} must use prefix {prefix}-"))


def check_lane_accepts_kinds(root: Path, nodes: dict[str, dict[str, Any]], findings: list[Finding]) -> None:
    lanes = lane_registry(root, findings)
    for node_id, node in nodes.items():
        lane = str(node.get("lane") or "")
        stage = str(node.get("stage") or "")
        status = str(node.get("status") or "")
        if lane not in LANES:
            findings.append(Finding("FAIL", "unknown_lane", f"{node_id} uses unknown lane {lane}"))
            continue
        if status not in STATUSES:
            findings.append(Finding("FAIL", "unknown_status", f"{node_id} uses unknown status {status}"))
        lane_spec = lanes.get(lane)
        if not lane_spec:
            if lane in LANES:
                findings.append(Finding("FAIL", "missing_lane_registry_entry", f"{node_id} uses lane {lane}, but no work_graph.lanes entry is registered"))
            else:
                findings.append(Finding("FAIL", "unknown_lane", f"{node_id} uses unknown lane {lane}"))
            continue
        stages = [str(item.get("stage") or "") for item in lane_spec.get("stages", []) if isinstance(item, dict)]
        if stage not in stages:
            findings.append(Finding("FAIL", "stage_not_in_lane", f"{node_id} stage {stage or '<missing>'} is not registered in lane {lane}"))
        accepts_kinds = as_str_list(lane_spec.get("accepts_kinds"))
        kind = str(node.get("kind") or "")
        if status in {"ready", "active"} and accepts_kinds and kind not in accepts_kinds:
            findings.append(Finding("FAIL", "lane_kind_not_accepted", f"{node_id} kind {kind} is in lane {lane}, but lane accepts only: {', '.join(accepts_kinds)}"))


def mission_slice_from_lane(mission_slice: dict[str, Any]) -> str:
    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    lane_action = mission_slice.get("lane_action") if isinstance(mission_slice.get("lane_action"), dict) else {}
    return str(control_plane.get("lane") or lane_action.get("lane") or "")


def mission_status_path_from_graph_root(graph_root: Path) -> Path:
    return graph_root.parent / "mission-status.yaml"


def mission_slice_operation_completed(status_doc: dict[str, Any], mission_id: str) -> bool:
    entry = status_doc.get(mission_id) if isinstance(status_doc.get(mission_id), dict) else {}
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    return str(work_graph.get("last_operation_status") or "").upper() == "PASS"


def check_mission_slice_primary_node_lanes(graph_root: Path, nodes: dict[str, dict[str, Any]], findings: list[Finding]) -> None:
    slices_root = graph_root / "mission-slices"
    if not slices_root.exists():
        return
    status_doc = load_yaml(mission_status_path_from_graph_root(graph_root))
    for path in sorted(slices_root.glob("*.yaml")):
        mission_slice = load_yaml(path)
        if not mission_slice:
            continue
        mission_id = str(mission_slice.get("mission_id") or path.stem)
        if mission_slice_operation_completed(status_doc, mission_id):
            continue
        from_lane = mission_slice_from_lane(mission_slice)
        control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
        slice_stage = str(control_plane.get("stage") or "")
        work_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
        primary_nodes = as_str_list(work_graph.get("primary_nodes"))
        for node_id in primary_nodes:
            node = nodes.get(node_id)
            if node is None:
                findings.append(Finding("FAIL", "mission_slice_primary_node_missing", f"Mission Slice {mission_id} references unknown primary node {node_id}"))
                continue
            node_lane = str(node.get("lane") or "")
            if from_lane and node_lane != from_lane:
                findings.append(Finding("FAIL", "mission_slice_primary_node_lane_mismatch", f"Mission Slice {mission_id} primary node {node_id} lane is {node_lane}, expected {from_lane}"))
            node_stage = str(node.get("stage") or "")
            if slice_stage and node_stage != slice_stage:
                findings.append(Finding("FAIL", "mission_slice_primary_node_stage_mismatch", f"Mission Slice {mission_id} primary node {node_id} stage is {node_stage}, expected {slice_stage}"))


def run(root: Path) -> dict:
    graph_root = resolve_graph_root(root)
    nodes, _paths, findings = load_nodes(graph_root)
    expected = build_views(nodes)
    check_node_kind_prefixes(root, nodes, findings)
    check_lane_accepts_kinds(root, nodes, findings)
    check_relations(nodes, findings)
    check_mission_slice_primary_node_lanes(graph_root, nodes, findings)
    board_path = graph_root / "boards" / "main.yaml"
    if not board_path.exists():
        findings.append(Finding("FAIL", "missing_board", f"Board view missing: {board_path}"))
    else:
        compare_lane_views(expected, load_yaml(board_path), findings)
    for rel in ("_index.yaml", "indexes/by-lane.yaml", "indexes/by-kind.yaml", "indexes/by-status.yaml", "indexes/by-relation.yaml"):
        if not (graph_root / rel).exists():
            findings.append(Finding("FAIL", "missing_derived_view", f"Derived view missing: {graph_root / rel}"))
    status = status_from_findings(findings)
    return {
        "status": status,
        "control": "work_graph_consistency",
        "graph_root": str(graph_root),
        "findings": [finding_dict(item) for item in findings],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run(Path(args.root).resolve())
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Work Graph consistency: {payload['status']}")
        for item in payload["findings"]:
            print(f"[{item['level']}] {item['code']}: {item['message']}")
    return 1 if payload["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
