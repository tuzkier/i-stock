from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.infra.runtime_paths import relpath


COMMON_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = COMMON_ROOT.parent


def project_context_path(root: Path) -> Path:
    return root / "project-context.md"


def project_context_template_path(root: Path) -> Path:
    for candidate in (
        root / "harness-runtime" / "templates" / "project-context.md",
        PACKAGE_ROOT / "harness-runtime" / "templates" / "project-context.md",
    ):
        if candidate.exists():
            return candidate
    return PACKAGE_ROOT / "harness-runtime" / "templates" / "project-context.md"


def cmd_context_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    path = project_context_path(root)
    exists = path.exists()
    payload: dict[str, object] = {
        "status": "PASS" if exists else "FAIL",
        "control": "context.check",
        "project_context_path": relpath(root, path),
        "exists": exists,
        "findings": [] if exists else [
            {
                "level": "FAIL",
                "code": "project_context_missing",
                "message": "project-context.md is not present; run 'harness context init' to create it from template, or record the absence as evidence.",
            }
        ],
    }
    return emit_payload(args, payload)


def cmd_context_init(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    target = project_context_path(root)
    if target.exists() and not args.replace:
        return emit_payload(args, fail_payload("context.init", "project_context_exists", f"project-context.md already exists: {relpath(root, target)}; pass --replace to overwrite"))
    template = project_context_template_path(root)
    if not template.exists():
        return emit_payload(args, fail_payload("context.init", "missing_project_context_template", f"project-context template not found: {template}"))
    target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "context.init",
            "project_context_path": relpath(root, target),
            "template": relpath(root, template),
            "findings": [],
        },
    )
