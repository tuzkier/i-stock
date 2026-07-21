"""Unit tests for contract patch helpers."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.contracts import apply_contract_patch  # noqa: E402


def test_apply_contract_patch_keeps_control_contract_targets_scoped() -> None:
    document = {"control_contract": {"status": "draft"}}
    patch = {"patches": [{"target": "status", "op": "set", "value": "ready"}]}

    try:
        apply_contract_patch(document, patch_doc=patch)
    except ValueError as exc:
        assert "patch target must be under control_contract" in str(exc)
    else:
        raise AssertionError("expected non-control_contract target to be rejected")


def test_apply_contract_patch_supports_legacy_top_level_contracts() -> None:
    document = {"stage": "finishing-branch", "branch_status": {"dirty": False}}
    patch = {
        "patches": [
            {
                "target": "branch_status",
                "op": "set",
                "value": {"dirty": True, "mission_branch": "dev/M-1"},
            }
        ]
    }

    applied = apply_contract_patch(document, patch_doc=patch)

    assert applied == [{"target": "branch_status", "op": "set"}]
    assert document["branch_status"] == {"dirty": True, "mission_branch": "dev/M-1"}
