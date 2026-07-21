"""Handlers for `harness verify ...` commands.

Spans compute-scope, run-tests, e2e-status, true-e2e-check, dispatch-worker,
dispatch-reviewer, detect-contradictions, compute-conclusion,
agent-eval-status, failure-path, and the aggregating gate-run.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from harness_cli_core.app.commands import contract_handlers as core_contract_handlers
from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.domain import behavior_graph as bg
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.findings import apply_compat_warning
from harness_cli_core.domain.contracts import (
    evaluate_reviewer_verdicts_for_gate,
    mission_has_tradeoff_approval,
)
from harness_cli_core.domain.verification import (
    BROWSER_PRIMARY_EVIDENCE_KINDS,
    NON_UI_PRIMARY_EVIDENCE_KINDS,
    evidence_role,
    is_ui_acceptance_trace,
    resolve_execution_brief_for_verify,
    resolve_verify_contract,
)


def cmd_verify_compute_scope(args: argparse.Namespace) -> int:
    """Output acceptance_list / task_list / test_layers / e2e_obligations /
    project_lint_enabled / required_evidence_matrix from the execution-brief.
    """
    root = Path(root_arg(args))
    mission = args.mission
    _brief_path, brief, err = resolve_execution_brief_for_verify(root, mission)
    if err or brief is None:
        return emit_payload(
            args,
            fail_payload(
                "verify.compute-scope",
                err or "brief_unloadable",
                f"Cannot load execution-brief for mission {mission}",
            ),
        )

    tasks = brief.get("tasks") or []
    acceptance_list: list[str] = []
    for t in tasks:
        if isinstance(t, dict):
            for ac in t.get("traces_to") or []:
                if isinstance(ac, str) and ac not in acceptance_list:
                    acceptance_list.append(ac)

    required_evidence_matrix: list[dict] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        task_id = t.get("id", "")
        for re_item in t.get("required_evidence") or []:
            if isinstance(re_item, dict):
                required_evidence_matrix.append(
                    {
                        "task_id": task_id,
                        "id": re_item.get("id", ""),
                        "path": re_item.get("path", ""),
                        "command": re_item.get("command", ""),
                        "verification_type": re_item.get(
                            "verification_type", re_item.get("type", "")
                        ),
                    }
                )

    execute_failure_ref: dict | None = None
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for er in t.get("execution_results") or []:
            if isinstance(er, dict) and er.get("failure_state"):
                execute_failure_ref = {
                    "task_id": t.get("id"),
                    "failure_state": er["failure_state"],
                }
                break
        if execute_failure_ref:
            break

    harness_config = root / "harness-runtime" / "config" / "harness.yaml"
    project_lint_enabled = False
    if harness_config.exists():
        try:
            cfg = yaml.safe_load(harness_config.read_text(encoding="utf-8")) or {}
            project_lint_enabled = bool((cfg.get("project_lint") or {}).get("enabled", False))
        except yaml.YAMLError:
            pass

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "verify.compute-scope",
            "mission_id": mission,
            "acceptance_list": acceptance_list,
            "task_list": [t.get("id") for t in tasks if isinstance(t, dict)],
            "test_layers": ["unit", "integration", "e2e"],
            "e2e_obligations": brief.get("e2e_obligations") or [],
            "project_lint_enabled": project_lint_enabled,
            "required_evidence_matrix": required_evidence_matrix,
            "execute_failure_ref": execute_failure_ref,
        },
    )


def cmd_verify_run_tests(args: argparse.Namespace) -> int:
    """Run a single test layer and write command evidence."""
    root = Path(root_arg(args))
    mission = args.mission
    layer = args.layer
    command = getattr(args, "command", None) or ""
    if not command:
        return emit_payload(
            args,
            fail_payload(
                "verify.run-tests",
                "command_required",
                "--command is required for verify run-tests",
            ),
        )
    traces_dir = root / "harness-runtime" / "harness" / "stages" / mission / "traces" / "cmd"
    traces_dir.mkdir(parents=True, exist_ok=True)
    started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    result = subprocess.run(
        command,
        shell=True,
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=300,
    )
    ended_at = dt.datetime.now(dt.timezone.utc).isoformat()
    cmd_id = f"cmd-{layer}-{started_at[:19].replace(':', '-').replace('T', '-')}"
    evidence = {
        "id": cmd_id,
        "kind": "command",
        "layer": layer,
        "command": command,
        "cwd": str(root),
        "exit_code": result.returncode,
        "started_at": started_at,
        "ended_at": ended_at,
        "result": "pass" if result.returncode == 0 else "fail",
        "stdout": result.stdout[:4096],
        "stderr": result.stderr[:4096],
        "artifact": str(traces_dir / f"{cmd_id}.json"),
    }
    (traces_dir / f"{cmd_id}.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    status = "PASS" if result.returncode == 0 else "FAIL"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "verify.run-tests",
            "mission_id": mission,
            "layer": layer,
            "command": command,
            "exit_code": result.returncode,
            "evidence_id": cmd_id,
            "artifact": evidence["artifact"],
        },
    )


def cmd_verify_e2e_status(args: argparse.Namespace) -> int:
    """Return current e2e-status.json content."""
    root = Path(root_arg(args))
    mission = args.mission
    e2e_path = root / "harness-runtime" / "harness" / "traces" / mission / "e2e" / "e2e-status.json"
    if not e2e_path.exists():
        e2e_path = root / "harness-runtime" / "harness" / "stages" / mission / "traces" / "e2e" / "e2e-status.json"
    if not e2e_path.exists():
        payload = {
            "status": "BLOCKED",
            "control": "verify.e2e-status",
            "mission_id": mission,
            "message": "e2e-status.json not found; run the E2E three-step pipeline first",
        }
        if getattr(args, "json", False):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"verify.e2e-status: BLOCKED — {payload['message']}")
        return 0
    try:
        data = json.loads(e2e_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return emit_payload(
            args,
            fail_payload(
                "verify.e2e-status",
                "e2e_status_invalid",
                "e2e-status.json is not valid JSON",
            ),
        )
    return emit_payload(
        args,
        {
            "status": data.get("status", "UNKNOWN"),
            "control": "verify.e2e-status",
            "mission_id": mission,
            "e2e_status": data,
            "artifact": str(e2e_path),
        },
    )


def cmd_verify_dispatch_worker(args: argparse.Namespace) -> int:
    """Generate the verification-engineer dispatch envelope."""
    root = Path(root_arg(args))
    mission = args.mission
    envelope_dir = (
        root / "harness-runtime" / "harness" / "stages" / mission / "traces" / "dispatches"
    )
    envelope_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    envelope = {
        "dispatch_id": f"dispatch-worker-{now.strftime('%Y%m%d-%H%M%S')}",
        "agent": "verification-engineer",
        "mission_id": mission,
        "execution_mode": "spawn_agent",
        "created_at": now.isoformat(),
        "write_scope": [
            f"harness-runtime/harness/artifacts/{mission}/verify/verification-report.md",
            f"harness-runtime/harness/stages/{mission}/contracts/verification-report.contract.yaml",
            f"harness-runtime/harness/traces/{mission}/**",
        ],
    }
    out = envelope_dir / "worker-dispatch.json"
    out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "verify.dispatch-worker",
            "mission_id": mission,
            "dispatch_id": envelope["dispatch_id"],
            "envelope_path": str(out),
        },
    )


def cmd_verify_dispatch_reviewer(args: argparse.Namespace) -> int:
    """Generate the reviewer dispatch envelope. Blocks main_agent_fallback."""
    root = Path(root_arg(args))
    mission = args.mission
    envelope_dir = (
        root / "harness-runtime" / "harness" / "stages" / mission / "traces" / "dispatches"
    )
    envelope_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    envelope = {
        "dispatch_id": f"dispatch-reviewer-{now.strftime('%Y%m%d-%H%M%S')}",
        "agent": "verification-effectiveness-reviewer",
        "mission_id": mission,
        "execution_mode": "spawn_agent",
        "readonly": True,
        "created_at": now.isoformat(),
        "main_agent_fallback": "BLOCKED",
        "note": "reviewer PASS must be from spawn_agent or human checkpoint; main_agent_fallback is rejected",
    }
    out = envelope_dir / "reviewer-dispatch.json"
    out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "verify.dispatch-reviewer",
            "mission_id": mission,
            "dispatch_id": envelope["dispatch_id"],
            "envelope_path": str(out),
        },
    )


def cmd_verify_detect_contradictions(args: argparse.Namespace) -> int:
    """Compare acceptance_trace.conclusion vs evidence results and report contradictions."""
    root = Path(root_arg(args))
    mission = args.mission
    artifact_arg = getattr(args, "artifact", None)
    _path, contract, err = resolve_verify_contract(root, mission, artifact_arg)
    if err or contract is None:
        return emit_payload(
            args,
            fail_payload(
                "verify.detect-contradictions",
                err or "contract_unloadable",
                f"Cannot load verification contract for mission {mission}",
            ),
        )

    contradictions: list[dict] = []
    command_evidence: dict[str, dict] = {}
    for ce in contract.get("command_evidence") or []:
        if isinstance(ce, dict) and ce.get("id"):
            command_evidence[ce["id"]] = ce

    for ac in contract.get("acceptance_trace") or []:
        if not isinstance(ac, dict):
            continue
        acceptance_id = ac.get("id") or ac.get("acceptance_id") or "<unknown>"
        conclusion = str(ac.get("conclusion", "")).lower()
        if conclusion != "pass":
            continue
        for cmd_id in ac.get("command_evidence_ids") or []:
            ce = command_evidence.get(cmd_id)
            if ce is None:
                continue
            ce_result = str(ce.get("result", "")).lower()
            if ce_result in {"fail", "blocked", "unavailable"}:
                contradictions.append(
                    {
                        "acceptance_id": acceptance_id,
                        "command_evidence_id": cmd_id,
                        "issue": f"acceptance_trace.conclusion=pass but command_evidence[{cmd_id}].result={ce_result!r}",
                    }
                )

    status = "FAIL" if contradictions else "PASS"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "verify.detect-contradictions",
            "mission_id": mission,
            "contradictions": contradictions,
        },
    )


def cmd_verify_compute_conclusion(args: argparse.Namespace) -> int:
    """Return PASS / FAIL / BLOCKED / PASS_WITH_RISK conclusion for verify."""
    root = Path(root_arg(args))
    mission = args.mission
    _path, contract, err = resolve_verify_contract(root, mission)
    if err or contract is None:
        return emit_payload(
            args,
            fail_payload(
                "verify.compute-conclusion",
                err or "contract_unloadable",
                f"Cannot load verification contract for mission {mission}",
            ),
        )

    execute_failure_ref = contract.get("execute_failure_ref")
    if execute_failure_ref:
        return emit_payload(
            args,
            {
                "status": "PASS",
                "control": "verify.compute-conclusion",
                "mission_id": mission,
                "conclusion": "BLOCKED",
                "failure_path": "blocked_execute_failure",
                "reason": f"execute already FAILED: {execute_failure_ref}",
            },
        )

    acceptance_traces = contract.get("acceptance_trace") or []
    conclusions = [
        str(ac.get("conclusion", "")).lower()
        for ac in acceptance_traces
        if isinstance(ac, dict)
    ]
    fail_count = sum(1 for c in conclusions if c in {"fail", "failed"})
    blocked_count = sum(1 for c in conclusions if c == "blocked")
    risk_count = sum(1 for c in conclusions if c == "pass_with_risk")

    if blocked_count > 0:
        conclusion = "BLOCKED"
        failure_path = "decision_gate"
    elif fail_count > 0:
        conclusion = "FAIL"
        failure_path = "bug_fix"
    elif risk_count > 0:
        conclusion = "PASS_WITH_RISK"
        failure_path = None
    else:
        conclusion = "PASS"
        failure_path = None

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "verify.compute-conclusion",
            "mission_id": mission,
            "conclusion": conclusion,
            "failure_path": failure_path,
            "ac_summary": {
                "total": len(conclusions),
                "pass": sum(1 for c in conclusions if c in {"pass", "passed"}),
                "fail": fail_count,
                "blocked": blocked_count,
                "pass_with_risk": risk_count,
            },
        },
    )


def cmd_verify_agent_eval_status(args: argparse.Namespace) -> int:
    """Check if agent-eval is required and surface its status."""
    root = Path(root_arg(args))
    mission = args.mission
    eval_report = (
        root / "harness-runtime" / "harness" / "stages" / mission / "agent-eval-report.md"
    )
    harness_config = root / "harness-runtime" / "config" / "harness.yaml"
    require_agent_eval = False
    if harness_config.exists():
        try:
            cfg = yaml.safe_load(harness_config.read_text(encoding="utf-8")) or {}
            ae = cfg.get("agent_engineering") or {}
            require_agent_eval = bool(ae.get("require_agent_eval", False))
        except yaml.YAMLError:
            pass

    if not require_agent_eval:
        return emit_payload(
            args,
            {
                "status": "PASS",
                "control": "verify.agent-eval-status",
                "mission_id": mission,
                "required": False,
                "passed": True,
                "failure_impact": None,
            },
        )

    if not eval_report.exists():
        return emit_payload(
            args,
            {
                "status": "BLOCKED",
                "control": "verify.agent-eval-status",
                "mission_id": mission,
                "required": True,
                "passed": False,
                "failure_impact": "agent-eval-report.md missing; run agent-eval skill",
            },
        )

    text = eval_report.read_text(encoding="utf-8")
    passed = "High" not in text or "未通过" not in text
    return emit_payload(
        args,
        {
            "status": "PASS" if passed else "FAIL",
            "control": "verify.agent-eval-status",
            "mission_id": mission,
            "required": True,
            "passed": passed,
            "failure_impact": None if passed else "agent-eval has High severity failures",
        },
    )


_VALID_FAILURE_KINDS = {
    "bug_fix",
    "execute",
    "decision_gate",
    "receiving_review",
    "blocked_execute_failure",
    "execute_evidence_missing",
}


def cmd_verify_failure_path(args: argparse.Namespace) -> int:
    """Record a typed failure path for the mission."""
    root = Path(root_arg(args))
    mission = args.mission
    kind = args.kind
    if kind not in _VALID_FAILURE_KINDS:
        return emit_payload(
            args,
            fail_payload(
                "verify.failure-path",
                "invalid_kind",
                f"kind must be one of {sorted(_VALID_FAILURE_KINDS)}",
            ),
        )
    traces_dir = root / "harness-runtime" / "harness" / "stages" / mission / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "kind": kind,
        "mission_id": mission,
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "stage": "verify",
    }
    (traces_dir / "failure_path.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "verify.failure-path",
            "mission_id": mission,
            "kind": kind,
            "record_path": str(traces_dir / "failure_path.json"),
        },
    )


def cmd_verify_true_e2e_check(args: argparse.Namespace) -> int:
    """Verify UI acceptance scenarios are backed by real browser-path primary evidence."""
    root = Path(root_arg(args))
    mission = args.mission
    _path, contract, err = resolve_verify_contract(root, mission)
    if err or contract is None:
        return emit_payload(
            args,
            fail_payload(
                "verify.true-e2e-check",
                err or "contract_unloadable",
                f"Cannot load verification contract for mission {mission}",
            ),
        )

    result_evidence: dict[str, dict[str, Any]] = {}
    for item in contract.get("result_evidence") or []:
        if isinstance(item, dict) and item.get("id"):
            result_evidence[str(item["id"])] = item

    failed_checks: list[dict[str, object]] = []
    checked_ui_acs = 0
    for ac in contract.get("acceptance_trace") or []:
        if not isinstance(ac, dict):
            continue
        if str(ac.get("conclusion") or "").lower() != "pass":
            continue
        if not is_ui_acceptance_trace(ac):
            continue
        checked_ui_acs += 1
        acceptance_id = str(ac.get("id") or ac.get("acceptance_id") or "<unknown>")
        res_ids = [str(rid) for rid in (ac.get("result_evidence_ids") or [])]
        browser_primary = False
        for rid in res_ids:
            ev = result_evidence.get(rid) or {}
            kind = str(ev.get("kind") or "").lower()
            role = evidence_role(ev)
            if kind in BROWSER_PRIMARY_EVIDENCE_KINDS and role in {
                "",
                "primary",
                "primary_user_path",
                "user_path",
                "browser_user_flow",
            }:
                browser_primary = True
            if kind in NON_UI_PRIMARY_EVIDENCE_KINDS and role in {
                "",
                "primary",
                "primary_user_path",
                "user_path",
                "assertion",
            }:
                failed_checks.append(
                    {
                        "check": "true_e2e_api_primary_not_allowed",
                        "code": "TRUE_E2E_API_PRIMARY_NOT_ALLOWED",
                        "acceptance_id": acceptance_id,
                        "evidence_id": rid,
                        "kind": kind,
                        "message": "API/DB/internal/mock evidence cannot be primary evidence for a UI acceptance scenario.",
                    }
                )
            if kind == "mock" and not (
                ev.get("api_contract_ref")
                or ev.get("contract_ref")
                or ev.get("fixture_parity_evidence_id")
                or ev.get("fixture_parity")
            ):
                failed_checks.append(
                    {
                        "check": "true_e2e_mock_without_parity",
                        "code": "TRUE_E2E_MOCK_WITHOUT_PARITY",
                        "acceptance_id": acceptance_id,
                        "evidence_id": rid,
                        "message": "Mock evidence needs API contract or fixture parity evidence when used as auxiliary UI acceptance evidence.",
                    }
                )
        if not browser_primary:
            failed_checks.append(
                {
                    "check": "true_e2e_primary_browser_evidence_missing",
                    "code": "TRUE_E2E_PRIMARY_BROWSER_EVIDENCE_MISSING",
                    "acceptance_id": acceptance_id,
                    "message": (
                        "UI acceptance scenario pass requires real browser-path primary evidence "
                        f"with kind in {sorted(BROWSER_PRIMARY_EVIDENCE_KINDS)}."
                    ),
                }
            )

    findings = [dict(item, level="FAIL") for item in failed_checks]
    status, compat_failed = apply_compat_warning(args, findings)
    return emit_payload(
        args,
        {
            "status": status,
            "control": "verify.true-e2e-check",
            "mission_id": mission,
            "checked_ui_acs": checked_ui_acs,
            "findings": findings,
            "failed_checks": compat_failed,
        },
    )


def _prototype_coverage_exemptions(contract: dict[str, Any]) -> dict[str, str]:
    """读契约可选字段 ``prototype_coverage_exemptions``（列表 of {id, reason}）→
    ``{id: reason}``。缺字段 / 形态不符 → 空 dict（无豁免）。镜像 stage-gate
    check_contracts 的同名 helper，使 verify 门与下游覆盖率门豁免登记同构。"""
    out: dict[str, str] = {}
    for item in contract.get("prototype_coverage_exemptions") or []:
        if not isinstance(item, dict):
            continue
        eid = str(item.get("id") or "")
        if eid:
            out[eid] = str(item.get("reason") or "")
    return out


def _resolve_covered_testids(
    contract: dict[str, Any] | None, required_testids: set[str]
) -> tuple[set[str] | None, str]:
    """求「已被通过的 e2e 断言覆盖的 behavior-graph testid 集」。

    **来源选择（务实、非破坏）**：verification-report contract 的 ``result_evidence``
    是 verification-engineer 已经在记录的结构化证据，且能关联到通过的 acceptance_trace。
    e2e-status.json 的义务以 capability 为粒度，不记录 testid→result 映射，扩它需要写一个
    脆弱的「扫测试源码找 behavior-graph testid」解析器（高成本、低信号），故不采用。

    本实现只在 **通过的 UI acceptance_trace** 关联的 ``result_evidence`` 上扫 testid：
    既支持显式字段（``testid`` / ``testids`` / ``data_testid`` / ``data-testid``），也在证据
    自由文本（``summary`` / ``detail`` / ``locator`` / ``evidence`` / ``note``）里按
    ``required_testids`` 全集做子串命中——只认图已声明为义务的 testid，避免误抓无关 token。

    返回 ``(covered_or_None, source)``：

    - contract 不可用 → ``(None, "source_unavailable")``，调用方据此整门跳过（**绝不 FAIL**）。
    - 否则 ``(命中集合, "verification_report_result_evidence")``。
    """
    if contract is None:
        return None, "source_unavailable"

    result_evidence: dict[str, dict[str, Any]] = {}
    for item in contract.get("result_evidence") or []:
        if isinstance(item, dict) and item.get("id"):
            result_evidence[str(item["id"])] = item

    # 只取「结论通过」的 acceptance_trace 关联的 result_evidence id（未通过的断言不算覆盖）。
    passed_result_ids: set[str] = set()
    for ac in contract.get("acceptance_trace") or []:
        if not isinstance(ac, dict):
            continue
        if str(ac.get("conclusion") or "").lower() != "pass":
            continue
        for rid in ac.get("result_evidence_ids") or []:
            passed_result_ids.add(str(rid))

    covered: set[str] = set()
    _testid_fields = ("testid", "testids", "data_testid", "data-testid")
    _text_fields = ("summary", "detail", "locator", "evidence", "note", "description")
    for rid in passed_result_ids:
        ev = result_evidence.get(rid)
        if not isinstance(ev, dict):
            continue
        # 显式 testid 字段（标量或列表）。
        for fld in _testid_fields:
            val = ev.get(fld)
            if isinstance(val, str) and val.strip():
                covered.add(val.strip())
            elif isinstance(val, list):
                covered |= {str(v).strip() for v in val if str(v).strip()}
        # 自由文本子串命中：只认 required 集里的 testid，避免误抓。
        blob = " ".join(
            str(ev.get(fld) or "") for fld in _text_fields
        )
        if blob:
            covered |= {tid for tid in required_testids if tid and tid in blob}

    return covered, "verification_report_result_evidence"


def cmd_verify_prototype_alignment_check(args: argparse.Namespace) -> int:
    """verify 阶段原型对齐 e2e 机器门：图里声明为 E2E 种子边（edge.e2e_obligation=true）
    的转移，其 edge.testid 必须被某条通过的 e2e 断言绑定，否则 FAIL。

    非破坏铁律：无 mission-local behavior-graph / 无 e2e_obligation 边 / covered 源不可得
    → 零 failed_check 跳过，对既有非 UI mission 行为不变。"""
    root = Path(root_arg(args))
    mission = args.mission

    # 1. mission-local behavior-graph。无图（非 UI / 未跑 interaction）→ 跳过。
    _gpath, graph = bg.load_behavior_graph(root, mission)
    if not graph:
        return emit_payload(
            args,
            {
                "status": "PASS",
                "control": "verify.prototype-alignment-check",
                "mission_id": mission,
                "findings": [],
                "failed_checks": [],
                "warnings": [],
                "source": "no_behavior_graph",
                "message": "无 mission-local behavior-graph（非 UI 任务 / 未跑 interaction），跳过原型对齐 e2e 门。",
            },
        )

    # 必需 testid 全集（占位 / 缺失的义务边在纯函数里转 WARN，不进必需集）。
    required_testids: set[str] = set()
    for e in bg.graph_tables(graph).get("edges", []):
        if not e.get("e2e_obligation"):
            continue
        testid = str(e.get("testid") or "")
        if not bg.is_placeholder_text(testid):
            required_testids.add(testid)

    # 无 e2e_obligation 义务边 → 跳过（仍可能有占位义务边的 WARN，下面纯函数会带出）。
    if not required_testids:
        findings = bg.prototype_e2e_alignment_coverage(
            graph=graph, covered_testids=set(), exemptions={},
        )
        warnings = [f for f in findings if f.get("level") == "WARN"]
        return emit_payload(
            args,
            {
                "status": "PASS",
                "control": "verify.prototype-alignment-check",
                "mission_id": mission,
                "findings": findings,
                "failed_checks": [],
                "warnings": warnings,
                "source": "no_e2e_obligation_edge",
                "message": "behavior-graph 无带 testid 的 e2e_obligation 边，跳过原型对齐 e2e 门。",
            },
        )

    # 2. covered_testids 来源 + 契约豁免。contract 不可得 → source_unavailable 跳过。
    _cpath, contract, _cerr = resolve_verify_contract(root, mission)
    covered_testids, source = _resolve_covered_testids(contract, required_testids)
    exemptions = _prototype_coverage_exemptions(contract or {})

    if covered_testids is None:
        # 拿不到覆盖证据：绝不误 FAIL，整门跳过并标注，由 reviewer / 人判断。
        return emit_payload(
            args,
            {
                "status": "PASS",
                "control": "verify.prototype-alignment-check",
                "mission_id": mission,
                "findings": [],
                "failed_checks": [],
                "warnings": [],
                "source": source,
                "message": (
                    "verification-report contract 不可得，无法解析已通过 e2e 断言绑定的 testid；"
                    "原型对齐 e2e 门跳过（source_unavailable），由 reviewer / 人判断。"
                ),
            },
        )

    # 3. 调纯函数判定。
    findings = bg.prototype_e2e_alignment_coverage(
        graph=graph, covered_testids=covered_testids, exemptions=exemptions,
    )
    failed_checks = [
        {
            "check": "prototype_e2e_alignment",
            "code": f.get("code"),
            "testid": f.get("testid"),
            "edge": f.get("edge"),
            "message": f.get("message"),
        }
        for f in findings
        if f.get("level") == "FAIL"
    ]
    warnings = [f for f in findings if f.get("level") == "WARN"]
    status = "FAIL" if failed_checks else "PASS"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "verify.prototype-alignment-check",
            "mission_id": mission,
            "required_testids": sorted(required_testids),
            "covered_testids": sorted(covered_testids),
            "findings": findings,
            "failed_checks": failed_checks,
            "warnings": warnings,
            "source": source,
        },
    )


def cmd_verify_gate_run(args: argparse.Namespace) -> int:
    """Aggregating gate for the verify stage.

    Wraps `contract check-acceptance-trace`, `verify true-e2e-check`,
    `verify detect-contradictions`, and `verify compute-conclusion`, then
    writes per-check flag files when PASS.
    """
    root = Path(root_arg(args))
    mission = args.mission

    # 1. contract check-acceptance-trace
    acceptance_trace_args = argparse.Namespace(**vars(args))
    acceptance_trace_args.mission = mission
    acceptance_trace_args.artifact = None
    acceptance_trace_args.upstream = None
    acceptance_trace_buf = io.StringIO()
    with contextlib.redirect_stdout(acceptance_trace_buf):
        core_contract_handlers.cmd_contract_check_acceptance_trace(acceptance_trace_args)
    try:
        acceptance_trace_result = json.loads(acceptance_trace_buf.getvalue())
    except json.JSONDecodeError:
        acceptance_trace_result = {"status": "BLOCKED", "failed_checks": []}

    # 2. true E2E check: UI ACs require browser-path primary evidence.
    true_e2e_args = argparse.Namespace(**vars(args))
    true_e2e_buf = io.StringIO()
    with contextlib.redirect_stdout(true_e2e_buf):
        cmd_verify_true_e2e_check(true_e2e_args)
    try:
        true_e2e_result = json.loads(true_e2e_buf.getvalue())
    except json.JSONDecodeError:
        true_e2e_result = {"status": "BLOCKED", "failed_checks": []}

    # 3. detect-contradictions
    contra_args = argparse.Namespace(**vars(args))
    contra_args.artifact = None
    contra_buf = io.StringIO()
    with contextlib.redirect_stdout(contra_buf):
        cmd_verify_detect_contradictions(contra_args)
    try:
        contra_result = json.loads(contra_buf.getvalue())
    except json.JSONDecodeError:
        contra_result = {"status": "BLOCKED", "contradictions": []}

    # 4. compute-conclusion
    concl_args = argparse.Namespace(**vars(args))
    concl_buf = io.StringIO()
    with contextlib.redirect_stdout(concl_buf):
        cmd_verify_compute_conclusion(concl_args)
    try:
        concl_result = json.loads(concl_buf.getvalue())
    except json.JSONDecodeError:
        concl_result = {"status": "BLOCKED", "conclusion": "BLOCKED"}

    failed_checks: list[dict] = []
    if acceptance_trace_result.get("status") not in {"PASS"}:
        for fc in acceptance_trace_result.get("failed_checks") or []:
            failed_checks.append(fc)
        if not acceptance_trace_result.get("failed_checks"):
            failed_checks.append(
                {
                    "check": "contract.check-acceptance-trace",
                    "status": acceptance_trace_result.get("status"),
                }
            )
    if true_e2e_result.get("status") not in {"PASS"}:
        for fc in true_e2e_result.get("failed_checks") or []:
            failed_checks.append(fc)
        if not true_e2e_result.get("failed_checks"):
            failed_checks.append(
                {
                    "check": "verify.true-e2e-check",
                    "status": true_e2e_result.get("status"),
                }
            )
    if contra_result.get("status") not in {"PASS"}:
        for c in contra_result.get("contradictions") or []:
            failed_checks.append({"check": "verify.detect-contradictions", **c})

    # 5. reviewer role_verdict 纳入：HOLD/BLOCKED 阻断 gate（除非已有 tradeoff 豁免）。
    # 非破坏：contract 缺失 / 无 role_verdicts / 无 reviewer verdict 时优雅跳过。
    _vpath, verify_contract, _verr = resolve_verify_contract(root, mission)
    reviewer_warnings: list[dict] = []
    if verify_contract is not None:
        has_approval = mission_has_tradeoff_approval(root, mission)
        verdict_signals = evaluate_reviewer_verdicts_for_gate(
            verify_contract, has_tradeoff_approval=has_approval
        )
        failed_checks.extend(verdict_signals["failed_checks"])
        reviewer_warnings = verdict_signals["warnings"]

    # 6. 原型对齐 e2e 门：e2e_obligation 边的 testid 须被通过的 e2e 断言绑定。
    # 非破坏：无 behavior-graph / 无义务边 / covered 源不可得 → 子门 PASS 零 failed_check，
    # gate run 对既有非 UI mission 行为不变。
    proto_align_args = argparse.Namespace(**vars(args))
    proto_align_buf = io.StringIO()
    with contextlib.redirect_stdout(proto_align_buf):
        cmd_verify_prototype_alignment_check(proto_align_args)
    try:
        proto_align_result = json.loads(proto_align_buf.getvalue())
    except json.JSONDecodeError:
        proto_align_result = {"status": "BLOCKED", "failed_checks": []}
    if proto_align_result.get("status") not in {"PASS"}:
        for fc in proto_align_result.get("failed_checks") or []:
            failed_checks.append(fc)
        if not proto_align_result.get("failed_checks"):
            failed_checks.append(
                {
                    "check": "verify.prototype-alignment-check",
                    "status": proto_align_result.get("status"),
                }
            )

    overall = "FAIL" if failed_checks else (concl_result.get("conclusion") or "PASS")
    if overall == "PASS":
        traces_dir = root / "harness-runtime" / "harness" / "stages" / mission / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)
        (traces_dir / "gate_run_pass.flag").write_text("PASS", encoding="utf-8")
        if true_e2e_result.get("status") == "PASS":
            (traces_dir / "true_e2e_pass.flag").write_text("PASS", encoding="utf-8")
        if not contra_result.get("contradictions"):
            (traces_dir / "contradictions_pass.flag").write_text("PASS", encoding="utf-8")
        if proto_align_result.get("status") == "PASS":
            (traces_dir / "prototype_alignment_pass.flag").write_text("PASS", encoding="utf-8")

    return emit_payload(
        args,
        {
            "status": overall,
            "control": "verify.gate-run",
            "mission_id": mission,
            "conclusion": concl_result.get("conclusion"),
            "failed_checks": failed_checks,
            "reviewer_warnings": reviewer_warnings,
            "acceptance_trace_status": acceptance_trace_result.get("status"),
            "true_e2e_status": true_e2e_result.get("status"),
            "contradictions_status": contra_result.get("status"),
            "prototype_alignment_status": proto_align_result.get("status"),
        },
    )


__all__ = [
    "cmd_verify_compute_scope",
    "cmd_verify_run_tests",
    "cmd_verify_e2e_status",
    "cmd_verify_dispatch_worker",
    "cmd_verify_dispatch_reviewer",
    "cmd_verify_detect_contradictions",
    "cmd_verify_compute_conclusion",
    "cmd_verify_agent_eval_status",
    "cmd_verify_failure_path",
    "cmd_verify_true_e2e_check",
    "cmd_verify_prototype_alignment_check",
    "cmd_verify_gate_run",
]
