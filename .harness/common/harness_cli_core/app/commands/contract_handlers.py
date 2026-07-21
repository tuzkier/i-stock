from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg, with_json
from harness_cli_core.domain.contracts import (
    add_execution_result,
    add_role_verdict,
    apply_intent_framing,
    apply_contract_patch,
    archive_review_round,
    build_contract_init_document,
    build_contract_summary_payload,
    build_recheck_pending_payload,
    check_acceptance_trace_payload,
    detect_finding_conflicts,
    finding_ownership_violations,
    load_code_review_contract,
    required_evidence_ids,
    resolve_execution_brief_for_verify,
    resolve_verify_contract,
    contract_hygiene_payload,
    contract_template_path,
    control_contract_document,
    dispute_escalation_signal,
    validate_role_verdict_dispatch,
)
from harness_cli_core.domain.autonomy import AUTONOMY_CANONICAL_LEVELS, autonomy_alias_map, reject_legacy_autonomy_level
from harness_cli_core.domain.manifest import load_manifest, write_manifest
from harness_cli_core.infra.io import load_yaml, write_yaml
from harness_cli_core.infra.process import run_python
from harness_cli_core.infra.time import now_iso
from harness_cli_core.infra.runtime_paths import load_runtime_config, mission_status_path, relpath, resolve_path, runtime_harness_root


COMMON_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = COMMON_ROOT.parent
SKILLS_ROOT = COMMON_ROOT / "skills"


def script(*parts: str) -> Path:
    return SKILLS_ROOT.joinpath(*parts)


def _contract_obligation_ids(contract: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in contract.get("obligations") or []:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
    graph = contract.get("evidence_graph") if isinstance(contract.get("evidence_graph"), dict) else {}
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), dict) else {}
    for item in nodes.get("obligations") or []:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
    return list(dict.fromkeys(ids))


def cmd_contract_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    forwarded = ["--root", str(root), "--artifact", str(artifact)]
    for upstream in args.upstream or []:
        forwarded.extend(["--upstream", upstream])
    if args.allow_placeholders:
        forwarded.append("--allow-placeholders")
    return run_python(script("stage-gate", "scripts", "check_contracts.py"), with_json(args, forwarded))


def cmd_contract_record_review(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    if artifact is None or not artifact.exists():
        return emit_payload(args, fail_payload("contract.record-review", "missing_contract_artifact", f"Contract artifact not found: {args.artifact}"))
    document, contract = control_contract_document(artifact)
    timestamp = now_iso()
    reviewed_obligations = getattr(args, "reviewed_obligation", None) or _contract_obligation_ids(contract)
    docs = getattr(args, "review_basis", None) or [str(artifact)]
    if isinstance(docs, str):
        docs = [docs]
    # Build review_basis as the canonical dict form bound to the contract's
    # work_graph_artifact (node_id + artifact_version), which `contract check`
    # (role_verdict_missing_artifact_version) requires for PASS / PASS_WITH_RISK
    # verdicts. Fall back to a flat doc list only when the contract has no
    # work_graph_artifact to bind against.
    wga = contract.get("work_graph_artifact") if isinstance(contract.get("work_graph_artifact"), dict) else {}
    if wga.get("node_id") and wga.get("artifact_version"):
        review_basis: Any = {
            "work_graph_artifact": {
                "node_id": wga.get("node_id"),
                "artifact_version": wga.get("artifact_version"),
            },
            "docs": docs,
        }
    else:
        review_basis = docs
    verdict = {
        "id": f"RV-{args.role}-{len(contract.get('role_verdicts') or []) + 1}",
        "role": args.role,
        "verdict": args.verdict,
        "reviewed_obligations": reviewed_obligations,
        "review_basis": review_basis,
        "summary": args.summary,
        "dispatch": {
            "subagent_id": args.subagent_id,
            "model": args.model,
            "execution_mode": "spawn_agent",
            "started_at": timestamp,
            "completed_at": timestamp,
        },
    }
    dispatch_reject = validate_role_verdict_dispatch(verdict)
    if dispatch_reject is not None:
        payload = fail_payload("contract.record-review", str(dispatch_reject["code"]), str(dispatch_reject["message"]))
        payload["findings"][0].update({key: value for key, value in dispatch_reject.items() if key not in {"code", "message"}})
        return emit_payload(args, payload)
    try:
        action = add_role_verdict(contract, verdict)
    except ValueError as exc:
        return emit_payload(args, fail_payload("contract.record-review", "invalid_role_verdicts", str(exc)))
    rounds_used = archive_review_round(contract, timestamp=timestamp, verdicts=[verdict])
    write_manifest(artifact, document)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "contract.record-review",
            "contract": relpath(root, artifact),
            "action": action,
            "verdict": verdict,
            "applied": [
                {"target": "control_contract.effectiveness_review.rounds_used", "value": rounds_used},
                {"target": "control_contract.role_verdicts", "op": action},
            ],
            "findings": [],
        },
    )


