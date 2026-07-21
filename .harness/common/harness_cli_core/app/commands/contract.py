from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ContractCommandHandlers:
    init: Callable[[argparse.Namespace], int]
    fill: Callable[[argparse.Namespace], int]
    patch: Callable[[argparse.Namespace], int]
    add_verdict: Callable[[argparse.Namespace], int]
    add_execution_result: Callable[[argparse.Namespace], int]
    check: Callable[[argparse.Namespace], int]
    summary: Callable[[argparse.Namespace], int]
    check_recheck_pending: Callable[[argparse.Namespace], int]
    add_round: Callable[[argparse.Namespace], int]
    record_review: Callable[[argparse.Namespace], int]
    check_finding_ownership: Callable[[argparse.Namespace], int]
    detect_conflicts: Callable[[argparse.Namespace], int]
    check_acceptance_trace: Callable[[argparse.Namespace], int]
    check_disputes: Callable[[argparse.Namespace], int]


def register_contract_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: ContractCommandHandlers,
) -> argparse.ArgumentParser:
    contract = subparsers.add_parser("contract")
    contract_sub = contract.add_subparsers(dest="contract_command", required=True)
    p = add_leaf(contract_sub, "init", handlers.init)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--node")
    p.add_argument("--template", required=True)
    p.add_argument("--artifact-version", default="v1")
    p.add_argument("--review-strategy")
    p.add_argument("--capability")
    p.add_argument("--output")
    p.add_argument("--replace", action="store_true")
    p = add_leaf(contract_sub, "fill", handlers.fill)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--artifact", required=True, help="Path to control contract YAML (auto-init from --template if missing)")
    p.add_argument("--intent-framing", required=True, help="YAML manifest with objective/user_stories/scope/acceptance_scenarios/work_graph/autonomy_level; see harness-runtime/templates/contracts/intent-framing.example.yaml")
    p.add_argument("--template", help="Contract template name (e.g. mission-contract); only used when --artifact does not yet exist")
    p = add_leaf(contract_sub, "patch", handlers.patch)
    p.add_argument("--artifact", required=True)
    p.add_argument("--patch", help="Path to a YAML manifest with {patches:[{target: control_contract.X.Y, op: set|merge|append, value: ...}]}. For business fields prefer `harness contract fill`.")
    p.add_argument("--add-round", action="store_true", help="M4.3 shortcut: increment control_contract.effectiveness_review.rounds_used by 1. Combine with --last-verdict to record the verdict at that round.")
    p.add_argument("--last-verdict", help="Record control_contract.effectiveness_review.last_verdict in tandem with --add-round (PASS / HOLD / PASS_WITH_RISK / BLOCKED).")
    p = add_leaf(contract_sub, "add-verdict", handlers.add_verdict)
    p.add_argument("--artifact", required=True)
    p.add_argument("--verdict")
    p.add_argument("--verdict-file")
    p = add_leaf(contract_sub, "add-execution-result", handlers.add_execution_result)
    p.add_argument("--artifact", required=True)
    p.add_argument("--result", required=True)
    p = add_leaf(contract_sub, "check", handlers.check)
    p.add_argument("--artifact", required=True)
    p.add_argument("--upstream", action="append")
    p.add_argument("--allow-placeholders", action="store_true")
    p = add_leaf(contract_sub, "summary", handlers.summary)
    p.add_argument("--mission", required=True)
    p.add_argument("--artifact", help="optional explicit contract path; defaults to harness-runtime/harness/missions/<id>/contracts/mission-contract.contract.yaml")
    p.add_argument("--format", choices=["user", "json"], default="json")
    p = add_leaf(contract_sub, "check-recheck-pending", handlers.check_recheck_pending)
    p.add_argument("--artifact", required=True)
    p = add_leaf(contract_sub, "add-round", handlers.add_round)
    p.add_argument("--mission", required=True)
    p.add_argument("--verdicts", help="JSON array of verdict objects for this round")
    p = add_leaf(contract_sub, "record-review", handlers.record_review)
    p.add_argument("--artifact", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--verdict", required=True, choices=["PASS", "PASS_WITH_RISK", "HOLD", "BLOCKED"])
    p.add_argument("--reviewed-obligation", action="append")
    p.add_argument("--review-basis", action="append")
    p.add_argument("--subagent-id", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--summary", required=True)
    p = add_leaf(contract_sub, "check-finding-ownership", handlers.check_finding_ownership)
    p.add_argument("--mission", required=True)
    p = add_leaf(contract_sub, "detect-conflicts", handlers.detect_conflicts)
    p.add_argument("--mission", required=True)
    p = add_leaf(contract_sub, "check-acceptance-trace", handlers.check_acceptance_trace)
    p.add_argument("--mission", required=True)
    p.add_argument("--artifact", help="Path to verification-report.contract.yaml; defaults to harness-runtime/harness/stages/<mission>/contracts/...")
    p.add_argument("--upstream", help="Path to execution-brief.contract.yaml for required_evidence_id cross-check; omit to skip H3 primary key validation")
    # 改造④：扫 effectiveness_review.disputes，命中 status=open 且 round>=max-rounds 的有证据反驳 → 需升级 Decision Gate 仲裁。
    p = add_leaf(contract_sub, "check-disputes", handlers.check_disputes)
    p.add_argument("--artifact", required=True)
    p.add_argument("--max-rounds", type=int, default=2, help="反驳轮次上限，达到即建议升级用户仲裁（默认 2，对齐 Capio 三轮上限）")
    return contract
