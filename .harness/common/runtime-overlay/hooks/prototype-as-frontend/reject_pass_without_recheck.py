#!/usr/bin/env python3
"""prototype-as-frontend PreToolUse hook: reject recording a frontend-reviewer
PASS while prototype-as-frontend.contract.yaml has pending_reviewer_recheck=true.

本路线 PASS 由 `harness contract record-review ... --verdict PASS` 落盘（Bash 命令，
非 Write 产物文件），故守卫挂在 Bash 上，与 code-review 的 reject_pass_without_recheck
同义："改代码 → 旧 PASS 失效 → 必须重审才能再 PASS"。

镜像副本（活跃实现见 .harness/common/hooks/checks/prototype_as_frontend.py，
经 registry["interaction"] 路由）。

Exit conventions:
  0 — pass (not recording a PASS verdict to the prototype-as-frontend contract)
  2 — block (recording PASS while pending_reviewer_recheck=true)
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

_RECORD_REVIEW_RE = re.compile(r"\bharness\s+contract\s+record-review\b")
_VERDICT_PASS_RE = re.compile(r"--verdict[=\s]+PASS\b")
# 兼容 harness-runtime/harness/stages/... 短写、harness-runtime/harness/stages/... 全路径、
# harness-runtime/harness/harness/stages/... 历史变体。
_ARTIFACT_MISSION_RE = re.compile(
    r"(?:harness-runtime/)?harness-runtime/harness/(?:harness-runtime/harness/)?stages/([^/]+)/"
    r"contracts/prototype-as-frontend\.contract\.yaml"
)


def _extract_mission(command: str) -> str | None:
    match = _ARTIFACT_MISSION_RE.search(command.replace("\\", "/"))
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


def _pending(contract_path: Path) -> bool:
    if not contract_path.exists() or yaml is None:
        return False
    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return False
    if not isinstance(data, dict):
        return False
    contract = data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data
    if not isinstance(contract, dict):
        return False
    eff = contract.get("effectiveness_review")
    return bool(isinstance(eff, dict) and eff.get("pending_reviewer_recheck"))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command")
    if not isinstance(command, str):
        return 0
    if not _RECORD_REVIEW_RE.search(command) or not _VERDICT_PASS_RE.search(command):
        return 0

    mission_id = _extract_mission(command)
    if mission_id is None:
        return 0

    cwd = payload.get("cwd") or str(Path.cwd())
    contract_path = _contract_path(cwd, mission_id)
    if _pending(contract_path):
        print(
            f"HarnessV2 prototype-as-frontend hook BLOCKED: {contract_path.name} has "
            "pending_reviewer_recheck=true. Recording a frontend-reviewer PASS is not "
            "allowed until the reviewer has re-examined the changed frontend code. "
            "Re-run frontend-reviewer and clear the recheck flag first.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
