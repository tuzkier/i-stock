"""任务 #2：verify gate 纳入 reviewer role_verdict=HOLD/BLOCKED 的 domain 测试。

覆盖 evaluate_reviewer_verdicts_for_gate 纯函数：
- contract 无 role_verdicts → 不受影响（空结果）。
- 有 HOLD → failed_check。
- 有 PASS → 通过。
- 有 HOLD 但有 approval → 降级为 warning。
以及 mission_has_tradeoff_approval 的 approvals.json 解析。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.contracts import (  # noqa: E402
    evaluate_reviewer_verdicts_for_gate,
    mission_has_tradeoff_approval,
)


# ---------------------------------------------------------------------------
# evaluate_reviewer_verdicts_for_gate — 非破坏路径
# ---------------------------------------------------------------------------

def test_none_contract_is_noop() -> None:
    result = evaluate_reviewer_verdicts_for_gate(None)
    assert result == {"failed_checks": [], "warnings": []}


def test_contract_without_role_verdicts_is_noop() -> None:
    result = evaluate_reviewer_verdicts_for_gate({"mission_id": "m1"})
    assert result["failed_checks"] == []
    assert result["warnings"] == []


def test_role_verdicts_not_a_list_is_noop() -> None:
    result = evaluate_reviewer_verdicts_for_gate({"role_verdicts": "broken"})
    assert result == {"failed_checks": [], "warnings": []}


def test_non_reviewer_role_ignored() -> None:
    # 非 reviewer 角色（不以 -reviewer / -effectiveness-reviewer 结尾）即便 HOLD 也不纳入。
    contract = {"role_verdicts": [{"role": "backend-engineer", "verdict": "HOLD"}]}
    result = evaluate_reviewer_verdicts_for_gate(contract)
    assert result["failed_checks"] == []


# ---------------------------------------------------------------------------
# evaluate_reviewer_verdicts_for_gate — 阻断 / 通过 / 豁免
# ---------------------------------------------------------------------------

def test_reviewer_hold_produces_failed_check() -> None:
    contract = {
        "role_verdicts": [
            {"id": "rv1", "role": "correctness-reviewer", "verdict": "HOLD"},
        ]
    }
    result = evaluate_reviewer_verdicts_for_gate(contract)
    assert len(result["failed_checks"]) == 1
    fc = result["failed_checks"][0]
    assert fc["check"] == "reviewer_verdict_open"
    assert fc["code"] == "REVIEWER_VERDICT_HOLD"
    assert fc["role"] == "correctness-reviewer"
    assert fc["verdict"] == "HOLD"
    assert result["warnings"] == []


def test_reviewer_blocked_produces_failed_check() -> None:
    contract = {"role_verdicts": [{"role": "security-reviewer", "verdict": "BLOCKED"}]}
    result = evaluate_reviewer_verdicts_for_gate(contract)
    assert len(result["failed_checks"]) == 1
    assert result["failed_checks"][0]["verdict"] == "BLOCKED"


def test_reviewer_pass_passes() -> None:
    contract = {"role_verdicts": [{"role": "tdd-reviewer", "verdict": "PASS"}]}
    result = evaluate_reviewer_verdicts_for_gate(contract)
    assert result["failed_checks"] == []
    assert result["warnings"] == []


def test_reviewer_pass_with_risk_does_not_block_gate() -> None:
    contract = {"role_verdicts": [{"role": "architecture-reviewer", "verdict": "PASS_WITH_RISK"}]}
    result = evaluate_reviewer_verdicts_for_gate(contract)
    assert result["failed_checks"] == []


def test_reviewer_hold_with_approval_downgrades_to_warning() -> None:
    contract = {"role_verdicts": [{"role": "correctness-reviewer", "verdict": "HOLD"}]}
    result = evaluate_reviewer_verdicts_for_gate(contract, has_tradeoff_approval=True)
    assert result["failed_checks"] == []
    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["role"] == "correctness-reviewer"
    assert result["warnings"][0]["verdict"] == "HOLD"


def test_latest_verdict_per_role_wins() -> None:
    # 同一角色多条，后者覆盖前者：HOLD 之后跟 PASS → 不阻断。
    contract = {
        "role_verdicts": [
            {"id": "rv1", "role": "correctness-reviewer", "verdict": "HOLD"},
            {"id": "rv2", "role": "correctness-reviewer", "verdict": "PASS"},
        ]
    }
    result = evaluate_reviewer_verdicts_for_gate(contract)
    assert result["failed_checks"] == []


# ---------------------------------------------------------------------------
# mission_has_tradeoff_approval
# ---------------------------------------------------------------------------

def _write_approvals(root: Path, entries: list[dict]) -> None:
    state_dir = root / "harness-runtime" / "harness" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "approvals.json").write_text(
        json.dumps({"approvals": entries}), encoding="utf-8"
    )


def test_approval_missing_file_returns_false(tmp_path: Path) -> None:
    assert mission_has_tradeoff_approval(tmp_path, "m1") is False


def test_approval_no_mission_returns_false(tmp_path: Path) -> None:
    assert mission_has_tradeoff_approval(tmp_path, None) is False
    assert mission_has_tradeoff_approval(tmp_path, "") is False


def test_approval_present_returns_true(tmp_path: Path) -> None:
    _write_approvals(
        tmp_path,
        [{"mission_id": "m1", "type": "tradeoff", "status": "approved"}],
    )
    assert mission_has_tradeoff_approval(tmp_path, "m1") is True


def test_approval_risk_type_also_counts(tmp_path: Path) -> None:
    _write_approvals(
        tmp_path,
        [{"mission_id": "m1", "type": "risk", "status": "approved"}],
    )
    assert mission_has_tradeoff_approval(tmp_path, "m1") is True


def test_approval_wrong_mission_or_status_returns_false(tmp_path: Path) -> None:
    _write_approvals(
        tmp_path,
        [
            {"mission_id": "other", "type": "tradeoff", "status": "approved"},
            {"mission_id": "m1", "type": "tradeoff", "status": "pending"},
        ],
    )
    assert mission_has_tradeoff_approval(tmp_path, "m1") is False
