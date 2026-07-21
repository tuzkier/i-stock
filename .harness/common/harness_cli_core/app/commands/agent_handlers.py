"""Handlers for `harness agent ...` typed action shims.

PT-CLI-EXTEND-01: `harness agent dispatch` is the TheForce CLI Bridge
persistence boundary — it appends a `dispatch_agent_run` intent to the target
workspace's runtime ledger and emits a `{run_id, status}` JSON envelope on
stdout. Adapter execution itself happens server-side.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from harness_cli_core.domain.runs import (
    append_control_event,
    new_run_id,
    workspace_initialized,
    workspace_runtime_dir,
)


AGENT_DISPATCH_EXIT_OK = 0
AGENT_DISPATCH_EXIT_ARG_INVALID = 2
AGENT_DISPATCH_EXIT_WORKSPACE_LOCK = 5
AGENT_DISPATCH_EXIT_ADAPTER_UNAVAILABLE = 9


def cmd_agent_dispatch(args: argparse.Namespace) -> int:
    """Record a dispatch_agent_run intent.

    Exit codes (consumed by the CLI Bridge for blocker emission):
      0  dispatch intent recorded
      2  argparse contract violation (handled by argparse before this runs)
      5  workspace lock or runtime not initialized
      9  adapter unavailable (env-controlled simulation for CLI Bridge tests)
    """
    workspace = Path(args.workspace)
    if not workspace_initialized(workspace):
        sys.stderr.write(
            f"workspace_lock: harness-runtime not initialized at {workspace_runtime_dir(workspace)}\n"
        )
        return AGENT_DISPATCH_EXIT_WORKSPACE_LOCK

    if os.environ.get("THEFORCE_ADAPTER_AVAILABILITY") == "none":
        sys.stderr.write(
            f"adapter_unavailable: backend={args.backend} is not currently dispatchable\n"
        )
        return AGENT_DISPATCH_EXIT_ADAPTER_UNAVAILABLE

    run_id = new_run_id()
    append_control_event(
        workspace,
        kind="dispatch_agent_run",
        filename="dispatch-intents.jsonl",
        extra={
            "run_id": run_id,
            "workspace_path": str(workspace),
            "mission_id": args.mission,
            "backend": args.backend,
            "permission_mode": args.permission,
        },
    )

    payload = {
        "run_id": run_id,
        "status": "queued",
        "mission_id": args.mission,
        "backend": args.backend,
        "permission_mode": args.permission,
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return AGENT_DISPATCH_EXIT_OK
