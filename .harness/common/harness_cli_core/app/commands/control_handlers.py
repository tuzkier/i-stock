from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.control_candidates import build_continue_candidates
from harness_cli_core.domain.control_context import build_context_index
from harness_cli_core.domain.control_frame import build_control_frame
from harness_cli_core.domain.control_guidance import build_control_guidance
from harness_cli_core.domain.control_status import collect_control_status
from harness_cli_core.infra.runtime_layout import resolve_runtime_layout


def cmd_control_status(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    layout = resolve_runtime_layout(root, explicit_runtime=getattr(args, "runtime_root", None))
    payload = collect_control_status(root, layout, mission=args.mission)
    payload["control"] = "control.status"
    return emit_payload(args, payload)


def cmd_control_candidates(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    if args.intent != "continue":
        return emit_payload(args, fail_payload("control.candidates", "unsupported_intent", f"unsupported control candidate intent: {args.intent}"))
    layout = resolve_runtime_layout(root, explicit_runtime=getattr(args, "runtime_root", None))
    payload = build_continue_candidates(root, layout, mission=args.mission)
    payload["control"] = "control.candidates"
    payload["intent"] = args.intent
    return emit_payload(args, payload)


def cmd_control_frame(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    layout = resolve_runtime_layout(root, explicit_runtime=getattr(args, "runtime_root", None))
    payload = build_control_frame(root, layout, args.mission)
    payload["control"] = "control.frame"
    return emit_payload(args, payload)


def cmd_control_guidance(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    layout = resolve_runtime_layout(root, explicit_runtime=getattr(args, "runtime_root", None))
    payload = build_control_guidance(root, layout, args.mission)
    payload["control"] = "control.guidance"
    return emit_payload(args, payload)


def cmd_control_context_index(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    layout = resolve_runtime_layout(root, explicit_runtime=getattr(args, "runtime_root", None))
    payload = build_context_index(root, layout, args.mission)
    payload["control"] = "control.context-index"
    return emit_payload(args, payload)
