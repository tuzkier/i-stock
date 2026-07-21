from __future__ import annotations

import argparse
from pathlib import Path


def add_common(parser: argparse.ArgumentParser, *, json_default: bool = False) -> None:
    parser.add_argument("--root", default=None, help="target project root; defaults to the global --root")
    if json_default:
        parser.set_defaults(json=True)
    else:
        parser.add_argument("--json", action="store_true", help="emit JSON when the wrapped command supports it")


def root_arg(args: argparse.Namespace) -> str:
    return str(Path(args.root or args.global_root).expanduser().resolve())


def with_json(args: argparse.Namespace, forwarded: list[str]) -> list[str]:
    if getattr(args, "json", False):
        forwarded.append("--json")
    return forwarded
"""Application-facing CLI concerns: parser wiring and response emission."""
