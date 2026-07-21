"""Handler for `harness mission artifacts-append` typed action shim.

PT-CLI-EXTEND-03: records an `index_artifact` typed action intent for a
RuntimeArtifact bound to a Mission. Enforces the 6-kind closed set
(text / code / config / log / metric / external_link, DATA-05).

Lives in its own module (rather than `mission_handlers.py`) because the
artifact-append command is a CLI Bridge persistence boundary, not a Mission
state-machine helper.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from harness_cli_core.app.commands.agent_handlers import (
    AGENT_DISPATCH_EXIT_OK,
    AGENT_DISPATCH_EXIT_WORKSPACE_LOCK,
)
from harness_cli_core.domain.runs import (
    append_control_event,
    workspace_initialized,
    workspace_runtime_dir,
)


ARTIFACT_KIND_CLOSED_SET = ("text", "code", "config", "log", "metric", "external_link")


def cmd_mission_artifacts_append(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    if not workspace_initialized(workspace):
        sys.stderr.write(
            f"workspace_lock: harness-runtime not initialized at {workspace_runtime_dir(workspace)}\n"
        )
        return AGENT_DISPATCH_EXIT_WORKSPACE_LOCK

    artifact_id = f"art-{uuid.uuid4().hex[:16]}"
    append_control_event(
        workspace,
        kind="index_artifact",
        filename="artifact-index.jsonl",
        extra={
            "artifact_id": artifact_id,
            "mission_id": args.mission,
            "artifact_kind": args.kind,
            "artifact_path": args.path,
        },
    )
    sys.stdout.write(
        json.dumps(
            {
                "artifact_id": artifact_id,
                "mission_id": args.mission,
                "kind": args.kind,
                "path": args.path,
            },
            ensure_ascii=False,
        )
        + "\n"
    )
    return AGENT_DISPATCH_EXIT_OK
