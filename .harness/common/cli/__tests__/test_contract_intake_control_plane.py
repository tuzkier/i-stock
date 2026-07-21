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
    template_source = Path(__file__).resolve().parents[4] / "harness-runtime" / "templates" / "contracts" / "mission-contract.contract.yaml"
    template_target = root / "harness-runtime" / "templates" / "contracts" / "mission-contract.contract.yaml"
    if template_source.exists():
        template_target.parent.mkdir(parents=True, exist_ok=True)
        template_target.write_text(template_source.read_text(encoding="utf-8"), encoding="utf-8")
    (root / "harness-runtime" / "config" / "harness.yaml").write_text(
        yaml.safe_dump(
            {
                "execution_governance": {"levels": {}},
                "work_graph": {
                    "lanes": {
                        "requirement-lane": {
                            "stages": [
                                {
                                    "stage": "intake",
                                    "skill": "intake",
                                    "carrier": "intake",
                                    "graph_operation": "advance_stage",
                                    "output_artifact": "harness-runtime/harness/missions/{mission_id}/mission-contract.md",
                                    "required_execution_roles": ["mission-framing-expert"],
                                    "required_review_roles": ["mission-contract-effectiveness-reviewer"],
                                }
                            ]
                        }
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return root


def _write_mission_slice(root: Path, mission: str) -> None:
    path = root / "harness-runtime" / "harness" / "work-graph" / "mission-slices" / f"{mission}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "mission_id": mission,
                "control_plane": {"lane": "requirement-lane", "stage": "intake"},
                "lane_action": {
                    "lane": "requirement-lane",
                    "stage": "intake",
                    "skill": "intake",
                    "carrier": "intake",
                    "graph_operation": "advance_stage",
                    "output_artifact": f"harness-runtime/harness/missions/{mission}/mission-contract.md",
                    "required_execution_roles": ["mission-framing-expert"],
                    "required_review_roles": ["mission-contract-effectiveness-reviewer"],
                },
                "work_graph": {"primary_nodes": ["REQ-BOARD"], "related_nodes": []},
                "operation": "advance_stage",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _intent_framing() -> dict:
    return {
        "objective": {"statement": "TheForce displays Work Graph Missions as a board."},
        "intent_role_analysis": {
            "actual_task_goal": "TheForce displays Work Graph Missions as a board.",
            "source_materials": ["user request"],
            "agent_instructions": ["先 intake"],
            "process_constraints": ["不要使用 MVP 收缩任务"],
            "discussion_outputs": [],
            "corrections": [],
            "execution_confirmation": "先 intake",
            "excluded_from_objective": [{"source": "先 intake", "reason": "process instruction"}],
            "open_intent_gaps": [
                {
                    "id": "GAP-01",
                    "question": "Which board layout should carry the feature?",
                    "source": "user said board-like",
                    "impact": "information architecture",
                    "handoff_stage": "discovery",
                    "reason_for_discovery": "needs existing-product evidence",
                    "boundary": "do not decide PRD or solution here",
                }
            ],
        },
        "intake_decision": {
            "confirmed": True,
            "confirmation_source": "先 intake",
            "confirmed_at_or_turn": "test",
        },
        "success_definition": {
            "desired_effect": "Users can inspect Work Graph Mission status and open the bound chat.",
            "deliverables": [
                {
                    "id": "DEL-01",
                    "name": "Board",
                    "format": "web UI",
                    "acceptance_link": {"acceptance": ["SCN-01"]},
                }
            ],
            "validation_evidence": [
                {
                    "id": "EVD-01",
                    "type": "test",
                    "method": "run focused tests",
                    "proves": {"acceptance": ["SCN-01"]},
                }
            ],
            "non_goals": ["No Work Graph mutation UI"],
        },
        "user_stories": [
            {
                "id": "US-01",
                "role": "TheForce user",
                "goal": "inspect Mission board",
                "value": "recover context",
                "story_context": {
                    "user": "project operator",
                    "problem": "runtime YAML is hard to scan",
                    "scenario": "open board",
                    "value": "clear control-plane status",
                    "success_metrics": [{"id": "SM-01", "signal": "board visible", "target": "fields match fixture"}],
                },
                "acceptance_refs": ["SCN-01"],
            }
        ],
        "scope": {
            "in": ["Read-only board projection"],
            "out": [{"statement": "Graph mutation", "reason": "not requested"}],
        },
        "acceptance_scenarios": [
            {
                "id": "SCN-01",
                "statement": "Board renders runtime nodes",
                "given": "runtime exists",
                "when": "user opens board",
                "then": "lane cards are visible",
            }
        ],
        "autonomy_level": "受控推进",
        "governance_risk": "high",
        "governance_assessment": {
            "hard_triggers": [{"id": "HT-01", "category": "product_decision", "rationale": "core IA"}],
            "dimensions": {"decision_authority": {"level": "high", "rationale": "IA decision"}},
            "scale_signals": {},
            "decision_rule": "按受控推进处理，不跳过 discovery/prd/solution/technical_analysis/breakdown 等阶段。",
            "user_confirmation_required": True,
            "downgrade_or_checkpoint_removal_requires_approval": True,
        },
        "required_checkpoints": ["prd", "solution", "technical_analysis", "breakdown", "verify", "delivery"],
        "work_graph": {
            "primary_nodes": ["REQ-BOARD"],
            "related_nodes": [],
            "operation": "advance_stage",
            "from_lane": "requirement-lane",
            "to_lane": "requirement-lane",
        },
    }


def test_intake_contract_fill_record_review_check_without_manual_yaml_patch(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    mission = "M-CONTRACT"
    mission_dir = root / "harness-runtime" / "harness" / "missions" / mission
    _write_mission_slice(root, mission)
    contracts_dir = mission_dir / "contracts"
    contracts_dir.mkdir(parents=True)
    (mission_dir / "mission-contract.md").write_text("# contract\n", encoding="utf-8")
    framing_path = mission_dir / "intent-framing.yaml"
    framing_path.write_text(yaml.safe_dump(_intent_framing(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    contract_path = contracts_dir / "mission-contract.contract.yaml"

    fill = _run_json(
        root,
        "contract",
        "fill",
        "--mission",
        mission,
        "--stage",
        "intake",
        "--artifact",
        str(contract_path),
        "--intent-framing",
        str(framing_path),
        "--template",
        "mission-contract",
    )
    assert fill["status"] == "PASS"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))["control_contract"]
    assert contract["version"] == 2
    assert contract["autonomy"].get("skippable_stages", []) == []
    assert contract["autonomy"]["human_checkpoints"] == [
        "prd",
        "solution",
        "technical_analysis",
        "breakdown",
        "verify",
        "delivery",
    ]
    assert contract["execution_result"]["fulfilled_obligations"] == []

    review = _run_json(
        root,
        "contract",
        "record-review",
        "--artifact",
        str(contract_path),
        "--role",
        "mission-contract-effectiveness-reviewer",
        "--verdict",
        "PASS",
        "--subagent-id",
        "agent-1",
        "--model",
        "gpt-test",
        "--summary",
        "review passed",
    )
    assert review["status"] == "PASS"
    assert review["verdict"]["reviewed_obligations"] == ["OBL-INTAKE-001"]
    assert review["applied"][0]["target"] == "control_contract.effectiveness_review.rounds_used"

    check = _run_json(root, "contract", "check", "--artifact", str(contract_path))
    assert check["status"] == "PASS"


def test_execution_result_cannot_fulfill_reviewer_obligation(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    mission = "M-BAD-OBLIGATION"
    mission_dir = root / "harness-runtime" / "harness" / "missions" / mission
    _write_mission_slice(root, mission)
    contracts_dir = mission_dir / "contracts"
    contracts_dir.mkdir(parents=True)
    (mission_dir / "mission-contract.md").write_text("# contract\n", encoding="utf-8")
    framing_path = mission_dir / "intent-framing.yaml"
    framing_path.write_text(yaml.safe_dump(_intent_framing(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    contract_path = contracts_dir / "mission-contract.contract.yaml"
    _run_json(
        root,
        "contract",
        "fill",
        "--mission",
        mission,
        "--stage",
        "intake",
        "--artifact",
        str(contract_path),
        "--intent-framing",
        str(framing_path),
        "--template",
        "mission-contract",
    )
    doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    doc["control_contract"]["execution_result"]["fulfilled_obligations"] = ["OBL-INTAKE-001"]
    contract_path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")

    result = _run(root, "contract", "check", "--artifact", str(contract_path), "--json")
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    codes = {finding["code"] for finding in payload["findings"]}
    assert "execution_result_cannot_fulfill_reviewer_obligation" in codes


def test_reviewer_add_verdict_autofills_missing_review_basis(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    mission = "M-IMPORT-REVIEW"
    mission_dir = root / "harness-runtime" / "harness" / "missions" / mission
    _write_mission_slice(root, mission)
    contracts_dir = mission_dir / "contracts"
    contracts_dir.mkdir(parents=True)
    (mission_dir / "mission-contract.md").write_text("# contract\n", encoding="utf-8")
    framing_path = mission_dir / "intent-framing.yaml"
    framing_path.write_text(yaml.safe_dump(_intent_framing(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    contract_path = contracts_dir / "mission-contract.contract.yaml"
    _run_json(
        root,
        "contract",
        "fill",
        "--mission",
        mission,
        "--stage",
        "intake",
        "--artifact",
        str(contract_path),
        "--intent-framing",
        str(framing_path),
        "--template",
        "mission-contract",
    )
    verdict_path = mission_dir / "review-verdict.yaml"
    verdict_path.write_text(
        yaml.safe_dump(
            {
                "id": "RV-imported",
                "role": "mission-contract-effectiveness-reviewer",
                "verdict": "PASS",
                "reviewed_obligations": ["OBL-INTAKE-001"],
                "dispatch": {
                    "subagent_id": "agent-1",
                    "model": "gpt-test",
                    "execution_mode": "spawn_agent",
                    "started_at": "2026-05-27T00:00:00Z",
                    "completed_at": "2026-05-27T00:00:01Z",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    # verdict 缺 review_basis 时，add-verdict 自动回填为 contract 自身路径
    # （a1da4bc 起的刻意行为），不再以 incomplete manifest 拒绝。
    autofilled = _run_json(root, "contract", "add-verdict", "--artifact", str(contract_path), "--verdict-file", str(verdict_path))
    assert autofilled["status"] == "PASS"
    assert autofilled["verdict"]["review_basis"], "missing review_basis should be auto-filled"

    # 显式提供 review_basis 时按原样保留。
    doc = yaml.safe_load(verdict_path.read_text(encoding="utf-8"))
    doc["review_basis"] = [str(contract_path)]
    verdict_path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    imported = _run_json(root, "contract", "add-verdict", "--artifact", str(contract_path), "--verdict-file", str(verdict_path))
    assert imported["status"] == "PASS"
    assert imported["verdict"]["review_basis"] == [str(contract_path)]


def test_gate_run_distinguishes_stage_and_contract_artifacts(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    mission = "M-GATE-ARTIFACTS"
    mission_dir = root / "harness-runtime" / "harness" / "missions" / mission
    _write_mission_slice(root, mission)
    mission_slice = root / "harness-runtime" / "harness" / "work-graph" / "mission-slices" / f"{mission}.yaml"
    contracts_dir = mission_dir / "contracts"
    contracts_dir.mkdir(parents=True)
    stage_artifact = mission_dir / "mission-contract.md"
    stage_artifact.write_text("# contract\n", encoding="utf-8")
    framing_path = mission_dir / "intent-framing.yaml"
    framing_path.write_text(yaml.safe_dump(_intent_framing(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    contract_path = contracts_dir / "mission-contract.contract.yaml"
    _run_json(
        root,
        "contract",
        "fill",
        "--mission",
        mission,
        "--stage",
        "intake",
        "--artifact",
        str(contract_path),
        "--intent-framing",
        str(framing_path),
        "--template",
        "mission-contract",
    )
    _run_json(
        root,
        "contract",
        "record-review",
        "--artifact",
        str(contract_path),
        "--role",
        "mission-contract-effectiveness-reviewer",
        "--verdict",
        "PASS",
        "--subagent-id",
        "agent-1",
        "--model",
        "gpt-test",
        "--summary",
        "review passed",
    )

    result = _run(
        root,
        "gate",
        "run",
        "--mission",
        mission,
        "--stage",
        "intake",
        "--mission-slice",
        str(mission_slice),
        "--artifact",
        str(stage_artifact),
        "--contract-artifact",
        str(contract_path),
        "--ai-interpretation",
        "Contract and reviewer evidence pass.",
        "--output-dir",
        str(root / "reports"),
        "--json",
    )
    assert result.returncode == 0, f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    summary = json.loads(result.stdout)
    payload = json.loads(Path(summary["json"]).read_text(encoding="utf-8"))
    assert payload["contract_check"]["status"] == "PASS"
    assert payload["artifacts"]["stage_artifact"] == str(stage_artifact)
    assert payload["artifacts"]["contract_artifact"] == str(contract_path)


def test_dependency_impact_required_contract_surface_is_checked(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    mission = "M-DEPENDENCY"
    mission_dir = root / "harness-runtime" / "harness" / "missions" / mission
    _write_mission_slice(root, mission)
    contracts_dir = mission_dir / "contracts"
    contracts_dir.mkdir(parents=True)
    dependency_artifact = mission_dir / "dependency-impact.md"
    dependency_artifact.write_text("# dependency impact\n", encoding="utf-8")
    (mission_dir / "mission-contract.md").write_text("# contract\n", encoding="utf-8")
    framing_path = mission_dir / "intent-framing.yaml"
    framing_path.write_text(yaml.safe_dump(_intent_framing(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    contract_path = contracts_dir / "mission-contract.contract.yaml"
    _run_json(
        root,
        "contract",
        "fill",
        "--mission",
        mission,
        "--stage",
        "intake",
        "--artifact",
        str(contract_path),
        "--intent-framing",
        str(framing_path),
        "--template",
        "mission-contract",
    )
    doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    doc["control_contract"]["dependency_impact"] = {
        "required": True,
        "artifact": str(dependency_artifact),
        "review_role": "dependency-validity-reviewer",
        "claims": [{"id": "DEP-01", "claim": "Existing board data dependency is touched."}],
    }
    contract_path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")

    failed = _run(root, "contract", "check", "--artifact", str(contract_path), "--json")
    assert failed.returncode == 1
    failed_codes = {finding["code"] for finding in json.loads(failed.stdout)["findings"]}
    assert "invalid_dependency_impact_claim" in failed_codes
    assert "missing_dependency_impact_review" in failed_codes

    doc = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    doc["control_contract"]["dependency_impact"]["claims"][0].update(
        {
            "confidence": "medium",
            "source_evidence": ["runtime fixture"],
            "failure_mode": "Board status may drift from mission slice.",
            "validation_action": "Run contract check and board fixture tests.",
        }
    )
    contract_path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    review = _run_json(
        root,
        "contract",
        "record-review",
        "--artifact",
        str(contract_path),
        "--role",
        "dependency-validity-reviewer",
        "--verdict",
        "PASS",
        "--reviewed-obligation",
        "OBL-INTAKE-001",
        "--review-basis",
        str(dependency_artifact),
        "--subagent-id",
        "agent-1",
        "--model",
        "gpt-test",
        "--summary",
        "dependency impact is valid",
    )
    assert review["status"] == "PASS"
    effectiveness_review = _run_json(
        root,
        "contract",
        "record-review",
        "--artifact",
        str(contract_path),
        "--role",
        "mission-contract-effectiveness-reviewer",
        "--verdict",
        "PASS",
        "--subagent-id",
        "agent-2",
        "--model",
        "gpt-test",
        "--summary",
        "mission contract remains valid",
    )
    assert effectiveness_review["status"] == "PASS"
    passed = _run_json(root, "contract", "check", "--artifact", str(contract_path))
    assert passed["status"] == "PASS"
