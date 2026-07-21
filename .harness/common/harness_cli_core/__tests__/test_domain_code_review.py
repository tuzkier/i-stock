"""Unit tests for `harness_cli_core.domain.code_review`."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.code_review import (  # noqa: E402
    ALWAYS_ENABLED_REVIEWERS,
    REVIEWER_TRIGGER_MAP,
    select_reviewers,
)
from harness_cli_core.domain.contracts import (  # noqa: E402
    code_review_contract_path,
    load_code_review_contract as resolve_code_review_contract,
)


# ---------------------------------------------------------------------------
# select_reviewers
# ---------------------------------------------------------------------------

def test_select_reviewers_always_enabled_with_no_features() -> None:
    selected, excluded = select_reviewers([])
    selected_roles = {item["role"] for item in selected}
    assert selected_roles == set(ALWAYS_ENABLED_REVIEWERS)
    assert all(item["reason"] == "always_enabled" for item in selected)
    excluded_roles = {item["role"] for item in excluded}
    # everything else must be excluded with reason=no_trigger
    expected_excluded = {
        role for roles in REVIEWER_TRIGGER_MAP.values() for role in roles
    } - set(ALWAYS_ENABLED_REVIEWERS)
    assert excluded_roles == expected_excluded


def test_select_reviewers_auth_feature_triggers_security_reviewer() -> None:
    selected, _excluded = select_reviewers(["auth"])
    roles = {item["role"]: item["reason"] for item in selected}
    assert "security-reviewer" in roles
    assert roles["security-reviewer"] == "diff_trigger"
    # always-enabled reviewers still present
    for role in ALWAYS_ENABLED_REVIEWERS:
        assert role in roles
        assert roles[role] == "always_enabled"


def test_select_reviewers_multiple_features_union_triggers() -> None:
    selected, _excluded = select_reviewers(["ui", "migration"])
    roles = {item["role"] for item in selected}
    assert "interaction-reviewer" in roles  # ui
    assert "data-engineer" in roles  # migration


def test_select_reviewers_substring_match_keeps_keyword_lookup_simple() -> None:
    """`select_reviewers` uses `keyword in feature`, so "auth_changes" still
    triggers `security-reviewer`. Pin that behavior."""
    selected, _excluded = select_reviewers(["auth_changes"])
    roles = {item["role"] for item in selected}
    assert "security-reviewer" in roles


# ---------------------------------------------------------------------------
# resolve_code_review_contract
# ---------------------------------------------------------------------------

def _write_contract(root: Path, mission: str, body: str) -> Path:
    artifact = code_review_contract_path(root, mission)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(body, encoding="utf-8")
    return artifact


def test_resolve_code_review_contract_returns_missing_when_absent(tmp_path: Path) -> None:
    artifact, contract, error = resolve_code_review_contract(tmp_path, "M-1")
    assert contract is None
    assert error == "code_review_contract_missing"
    assert artifact == code_review_contract_path(tmp_path, "M-1")


def test_resolve_code_review_contract_returns_invalid_yaml(tmp_path: Path) -> None:
    _write_contract(tmp_path, "M-1", "control_contract: { unterminated:")
    _, contract, error = resolve_code_review_contract(tmp_path, "M-1")
    assert contract is None
    assert error == "code_review_contract_invalid_yaml"


def test_resolve_code_review_contract_coerces_non_mapping_root_to_empty(
    tmp_path: Path,
) -> None:
    """`load_code_review_contract` goes through `load_manifest`, which silently
    coerces non-mapping YAML into ``{}``. That makes the
    ``code_review_contract_invalid_root`` branch effectively unreachable from
    this entrypoint. The test pins the current behavior so future tightening
    is a deliberate change."""
    _write_contract(tmp_path, "M-1", "42")
    _, contract, error = resolve_code_review_contract(tmp_path, "M-1")
    assert contract == {}
    assert error is None


def test_resolve_code_review_contract_unwraps_control_contract(tmp_path: Path) -> None:
    _write_contract(
        tmp_path,
        "M-1",
        "control_contract:\n  findings: []\n  effectiveness_review:\n    pending_reviewer_recheck: false\n",
    )
    _, contract, error = resolve_code_review_contract(tmp_path, "M-1")
    assert error is None
    assert contract is not None
    assert contract["findings"] == []
    assert contract["effectiveness_review"]["pending_reviewer_recheck"] is False


def test_resolve_code_review_contract_accepts_top_level_shape(tmp_path: Path) -> None:
    _write_contract(tmp_path, "M-1", "findings: []\n")
    _, contract, error = resolve_code_review_contract(tmp_path, "M-1")
    assert error is None
    assert contract == {"findings": []}
