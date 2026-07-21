#!/usr/bin/env python3
"""prototype-as-frontend PostToolUse hook: set
prototype-as-frontend.contract.yaml pending_reviewer_recheck=true after any
frontend-changeset.md edit.

frontend_engineering 路线（stage=interaction）改前端工程代码时，强制以
frontend-changeset.md 作为本轮改动载体（workflow 步骤 5）。改了变更清单就置脏
契约的 effectiveness_review.pending_reviewer_recheck，让旧 frontend-reviewer PASS
失效，必须重审才能再 record-review PASS。

镜像副本（活跃实现见 .harness/common/hooks/checks/prototype_as_frontend.py，
经 registry["interaction"] 路由）。

Exit conventions: 0 = always (PostToolUse hooks are advisory).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

_CHANGESET_PATH_RE = re.compile(
    r"harness-runtime/harness/stages/([^/]+)/frontend-changeset\.md$"
)


def _extract_mission_from_path(path: str) -> str | None:
    match = _CHANGESET_PATH_RE.search(path.replace("\\", "/"))
    return match.group(1) if match else None


def _contract_path(cwd: str, mission_id: str) -> Path:
    return (
        Path(cwd)
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "contracts"
        / "prototype-as-frontend.contract.yaml"
    )


def _set_pending(contract_path: Path) -> None:
    if not contract_path.exists() or yaml is None:
        return
    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return
    if not isinstance(data, dict):
        return
    contract = data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data
    if not isinstance(contract, dict):
        return
    eff = contract.setdefault("effectiveness_review", {})
    if isinstance(eff, dict):
        eff["pending_reviewer_recheck"] = True
    try:
        contract_path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    except OSError:
        return


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name")
    if tool_name not in {"Edit", "Write", "MultiEdit"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not isinstance(file_path, str):
        return 0

    mission_id = _extract_mission_from_path(file_path)
    if not mission_id:
        return 0

    cwd = payload.get("cwd") or str(Path.cwd())
    _set_pending(_contract_path(cwd, mission_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
