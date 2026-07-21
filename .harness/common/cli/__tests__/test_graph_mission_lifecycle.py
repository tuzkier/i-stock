from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


CLI_ENTRY = Path(__file__).resolve().parents[1] / "harness_cli.py"


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI_ENTRY), "--root", str(root), *args],
        capture_output=True,
        text=True,
    )


def _run_json(root: Path, *args: str) -> dict:
    result = _run(root, *args, "--json")
    assert result.returncode == 0, f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    return json.loads(result.stdout)


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / "harness-runtime" / "config").mkdir(parents=True)
    (root / "harness-runtime" / "harness").mkdir(parents=True)
    config = {
        "work_graph": {
            "node_kinds": {
                "requirement": {"prefix": "REQ", "directory": "requirements"},
            },
            "lanes": {
                "requirement-lane": {
                    "accepts_kinds": ["requirement"],
                    "stages": [
                        {
                            "stage": "intake",
                            "graph_operation": "advance_stage",
                            "operation_profiles": {"advance_stage": {"to_stage": "discovery"}},
                        },
                        {
                            "stage": "discovery",
                            "graph_operation": "advance_stage",
                            "operation_profiles": {"advance_stage": {"to_stage": "prd"}},
                        },
                    ],
                },
            },
        },
    }
    (root / "harness-runtime" / "config" / "harness.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )
    return root


def test_mission_document_resolves_task_order_path_by_mission_and_type(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    brief = root / "harness-runtime" / "harness" / "artifacts" / "M-1" / "breakdown" / "execution-brief.md"
    brief.parent.mkdir(parents=True)
    brief.write_text("# Execution Brief\n", encoding="utf-8")

    payload = _run_json(root, "mission", "document", "--mission", "M-1", "--type", "task-order")

    assert payload["status"] == "PASS"
    assert payload["path"] == "harness-runtime/harness/artifacts/M-1/breakdown/execution-brief.md"
    assert payload["exists"] is True


def test_mission_document_plain_output_is_path_only(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    solution = root / "harness-runtime" / "harness" / "artifacts" / "M-1" / "solution" / "solution.md"
    solution.parent.mkdir(parents=True)
    solution.write_text("# Solution\n", encoding="utf-8")

    result = _run(root, "mission", "document", "--mission", "M-1", "--type", "solution")

    assert result.returncode == 0
    assert result.stdout.strip() == "harness-runtime/harness/artifacts/M-1/solution/solution.md"


def test_control_context_index_uses_mission_document_rule(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    brief = root / "harness-runtime" / "harness" / "artifacts" / "M-1" / "breakdown" / "execution-brief.md"
    brief.parent.mkdir(parents=True)
    brief.write_text("# Execution Brief\n", encoding="utf-8")
    slice_path = root / "harness-runtime" / "harness" / "work-graph" / "mission-slices" / "M-1.yaml"
    slice_path.parent.mkdir(parents=True)
    slice_path.write_text(
        yaml.safe_dump(
            {
                "mission_id": "M-1",
                "control_plane": {"lane": "development-lane", "stage": "execute"},
                "work_graph": {"primary_nodes": []},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (root / "harness-runtime" / "harness" / "mission-status.yaml").write_text(
        yaml.safe_dump(
            {
                "M-1": {
                    "status": "active",
                    "current_lane": "development-lane",
                    "current_stage": "execute",
                    "work_graph": {"mission_slice": "harness-runtime/harness/work-graph/mission-slices/M-1.yaml"},
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = _run_json(root, "control", "context-index", "--mission", "M-1")

    task_order = [item for item in payload["upstream_artifacts"] if item["kind"] == "task-order"]
    assert task_order == [
        {
            "kind": "task-order",
            "path": "harness-runtime/harness/artifacts/M-1/breakdown/execution-brief.md",
            "required": False,
            "exists": True,
            "source": "mission_document_rule",
            "candidates": [
                {
                    "path": "harness-runtime/harness/artifacts/M-1/breakdown/execution-brief.md",
                    "exists": True,
                }
            ],
        }
    ]


def test_graph_node_create_requires_stage(tmp_path: Path) -> None:
    # --stage 在 argparse 层是可选项（结构化命令注册测试会不带 --stage 解析 create）；
    # stage 的必填由 work-graph operation 层校验：create_node target 必须含
    # id/kind/title/lane/stage/status，缺 stage 返回结构化 FAIL（invalid_create_target），
    # 而非 argparse error。
    root = _workspace(tmp_path)
    result = _run(
        root,
        "graph",
        "node",
        "create",
        "--node-id",
        "REQ-NO-STAGE",
        "--kind",
        "requirement",
        "--title",
        "No stage",
        "--lane",
        "requirement-lane",
        "--status",
        "active",
    )
    assert result.returncode != 0
    assert "invalid_create_target" in (result.stdout + result.stderr)


def test_graph_node_create_persists_stage(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    payload = _run_json(
        root,
        "graph",
        "node",
        "create",
        "--node-id",
        "REQ-STAGE",
        "--kind",
        "requirement",
        "--title",
        "Stage-aware node",
        "--lane",
        "requirement-lane",
        "--stage",
        "intake",
        "--status",
        "active",
    )
    assert payload["status"] == "PASS"

    node_payload = _run_json(root, "graph", "node", "show", "REQ-STAGE")
    node = yaml.safe_load(node_payload["yaml"])
    assert node["stage"] == "intake"

    check = _run_json(root, "graph", "check")
    assert check["status"] == "PASS"


def test_create_slice_objective_sets_mission_title_and_enables_stage_start(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _run_json(root, "mission", "init")
    _run_json(
        root,
        "graph",
        "node",
        "create",
        "--node-id",
        "REQ-MISSION",
        "--kind",
        "requirement",
        "--title",
        "Mission requirement",
        "--lane",
        "requirement-lane",
        "--stage",
        "intake",
        "--status",
        "active",
    )

    objective = "Visualize Work Graph stages as a Mission board"
    slice_payload = _run_json(
        root,
        "mission",
        "create-slice",
        "--mission",
        "20260527-workgraph-board",
        "--primary-node",
        "REQ-MISSION",
        "--lane-action",
        "intake",
        "--objective",
        objective,
    )
    assert slice_payload["status"] == "PASS"
    assert slice_payload["mission_slice"]["objective"] == objective
    assert slice_payload["mission_status"]["title"] == objective

    stage_payload = _run_json(
        root,
        "mission",
        "stage",
        "start",
        "--mission",
        "20260527-workgraph-board",
        "--stage",
        "intake",
    )
    assert stage_payload["status"] == "PASS"
    assert stage_payload["mission_status"]["stages"]["intake"] == "in-progress"


def test_gate_transition_advances_graph_and_refreshes_next_slice(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _run_json(root, "mission", "init")
    _run_json(
        root,
        "graph",
        "node",
        "create",
        "--node-id",
        "REQ-TRANSITION",
        "--kind",
        "requirement",
        "--title",
        "Transition requirement",
        "--lane",
        "requirement-lane",
        "--stage",
        "intake",
        "--status",
        "active",
    )
    mission = "20260527-transition"
    _run_json(
        root,
        "mission",
        "create-slice",
        "--mission",
        mission,
        "--primary-node",
        "REQ-TRANSITION",
        "--lane-action",
        "intake",
        "--objective",
        "Verify transition command",
    )
    contract_path = root / "harness-runtime" / "harness" / "missions" / mission / "contracts" / "transition.contract.yaml"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(
        yaml.safe_dump(
            {
                "control_contract": {
                    "type": "memory_update_contract",
                    "version": 1,
                    "mission_id": mission,
                    "stage": "intake",
                    "status": "ready",
                    "upstream": [],
                    "consumers": [],
                    "decisions": [
                        {
                            "id": "MEM-01",
                            "source": "retrospective",
                            "target": "runtime-asset",
                            "change_type": "applied",
                            "target_ref": "harness-runtime/harness/mission-status.yaml",
                        }
                    ],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    slice_path = root / "harness-runtime" / "harness" / "work-graph" / "mission-slices" / f"{mission}.yaml"

    payload = _run_json(
        root,
        "gate",
        "transition",
        "--mission",
        mission,
        "--stage",
        "intake",
        "--mission-slice",
        str(slice_path),
        "--contract-artifact",
        str(contract_path),
        "--primary-node",
        "REQ-TRANSITION",
        "--ai-interpretation",
        "Contract check passed and graph can advance.",
    )

    assert payload["status"] == "PASS"
    assert payload["gate_run"]["gate_effect"] == "allow"
    assert payload["gate_advance"]["status"] == "PASS"
    assert payload["board_select"]["status"] == "PASS"
    assert payload["board_select"]["mission_slice"]["control_plane"]["stage"] == "discovery"

    status_doc = yaml.safe_load((root / "harness-runtime" / "harness" / "mission-status.yaml").read_text(encoding="utf-8"))
    mission_status = status_doc[mission]
    assert mission_status["stages"]["intake"] == "done"


def test_graph_apply_attaches_artifact_refs_without_work_graph_copy(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _run_json(
        root,
        "graph",
        "node",
        "create",
        "--node-id",
        "REQ-ARTIFACT",
        "--kind",
        "requirement",
        "--title",
        "Artifact requirement",
        "--lane",
        "requirement-lane",
        "--stage",
        "discovery",
        "--status",
        "active",
    )
    artifact_path = root / "harness-runtime" / "harness" / "artifacts" / "M-1" / "solution" / "solution.md"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("# Solution\n", encoding="utf-8")
    operation_path = root / "operation.yaml"
    operation_path.write_text(
        yaml.safe_dump(
            {
                "operation_id": "M-1__REQ-ARTIFACT__advance_stage",
                "type": "advance_stage",
                "node_id": "REQ-ARTIFACT",
                "lane": "requirement-lane",
                "from_stage": "discovery",
                "to_stage": "prd",
                "mission_id": "M-1",
                "work_graph_artifact": {
                    "node_id": "REQ-ARTIFACT",
                    "artifact_set_id": "AS-REQ-ARTIFACT-solution-v1",
                    "artifact_version": "v1",
                    "promoted_by_mission": "M-1",
                    "artifact_refs": [
                        {
                            "artifact_id": "M-1:solution",
                            "role": "solution",
                            "path": "harness-runtime/harness/artifacts/M-1/solution/solution.md",
                        }
                    ],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = _run_json(root, "graph", "apply", "--operation", str(operation_path))

    assert payload["status"] == "PASS"
    node_payload = _run_json(root, "graph", "node", "show", "REQ-ARTIFACT")
    node = yaml.safe_load(node_payload["yaml"])
    assert node["artifact"]["artifact_refs"] == [
        {
            "artifact_id": "M-1:solution",
            "role": "solution",
            "path": "harness-runtime/harness/artifacts/M-1/solution/solution.md",
            "kind": "text",
        }
    ]
    assert not (root / "harness-runtime" / "harness" / "work-graph" / "artifacts" / "REQ-ARTIFACT").exists()


def test_trace_report_counts_stage_scoped_events(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    mission = "20260527-trace"

    init = _run_json(root, "trace", "log-init", "--mission", mission, "--stage", "intake")
    assert init["status"] == "PASS"
    assert init["created"] is True

    discovery_init = _run_json(root, "trace", "log-init", "--mission", mission, "--stage", "discovery")
    assert discovery_init["status"] == "PASS"
    assert discovery_init["created"] is False
    _run_json(root, "trace", "step-enter", "--mission", mission, "--step", "dependency-check", "--phase", "discovery")

    report = _run_json(root, "trace", "report", "--mission", mission, "--stage", "discovery")
    assert report["status"] == "PASS"
    assert report["event_count"] == 3
    assert report["event_counts"]["log-init"] == 1
    assert report["event_counts"]["stage-init"] == 1
    assert report["event_counts"]["step-enter"] == 1
    assert report["stage_counts"]["discovery"] == 2
    assert report["stage_event_count"] == 2


def test_create_slice_replace_updates_legacy_generic_title(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    mission_id = "20260527-legacy-title"
    _run_json(root, "mission", "init")
    _run_json(
        root,
        "graph",
        "node",
        "create",
        "--node-id",
        "REQ-LEGACY",
        "--kind",
        "requirement",
        "--title",
        "Legacy requirement",
        "--lane",
        "requirement-lane",
        "--stage",
        "intake",
        "--status",
        "active",
    )
    status_path = root / "harness-runtime" / "harness" / "mission-status.yaml"
    status_path.write_text(
        yaml.safe_dump({mission_id: {"title": f"Mission Slice {mission_id}", "status": "active"}}, sort_keys=False),
        encoding="utf-8",
    )
    objective = "Legacy title repaired"

    payload = _run_json(
        root,
        "mission",
        "create-slice",
        "--mission",
        mission_id,
        "--primary-node",
        "REQ-LEGACY",
        "--lane-action",
        "intake",
        "--objective",
        objective,
        "--replace",
    )

    assert payload["status"] == "PASS"
    assert payload["mission_status"]["title"] == objective


def test_create_slice_rejects_conflicting_objective_aliases(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _run_json(root, "mission", "init")
    result = _run(
        root,
        "mission",
        "create-slice",
        "--mission",
        "M-CONFLICT",
        "--primary-node",
        "REQ-MISSING",
        "--lane-action",
        "intake",
        "--objective",
        "A",
        "--title",
        "B",
        "--json",
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "FAIL"
    assert payload["findings"][0]["code"] == "conflicting_objective"
