"""Handlers for `harness gate ...` commands.

`gate run` is the only non-trivial command in this family: it optionally
materializes the contract-check JSON via a sub-script before invoking
``render_gate_report.py``. The remaining commands are thin script shims.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from harness_cli_core.app.parser import root_arg, with_json
from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.infra.process import run_python, run_python_capture


COMMON_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = COMMON_ROOT / "skills"


def script(*parts: str) -> Path:
    return SKILLS_ROOT.joinpath(*parts)


def cmd_gate_advance(args: argparse.Namespace) -> int:
    forwarded = [
        "--root",
        root_arg(args),
        "--mission-id",
        args.mission,
        "--gate-report",
        args.gate_report,
    ]
    if args.contract_artifact:
        forwarded.extend(["--contract-artifact", args.contract_artifact])
    if args.allow_warnings:
        forwarded.append("--allow-warnings")
    return run_python(
        script("board-router", "scripts", "advance_after_gate.py"),
        with_json(args, forwarded),
    )


def cmd_gate_run(args: argparse.Namespace) -> int:
    temp_path: Path | None = None
    contract_check_json = args.contract_check_json
    if not args.mission_slice:
        print(
            "harness gate run: --mission-slice is required so Gate reports are bound to a Work Graph Mission Slice",
            file=sys.stderr,
        )
        return 64
    if not contract_check_json:
        contract_artifact = args.contract_artifact or args.artifact
        if not contract_artifact:
            print("harness gate run: --artifact, --contract-artifact, or --contract-check-json is required", file=sys.stderr)
            return 64
        check_cmd = [
            sys.executable,
            str(script("stage-gate", "scripts", "check_contracts.py")),
            "--root",
            root_arg(args),
            "--artifact",
            contract_artifact,
            "--json",
        ]
        if args.allow_placeholders:
            check_cmd.append("--allow-placeholders")
        for upstream in args.upstream or []:
            check_cmd.extend(["--upstream", upstream])
        check_result = subprocess.run(
            check_cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check_result.stderr:
            print(check_result.stderr, end="", file=sys.stderr)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".json", delete=False
        ) as handle:
            handle.write(check_result.stdout)
            temp_path = Path(handle.name)
        contract_check_json = str(temp_path)
        if check_result.returncode not in {0, 1}:
            return check_result.returncode
    forwarded = [
        "--root",
        root_arg(args),
        "--contract-check-json",
        contract_check_json,
        "--mission-id",
        args.mission,
        "--from-stage",
        args.stage,
        "--to-stage",
        args.to_stage or args.stage,
    ]
    if args.mission_slice:
        forwarded.extend(["--mission-slice", args.mission_slice])
    for report in args.control_report or []:
        forwarded.extend(["--control-report", report])
    for control in args.required_control or []:
        forwarded.extend(["--required-control", control])
    for checkpoint in args.required_checkpoint or []:
        forwarded.extend(["--required-checkpoint", checkpoint])
    for checkpoint in args.human_checkpoint or []:
        forwarded.extend(["--human-checkpoint", checkpoint])
    interpretation = (args.ai_interpretation or "").strip()
    skip_reason = (getattr(args, "no_interpretation", None) or "").strip()
    if interpretation and skip_reason:
        print(
            "harness gate run: --ai-interpretation and --no-interpretation are mutually exclusive",
            file=sys.stderr,
        )
        return 2
    if not interpretation and not skip_reason:
        print(
            "harness gate run: --ai-interpretation is required so the gate report records why this decision is justified; "
            "pass --no-interpretation \"<reason>\" to opt out (e.g. automated reruns).",
            file=sys.stderr,
        )
        return 2
    if interpretation:
        forwarded.extend(["--ai-interpretation", interpretation])
    else:
        forwarded.extend(["--ai-interpretation", f"[omitted] {skip_reason}"])
    if args.output_dir:
        forwarded.extend(["--output-dir", args.output_dir])
    if args.artifact:
        forwarded.extend(["--stage-artifact", args.artifact])
    if args.contract_artifact:
        forwarded.extend(["--contract-artifact", args.contract_artifact])
    try:
        result = run_python_capture(
            script("stage-gate", "scripts", "render_gate_report.py"),
            forwarded,
        )
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.stdout:
            print(result.stdout, end="")
        if result.returncode != 0:
            return result.returncode
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return 64
        if payload.get("gate_effect") in {"block", "pause"} or payload.get("decision") == "cannot_continue":
            return 1
        return 0
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)


def cmd_gate_transition(args: argparse.Namespace) -> int:
    root = Path(root_arg(args)).resolve()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
        temp_contract_check = Path(handle.name)
        json.dump({"status": "PASS", "findings": []}, handle, ensure_ascii=False)
    try:
        render_args = [
            "--root",
            str(root),
            "--contract-check-json",
            str(temp_contract_check),
            "--mission-id",
            args.mission,
            "--from-stage",
            args.stage,
            "--to-stage",
            args.to_stage or args.stage,
            "--mission-slice",
            args.mission_slice,
            "--ai-interpretation",
            args.ai_interpretation,
            "--output-dir",
            str(root / "harness-runtime" / "harness" / "state" / "gate-reports"),
        ]
        if args.contract_artifact:
            render_args.extend(["--contract-artifact", args.contract_artifact])
        render_result = run_python_capture(script("stage-gate", "scripts", "render_gate_report.py"), render_args)
        if render_result.returncode != 0:
            return emit_payload(
                args,
                fail_payload("gate.transition", "gate_run_failed", render_result.stderr or render_result.stdout),
            )
        gate_run = json.loads(render_result.stdout)
        gate_report = gate_run.get("json")
        advance_args = [
            sys.executable,
            str(script("board-router", "scripts", "advance_after_gate.py")),
            "--root",
            str(root),
            "--mission-id",
            args.mission,
            "--gate-report",
            str(gate_report),
            "--json",
        ]
        if args.contract_artifact:
            advance_args.extend(["--contract-artifact", args.contract_artifact])
        if args.allow_warnings:
            advance_args.append("--allow-warnings")
        advance_result = subprocess.run(advance_args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if advance_result.returncode != 0:
            return emit_payload(
                args,
                fail_payload("gate.transition", "gate_advance_failed", advance_result.stderr or advance_result.stdout),
            )
        gate_advance = json.loads(advance_result.stdout)

        select_args = [
            sys.executable,
            str(script("board-router", "scripts", "select_next_node.py")),
            "--root",
            str(root),
            "--mission-id",
            args.mission,
            "--json",
        ]
        for node_id in args.primary_node or []:
            select_args.extend(["--primary-node", node_id])
        for node_id in args.related_node or []:
            select_args.extend(["--related-node", node_id])
        select_result = subprocess.run(select_args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if select_result.returncode != 0:
            return emit_payload(
                args,
                fail_payload("gate.transition", "board_select_failed", select_result.stderr or select_result.stdout),
            )
        board_select = json.loads(select_result.stdout)
        return emit_payload(
            args,
            {
                "status": "PASS",
                "control": "gate.transition",
                "mission_id": args.mission,
                "gate_run": gate_run,
                "gate_advance": gate_advance,
                "board_select": board_select,
                "findings": [],
            },
        )
    finally:
        temp_contract_check.unlink(missing_ok=True)


def cmd_gate_report_render(args: argparse.Namespace) -> int:
    forwarded = [
        "--root",
        root_arg(args),
        "--contract-check-json",
        args.contract_check_json,
        "--mission-id",
        args.mission,
        "--from-stage",
        args.from_stage,
        "--to-stage",
        args.to_stage,
    ]
    if args.mission_slice:
        forwarded.extend(["--mission-slice", args.mission_slice])
    for report in args.control_report or []:
        forwarded.extend(["--control-report", report])
    for control in args.required_control or []:
        forwarded.extend(["--required-control", control])
    for checkpoint in args.required_checkpoint or []:
        forwarded.extend(["--required-checkpoint", checkpoint])
    for checkpoint in args.human_checkpoint or []:
        forwarded.extend(["--human-checkpoint", checkpoint])
    interpretation = (args.ai_interpretation or "").strip()
    skip_reason = (getattr(args, "no_interpretation", None) or "").strip()
    if interpretation and skip_reason:
        print(
            "harness gate report render: --ai-interpretation and --no-interpretation are mutually exclusive",
            file=sys.stderr,
        )
        return 2
    if not interpretation and not skip_reason:
        print(
            "harness gate report render: --ai-interpretation is required; pass --no-interpretation \"<reason>\" to opt out.",
            file=sys.stderr,
        )
        return 2
    if interpretation:
        forwarded.extend(["--ai-interpretation", interpretation])
    else:
        forwarded.extend(["--ai-interpretation", f"[omitted] {skip_reason}"])
    if args.output_dir:
        forwarded.extend(["--output-dir", args.output_dir])
    return run_python(
        script("stage-gate", "scripts", "render_gate_report.py"),
        forwarded,
    )


def cmd_gate_control_reports(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args)]
    if args.mission:
        forwarded.extend(["--mission-id", args.mission])
    for report in args.report or []:
        forwarded.extend(["--report", report])
    for control in args.required_control or []:
        forwarded.extend(["--required-control", control])
    return run_python(
        script("stage-gate", "scripts", "check_control_reports.py"),
        with_json(args, forwarded),
    )
