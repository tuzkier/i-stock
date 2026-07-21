"""Pure helpers for the verify stage (verification-report contract + evidence shape)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


# Evidence kinds that count as real browser-path primary evidence for UI
# acceptance scenarios. API / DB / mock evidence can prepare or cross-check
# data but cannot be the primary result for a UI acceptance criterion.
BROWSER_PRIMARY_EVIDENCE_KINDS = {
    "dom",
    "dom_snapshot",
    "screenshot",
    "video",
    "trace",
    "accessibility_snapshot",
}

# Evidence kinds that must not be used as primary evidence for a UI
# acceptance scenario; they are allowed as auxiliary / parity evidence.
NON_UI_PRIMARY_EVIDENCE_KINDS = {
    "api",
    "api_response",
    "db",
    "database",
    "internal_state",
    "mock",
    "log",
}


def verify_report_path(root: Path, mission: str) -> Path:
    return (
        root
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission
        / "contracts"
        / "verification-report.contract.yaml"
    )


def resolve_verify_contract(
    root: Path, mission: str, artifact_arg: str | None = None
) -> tuple[Path, dict[str, Any] | None, str | None]:
    path = Path(artifact_arg) if artifact_arg else verify_report_path(root, mission)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        return path, None, "verification_report_contract_missing"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return path, None, "verification_report_contract_invalid_yaml"
    if not isinstance(doc, dict):
        return path, None, "verification_report_contract_invalid_root"
    contract = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
    if not isinstance(contract, dict):
        return path, None, "verification_report_contract_invalid_shape"
    return path, contract, None


def resolve_execution_brief_for_verify(
    root: Path, mission: str, upstream_arg: str | None = None
) -> tuple[Path, dict[str, Any] | None, str | None]:
    """Resolve execution-brief.contract.yaml for verify commands."""
    if upstream_arg:
        path = Path(upstream_arg)
        if not path.is_absolute():
            path = root / path
    else:
        path = (
            root
            / "harness-runtime"
            / "harness"
            / "stages"
            / mission
            / "contracts"
            / "execution-brief.contract.yaml"
        )
    if not path.exists():
        return path, None, "execution_brief_contract_missing"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return path, None, "execution_brief_contract_invalid_yaml"
    if not isinstance(doc, dict):
        return path, None, "execution_brief_contract_invalid_root"
    contract = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
    return path, contract, None


def evidence_role(ev: dict[str, Any]) -> str:
    return str(
        ev.get("evidence_role")
        or ev.get("role")
        or ev.get("purpose")
        or ""
    ).lower()


def is_ui_acceptance_trace(ac: dict[str, Any]) -> bool:
    return (
        str(ac.get("surface_type") or "").lower() == "ui"
        or bool(ac.get("ui_surface"))
        or str(ac.get("ac_type") or "").lower() == "ui"
    )
