from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class MissionCommandHandlers:
    init: Callable[[argparse.Namespace], int]
    create_slice: Callable[[argparse.Namespace], int]
    status: Callable[[argparse.Namespace], int]
    reset_stage: Callable[[argparse.Namespace], int]
    stage_start: Callable[[argparse.Namespace], int]
    stage_complete: Callable[[argparse.Namespace], int]
    close: Callable[[argparse.Namespace], int]
    new_id: Callable[[argparse.Namespace], int]
    artifacts: Callable[[argparse.Namespace], int]
    document: Callable[[argparse.Namespace], int]
    retrospective_data: Callable[[argparse.Namespace], int]
    artifacts_append: Callable[[argparse.Namespace], int]


def register_mission_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: MissionCommandHandlers,
) -> argparse.ArgumentParser:
    mission = subparsers.add_parser("mission")
    mission_sub = mission.add_subparsers(dest="mission_command", required=True)
    p = add_leaf(mission_sub, "init", handlers.init)
    p.add_argument("--replace", action="store_true")
    p = add_leaf(mission_sub, "create-slice", handlers.create_slice)
    p.add_argument("--mission", required=True)
    p.add_argument("--primary-node", action="append", required=True)
    p.add_argument("--related-node", action="append")
    p.add_argument("--input-node", action="append")
    p.add_argument("--output-node", action="append")
    p.add_argument("--lane-action", required=True)
    p.add_argument("--objective")
    p.add_argument("--title", help="deprecated alias for --objective")
    p.add_argument("--operation", help="operation name, such as advance_lane; defaults to the lane action registration")
    p.add_argument("--graph-operation", help="deprecated: operation name or graph operation manifest path")
    p.add_argument("--graph-operation-manifest", help="path to an explicit graph operation manifest")
    p.add_argument("--replace", action="store_true")
    p = add_leaf(mission_sub, "status", handlers.status)
    p.add_argument("--mission")
    p.add_argument("--active", action="store_true", help="only return missions with an active Mission Slice")
    p.add_argument("--open", dest="open_only", action="store_true", help="only return missions whose status is not closed")
    p.add_argument("--status", dest="status_filter", action="append", help="filter by mission status; may be repeated")
    p.add_argument("--current-stage", action="append", help="filter by current_stage; may be repeated")
    p.add_argument("--stage", action="append", help="filter by a key in stages; may be repeated")
    p.add_argument("--stage-status", action="append", help="filter by stage status, optionally combined with --stage")
    p.add_argument("--ids-only", action="store_true", help="return matching mission ids without mission payloads")
    p = add_leaf(mission_sub, "reset-stage", handlers.reset_stage)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--primary-node", action="append")
    p.add_argument("--related-node", action="append")
    p.add_argument("--output-node-policy", choices=["keep", "defer", "prune"], default="defer")
    p.add_argument("--preserve-stage-history", action="store_true")
    p.add_argument("--preserve-checkpoints", action="store_true")
    p.add_argument("--reason", default="Mission reset by harness mission reset-stage")
    mission_stage = mission_sub.add_parser("stage")
    mission_stage_sub = mission_stage.add_subparsers(dest="mission_stage_command", required=True)
    p = add_leaf(mission_stage_sub, "start", handlers.stage_start)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p = add_leaf(mission_stage_sub, "complete", handlers.stage_complete)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p = add_leaf(mission_sub, "close", handlers.close)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--strategy",
        required=True,
        choices=["merged", "pr", "kept", "discarded", "delivered", "cancelled", "manual"],
        help=(
            "Close strategy. New values: merged | pr | kept | discarded. "
            "Legacy aliases: delivered (→merged) | cancelled (→discarded) | manual (→kept)."
        ),
    )
    p.add_argument("--pr-url", dest="pr_url", help="PR URL when strategy=pr.")
    p.add_argument("--kept-reason", dest="kept_reason", help="Reason string when strategy=kept.")
    p = add_leaf(mission_sub, "new-id", handlers.new_id)
    p.add_argument("--slug", required=True, help="short kebab-case identifier (lowercase ASCII letters, digits, hyphens)")
    p.add_argument("--date", help="optional YYYYMMDD override; defaults to today's date in Asia/Shanghai")
    p = add_leaf(mission_sub, "artifacts", handlers.artifacts)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", help="Filter artifacts to a specific stage subdirectory.")
    p = add_leaf(mission_sub, "document", handlers.document)
    p.add_argument("--mission", required=True)
    p.add_argument("--type", required=True, help="Document type such as task-order, product-definition, solution, tech-design")
    p = add_leaf(mission_sub, "retrospective-data", handlers.retrospective_data)
    p.add_argument("--mission", required=True)
    p = add_leaf(
        mission_sub,
        "artifacts-append",
        handlers.artifacts_append,
        description=(
            "Record an index_artifact typed action intent into the workspace runtime ledger. "
            "Enforces the 6-kind closed set: text / code / config / log / metric / external_link."
        ),
    )
    p.add_argument("--workspace", required=True, help="Absolute path to the target workspace root")
    p.add_argument("--mission", required=True, help="Mission id receiving the artifact")
    p.add_argument("--kind", required=True, choices=["text", "code", "config", "log", "metric", "external_link"])
    p.add_argument("--path", required=True, help="Filesystem path or external URL of the artifact")
    return mission
