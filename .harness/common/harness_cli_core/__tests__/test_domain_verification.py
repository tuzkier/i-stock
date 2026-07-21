"""Unit tests for `harness_cli_core.domain.verification`."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.verification import (  # noqa: E402
    BROWSER_PRIMARY_EVIDENCE_KINDS,
    NON_UI_PRIMARY_EVIDENCE_KINDS,
    evidence_role,
    is_ui_acceptance_trace,
    resolve_execution_brief_for_verify,
    resolve_verify_contract,
    verify_report_path,
)


def _write(root: Path, rel: str, body: str) -> Path:
    artifact = root / rel
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(body, encoding="utf-8")
    return artifact


# ---------------------------------------------------------------------------
# evidence kinds disjoint
# ---------------------------------------------------------------------------

def test_browser_and_non_ui_evidence_kinds_are_disjoint() -> None:
    assert not (BROWSER_PRIMARY_EVIDENCE_KINDS & NON_UI_PRIMARY_EVIDENCE_KINDS)


# ---------------------------------------------------------------------------
# evidence_role
# ---------------------------------------------------------------------------

def test_evidence_role_prefers_evidence_role_key_and_lowercases() -> None:
    assert evidence_role({"evidence_role": "PRIMARY"}) == "primary"


def test_evidence_role_falls_back_through_role_and_purpose() -> None:
    assert evidence_role({"role": "Assertion"}) == "assertion"
    assert evidence_role({"purpose": "user_path"}) == "user_path"


def test_evidence_role_empty_when_no_keys() -> None:
    assert evidence_role({}) == ""


# ---------------------------------------------------------------------------
# is_ui_acceptance_trace
# ---------------------------------------------------------------------------

def test_is_ui_acceptance_trace_recognises_surface_type() -> None:
    assert is_ui_acceptance_trace({"surface_type": "UI"})


def test_is_ui_acceptance_trace_recognises_ui_surface_truthy() -> None:
    assert is_ui_acceptance_trace({"ui_surface": "/dashboard"})


def test_is_ui_acceptance_trace_recognises_ac_type() -> None:
    assert is_ui_acceptance_trace({"ac_type": "ui"})


def test_is_ui_acceptance_trace_false_for_api_only() -> None:
    assert not is_ui_acceptance_trace({"surface_type": "api"})


# ---------------------------------------------------------------------------
# resolve_verify_contract
# ---------------------------------------------------------------------------

def test_resolve_verify_contract_missing(tmp_path: Path) -> None:
    artifact, contract, err = resolve_verify_contract(tmp_path, "M-1")
    assert contract is None
    assert err == "verification_report_contract_missing"
    assert artifact == verify_report_path(tmp_path, "M-1")


def test_resolve_verify_contract_invalid_yaml(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "harness-runtime/harness/stages/M-1/contracts/verification-report.contract.yaml",
        "control_contract: { not closed:",
    )
    _, contract, err = resolve_verify_contract(tmp_path, "M-1")
    assert contract is None
    assert err == "verification_report_contract_invalid_yaml"


def test_resolve_verify_contract_unwraps_control_contract(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "harness-runtime/harness/stages/M-1/contracts/verification-report.contract.yaml",
        "control_contract:\n  acceptance_trace: []\n",
    )
    _, contract, err = resolve_verify_contract(tmp_path, "M-1")
    assert err is None
    assert contract == {"acceptance_trace": []}


def test_resolve_verify_contract_accepts_explicit_artifact_arg(tmp_path: Path) -> None:
    artifact = _write(
        tmp_path,
        "custom/report.yaml",
        "control_contract:\n  acceptance_trace: []\n",
    )
    resolved, contract, err = resolve_verify_contract(tmp_path, "M-1", str(artifact))
    assert err is None
    assert contract == {"acceptance_trace": []}
    assert resolved == artifact


# ---------------------------------------------------------------------------
# resolve_execution_brief_for_verify
# ---------------------------------------------------------------------------

def test_resolve_execution_brief_missing(tmp_path: Path) -> None:
    _path, brief, err = resolve_execution_brief_for_verify(tmp_path, "M-1")
    assert brief is None
    assert err == "execution_brief_contract_missing"


def test_resolve_execution_brief_unwraps_control_contract(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "harness-runtime/harness/stages/M-1/contracts/execution-brief.contract.yaml",
        "control_contract:\n  tasks: []\n",
    )
    _path, brief, err = resolve_execution_brief_for_verify(tmp_path, "M-1")
    assert err is None
    assert brief == {"tasks": []}
