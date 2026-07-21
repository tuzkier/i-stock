"""Handlers for `harness evidence ...` commands.

Spans evidence-graph build/check (script shims), evidence add/link (direct
mutation of the per-mission evidence store), evidence command collect, and
evidence visual manifest generation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg, with_json
from harness_cli_core.domain.contracts import upsert_by_id
from harness_cli_core.domain.evidence import evidence_store_path, load_evidence_store
from harness_cli_core.domain.manifest import load_manifest, write_manifest
from harness_cli_core.infra.process import run_python
from harness_cli_core.infra.runtime_paths import relpath, resolve_path


COMMON_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = COMMON_ROOT / "skills"


def script(*parts: str) -> Path:
    return SKILLS_ROOT.joinpath(*parts)


def cmd_evidence_graph_check(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args), "--graph", args.graph]
    if args.current_git_ref:
        forwarded.extend(["--current-git-ref", args.current_git_ref])
    return run_python(script("stage-gate", "scripts", "check_evidence_graph.py"), with_json(args, forwarded))


def cmd_evidence_graph_build(args: argparse.Namespace) -> int:
    forwarded: list[str] = []
    for artifact in args.artifact or []:
        forwarded.extend(["--artifact", artifact])
    if args.mission:
        forwarded.extend(["--mission-id", args.mission])
    if args.evidence_store:
        forwarded.extend(["--evidence-store", args.evidence_store])
    elif args.mission:
        store = evidence_store_path(Path(root_arg(args)), args.mission)
        if store.exists():
            forwarded.extend(["--evidence-store", str(store)])
    if args.output:
        forwarded.extend(["--output", args.output])
    return run_python(script("stage-gate", "scripts", "evidence_graph.py"), with_json(args, forwarded))


def cmd_evidence_add(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    store_path = evidence_store_path(root, args.mission, args.store)
    store = load_evidence_store(store_path, args.mission)
    evidence_path = resolve_path(root, args.evidence)
    if evidence_path is None or not evidence_path.exists():
        return emit_payload(args, fail_payload("evidence.add", "missing_evidence_manifest", "Evidence manifest must exist"))
    evidence = load_manifest(evidence_path)
    evidence = evidence.get("evidence") if isinstance(evidence.get("evidence"), dict) else evidence
    if not isinstance(evidence, dict) or not evidence.get("id"):
        return emit_payload(args, fail_payload("evidence.add", "invalid_evidence", "Evidence manifest must be an object with id"))
    evidence.setdefault("mission_id", args.mission)
    action = upsert_by_id(store["evidence"], evidence)
    write_manifest(store_path, store)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "evidence.add",
            "store": relpath(root, store_path),
            "action": action,
            "evidence": evidence,
            "findings": [],
        },
    )


def cmd_evidence_link(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    store_path = evidence_store_path(root, args.mission, args.store)
    store = load_evidence_store(store_path, args.mission)
    evidence = next((item for item in store["evidence"] if str(item.get("id") or "") == args.from_id), None)
    if evidence is None:
        return emit_payload(args, fail_payload("evidence.link", "missing_evidence_node", f"Evidence node not found: {args.from_id}"))
    covers = evidence.setdefault("covers", {})
    if not isinstance(covers, dict):
        return emit_payload(args, fail_payload("evidence.link", "invalid_evidence_covers", "evidence.covers must be an object"))
    obligations = covers.setdefault("obligations", [])
    if not isinstance(obligations, list):
        return emit_payload(args, fail_payload("evidence.link", "invalid_evidence_obligations", "evidence.covers.obligations must be a list"))
    if args.to not in obligations:
        obligations.append(args.to)
    link = {"from": args.from_id, "to": args.to, "type": args.type}
    if link not in store["links"]:
        store["links"].append(link)
    write_manifest(store_path, store)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "evidence.link",
            "store": relpath(root, store_path),
            "link": link,
            "findings": [],
        },
    )


def cmd_evidence_command_collect(args: argparse.Namespace) -> int:
    forwarded = [
        "--cwd",
        str(Path(args.cwd).expanduser().resolve()) if args.cwd else root_arg(args),
    ]
    if args.timeout is not None:
        forwarded.extend(["--timeout", str(args.timeout)])
    if args.output_dir:
        forwarded.extend(["--output-dir", args.output_dir])
    if args.mission:
        forwarded.extend(["--mission-id", args.mission])
    if args.store:
        forwarded.extend(["--store", args.store])
    if args.no_run:
        forwarded.append("--no-run")
    return run_python(script("verify", "scripts", "collect_command_evidence.py"), with_json(args, forwarded))


def cmd_evidence_visual_manifest(args: argparse.Namespace) -> int:
    forwarded = [
        "--mission-id",
        args.mission,
        "--stage-dir",
        args.stage_dir,
    ]
    source_dirs = args.source_dir if isinstance(args.source_dir, list) else [args.source_dir]
    for source_dir in source_dirs:
        forwarded.extend(["--source-dir", source_dir])
    if args.copy:
        forwarded.append("--copy")
    if args.output:
        forwarded.extend(["--output", args.output])
    return run_python(script("visual-interaction-design", "scripts", "visual_manifest.py"), forwarded)
