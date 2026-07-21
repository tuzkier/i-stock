#!/usr/bin/env python3
"""verify M3.1 PreToolUse hook: block verification-engineer from writing
files outside the allowed write_scope.

Allowed paths (default; project may extend via allow_extra_write_paths in
the effective-overlay or verification-report.contract.yaml
evidence_path_lock):
  - harness-runtime/harness/stages/*/verification-report.md
  - harness-runtime/harness/stages/*/contracts/verification-report.contract.yaml
  - harness-runtime/harness/traces/**
  - harness-runtime/harness/approvals.json
  - Any path listed in verification-report.contract.yaml evidence_path_lock
    .allowed_write_paths[]

Writes to src/** and tests/** are always blocked (use failure_path
hook require_failure_path.py for that path — this hook focuses on the
positive scope enforcement for the worker).

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

_DEFAULT_ALLOWED: list[str] = [
    "harness-runtime/harness/stages/*/verification-report.md",
    "harness-runtime/harness/stages/*/contracts/verification-report.contract.yaml",
    "harness-runtime/harness/traces/**",
    "harness-runtime/harness/approvals.json",
    "harness-runtime/harness/stages/*/contracts/",
]

_WORKER_FLAG_GLOB = "harness-runtime/harness/stages/*/traces/worker_turn.flag"

# Paths that are unconditionally allowed (Harness meta-files, temp files, etc.)
_ALWAYS_ALLOWED_PREFIXES = (
    ".harness/",
    ".claude/",
    ".cursor/",
    "/tmp/",
    "tmp/",
)


def _match_any(file_path: str, patterns: list[str]) -> bool:
    norm = file_path.lstrip("./")
    for pat in patterns:
        pat_norm = pat.lstrip("./")
        if fnmatch.fnmatch(norm, pat_norm) or fnmatch.fnmatch(file_path, pat_norm):
            return True
        # also try with harness-runtime prefix stripped
        if norm.startswith("harness-runtime/"):
            stripped = norm[len("harness-runtime/"):]
            if fnmatch.fnmatch(stripped, pat_norm):
                return True
    return False


def _is_worker_context(payload: dict, cwd: Path) -> bool:
    agent_ctx = payload.get("agent_context") or {}
    if isinstance(agent_ctx, dict):
        agent_id = (
            agent_ctx.get("agent_id") or agent_ctx.get("subagent_type") or ""
        ).lower().replace("-", "").replace("_", "")
        if agent_id in {"verificationengineer", "verification-engineer".replace("-", "")}:
            return True
    for flag_path in cwd.glob(_WORKER_FLAG_GLOB):
        if flag_path.exists():
            return True
    return False


def _load_extra_allowed(cwd: Path) -> list[str]:
    """Load evidence_path_lock.allowed_write_paths from verification contract."""
    extra: list[str] = []
    if yaml is None:
        return extra
    for contract_path in cwd.glob(
        "harness-runtime/harness/stages/*/contracts/verification-report.contract.yaml"
    ):
        try:
            data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        doc = data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data
        lock = doc.get("evidence_path_lock") if isinstance(doc.get("evidence_path_lock"), dict) else {}
        for p in lock.get("allowed_write_paths") or []:
            if isinstance(p, str):
                extra.append(p)
    return extra


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        return 0
    cwd = Path(payload.get("cwd") or ".")
    if not _is_worker_context(payload, cwd):
        return 0
    # Always-allowed prefixes (harness meta, tooling config)
    norm_fp = file_path.lstrip("./")
    for prefix in _ALWAYS_ALLOWED_PREFIXES:
        if norm_fp.startswith(prefix.lstrip("./")):
            return 0
    extra = _load_extra_allowed(cwd)
    allowed = _DEFAULT_ALLOWED + extra
    if _match_any(file_path, allowed):
        return 0
    print(
        "HarnessV2 verify hook BLOCKED (WORKER_WRITE_SCOPE_VIOLATION): "
        f"verification-engineer is not permitted to write {file_path!r}. "
        "Allowed paths: verification-report.md, verification-report.contract.yaml, "
        "traces/**, approvals.json, and evidence_path_lock.allowed_write_paths. "
        "If a code fix is needed, record a failure_path via "
        "`harness verify failure-path --kind bug_fix --json` first.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
