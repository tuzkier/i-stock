"""Handlers for `harness run cancel|retry` typed action shims.

PT-CLI-EXTEND-02: cancel / retry CLI Bridge shims for the AgentRun
lifecycle typed actions. INV-09 (retry never overwrites the old Run);
SOL-RISK-002 / SCN-RUN-CANCEL-DEGRADE (cancel degrades honestly when the
backend cannot natively cancel).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from harness_cli_core.app.commands.agent_handlers import (
    AGENT_DISPATCH_EXIT_OK,
    AGENT_DISPATCH_EXIT_WORKSPACE_LOCK,
)
from harness_cli_core.domain.runs import (
    append_control_event,
    new_run_id,
    workspace_initialized,
    workspace_runtime_dir,
)


def cmd_run_cancel(args: argparse.Namespace) -> int:
    """Record a `cancel_run` typed action intent.

    When the targeted Run's backend cannot honor cancel natively (CLI Bridge
    sets THEFORCE_ADAPTER_CANCEL_SUPPORT=none), degrade to
    `cancellation_requested` and surface `capability_downgrade=true` so the UI
    can show an honest capability snapshot (SOL-RISK-002,
    SCN-RUN-CANCEL-DEGRADE). Exit code remains 0 in the degrade path;
    consumers read `status`.
    """
    workspace = Path(args.workspace)
    if not workspace_initialized(workspace):
        sys.stderr.write(
            f"workspace_lock: harness-runtime not initialized at {workspace_runtime_dir(workspace)}\n"
        )
        return AGENT_DISPATCH_EXIT_WORKSPACE_LOCK

    cancel_support = os.environ.get("THEFORCE_ADAPTER_CANCEL_SUPPORT", "full")
    degraded = cancel_support == "none"
    status = "cancellation_requested" if degraded else "cancelled"

    append_control_event(
        workspace,
        kind="cancel_run",
        filename="cancel-intents.jsonl",
        extra={
            "run_id": args.run,
            "status": status,
            "capability_downgrade": degraded,
        },
    )

    payload: dict[str, object] = {
        "run_id": args.run,
        "status": status,
    }
    if degraded:
        payload["capability_downgrade"] = True
        payload["reason"] = "backend_cancel_unsupported"
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return AGENT_DISPATCH_EXIT_OK


def cmd_run_retry(args: argparse.Namespace) -> int:
    """Record a `retry_run` typed action intent.

    Allocates a NEW run_id (INV-09: the old AgentRun must never be
    overwritten) and links the new run back to the original via `retry_of`.
    Emits `{new_run_id, retry_of, status}` on stdout.
    """
    workspace = Path(args.workspace)
    if not workspace_initialized(workspace):
        sys.stderr.write(
            f"workspace_lock: harness-runtime not initialized at {workspace_runtime_dir(workspace)}\n"
        )
        return AGENT_DISPATCH_EXIT_WORKSPACE_LOCK

    new_id = new_run_id()
    append_control_event(
        workspace,
        kind="retry_run",
        filename="retry-intents.jsonl",
        extra={
            "run_id": new_id,
            "retry_of": args.run,
            "status": "queued",
        },
    )
    payload = {
        "new_run_id": new_id,
        "retry_of": args.run,
        "status": "queued",
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return AGENT_DISPATCH_EXIT_OK
