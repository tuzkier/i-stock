"""finishing-branch legacy contract checks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))
CHECK_SCRIPTS = COMMON_ROOT / "skills" / "stage-gate" / "scripts"
if str(CHECK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CHECK_SCRIPTS))

import check_contracts as cc  # noqa: E402


def _legacy_contract() -> dict:
    return {
        "stage": "finishing-branch",
        "mission_id": "M-1",
        "branch_status": {"mission_branch": "dev/M-1", "base_branch": "main"},
        "release_readiness": {"delivery_package": "delivery-package.md"},
        "test_evidence": {"command": "python3 -m pytest -q", "exit_code": 0},
        "close_choice": {"strategy": "push_pr", "selected_by": "user"},
        "git_ops": [
            {
                "op": "push",
                "command": "git push origin dev/M-1",
                "executed": True,
                "exit_code": 0,
            }
        ],
        "pr_body": {"required": True, "pr_url": "http://bitbucket/pr/1"},
        "mission_close": {"close_strategy": "pr", "branch_closed": False},
        "effectiveness_review": {"last_gate_run_status": "preflight_pass"},
    }


def test_legacy_finishing_branch_contract_passes(tmp_path: Path) -> None:
    artifact = tmp_path / "finishing-branch.contract.yaml"
    artifact.write_text(yaml.safe_dump(_legacy_contract(), allow_unicode=True), encoding="utf-8")

    status, findings, contract = cc.run(
        argparse.Namespace(
            artifact=str(artifact),
            root=str(tmp_path),
            upstream=[],
            allow_placeholders=False,
        )
    )

    assert status == "PASS"
    assert contract and contract["stage"] == "finishing-branch"
    assert [finding.code for finding in findings] == ["contract_valid"]


def test_legacy_finishing_branch_contract_requires_final_choice(tmp_path: Path) -> None:
    contract = _legacy_contract()
    contract["close_choice"]["strategy"] = "pending_user_choice"
    artifact = tmp_path / "finishing-branch.contract.yaml"
    artifact.write_text(yaml.safe_dump(contract, allow_unicode=True), encoding="utf-8")

    status, findings, _ = cc.run(
        argparse.Namespace(
            artifact=str(artifact),
            root=str(tmp_path),
            upstream=[],
            allow_placeholders=False,
        )
    )

    assert status == "FAIL"
    assert any(finding.code == "close_choice_pending" for finding in findings)
