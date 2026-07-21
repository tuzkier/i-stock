#!/usr/bin/env python3
"""HarnessV2 discovery PreToolUse hook: enforce graphify brownfield evidence.

Triggered on PreToolUse(Edit|Write|MultiEdit) when the AI is about to write
`harness-runtime/harness/artifacts/<mission_id>/discovery/discovery-brief.md`.

Discovery workflow Step 2 declares: brownfield missions MUST have at least
one graphify query / context recorded before the brief is written, OR the
brief's external contract.yaml MUST list a `graphify_unavailable` /
`graphify_stale` degradation. Without either, the brief is built on grep-only
evidence and downstream reviewer / lint cannot trust the affected_capabilities
section.

The hook reads two on-disk signals:

1. `graphify-out/` directory presence + freshness → if absent, the mission is
   treated as not-brownfield (greenfield path); hook is a no-op.
2. `harness-runtime/harness/stages/<mission_id>/contracts/discovery-brief.contract.yaml`
   → checks `existing_solutions[].source` for any graphify_* entry OR
   `degradations[].kind` for graphify_unavailable / graphify_stale.

Exit conventions: 0 = allow; 2 = block.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML always available in runtime
    yaml = None

_DISCOVERY_BRIEF_PATH_RE = re.compile(
    r"harness-runtime/harness/stages/(?P<mission>[^/]+)/discovery-brief\.md$"
)
_GRAPHIFY_INDEX_FRESH_HOURS = 24


def _resolve_target_path(payload: dict) -> str | None:
    tool_input = payload.get("tool_input") or {}
    for key in ("file_path", "filePath", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return None


def _is_brownfield(cwd: Path) -> bool:
    """Brownfield ≡ a populated graphify-out/ index exists at the project root."""
    graphify = cwd / "graphify-out"
    if not graphify.exists() or not graphify.is_dir():
        return False
    try:
        return any(graphify.iterdir())
    except OSError:
        return False


def _contract_has_graphify_evidence(contract_path: Path) -> tuple[bool, str]:
    """Return (ok, reason). ok=True if contract carries either a graphify_*
    existing_solutions[].source entry or a degradations[] graphify_unavailable
    / graphify_stale record (so the brownfield gap is at least acknowledged)."""
    if yaml is None or not contract_path.exists():
        return False, "contract.yaml not yet materialized; run `harness contract fill --template discovery-brief` first."
    try:
        document = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return False, f"contract.yaml is not valid YAML: {exc}"
    contract = document.get("control_contract")
    if not isinstance(contract, dict):
        return False, "contract.yaml is missing `control_contract:` root."

    existing = contract.get("existing_solutions") or []
    if isinstance(existing, list):
        for item in existing:
            if isinstance(item, dict) and str(item.get("source", "")).startswith("graphify"):
                return True, "graphify_* source recorded in existing_solutions[]"

    degradations = contract.get("degradations") or []
    if isinstance(degradations, list):
        for item in degradations:
            if isinstance(item, dict) and item.get("kind") in {"graphify_unavailable", "graphify_stale"}:
                return True, f"{item.get('kind')} recorded in degradations[]"

    return False, (
        "brownfield mission but contract.yaml lacks graphify_* in existing_solutions[] "
        "AND no graphify_unavailable/graphify_stale in degradations[]; either run graphify "
        "queries first or record the degradation explicitly."
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") not in {"Edit", "Write", "MultiEdit"}:
        return 0

    target = _resolve_target_path(payload)
    if target is None:
        return 0

    cwd = Path(payload.get("cwd") or Path.cwd()).resolve()
    try:
        rel = str(Path(target).resolve().relative_to(cwd))
    except (ValueError, OSError):
        rel = target

    match = _DISCOVERY_BRIEF_PATH_RE.search(rel)
    if not match:
        return 0

    if not _is_brownfield(cwd):
        return 0

    mission = match.group("mission")
    contract_path = cwd / "harness-runtime" / "harness" / "stages" / mission / "contracts" / "discovery-brief.contract.yaml"
    ok, reason = _contract_has_graphify_evidence(contract_path)
    if ok:
        return 0

    print(
        f"HarnessV2 discovery hook BLOCKED: brownfield mission {mission!r} cannot write "
        f"{rel} without graphify evidence. {reason}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