def cmd_contract_init(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    template_path = contract_template_path(root, args.template, package_root=PACKAGE_ROOT)
    if not template_path.exists():
        return emit_payload(args, fail_payload("contract.init", "missing_contract_template", f"Contract template not found: {template_path}"))
    document = load_yaml(template_path)
    if not document:
        return emit_payload(args, fail_payload("contract.init", "invalid_contract_template", f"Contract template is empty or invalid: {template_path}"))
    materialized, contract, applied_fields = build_contract_init_document(
        document,
        mission_id=args.mission,
        stage=args.stage,
        node_id=args.node,
        artifact_version=args.artifact_version,
        review_strategy=args.review_strategy,
        capability=args.capability,
    )
    output = resolve_path(root, args.output) if args.output else root / f"harness-runtime/harness/stages/{args.mission}/contracts/{args.template}.contract.yaml"
    assert output is not None
    if output.exists() and not args.replace:
        return emit_payload(args, fail_payload("contract.init", "contract_exists", f"Contract already exists: {relpath(root, output)}"))
    write_manifest(output, materialized)
    hygiene = contract_hygiene_payload(contract)
    return emit_payload(
        args,
        {
            "status": hygiene["status"],
            "control": "contract.init",
            "contract": relpath(root, output),
            "template": relpath(root, template_path),
            "applied_fields": applied_fields,
            "hygiene": hygiene,
            "findings": [],
        },
    )


def cmd_contract_fill(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    framing_path = resolve_path(root, args.intent_framing)
    if framing_path is None or not framing_path.exists():
        return emit_payload(args, fail_payload("contract.fill", "missing_intent_framing", f"Intent framing manifest not found: {args.intent_framing}"))
    framing = load_manifest(framing_path)
    if not isinstance(framing, dict) or not framing:
        return emit_payload(args, fail_payload("contract.fill", "invalid_intent_framing", "Intent framing manifest must be a non-empty YAML object"))

    legacy_reject = reject_legacy_autonomy_level(
        "contract.fill",
        framing.get("autonomy_level"),
        autonomy_alias_map(load_runtime_config(root)),
    )
    if legacy_reject is not None:
        return emit_payload(args, legacy_reject)

    if artifact is None:
        return emit_payload(args, fail_payload("contract.fill", "missing_artifact_path", "--artifact must be a resolvable path"))
    if not artifact.exists():
        if not args.template:
            return emit_payload(
                args,
                fail_payload(
                    "contract.fill",
                    "contract_missing_no_template",
                    f"Contract not found and --template not provided: {relpath(root, artifact)}",
                ),
            )
        template_path = contract_template_path(root, args.template, package_root=PACKAGE_ROOT)
        if not template_path.exists():
            return emit_payload(args, fail_payload("contract.fill", "missing_contract_template", f"Contract template not found: {template_path}"))
        document = load_yaml(template_path)
        if not document:
            return emit_payload(args, fail_payload("contract.fill", "invalid_contract_template", f"Contract template is empty or invalid: {template_path}"))
        document, _contract, _applied = build_contract_init_document(
            document,
            mission_id=args.mission,
            stage=args.stage,
            artifact_version="v1",
        )
        artifact.parent.mkdir(parents=True, exist_ok=True)
        write_manifest(artifact, document)

    document, contract = control_contract_document(artifact)
    contract.setdefault("mission_id", args.mission)
    contract.setdefault("stage", args.stage)

    try:
        applied = apply_intent_framing(contract, framing)
    except ValueError as exc:
        return emit_payload(args, fail_payload("contract.fill", "invalid_intent_framing", str(exc)))

    write_manifest(artifact, document)
    hygiene = contract_hygiene_payload(contract)

    mission_status_synced = False
    canonical_level = (
        contract.get("autonomy", {}).get("level")
        if isinstance(contract.get("autonomy"), dict)
        else None
    )
    if isinstance(canonical_level, str) and canonical_level in AUTONOMY_CANONICAL_LEVELS:
        status_path = mission_status_path(root)
        if status_path.exists():
            status_doc = load_yaml(status_path)
            if isinstance(status_doc, dict) and isinstance(status_doc.get(args.mission), dict):
                entry = status_doc[args.mission]
                if entry.get("autonomy_level") != canonical_level:
                    entry["autonomy_level"] = canonical_level
                    write_yaml(status_path, status_doc)
                    mission_status_synced = True
                else:
                    mission_status_synced = True

    return emit_payload(
        args,
        {
            "status": hygiene["status"],
            "control": "contract.fill",
            "contract": relpath(root, artifact),
            "intent_framing": relpath(root, framing_path),
            "applied_fields": applied,
            "mission_status_synced": mission_status_synced,
            "hygiene": hygiene,
            "findings": [],
        },
    )
    output = resolve_path(root, args.output) if args.output else root / f"harness-runtime/harness/stages/{args.mission}/contracts/{args.template}.contract.yaml"
    assert output is not None
    if output.exists() and not args.replace:
        return emit_payload(args, fail_payload("contract.init", "contract_exists", f"Contract already exists: {relpath(root, output)}"))
    write_manifest(output, materialized)
    hygiene = contract_hygiene_payload(contract)
    return emit_payload(
        args,
        {
            "status": hygiene["status"],
            "control": "contract.init",
            "contract": relpath(root, output),
            "template": relpath(root, template_path),
            "applied_fields": applied_fields,
            "hygiene": hygiene,
            "findings": [],
        },
    )


def cmd_contract_summary(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission_id = args.mission
    artifact = resolve_path(root, args.artifact) if args.artifact else None
    if artifact is None:
        artifact = (
            runtime_harness_root(root)
            / "missions"
            / mission_id
            / "contracts"
            / "mission-contract.contract.yaml"
        )
    if not artifact.exists():
        return emit_payload(
            args,
            fail_payload(
                "contract.summary",
                "MISSING_CONTRACT",
                f"contract artifact not found: {relpath(root, artifact)}",
            ),
        )
    _, contract = control_contract_document(artifact)
    if not isinstance(contract, dict):
        return emit_payload(
            args,
            fail_payload(
                "contract.summary",
                "INVALID_CONTRACT",
                f"contract artifact does not contain a control_contract block: {relpath(root, artifact)}",
            ),
        )
    return emit_payload(
        args,
        build_contract_summary_payload(root, mission_id, artifact, contract, fmt=getattr(args, "format", "json") or "json"),
    )


def cmd_contract_check_recheck_pending(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    if artifact is None or not artifact.exists():
        return emit_payload(
            args,
            fail_payload(
                "contract.check-recheck-pending",
                "MISSING_CONTRACT",
                f"contract artifact not found: {args.artifact}",
            ),
        )
    _, contract = control_contract_document(artifact)
    if not isinstance(contract, dict):
        return emit_payload(
            args,
            fail_payload(
                "contract.check-recheck-pending",
                "INVALID_CONTRACT",
                f"contract artifact does not contain a control_contract block: {relpath(root, artifact)}",
            ),
        )
    return emit_payload(args, build_recheck_pending_payload(root, artifact, contract))


def cmd_contract_check_disputes(args: argparse.Namespace) -> int:
    """改造④：扫 contract 的 disputes，报告需升级 Decision Gate 仲裁的有界反驳。

    status=open 且有证据引用且 round>=max-rounds 的反驳 → 升级用户仲裁；否则 PASS。
    主 Agent 在审查-修复循环中调用本命令判断是否该升级，不靠口头自觉。
    """
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    if artifact is None or not artifact.exists():
        return emit_payload(
            args,
            fail_payload("contract.check-disputes", "MISSING_CONTRACT", f"contract artifact not found: {args.artifact}"),
        )
    _, contract = control_contract_document(artifact)
    if not isinstance(contract, dict):
        return emit_payload(
            args,
            fail_payload("contract.check-disputes", "INVALID_CONTRACT", f"contract artifact does not contain a control_contract block: {relpath(root, artifact)}"),
        )
    max_rounds = int(getattr(args, "max_rounds", 2) or 2)
    signal = dispute_escalation_signal(contract, max_rounds=max_rounds)
    if not signal:
        return emit_payload(
            args,
            {"status": "PASS", "control": "contract.check-disputes", "escalation": None, "findings": []},
        )
    disputes = signal.get("disputes") or []
    findings = [
        {
            "level": "BLOCKED",
            "code": "dispute_needs_arbitration",
            "message": (
                f"反驳 gap={d.get('gap_id')} 对 reviewer={d.get('role')} 已达 {d.get('round')} 轮仍未一致，"
                f"超过上限 {max_rounds}：升级 Decision Gate 由用户仲裁，裁决经 harness clarification record / approval 落盘"
            ),
        }
        for d in disputes
    ]
    return emit_payload(
        args,
        {"status": "BLOCKED", "control": "contract.check-disputes", "escalation": signal, "findings": findings},
    )


def cmd_contract_patch(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    if artifact is None or not artifact.exists():
        return emit_payload(args, fail_payload("contract.patch", "missing_contract", f"Contract artifact not found: {args.artifact}"))

    add_round = bool(getattr(args, "add_round", False))
    patch_path = resolve_path(root, args.patch) if args.patch else None
    if not add_round and patch_path is None:
        return emit_payload(
            args,
            fail_payload(
                "contract.patch",
                "missing_contract_patch_input",
                "Provide --patch <manifest> or --add-round for the targeted shortcut",
            ),
        )

    patch_doc = None
    if patch_path is not None:
        if not patch_path.exists():
            return emit_payload(args, fail_payload("contract.patch", "missing_contract_patch_input", f"Patch manifest not found: {args.patch}"))
        patch_doc = load_manifest(patch_path)

    document = load_manifest(artifact)
    try:
        applied = apply_contract_patch(
            document,
            add_round=add_round,
            last_verdict=getattr(args, "last_verdict", None),
            patch_doc=patch_doc,
        )
    except ValueError as exc:
        return emit_payload(args, fail_payload("contract.patch", "invalid_contract_patch", str(exc)))

    write_manifest(artifact, document)
    return emit_payload(
        args,
        {"status": "PASS", "control": "contract.patch", "contract": relpath(root, artifact), "applied": applied, "findings": []},
    )


def cmd_contract_add_verdict(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    verdict_arg = getattr(args, "verdict_file", None) or getattr(args, "verdict", None)
    verdict_path = resolve_path(root, verdict_arg) if verdict_arg else None
    if artifact is None or verdict_path is None or not artifact.exists() or not verdict_path.exists():
        return emit_payload(args, fail_payload("contract.add_verdict", "missing_verdict_input", "Contract artifact and verdict manifest must both exist"))
    document, contract = control_contract_document(artifact)
    verdict = load_manifest(verdict_path)
    verdict = verdict.get("role_verdict") if isinstance(verdict.get("role_verdict"), dict) else verdict
    if not isinstance(verdict, dict) or not verdict.get("role") or not verdict.get("verdict"):
        return emit_payload(args, fail_payload("contract.add_verdict", "invalid_role_verdict", "Role verdict must be an object with role and verdict"))

    dispatch_reject = validate_role_verdict_dispatch(verdict)
    if dispatch_reject is not None:
        payload = fail_payload("contract.add_verdict", str(dispatch_reject["code"]), str(dispatch_reject["message"]))
        payload["findings"][0].update({key: value for key, value in dispatch_reject.items() if key not in {"code", "message"}})
        return emit_payload(args, payload)

    if not verdict.get("review_basis"):
        verdict["review_basis"] = [relpath(root, artifact)]

    try:
        action = add_role_verdict(contract, verdict)
    except ValueError as exc:
        return emit_payload(args, fail_payload("contract.add_verdict", "invalid_role_verdicts", str(exc)))
    write_manifest(artifact, document)
    return emit_payload(
        args,
        {"status": "PASS", "control": "contract.add_verdict", "contract": relpath(root, artifact), "action": action, "verdict": verdict, "findings": []},
    )


def cmd_contract_add_execution_result(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact = resolve_path(root, args.artifact)
    result_path = resolve_path(root, args.result)
    if artifact is None or result_path is None or not artifact.exists() or not result_path.exists():
        return emit_payload(args, fail_payload("contract.add_execution_result", "missing_execution_result_input", "Contract artifact and execution result manifest must both exist"))
    document, contract = control_contract_document(artifact)
    result = load_manifest(result_path)
    result = result.get("execution_result") if isinstance(result.get("execution_result"), dict) else result
    if not isinstance(result, dict) or not result.get("role") or not result.get("status"):
        return emit_payload(args, fail_payload("contract.add_execution_result", "invalid_execution_result", "execution_result must be an object with role and status"))

    used_list, count = add_execution_result(contract, result)
    write_manifest(artifact, document)
    payload = {
        "status": "PASS",
        "control": "contract.add_execution_result",
        "contract": relpath(root, artifact),
        "execution_result": result,
        "findings": [],
    }
    if used_list:
        payload["execution_results_count"] = count
    return emit_payload(args, payload)


def _code_review_contract_or_fail(args: argparse.Namespace, control: str) -> tuple[Path, dict[str, Any] | None, int | None]:
    root = Path(root_arg(args))
    artifact, contract, err = load_code_review_contract(root, args.mission)
    if err:
        return artifact, None, emit_payload(
            args,
            fail_payload(
                control,
                err,
                f"Cannot load code-review contract for mission {args.mission!r}: {err}",
            ),
        )
    return artifact, contract, None


def cmd_contract_add_round(args: argparse.Namespace) -> int:
    artifact, contract, fail = _code_review_contract_or_fail(args, "contract.add-round")
    if fail is not None:
        return fail
    assert contract is not None
    verdicts_raw = getattr(args, "verdicts", None)
    if verdicts_raw:
        try:
            verdicts = json.loads(verdicts_raw)
        except (json.JSONDecodeError, TypeError):
            verdicts = []
    else:
        verdicts = []
    rounds_used = archive_review_round(contract, timestamp=now_iso(), verdicts=verdicts)
    write_manifest(artifact, {"control_contract": contract})
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "contract.add-round",
            "mission": args.mission,
            "rounds_used": rounds_used,
            "findings": [],
        },
    )


def cmd_contract_check_finding_ownership(args: argparse.Namespace) -> int:
    _artifact, contract, fail = _code_review_contract_or_fail(args, "contract.check-finding-ownership")
    if fail is not None:
        return fail
    assert contract is not None
    violations = finding_ownership_violations(contract)
    status = "PASS" if not violations else "WARN"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "contract.check-finding-ownership",
            "mission": args.mission,
            "ownership_violations": len(violations),
            "findings": violations,
        },
    )


def cmd_contract_detect_conflicts(args: argparse.Namespace) -> int:
    _artifact, contract, fail = _code_review_contract_or_fail(args, "contract.detect-conflicts")
    if fail is not None:
        return fail
    assert contract is not None
    conflicts, warnings = detect_finding_conflicts(contract)
    all_findings = conflicts + warnings
    status = "FAIL" if conflicts else ("WARN" if warnings else "PASS")
    return emit_payload(
        args,
        {
            "status": status,
            "control": "contract.detect-conflicts",
            "mission": args.mission,
            "conflict_count": len(conflicts),
            "findings": all_findings,
        },
    )


def cmd_contract_check_acceptance_trace(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    artifact_arg = getattr(args, "artifact", None)
    upstream_arg = getattr(args, "upstream", None)

    _path, contract, err = resolve_verify_contract(root, mission, artifact_arg)
    if err or contract is None:
        return emit_payload(
            args,
            fail_payload("contract.check-acceptance-trace", err or "contract_unloadable", f"Cannot load verification contract for mission {mission}"),
        )

    _brief_path, brief, _brief_err = resolve_execution_brief_for_verify(root, mission, upstream_arg)
    return emit_payload(
        args,
        check_acceptance_trace_payload(mission, contract, valid_re_ids=required_evidence_ids(brief)),
    )
